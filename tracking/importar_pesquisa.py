"""Importa a pesquisa inteira (``reports/experiments/`` da dissertação) para um MLflow local.

Complementa :mod:`tracking.importar_runs` (que serve ao portfólio e ao CI e não é alterado): este módulo
lê **todas** as entradas de um diretório de resultados, cada uma classificada num catálogo YAML
(papel, motivo, fonte, revisado), e as organiza em runs mães, runs filhas e runs de análise.
Nada é recalculado: só se copiam números e arquivos já existentes, e os arquivos de origem são
abertos apenas para leitura.

Como rodar (a partir da raiz do repositório)::

    uv run python -m tracking.importar_pesquisa \\
        --results-dir D:/Project/dataspell_workspace_template/reports/experiments \\
        --catalogo D:/Project/mlflow_pesquisa/catalogo_runs.yaml \\
        --tracking-uri sqlite:///D:/Project/mlflow_pesquisa/mlflow.db \\
        --artifact-root D:/Project/mlflow_pesquisa/artifacts

Catálogo (YAML): ``{"entradas": [ {run_id, tipo, familia, base, papel, motivo, fonte, revisado}, ... ]}``,
uma entrada por item do diretório de resultados. ``tipo`` é ``run`` (pasta com ``metrics.json``),
``pasta`` (pasta sem ``metrics.json``) ou ``arquivo`` (arquivo solto na raiz; exige ``grupo``, e os
arquivos do mesmo grupo viram uma única run). O importador falha alto se um item do diretório não
estiver no catálogo, se o catálogo citar item inexistente, se o ``tipo`` não bater com o disco ou se
faltar chave.

Organização no MLflow
---------------------
* **Runs do benchmark** (``tipo: run``) vão para o experimento ``<familia>/<base>`` — bases nunca se
  misturam no mesmo experimento (PROTOCOLO §0.16). Cada pasta vira:

  - uma **run mãe** (nome = id da pasta) com as tags do catálogo (``papel``, ``motivo``, ``fonte``,
    ``revisado``, ``familia``, ``base``), ``run_id``, ``commit``, ``git_sujo``, ``modo``, ``status``,
    ``horizonte``, ``alvo``, ``provisorio=true``, a nota da run gerada do catálogo, params
    ``experimento.*``/``split.*``, os arquivos de dados do manifesto como *datasets* de entrada e os
    arquivos da pasta como artefatos (``predictions.csv`` só com ``--com-previsoes``);
  - **runs filhas** aninhadas (tag ``mlflow.parentRunId``), uma por (modelo, conjunto de features),
    com params, métricas agregadas e por fold (``step=fold``) exatamente como em
    :mod:`tracking.importar_runs` (mesmos nomes; NaN fica NaN). Exceção documentada: nas runs de
    julho/2026 cujo ``por_fold`` não tem a coluna ``seed`` (uma semente só), a métrica por fold se
    chama ``por_fold/<métrica>`` e a run ganha a tag ``por_fold_sem_semente=true``.

* **Pastas sem métricas** (análises, testes DM, runs interrompidas) e **grupos de arquivos soltos**:
  uma run única, sem filhas, no experimento ``analises`` (ou ``interrompidas`` quando
  ``papel: interrompida``), com as tags do catálogo e todos os arquivos como artefatos; arquivos
  acima de 20 MB não são copiados e ficam listados na tag ``arquivos_omitidos``.

* **Datasets**: cada arquivo de dados do manifesto (``dataset_sih``, ``dataset_cams``,
  ``dataset_cetesb``, ``dataset_meteo``) entra como input da run mãe com nome = caminho (barras
  normalizadas para ``/``) e digest = sha256 do manifesto. O MLflow 3.18 limita o digest a 36
  caracteres: o digest é o **prefixo de 36 caracteres** do sha256, e o sha256 inteiro vai no
  ``profile`` do dataset e na tag de input ``sha256``.

* **Idempotente**: antes de criar, procura (em todos os experimentos ativos) uma run com a tag
  ``run_id``. Se ela existe e está completa, pula — e, se ``papel``/``motivo``/``fonte``/``revisado``
  mudaram no catálogo, atualiza essas tags (e a nota) na mãe e nas filhas. Importação incompleta ou
  experimento diferente do esperado falham alto. ``--recriar`` apaga (soft delete) e recria;
  ``mlflow gc`` expurga as apagadas.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# isort: off
# importar_runs primeiro: define MLFLOW_ALLOW_FILE_STORE e MLFLOW_DISABLE_AGENT_HINT antes de o mlflow carregar.
from tracking import importar_runs as base
from mlflow import MlflowClient
from mlflow.entities import Dataset, DatasetInput, InputTag, Metric, Param, RunTag
from mlflow.store.tracking.sqlalchemy_store import SqlAlchemyStore

# isort: on

ErroImportacao = base.ErroImportacao

PAPEIS = (
    "valida",
    "contraste",
    "diagnostico",
    "registro",
    "provisoria",
    "interrompida",
    "smoke",
    "triagem",
    "analise",
    "a_classificar",
)
TIPOS = ("run", "pasta", "arquivo")
CHAVES_CATALOGO = ("run_id", "tipo", "familia", "base", "papel", "motivo", "fonte", "revisado")
TAGS_SINCRONIZAVEIS = ("papel", "motivo", "fonte", "revisado")
DATASETS_MANIFESTO = ("sih", "cams", "cetesb", "meteo")
LIMITE_ARTEFATO_MB = 20.0
EXPERIMENTO_ANALISES = "analises"
EXPERIMENTO_INTERROMPIDAS = "interrompidas"
PREVISOES = "predictions.csv"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_DIGEST = 36  # mlflow.utils.validation.MAX_DATASET_DIGEST_SIZE no MLflow 3.18


# ----------------------------------------------------------------------------------------------
# Catálogo
# ----------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class EntradaCatalogo:
    run_id: str
    tipo: str
    familia: str
    base: str
    papel: str
    motivo: str
    fonte: str
    revisado: bool
    grupo: str | None = None

    def tags(self) -> dict[str, str]:
        return {
            "papel": self.papel,
            "motivo": self.motivo,
            "fonte": self.fonte,
            "revisado": "true" if self.revisado else "false",
            "familia": self.familia,
            "base": self.base,
        }

    def nota(self, extra: str = "") -> str:
        revisao = "revisado pelo pesquisador" if self.revisado else "NÃO revisado pelo pesquisador (revisado: false)"
        texto = (
            f"**Papel:** {self.papel} — {self.motivo}\n\n"
            f"**Fonte da classificação:** {self.fonte or '(nenhuma)'}\n\n"
            f"**Catálogo:** {revisao}. O MLflow é índice: valem os artefatos da run, os configs, o PROTOCOLO e o CHANGELOG."
        )
        return f"{texto}\n\n{extra}" if extra else texto


@dataclass(frozen=True)
class Unidade:
    """O que vira uma run MLflow de topo: uma pasta de run, uma pasta sem métricas ou um grupo de arquivos."""

    nome: str  # valor da tag run_id
    tipo: str  # run | pasta | arquivo
    entrada: EntradaCatalogo  # para grupos, a primeira entrada (todas têm de concordar)
    caminhos: tuple[Path, ...]  # pasta (run/pasta) ou arquivos (grupo)

    @property
    def experimento(self) -> str:
        if self.tipo == "run":
            return f"{self.entrada.familia}/{self.entrada.base}"
        return EXPERIMENTO_INTERROMPIDAS if self.entrada.papel == "interrompida" else EXPERIMENTO_ANALISES


def _texto(valor: Any, chave: str, rid: str) -> str:
    if not isinstance(valor, str) or (chave not in ("fonte",) and not valor.strip()):
        raise ErroImportacao(f"catálogo, entrada {rid!r}: '{chave}' deveria ser texto não vazio, veio {valor!r}")
    return valor


def carregar_catalogo(caminho: Path | str) -> dict[str, EntradaCatalogo]:
    caminho = Path(caminho)
    if not caminho.is_file():
        raise ErroImportacao(f"catálogo não encontrado: {caminho}")
    with caminho.open(encoding="utf-8") as fh:
        doc = yaml.safe_load(fh)
    if not isinstance(doc, dict) or not isinstance(doc.get("entradas"), list):
        raise ErroImportacao(f"{caminho}: esperava um mapa com a lista 'entradas'")
    catalogo: dict[str, EntradaCatalogo] = {}
    for i, bruto in enumerate(doc["entradas"]):
        if not isinstance(bruto, dict):
            raise ErroImportacao(f"{caminho}: entrada {i} não é um mapa")
        rid = bruto.get("run_id", f"#{i}")
        faltando = [c for c in CHAVES_CATALOGO if c not in bruto]
        if faltando:
            raise ErroImportacao(f"catálogo, entrada {rid!r}: faltam chaves {faltando}")
        rid = _texto(bruto["run_id"], "run_id", rid)
        if rid in catalogo:
            raise ErroImportacao(f"catálogo: run_id duplicado {rid!r}")
        tipo, papel = bruto["tipo"], bruto["papel"]
        if tipo not in TIPOS:
            raise ErroImportacao(f"catálogo, entrada {rid!r}: tipo {tipo!r} fora de {TIPOS}")
        if papel not in PAPEIS:
            raise ErroImportacao(f"catálogo, entrada {rid!r}: papel {papel!r} fora de {PAPEIS}")
        if not isinstance(bruto["revisado"], bool):
            raise ErroImportacao(f"catálogo, entrada {rid!r}: 'revisado' deveria ser booleano")
        grupo = bruto.get("grupo")
        if tipo == "arquivo":
            grupo = _texto(grupo, "grupo", rid)
            base._validar_tag(grupo, "grupo", rid)
        else:
            base._validar_tag(rid, "run_id", rid)
        catalogo[rid] = EntradaCatalogo(
            run_id=rid,
            tipo=tipo,
            familia=_texto(bruto["familia"], "familia", rid),
            base=_texto(bruto["base"], "base", rid),
            papel=papel,
            motivo=_texto(bruto["motivo"], "motivo", rid),
            fonte=_texto(bruto["fonte"], "fonte", rid),
            revisado=bruto["revisado"],
            grupo=grupo,
        )
    if not catalogo:
        raise ErroImportacao(f"{caminho}: catálogo vazio")
    return catalogo


def montar_unidades(results_dir: Path, catalogo: dict[str, EntradaCatalogo]) -> list[Unidade]:
    """Cruza o diretório com o catálogo (falha alto em qualquer divergência) e agrupa em unidades."""
    if not results_dir.is_dir():
        raise ErroImportacao(f"diretório de resultados não encontrado: {results_dir}")
    itens = {p.name: p for p in results_dir.iterdir()}
    fora = sorted(set(itens) - set(catalogo))
    if fora:
        raise ErroImportacao(f"{len(fora)} itens de {results_dir} fora do catálogo: {fora}")
    inexistentes = sorted(set(catalogo) - set(itens))
    if inexistentes:
        raise ErroImportacao(f"o catálogo cita {len(inexistentes)} itens inexistentes em {results_dir}: {inexistentes}")

    unidades: list[Unidade] = []
    grupos: dict[str, list[EntradaCatalogo]] = {}
    for nome in sorted(itens):
        caminho, entrada = itens[nome], catalogo[nome]
        if caminho.is_file():
            real = "arquivo"
        elif (caminho / "metrics.json").is_file():
            real = "run"
        else:
            real = "pasta"
        if entrada.tipo != real:
            raise ErroImportacao(f"catálogo diz tipo {entrada.tipo!r} para {nome!r}, mas no disco é {real!r}")
        if real == "arquivo":
            grupos.setdefault(entrada.grupo, []).append(entrada)
        else:
            unidades.append(Unidade(nome=nome, tipo=real, entrada=entrada, caminhos=(caminho,)))
    for grupo, entradas in sorted(grupos.items()):
        if grupo in itens:
            raise ErroImportacao(f"grupo {grupo!r} colide com um item de mesmo nome em {results_dir}")
        ref = entradas[0]
        for e in entradas[1:]:
            if (e.familia, e.base, e.papel, e.motivo, e.fonte, e.revisado) != (
                ref.familia,
                ref.base,
                ref.papel,
                ref.motivo,
                ref.fonte,
                ref.revisado,
            ):
                raise ErroImportacao(f"grupo {grupo!r}: entradas {ref.run_id!r} e {e.run_id!r} divergem no catálogo")
        unidades.append(
            Unidade(
                nome=grupo,
                tipo="arquivo",
                entrada=ref,
                caminhos=tuple(itens[e.run_id] for e in entradas),
            )
        )
    return unidades


def filtrar_unidades(unidades: list[Unidade], pedidos: list[str] | None) -> list[Unidade]:
    if not pedidos:
        return unidades
    por_nome = {u.nome: u for u in unidades}
    por_arquivo = {c.name: u for u in unidades if u.tipo == "arquivo" for c in u.caminhos}
    escolhidas: dict[str, Unidade] = {}
    for p in pedidos:
        u = por_nome.get(p) or por_arquivo.get(p)
        if u is None:
            raise ErroImportacao(f"--runs: {p!r} não é pasta, grupo nem arquivo do catálogo")
        escolhidas[u.nome] = u
    return [u for u in unidades if u.nome in escolhidas]


# ----------------------------------------------------------------------------------------------
# Conversões específicas da pesquisa
# ----------------------------------------------------------------------------------------------


def alvo_pesquisa(run: base.RunBenchmark) -> str:
    """Como :func:`importar_runs.alvo_da_run`, aceitando também o filtro por lista de ``CAR_INT``.

    O smoke ``su_h1_*`` filtrou ``carater_internacao: ["02"]``; o alvo vira ``car_int_02`` (exige o
    arquivo ``*_urgencia.parquet``, como a regra original).
    """
    dados = base._obter(run.config, "dados", f"{run.run_id}/config.json")
    alvo_cfg = dados.get("alvo") if isinstance(dados.get("alvo"), dict) else {}
    carater = alvo_cfg.get("carater_internacao")
    if isinstance(carater, list):
        sih = str(base._obter(dados, "sih", f"{run.run_id}/config.json dados"))
        if not carater or not sih.replace("\\", "/").endswith("_urgencia.parquet"):
            raise ErroImportacao(f"{run.run_id}: carater_internacao={carater!r} com dados.sih={sih!r}")
        return "car_int_" + "_".join(str(c) for c in carater)
    return base.alvo_da_run(run)


def metricas_por_fold_pesquisa(linhas: list[dict[str, Any]], run_id: str, ts: int) -> tuple[list[Metric], bool]:
    """Métricas por fold; ``(métricas, sem_semente)``. Com ``seed`` em todas as linhas = importar_runs."""
    com_seed = ["seed" in linha for linha in linhas]
    if all(com_seed):
        return base.metricas_por_fold(linhas, run_id, ts), False
    if any(com_seed):
        raise ErroImportacao(f"{run_id}/metrics.json por_fold: 'seed' presente em umas linhas e ausente em outras")
    saida: list[Metric] = []
    vistos: set[tuple[str, int]] = set()
    for linha in linhas:
        fold = linha.get("fold")
        if isinstance(fold, bool) or not isinstance(fold, int):
            raise ErroImportacao(f"{run_id}/metrics.json por_fold: 'fold' ausente ou não inteiro em {linha}")
        for chave, valor in linha.items():
            if chave in base.CHAVES_IDENTIFICADORAS_FOLD:
                continue
            if not base._eh_numero(valor):
                raise ErroImportacao(f"{run_id}/metrics.json por_fold: '{chave}' não é numérico: {valor!r}")
            if (chave, fold) in vistos:
                raise ErroImportacao(f"{run_id}/metrics.json por_fold: (métrica, fold) duplicado: {(chave, fold)}")
            vistos.add((chave, fold))
            saida.append(Metric(key=f"por_fold/{chave}", value=float(valor), timestamp=ts, step=fold))
    if not saida:
        raise ErroImportacao(f"{run_id}/metrics.json por_fold: nenhuma métrica encontrada")
    return saida, True


def datasets_do_manifesto(manifest: dict[str, Any], run_id: str) -> tuple[list[DatasetInput], list[str]]:
    """``(datasets, sem_sha)``: inputs com digest do manifesto e arquivos que o manifesto cita sem sha256.

    ``dataset_<tipo>: null`` (ex.: meteo vinda do próprio CAMS nas runs de julho) não é arquivo e é
    ignorado. Caminho presente sem ``_sha256`` (um smoke de julho) não vira dataset — não há digest a
    registrar — e volta em ``sem_sha`` para a tag ``datasets_sem_sha256``. sha256 malformado falha alto.
    """
    entradas: list[DatasetInput] = []
    sem_sha: list[str] = []
    for tipo in DATASETS_MANIFESTO:
        chave = f"dataset_{tipo}"
        if manifest.get(chave) is None:
            if manifest.get(f"{chave}_sha256") is not None:
                raise ErroImportacao(f"{run_id}/manifest.json: '{chave}_sha256' sem '{chave}'")
            continue
        caminho = str(manifest[chave]).replace("\\", "/")
        sha = manifest.get(f"{chave}_sha256")
        if sha is None:
            sem_sha.append(f"{tipo}:{caminho}")
            continue
        if not isinstance(sha, str) or not SHA256_RE.match(sha):
            raise ErroImportacao(f"{run_id}/manifest.json: '{chave}_sha256' inválido: {sha!r}")
        ds = Dataset(
            name=caminho,
            digest=sha[:MAX_DIGEST],
            source_type="local",
            source=json.dumps({"uri": caminho}, ensure_ascii=False),
            profile=json.dumps({"sha256": sha, "origem": f"manifest.json:{chave}"}, ensure_ascii=False),
        )
        entradas.append(DatasetInput(ds, tags=[InputTag("mlflow.data.context", tipo), InputTag("sha256", sha)]))
    if not entradas:
        raise ErroImportacao(f"{run_id}/manifest.json: nenhum dataset_* com sha256 encontrado")
    return entradas, sem_sha


def _arquivos(caminhos: tuple[Path, ...]) -> list[tuple[Path, str | None]]:
    """(arquivo, artifact_path) de pastas (recursivo, preservando subpastas) ou arquivos soltos."""
    saida: list[tuple[Path, str | None]] = []
    for c in caminhos:
        if c.is_file():
            saida.append((c, None))
            continue
        for arq in sorted(p for p in c.rglob("*") if p.is_file()):
            pai = arq.parent.relative_to(c).as_posix()
            saida.append((arq, None if pai == "." else pai))
    return saida


def _ts_arquivos(arquivos: list[tuple[Path, str | None]], caminhos: tuple[Path, ...]) -> int:
    mtimes = [a.stat().st_mtime for a, _ in arquivos] or [c.stat().st_mtime for c in caminhos]
    return int(max(mtimes) * 1000)


# ----------------------------------------------------------------------------------------------
# Escrita no MLflow
# ----------------------------------------------------------------------------------------------


@dataclass
class Resumo:
    maes_criadas: int = 0
    filhas_criadas: int = 0
    analises_criadas: int = 0
    puladas: int = 0
    tags_atualizadas: int = 0
    apagadas: int = 0
    artefatos: int = 0
    omitidos: list[str] = field(default_factory=list)
    experimentos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


class Importador:
    def __init__(
        self,
        client: MlflowClient,
        artifact_root: Path | None,
        com_previsoes: bool,
        recriar: bool,
        limite_mb: float = LIMITE_ARTEFATO_MB,
        log=print,
    ) -> None:
        self.client = client
        self.artifact_root = artifact_root
        self.com_previsoes = com_previsoes
        self.recriar = recriar
        self.limite_bytes = int(limite_mb * 1024 * 1024)
        self.log = log
        self.resumo = Resumo()
        self._exp_ids: dict[str, str] = {}

    # --- experimentos e busca ---------------------------------------------------------------

    def experimento_id(self, nome: str, unidade: Unidade) -> str:
        if nome in self._exp_ids:
            return self._exp_ids[nome]
        exp = self.client.get_experiment_by_name(nome)
        if exp is None:
            local = None
            if self.artifact_root is not None:
                local = (self.artifact_root / re.sub(r"[^A-Za-z0-9_.-]+", "__", nome)).resolve().as_uri()
            tags = {"projeto": "dissertacao-pm25-internacoes", "provisorio": "true"}
            if unidade.tipo == "run":
                tags.update({"familia": unidade.entrada.familia, "base": unidade.entrada.base})
            exp_id = self.client.create_experiment(nome, artifact_location=local, tags=tags)
        elif exp.lifecycle_stage != "active":
            raise ErroImportacao(f"experimento '{nome}' está '{exp.lifecycle_stage}'; restaure-o ou rode `mlflow gc`")
        else:
            exp_id = exp.experiment_id
        self._exp_ids[nome] = exp_id
        if nome not in self.resumo.experimentos:
            self.resumo.experimentos.append(nome)
        return exp_id

    def _todas_experiencias(self) -> list[str]:
        return [e.experiment_id for e in self.client.search_experiments()]

    def existentes(self, nome: str) -> list[Any]:
        """Runs ativas (qualquer experimento) com a tag ``run_id`` = nome (mãe, filhas ou análise)."""
        ids = self._todas_experiencias()
        if not ids:
            return []
        return list(self.client.search_runs(ids, filter_string=f"tags.run_id = '{nome}'", max_results=50_000))

    # --- artefatos --------------------------------------------------------------------------

    def _registrar_artefatos(self, rid: str, arquivos: list[tuple[Path, str | None]], pular: set[str]) -> list[str]:
        omitidos: list[str] = []
        for arq, destino in arquivos:
            rel = f"{destino}/{arq.name}" if destino else arq.name
            if rel in pular:
                continue
            if arq.stat().st_size > self.limite_bytes:
                omitidos.append(f"{rel} ({arq.stat().st_size / 1024 / 1024:.1f} MB)")
                continue
            self.client.log_artifact(rid, str(arq), artifact_path=destino)
            self.resumo.artefatos += 1
        return omitidos

    # --- sincronização das tags do catálogo -------------------------------------------------

    def _sincronizar(self, unidade: Unidade, runs: list[Any]) -> None:
        novas = unidade.entrada.tags()
        mudou = False
        for r in runs:
            atuais = r.data.tags
            diffs = [k for k in TAGS_SINCRONIZAVEIS if atuais.get(k) != novas[k]]
            if not diffs:
                continue
            mudou = True
            for k in diffs:
                self.client.set_tag(r.info.run_id, k, novas[k])
            if atuais.get("tipo") in ("mae", "analise"):
                extra = atuais.get("nota_extra", "")
                self.client.set_tag(r.info.run_id, "mlflow.note.content", unidade.entrada.nota(extra))
        if mudou:
            self.resumo.tags_atualizadas += 1
            self.log(f"{unidade.nome}: tags do catálogo atualizadas")

    def _preparar(self, unidade: Unidade, exp_id: str) -> bool:
        """True se a unidade deve ser (re)criada; False se já existe completa (e foi pulada)."""
        existentes = self.existentes(unidade.nome)
        if not existentes:
            return True
        if self.recriar:
            for r in existentes:
                self.client.delete_run(r.info.run_id)
                self.resumo.apagadas += 1
            return True
        topo = [r for r in existentes if r.data.tags.get("tipo") in ("mae", "analise")]
        if len(topo) != 1:
            raise ErroImportacao(
                f"{unidade.nome}: {len(topo)} runs de topo no MLflow (esperava 1); rode com --recriar --runs {unidade.nome}"
            )
        mae = topo[0]
        if mae.info.experiment_id != exp_id:
            raise ErroImportacao(
                f"{unidade.nome}: já importada em outro experimento (id {mae.info.experiment_id}); "
                f"o catálogo mudou familia/base? Rode com --recriar --runs {unidade.nome}"
            )
        if mae.data.tags.get("importacao_completa") != "true":
            raise ErroImportacao(
                f"{unidade.nome}: importação anterior incompleta; rode com --recriar --runs {unidade.nome}"
            )
        self._sincronizar(unidade, existentes)
        self.resumo.puladas += 1
        return False

    # --- runs do benchmark ------------------------------------------------------------------

    def importar_run(self, unidade: Unidade) -> None:
        pasta = unidade.caminhos[0]
        run = base.carregar_run(pasta)
        entrada = unidade.entrada
        horizonte = base.horizonte_da_run(run)
        alvo = alvo_pesquisa(run)
        exp_id = self.experimento_id(unidade.experimento, unidade)
        if not self._preparar(unidade, exp_id):
            return
        ts = base._timestamp_ms(run.manifest, run.run_id)
        manifest = run.manifest

        por_fold: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for linha in run.metrics["por_fold"]:
            por_fold.setdefault(base._par(linha, run.run_id, "por_fold"), []).append(linha)
        sem_semente = not any("seed" in linha for linha in run.metrics["por_fold"])

        tags_mae = {
            "run_id": run.run_id,
            "tipo": "mae",
            **entrada.tags(),
            "commit": str(base._obter(manifest, "git_commit", f"{run.run_id}/manifest.json")),
            "git_sujo": "true" if bool(manifest["git_sujo"]) else "false",
            "modo": str(manifest["modo"]),
            "status": str(manifest["status"]),
            "horizonte": str(horizonte),
            "alvo": alvo,
            "provisorio": "true",
            "origem": str(pasta),
            "n_filhas": str(len(run.metrics["agregado"])),
        }
        for chave in ("fonte_pm25", "fonte_meteo", "git_branch", "n_predicoes"):
            if chave in manifest:
                tags_mae[chave] = str(manifest[chave])
        if sem_semente:
            tags_mae["por_fold_sem_semente"] = "true"
        arquivos = _arquivos((pasta,))
        pular = set() if self.com_previsoes else {PREVISOES}
        extra = "Artefatos: arquivos da pasta de origem" + ("." if self.com_previsoes else f" (sem {PREVISOES}).")
        tags_mae["nota_extra"] = extra
        params_mae: dict[str, str] = {}
        base._achatar(run.config["experimento"], "experimento", params_mae)
        base._achatar(run.config["split"], "split", params_mae)

        mae = self.client.create_run(exp_id, start_time=ts, tags=tags_mae, run_name=run.run_id)
        mid = mae.info.run_id
        try:
            self.client.log_batch(
                mid,
                params=[Param(k, v) for k, v in params_mae.items()],
                tags=[RunTag("mlflow.note.content", entrada.nota(extra))],
            )
            datasets, sem_sha = datasets_do_manifesto(manifest, run.run_id)
            self.client.log_inputs(mid, datasets=datasets)
            if sem_sha:
                self.client.set_tag(mid, "datasets_sem_sha256", "; ".join(sem_sha))
                self.resumo.avisos.append(f"{run.run_id}: dataset sem sha256 no manifesto: {sem_sha}")
            omitidos = self._registrar_artefatos(mid, arquivos, pular)
            if omitidos:
                self.client.set_tag(mid, "arquivos_omitidos", "; ".join(omitidos))
                self.resumo.omitidos.extend(f"{run.run_id}/{o}" for o in omitidos)

            pares_nan: list[str] = []
            for linha in run.metrics["agregado"]:
                modelo, feature_set = base._par(linha, run.run_id, "agregado")
                agregado = base.metricas_agregado(linha, run.run_id)
                nan = sorted(k for k, v in agregado.items() if math.isnan(v))
                tags = base.tags_da_run(run, modelo, feature_set, horizonte, alvo)
                tags.update(
                    {
                        "mlflow.parentRunId": mid,
                        "tipo": "filha",
                        **{k: v for k, v in entrada.tags().items()},
                    }
                )
                if nan:
                    tags["metricas_nan"] = ",".join(nan)
                    pares_nan.append(f"{modelo}/{feature_set}")
                fold_metricas, sem = metricas_por_fold_pesquisa(por_fold[(modelo, feature_set)], run.run_id, ts)
                if sem:
                    tags["por_fold_sem_semente"] = "true"
                params = base.params_da_run(run, modelo, feature_set)
                filha = self.client.create_run(exp_id, start_time=ts, tags=tags, run_name=f"{modelo}__{feature_set}")
                fid = filha.info.run_id
                try:
                    self.client.log_batch(
                        fid,
                        metrics=[Metric(key=k, value=v, timestamp=ts, step=0) for k, v in agregado.items()],
                        params=[Param(key=k, value=v) for k, v in params.items()],
                        tags=[
                            RunTag(
                                "mlflow.note.content",
                                f"Importada de {run.run_id}/metrics.json (papel da run: {entrada.papel}); provisória.",
                            )
                        ],
                    )
                    self.client.log_batch(fid, metrics=fold_metricas)
                    self.client.set_terminated(fid, status="FINISHED", end_time=ts)
                except Exception:
                    self.client.set_terminated(fid, status="FAILED", end_time=ts)
                    raise
                self.resumo.filhas_criadas += 1
            if pares_nan:
                self.resumo.avisos.append(f"{run.run_id}: {len(pares_nan)} pares com NaN (tag metricas_nan)")
            self.client.set_tag(mid, "importacao_completa", "true")
            self.client.set_terminated(mid, status="FINISHED", end_time=ts)
        except Exception:
            self.client.set_terminated(mid, status="FAILED", end_time=ts)
            raise
        self.resumo.maes_criadas += 1
        self.log(f"{run.run_id}: mãe + {len(run.metrics['agregado'])} filhas -> {unidade.experimento}")

    # --- análises, pastas sem métricas, grupos de arquivos ----------------------------------

    def importar_analise(self, unidade: Unidade) -> None:
        exp_id = self.experimento_id(unidade.experimento, unidade)
        if not self._preparar(unidade, exp_id):
            return
        arquivos = _arquivos(unidade.caminhos)
        ts = _ts_arquivos(arquivos, unidade.caminhos)
        e = unidade.entrada
        origem = "; ".join(str(c) for c in unidade.caminhos)
        extra = f"Tipo: {unidade.tipo}; {len(arquivos)} arquivos de origem. Sem métricas: run só de artefatos."
        tags = {
            "run_id": unidade.nome,
            "tipo": "analise",
            **e.tags(),
            "provisorio": "true",
            "tipo_origem": unidade.tipo,
            "origem": origem if len(origem) < 7000 else origem[:7000],
            "n_arquivos": str(len(arquivos)),
            "nota_extra": extra,
        }
        if unidade.tipo == "arquivo":
            tags["arquivos"] = ",".join(c.name for c in unidade.caminhos)
        r = self.client.create_run(exp_id, start_time=ts, tags=tags, run_name=unidade.nome)
        rid = r.info.run_id
        try:
            self.client.set_tag(rid, "mlflow.note.content", e.nota(extra))
            omitidos = self._registrar_artefatos(rid, arquivos, set())
            self.client.set_tag(rid, "arquivos_omitidos", "; ".join(omitidos) if omitidos else "nenhum")
            self.resumo.omitidos.extend(f"{unidade.nome}/{o}" for o in omitidos)
            self.client.set_tag(rid, "importacao_completa", "true")
            self.client.set_terminated(rid, status="FINISHED", end_time=ts)
        except Exception:
            self.client.set_terminated(rid, status="FAILED", end_time=ts)
            raise
        self.resumo.analises_criadas += 1
        self.log(f"{unidade.nome}: run de {unidade.tipo} ({len(arquivos)} arquivos) -> {unidade.experimento}")


def importar(
    results_dir: Path | str,
    catalogo: Path | str,
    tracking_uri: str,
    artifact_root: Path | str | None = None,
    com_previsoes: bool = False,
    recriar: bool = False,
    runs: list[str] | None = None,
    limite_mb: float = LIMITE_ARTEFATO_MB,
    log=print,
) -> Resumo:
    """Importa as unidades de ``results_dir`` (todas ou ``runs``) segundo ``catalogo``."""
    results_dir = Path(results_dir)
    if artifact_root is not None and tracking_uri.startswith("sqlite:"):
        # cria o banco (se ainda não existe) com o experimento Default dentro de artifact_root, e não em ./mlruns
        SqlAlchemyStore(tracking_uri, Path(artifact_root).resolve().as_uri())
    cat = carregar_catalogo(catalogo)
    unidades = filtrar_unidades(montar_unidades(results_dir, cat), runs)
    # valida todas as runs antes de escrever qualquer coisa no MLflow (falha alto cedo)
    for u in unidades:
        if u.tipo == "run":
            r = base.carregar_run(u.caminhos[0])
            base.horizonte_da_run(r)
            alvo_pesquisa(r)
            datasets_do_manifesto(r.manifest, r.run_id)
    imp = Importador(
        MlflowClient(tracking_uri=tracking_uri),
        Path(artifact_root) if artifact_root else None,
        com_previsoes=com_previsoes,
        recriar=recriar,
        limite_mb=limite_mb,
        log=log,
    )
    for u in unidades:
        if u.tipo == "run":
            imp.importar_run(u)
        else:
            imp.importar_analise(u)
    return imp.resumo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--results-dir", required=True, help="pasta reports/experiments (só leitura)")
    parser.add_argument("--catalogo", required=True, help="catálogo YAML com uma entrada por item do diretório")
    parser.add_argument("--tracking-uri", required=True, help="ex.: sqlite:///D:/Project/mlflow_pesquisa/mlflow.db")
    parser.add_argument(
        "--artifact-root", help="raiz dos artefatos dos experimentos criados (padrão do MLflow se omitido)"
    )
    parser.add_argument("--com-previsoes", action="store_true", help=f"anexa {PREVISOES} às runs mães")
    parser.add_argument("--recriar", action="store_true", help="apaga (soft delete) e recria o que já foi importado")
    parser.add_argument("--runs", nargs="+", metavar="ID", help="subconjunto: pastas, grupos ou arquivos do catálogo")
    parser.add_argument("--quiet", action="store_true", help="não imprime o progresso")
    args = parser.parse_args(argv)

    log = (lambda *_: None) if args.quiet else print
    inicio = time.perf_counter()
    try:
        resumo = importar(
            args.results_dir,
            args.catalogo,
            args.tracking_uri,
            artifact_root=args.artifact_root,
            com_previsoes=args.com_previsoes,
            recriar=args.recriar,
            runs=args.runs,
            log=log,
        )
    except ErroImportacao as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    print(
        f"mães criadas {resumo.maes_criadas}, filhas criadas {resumo.filhas_criadas}, "
        f"análises criadas {resumo.analises_criadas}, puladas {resumo.puladas} "
        f"(tags atualizadas em {resumo.tags_atualizadas}), apagadas {resumo.apagadas}; "
        f"artefatos {resumo.artefatos}, omitidos {len(resumo.omitidos)}; "
        f"{len(resumo.experimentos)} experimentos; {len(resumo.avisos)} avisos de NaN; "
        f"{time.perf_counter() - inicio:.0f} s; tracking URI {args.tracking_uri}"
    )
    for a in resumo.avisos:
        print(f"  aviso: {a}")
    for o in resumo.omitidos:
        print(f"  omitido (> {LIMITE_ARTEFATO_MB:.0f} MB): {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

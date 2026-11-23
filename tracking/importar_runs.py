"""Importa as runs do benchmark (``results/runs/<RUN_ID>/``) para o MLflow.

O importador **só copia números** dos artefatos já executados — ``config.json``,
``manifest.json`` e ``metrics.json`` — para um tracking server do MLflow. Nenhum
cálculo é refeito; nenhum valor é inventado, arredondado ou substituído.

Como rodar (a partir da raiz do repositório)::

    # importa todas as pastas de results/runs/ em file:./mlruns
    uv run python -m tracking.importar_runs

    # só algumas runs, ou outro diretório de resultados / tracking URI
    uv run python -m tracking.importar_runs --runs ur_h1_cetesb_cetesb_full_20261116-191534
    uv run python -m tracking.importar_runs --results-dir results/runs --tracking-uri sqlite:///mlruns/mlflow.db

    # apaga (soft delete) e recria as runs MLflow já importadas
    uv run python -m tracking.importar_runs --recriar

    # interface web
    uv run mlflow ui --backend-store-uri file:./mlruns
    # (o docker-compose.yml sobe o serviço ``mlflow`` na porta 5000 com o mesmo file store)

Atenção: a partir do MLflow 3.x o backend em sistema de arquivos (``file:./mlruns``)
está em modo de manutenção e exige a variável de ambiente ``MLFLOW_ALLOW_FILE_STORE=true``.
Este módulo define essa variável para si mesmo (``os.environ.setdefault``), mas o
``mlflow ui`` e o contêiner precisam dela no ambiente::

    MLFLOW_ALLOW_FILE_STORE=true uv run mlflow ui --backend-store-uri file:./mlruns

Organização no MLflow
---------------------
* **Um experimento por (horizonte, alvo)**: ``h1_total``, ``h5_total``, ..., ``h1_urgencia``, ...
  O horizonte vem de ``config.json`` → ``experimento.horizonte``; o alvo é ``urgencia`` quando
  ``dados.alvo.carater_internacao == "nao_eletivo"`` **e** ``dados.sih`` termina em
  ``_urgencia.parquet`` (as duas condições têm de concordar; caso contrário o importador falha).
* **Uma run MLflow por (modelo, conjunto de features)** de cada run do benchmark.
  - params: ``experimento.*``, ``split.*`` e ``modelo.*`` (hiperparâmetros de ``modelos.<modelo>``),
    mais ``feature_set.blocos`` quando o manifesto lista os blocos do conjunto;
  - métricas agregadas (seção ``agregado`` do ``metrics.json``): ``MAE_medio``, ``MASE_medio``, ...
    registradas com o mesmo nome e o mesmo valor;
  - métricas por fold (seção ``por_fold``): ``por_fold/seed<semente>/<métrica>`` com ``step=fold``;
  - tags: ``run_id``, ``commit``, ``git_sujo``, ``provisorio=true``, ``modelo``, ``feature_set``,
    ``horizonte``, ``alvo`` (e algumas auxiliares: ``status``, ``fonte_pm25``, ``fonte_meteo``).
* Valores ``NaN`` do ``metrics.json`` (por exemplo ``MAE_std_semente`` dos modelos determinísticos)
  são registrados **como estão** (o MLflow aceita NaN) e listados na tag ``metricas_nan``; um aviso
  é impresso. Nunca são substituídos por zero.
* **Idempotente**: antes de criar uma run MLflow o importador procura, no experimento, uma run ativa
  com as mesmas tags ``run_id``, ``modelo`` e ``feature_set``; se existir, pula. Com ``--recriar``
  a run existente é apagada (soft delete) e criada de novo. ``mlflow gc`` expurga as apagadas.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# O file store do MLflow 3.x exige opt-in explícito; definimos antes de importar o mlflow.
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

from mlflow import MlflowClient  # noqa: E402
from mlflow.entities import Metric, Param, RunTag  # noqa: E402

RAIZ_REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR_PADRAO = RAIZ_REPO / "results" / "runs"
TRACKING_URI_PADRAO = "file:./mlruns"

ARQUIVOS_OBRIGATORIOS = ("config.json", "manifest.json", "metrics.json")
# Colunas de ``por_fold`` que identificam a linha, não são métricas.
CHAVES_IDENTIFICADORAS_FOLD = {"model", "feature_set", "seed", "fold", "teste_inicio", "teste_fim"}
CHAVES_IDENTIFICADORAS_AGREGADO = {"model", "feature_set"}
TAGS_PROIBIDAS = ("'", '"', "\\")


class ErroImportacao(RuntimeError):
    """Artefato ausente, chave inexistente ou inconsistência entre arquivos."""


@dataclass(frozen=True)
class RunBenchmark:
    """Os três artefatos de uma run do benchmark, já lidos."""

    run_id: str
    pasta: Path
    config: dict[str, Any]
    manifest: dict[str, Any]
    metrics: dict[str, Any]


@dataclass
class Resumo:
    """Contagens do que o importador fez."""

    runs_benchmark: int = 0
    criadas: int = 0
    puladas: int = 0
    apagadas: int = 0
    experimentos: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


# ----------------------------------------------------------------------------------------------
# Leitura e validação dos artefatos
# ----------------------------------------------------------------------------------------------


def _obter(dic: dict[str, Any], caminho: str, origem: str) -> Any:
    """Acessa ``a.b.c`` em ``dic``; falha alto se qualquer nível faltar."""
    atual: Any = dic
    for parte in caminho.split("."):
        if not isinstance(atual, dict) or parte not in atual:
            raise ErroImportacao(f"{origem}: chave obrigatória '{caminho}' não encontrada")
        atual = atual[parte]
    return atual


def ler_json(caminho: Path) -> dict[str, Any]:
    if not caminho.is_file():
        raise ErroImportacao(f"arquivo esperado não encontrado: {caminho}")
    with caminho.open(encoding="utf-8") as fh:
        conteudo = json.load(fh)
    if not isinstance(conteudo, dict):
        raise ErroImportacao(f"{caminho}: esperava um objeto JSON no topo")
    return conteudo


def carregar_run(pasta: Path) -> RunBenchmark:
    """Lê ``config/manifest/metrics.json`` de uma pasta de run e checa a consistência básica."""
    if not pasta.is_dir():
        raise ErroImportacao(f"pasta de run não encontrada: {pasta}")
    for nome in ARQUIVOS_OBRIGATORIOS:
        if not (pasta / nome).is_file():
            raise ErroImportacao(f"{pasta.name}: falta {nome}")
    config = ler_json(pasta / "config.json")
    manifest = ler_json(pasta / "manifest.json")
    metrics = ler_json(pasta / "metrics.json")

    run_id = _obter(manifest, "run_id", f"{pasta.name}/manifest.json")
    if run_id != pasta.name:
        raise ErroImportacao(f"{pasta.name}: manifest.run_id = '{run_id}' difere do nome da pasta")
    for chave in ("git_commit", "git_sujo", "modo", "status", "timestamp"):
        _obter(manifest, chave, f"{run_id}/manifest.json")
    for chave in ("por_fold", "agregado"):
        if not isinstance(_obter(metrics, chave, f"{run_id}/metrics.json"), list):
            raise ErroImportacao(f"{run_id}/metrics.json: '{chave}' deveria ser uma lista")
    _obter(config, "experimento.horizonte", f"{run_id}/config.json")
    _obter(config, "split", f"{run_id}/config.json")
    _obter(config, "modelos", f"{run_id}/config.json")

    pares_agregado = {_par(linha, run_id, "agregado") for linha in metrics["agregado"]}
    pares_fold = {_par(linha, run_id, "por_fold") for linha in metrics["por_fold"]}
    if pares_agregado != pares_fold:
        raise ErroImportacao(
            f"{run_id}/metrics.json: pares (modelo, feature_set) de 'agregado' e 'por_fold' diferem: "
            f"{sorted(pares_agregado ^ pares_fold)}"
        )
    if len(pares_agregado) != len(metrics["agregado"]):
        raise ErroImportacao(f"{run_id}/metrics.json: 'agregado' tem pares (modelo, feature_set) duplicados")
    return RunBenchmark(run_id=run_id, pasta=pasta, config=config, manifest=manifest, metrics=metrics)


def _par(linha: dict[str, Any], run_id: str, secao: str) -> tuple[str, str]:
    for chave in ("model", "feature_set"):
        if chave not in linha:
            raise ErroImportacao(f"{run_id}/metrics.json: linha de '{secao}' sem '{chave}': {linha}")
    return str(linha["model"]), str(linha["feature_set"])


def horizonte_da_run(run: RunBenchmark) -> int:
    h = _obter(run.config, "experimento.horizonte", f"{run.run_id}/config.json")
    if isinstance(h, bool) or not isinstance(h, int) or h < 1:
        raise ErroImportacao(f"{run.run_id}: experimento.horizonte inválido: {h!r}")
    return h


def alvo_da_run(run: RunBenchmark) -> str:
    """``"urgencia"`` ou ``"total"``; as duas evidências do config têm de concordar."""
    dados = _obter(run.config, "dados", f"{run.run_id}/config.json")
    sih = str(_obter(dados, "sih", f"{run.run_id}/config.json dados"))
    carater = dados.get("alvo", {}).get("carater_internacao") if isinstance(dados.get("alvo"), dict) else None
    por_carater = carater == "nao_eletivo"
    por_arquivo = sih.replace("\\", "/").endswith("_urgencia.parquet")
    if por_carater != por_arquivo:
        raise ErroImportacao(
            f"{run.run_id}: alvo ambíguo — dados.alvo.carater_internacao={carater!r} mas dados.sih={sih!r}"
        )
    return "urgencia" if por_carater else "total"


def nome_experimento(horizonte: int, alvo: str) -> str:
    return f"h{horizonte}_{alvo}"


# ----------------------------------------------------------------------------------------------
# Conversão para entidades do MLflow
# ----------------------------------------------------------------------------------------------


def _achatar(valor: Any, prefixo: str, saida: dict[str, str]) -> None:
    """Achata dicts aninhados em chaves pontilhadas; listas/escalares viram texto.

    Um dict cujas chaves colidem sem distinção de caixa (ex.: ``grade.p`` e ``grade.P`` do SARIMAX)
    é serializado inteiro como JSON, porque o file store do MLflow grava um arquivo por param e
    sistemas de arquivos como o NTFS não distinguem ``p`` de ``P``.
    """
    if isinstance(valor, dict):
        if len({str(k).lower() for k in valor}) != len(valor):
            saida[prefixo] = json.dumps(valor, ensure_ascii=False)
            return
        for chave, sub in valor.items():
            _achatar(sub, f"{prefixo}.{chave}" if prefixo else str(chave), saida)
    elif isinstance(valor, (list, tuple)):
        saida[prefixo] = json.dumps(list(valor), ensure_ascii=False)
    elif valor is None:
        saida[prefixo] = "null"
    elif isinstance(valor, bool):
        saida[prefixo] = "true" if valor else "false"
    else:
        saida[prefixo] = str(valor)


def params_da_run(run: RunBenchmark, modelo: str, feature_set: str) -> dict[str, str]:
    params: dict[str, str] = {}
    _achatar(_obter(run.config, "experimento", f"{run.run_id}/config.json"), "experimento", params)
    _achatar(_obter(run.config, "split", f"{run.run_id}/config.json"), "split", params)
    modelos = _obter(run.config, "modelos", f"{run.run_id}/config.json")
    if modelo not in modelos:
        raise ErroImportacao(f"{run.run_id}: modelo '{modelo}' do metrics.json não existe em config.modelos")
    _achatar(modelos[modelo], "modelo", params)
    feature_sets = run.manifest.get("feature_sets")
    if isinstance(feature_sets, dict) and feature_set in feature_sets:
        _achatar(feature_sets[feature_set], "feature_set.blocos", params)
    for chave in ("fonte_pm25", "fonte_meteo"):
        if chave in run.manifest:
            _achatar(run.manifest[chave], f"dados.{chave}", params)
    return params


def _eh_numero(valor: Any) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def metricas_agregado(linha: dict[str, Any], run_id: str) -> dict[str, float]:
    saida: dict[str, float] = {}
    for chave, valor in linha.items():
        if chave in CHAVES_IDENTIFICADORAS_AGREGADO:
            continue
        if not _eh_numero(valor):
            raise ErroImportacao(f"{run_id}/metrics.json agregado: '{chave}' não é numérico: {valor!r}")
        saida[str(chave)] = float(valor)
    if not saida:
        raise ErroImportacao(f"{run_id}/metrics.json agregado: linha sem métricas: {linha}")
    return saida


def chave_por_fold(metrica: str, seed: int) -> str:
    return f"por_fold/seed{seed}/{metrica}"


def metricas_por_fold(linhas: list[dict[str, Any]], run_id: str, timestamp_ms: int) -> list[Metric]:
    """Uma ``Metric`` por (métrica, semente, fold), com ``step=fold``."""
    saida: list[Metric] = []
    vistos: set[tuple[str, int, int]] = set()
    for linha in linhas:
        for chave in ("seed", "fold"):
            if chave not in linha or isinstance(linha[chave], bool) or not isinstance(linha[chave], int):
                raise ErroImportacao(f"{run_id}/metrics.json por_fold: '{chave}' ausente ou não inteiro em {linha}")
        seed, fold = int(linha["seed"]), int(linha["fold"])
        for chave, valor in linha.items():
            if chave in CHAVES_IDENTIFICADORAS_FOLD:
                continue
            if not _eh_numero(valor):
                raise ErroImportacao(f"{run_id}/metrics.json por_fold: '{chave}' não é numérico: {valor!r}")
            ident = (str(chave), seed, fold)
            if ident in vistos:
                raise ErroImportacao(f"{run_id}/metrics.json por_fold: (métrica, seed, fold) duplicado: {ident}")
            vistos.add(ident)
            saida.append(
                Metric(key=chave_por_fold(str(chave), seed), value=float(valor), timestamp=timestamp_ms, step=fold)
            )
    if not saida:
        raise ErroImportacao(f"{run_id}/metrics.json por_fold: nenhuma métrica encontrada")
    return saida


def _timestamp_ms(manifest: dict[str, Any], run_id: str) -> int:
    bruto = _obter(manifest, "timestamp", f"{run_id}/manifest.json")
    try:
        return int(datetime.fromisoformat(str(bruto)).timestamp() * 1000)
    except ValueError as exc:
        raise ErroImportacao(f"{run_id}/manifest.json: timestamp inválido {bruto!r}") from exc


def _validar_tag(valor: str, nome: str, run_id: str) -> str:
    if any(c in valor for c in TAGS_PROIBIDAS) or not valor:
        raise ErroImportacao(f"{run_id}: valor da tag '{nome}' inválido para busca no MLflow: {valor!r}")
    return valor


def tags_da_run(run: RunBenchmark, modelo: str, feature_set: str, horizonte: int, alvo: str) -> dict[str, str]:
    manifest, rid = run.manifest, run.run_id
    tags = {
        "run_id": _validar_tag(rid, "run_id", rid),
        "commit": str(_obter(manifest, "git_commit", f"{rid}/manifest.json")),
        "git_sujo": "true" if bool(_obter(manifest, "git_sujo", f"{rid}/manifest.json")) else "false",
        "provisorio": "true",
        "modelo": _validar_tag(modelo, "modelo", rid),
        "feature_set": _validar_tag(feature_set, "feature_set", rid),
        "horizonte": str(horizonte),
        "alvo": alvo,
        "status": str(_obter(manifest, "status", f"{rid}/manifest.json")),
        "modo": str(_obter(manifest, "modo", f"{rid}/manifest.json")),
        "origem": str(run.pasta.relative_to(RAIZ_REPO)) if run.pasta.is_relative_to(RAIZ_REPO) else str(run.pasta),
    }
    for chave in ("fonte_pm25", "fonte_meteo", "git_branch"):
        if chave in manifest:
            tags[chave] = str(manifest[chave])
    return tags


# ----------------------------------------------------------------------------------------------
# Escrita no MLflow
# ----------------------------------------------------------------------------------------------


def _experimento_id(client: MlflowClient, nome: str) -> str:
    exp = client.get_experiment_by_name(nome)
    if exp is None:
        return client.create_experiment(
            nome, tags={"projeto": "sp-respiratory-admissions-forecast", "provisorio": "true"}
        )
    if exp.lifecycle_stage != "active":
        raise ErroImportacao(
            f"experimento '{nome}' existe em estado '{exp.lifecycle_stage}'; restaure-o ou rode `mlflow gc` antes"
        )
    return exp.experiment_id


def runs_existentes(client: MlflowClient, exp_id: str, run_id: str) -> dict[tuple[str, str], list[Any]]:
    """Runs MLflow ativas já importadas desta run do benchmark, indexadas por (modelo, feature_set).

    Uma única busca por run do benchmark: no file store cada ``search_runs`` lê todas as runs do
    experimento (e seus arquivos de métricas), então buscar par a par seria quadrático.
    """
    indice: dict[tuple[str, str], list[Any]] = {}
    for mlrun in client.search_runs([exp_id], filter_string=f"tags.run_id = '{run_id}'", max_results=50_000):
        tags = mlrun.data.tags
        if "modelo" not in tags or "feature_set" not in tags:
            raise ErroImportacao(f"run MLflow {mlrun.info.run_id} com tag run_id={run_id} sem tags modelo/feature_set")
        indice.setdefault((tags["modelo"], tags["feature_set"]), []).append(mlrun)
    return indice


def importar_run(client: MlflowClient, run: RunBenchmark, resumo: Resumo, recriar: bool = False, log=print) -> None:
    """Cria uma run MLflow por (modelo, feature_set) presente em ``metrics.agregado``."""
    horizonte = horizonte_da_run(run)
    alvo = alvo_da_run(run)
    nome = nome_experimento(horizonte, alvo)
    exp_id = _experimento_id(client, nome)
    if nome not in resumo.experimentos:
        resumo.experimentos.append(nome)
    ts = _timestamp_ms(run.manifest, run.run_id)

    por_fold: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for linha in run.metrics["por_fold"]:
        por_fold.setdefault(_par(linha, run.run_id, "por_fold"), []).append(linha)

    existentes_por_par = runs_existentes(client, exp_id, run.run_id)
    pares_nan: list[str] = []
    for linha in run.metrics["agregado"]:
        modelo, feature_set = _par(linha, run.run_id, "agregado")
        existentes = existentes_por_par.get((modelo, feature_set), [])
        if existentes and not recriar:
            resumo.puladas += 1
            continue
        for antiga in existentes:
            client.delete_run(antiga.info.run_id)
            resumo.apagadas += 1

        agregado = metricas_agregado(linha, run.run_id)
        nan = sorted(k for k, v in agregado.items() if math.isnan(v))
        tags = tags_da_run(run, modelo, feature_set, horizonte, alvo)
        if nan:
            tags["metricas_nan"] = ",".join(nan)
            pares_nan.append(f"{modelo}/{feature_set}: {','.join(nan)}")
        params = params_da_run(run, modelo, feature_set)

        mlrun = client.create_run(exp_id, start_time=ts, tags=tags, run_name=f"{modelo}__{feature_set}")
        rid = mlrun.info.run_id
        try:
            client.log_batch(
                rid,
                metrics=[Metric(key=k, value=v, timestamp=ts, step=0) for k, v in agregado.items()],
                params=[Param(key=k, value=v) for k, v in params.items()],
                tags=[
                    RunTag(key="mlflow.note.content", value=f"Importada de {run.pasta.name}/metrics.json; provisória.")
                ],
            )
            client.log_batch(rid, metrics=metricas_por_fold(por_fold[(modelo, feature_set)], run.run_id, ts))
            client.set_terminated(rid, status="FINISHED", end_time=ts)
        except Exception:
            client.set_terminated(rid, status="FAILED", end_time=ts)
            raise
        resumo.criadas += 1
    if pares_nan:
        aviso = (
            f"{run.run_id}: {len(pares_nan)} pares com métricas NaN no metrics.json, registradas como NaN "
            f"(tag metricas_nan): {'; '.join(pares_nan)}"
        )
        resumo.avisos.append(aviso)
        log(f"AVISO {aviso}")


def pastas_de_runs(results_dir: Path, runs: list[str] | None) -> list[Path]:
    if not results_dir.is_dir():
        raise ErroImportacao(f"diretório de resultados não encontrado: {results_dir}")
    if runs:
        pastas = [results_dir / r for r in runs]
        faltando = [p.name for p in pastas if not p.is_dir()]
        if faltando:
            raise ErroImportacao(f"runs pedidas não encontradas em {results_dir}: {faltando}")
        return pastas
    pastas = sorted(p for p in results_dir.iterdir() if p.is_dir())
    if not pastas:
        raise ErroImportacao(f"nenhuma pasta de run em {results_dir}")
    return pastas


def importar(
    results_dir: Path | str = RESULTS_DIR_PADRAO,
    tracking_uri: str = TRACKING_URI_PADRAO,
    runs: list[str] | None = None,
    recriar: bool = False,
    log=print,
) -> Resumo:
    """Importa todas (ou ``runs``) as pastas de ``results_dir`` para ``tracking_uri``."""
    results_dir = Path(results_dir)
    client = MlflowClient(tracking_uri=tracking_uri)
    resumo = Resumo()
    for pasta in pastas_de_runs(results_dir, runs):
        run = carregar_run(pasta)
        antes = (resumo.criadas, resumo.puladas, resumo.apagadas)
        importar_run(client, run, resumo, recriar=recriar, log=log)
        resumo.runs_benchmark += 1
        c, p, a = (resumo.criadas - antes[0], resumo.puladas - antes[1], resumo.apagadas - antes[2])
        log(
            f"{run.run_id}: {c} criadas, {p} puladas, {a} apagadas -> experimento {nome_experimento(horizonte_da_run(run), alvo_da_run(run))}"
        )
    return resumo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--results-dir",
        default=str(RESULTS_DIR_PADRAO),
        help="pasta com as runs (padrão: results/runs na raiz do repo)",
    )
    parser.add_argument(
        "--tracking-uri", default=TRACKING_URI_PADRAO, help=f"tracking URI do MLflow (padrão: {TRACKING_URI_PADRAO})"
    )
    parser.add_argument(
        "--runs", nargs="+", metavar="RUN_ID", help="ids das runs a importar (padrão: todas as subpastas)"
    )
    parser.add_argument(
        "--recriar", action="store_true", help="apaga (soft delete) e recria as runs MLflow já importadas"
    )
    parser.add_argument("--quiet", action="store_true", help="não imprime o progresso")
    args = parser.parse_args(argv)

    log = (lambda *_: None) if args.quiet else print
    try:
        resumo = importar(args.results_dir, args.tracking_uri, args.runs, args.recriar, log=log)
    except ErroImportacao as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    print(
        f"{resumo.runs_benchmark} runs do benchmark lidas; {resumo.criadas} runs MLflow criadas, "
        f"{resumo.puladas} puladas (já existiam), {resumo.apagadas} apagadas; "
        f"experimentos: {', '.join(resumo.experimentos)}; {len(resumo.avisos)} avisos (NaN); "
        f"tracking URI: {args.tracking_uri}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

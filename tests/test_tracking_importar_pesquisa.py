"""Importador da pesquisa (``tracking.importar_pesquisa``): mães, filhas, análises, datasets e catálogo.

Não depende do repositório da dissertação: monta um diretório de resultados temporário com duas
pastas de ``results/runs/`` do portfólio, uma pasta de análise, uma pasta interrompida e um grupo de
arquivos soltos, mais um catálogo temporário; o tracking URI é SQLite em ``tmp_path``.
"""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pytest
import yaml

pytest.importorskip("mlflow", reason="dependência opcional [tracking]: mlflow")

from mlflow import MlflowClient  # noqa: E402

from tracking import importar_pesquisa as imp  # noqa: E402
from tracking import importar_runs as base  # noqa: E402

RUNS_PORTFOLIO = Path(__file__).resolve().parents[1] / "results" / "runs"
RUN_URG = "ur_h1_cetesb_cetesb_full_20261116-191534"
RUN_TOT = "mh_h5_cetesb_cetesb_full_20261110-211453"
ANALISE = "TESTES_DM_fake_20990101"
INTERROMPIDA = "mh_h30_fake_full_20990101-000000"
GRUPO = "COMPARACAO_FAKE_V01"
ARQUIVOS_GRUPO = (f"{GRUPO}.md", f"{GRUPO}_long.csv")
LIMITE_MB = 1.0  # o arquivo "grande" do teste tem 1,5 MB; os artefatos das runs ficam abaixo de 1 MB


def _entrada(run_id: str, tipo: str, familia: str, base_: str, papel: str, **extra) -> dict:
    return {
        "run_id": run_id,
        "tipo": tipo,
        "familia": familia,
        "base": base_,
        "papel": papel,
        "motivo": f"motivo de teste para {run_id}",
        "fonte": "teste",
        "revisado": False,
        **extra,
    }


def _catalogo_padrao() -> list[dict]:
    return [
        _entrada(RUN_URG, "run", "alvo_urgencia", "cetesb", "valida"),
        _entrada(RUN_TOT, "run", "multihorizonte", "cetesb", "valida"),
        _entrada(ANALISE, "pasta", "teste_dm", "cetesb", "analise"),
        _entrada(INTERROMPIDA, "pasta", "multihorizonte", "cetesb", "interrompida"),
        *[
            {**_entrada(nome, "arquivo", "comparacao", "entre_bases", "analise"), "grupo": GRUPO, "motivo": "grupo"}
            for nome in ARQUIVOS_GRUPO
        ],
    ]


def _escrever_catalogo(caminho: Path, entradas: list[dict]) -> Path:
    caminho.write_text(yaml.safe_dump({"entradas": entradas}, allow_unicode=True), encoding="utf-8")
    return caminho


def _montar_results(raiz: Path) -> Path:
    results = raiz / "experiments"
    results.mkdir()
    for rid in (RUN_URG, RUN_TOT):
        shutil.copytree(RUNS_PORTFOLIO / rid, results / rid)
    analise = results / ANALISE
    (analise / "h1").mkdir(parents=True)
    (analise / "RELATORIO_DM.md").write_text("# relatório fake\n", encoding="utf-8")
    (analise / "h1" / "dm_contrastes.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (analise / "grande.bin").write_bytes(b"\0" * int(1.5 * 1024 * 1024))
    interrompida = results / INTERROMPIDA
    (interrompida / "figures").mkdir(parents=True)
    (interrompida / "data_quality.json").write_text('{"veredito": "PASS"}', encoding="utf-8")
    for nome in ARQUIVOS_GRUPO:
        (results / nome).write_text("conteúdo\n", encoding="utf-8")
    return results


def _importar(results: Path, catalogo: Path, uri: str, artifacts: Path, **kw):
    return imp.importar(results, catalogo, uri, artifact_root=artifacts, limite_mb=LIMITE_MB, log=lambda *_: None, **kw)


def _uri(raiz: Path) -> str:
    return f"sqlite:///{(raiz / 'mlflow.db').as_posix()}"


@pytest.fixture(scope="module")
def ambiente(tmp_path_factory: pytest.TempPathFactory):
    raiz = tmp_path_factory.mktemp("pesquisa")
    results = _montar_results(raiz)
    catalogo = _escrever_catalogo(raiz / "catalogo.yaml", _catalogo_padrao())
    uri, artifacts = _uri(raiz), raiz / "artifacts"
    resumo = _importar(results, catalogo, uri, artifacts)
    client = MlflowClient(tracking_uri=uri)
    todas = client.search_runs([e.experiment_id for e in client.search_experiments()], max_results=10_000)
    return {
        "raiz": raiz,
        "results": results,
        "catalogo": catalogo,
        "uri": uri,
        "artifacts": artifacts,
        "resumo": resumo,
        "client": client,
        "runs": todas,
    }


def _metrics_json(results: Path, rid: str) -> dict:
    return json.loads((results / rid / "metrics.json").read_text(encoding="utf-8"))


def _iguais(a: float, b: float) -> bool:
    """Igualdade exata; NaN só é igual a NaN."""
    if math.isnan(b):
        return math.isnan(a)
    return a == b


def _mae(runs, rid: str):
    maes = [r for r in runs if r.data.tags.get("run_id") == rid and r.data.tags.get("tipo") == "mae"]
    assert len(maes) == 1, f"{rid}: {len(maes)} runs mães"
    return maes[0]


def test_contagens_e_experimentos(ambiente):
    resumo, client, results = ambiente["resumo"], ambiente["client"], ambiente["results"]
    n_filhas = sum(len(_metrics_json(results, rid)["agregado"]) for rid in (RUN_URG, RUN_TOT))
    assert resumo.maes_criadas == 2
    assert resumo.filhas_criadas == n_filhas
    assert resumo.analises_criadas == 3  # pasta de análise, pasta interrompida e grupo de arquivos
    assert resumo.puladas == resumo.apagadas == 0
    nomes = {e.name for e in client.search_experiments()}
    assert {"alvo_urgencia/cetesb", "multihorizonte/cetesb", "analises", "interrompidas"} <= nomes
    assert len(ambiente["runs"]) == 2 + n_filhas + 3


def test_hierarquia_mae_filhas(ambiente):
    runs, results = ambiente["runs"], ambiente["results"]
    for rid, exp in ((RUN_URG, "alvo_urgencia/cetesb"), (RUN_TOT, "multihorizonte/cetesb")):
        mae = _mae(runs, rid)
        assert mae.info.run_name == rid
        assert ambiente["client"].get_experiment(mae.info.experiment_id).name == exp
        filhas = [r for r in runs if r.data.tags.get("mlflow.parentRunId") == mae.info.run_id]
        assert len(filhas) == len(_metrics_json(results, rid)["agregado"])
        assert all(f.data.tags["tipo"] == "filha" and f.data.tags["run_id"] == rid for f in filhas)
        assert all(f.info.experiment_id == mae.info.experiment_id for f in filhas)
        assert mae.data.tags["n_filhas"] == str(len(filhas))
        assert mae.data.tags["importacao_completa"] == "true"


def test_metricas_das_filhas_identicas_ao_json(ambiente):
    """Toda métrica agregada e por fold de cada filha é == à do metrics.json (NaN <-> NaN), e nada a mais."""
    runs, client, results = ambiente["runs"], ambiente["client"], ambiente["results"]
    for rid in (RUN_URG, RUN_TOT):
        metrics = _metrics_json(results, rid)
        mae = _mae(runs, rid)
        filhas = {
            (r.data.tags["modelo"], r.data.tags["feature_set"]): r
            for r in runs
            if r.data.tags.get("mlflow.parentRunId") == mae.info.run_id
        }
        assert len(filhas) == len(metrics["agregado"])
        for linha in metrics["agregado"]:
            r = filhas[(linha["model"], linha["feature_set"])]
            for chave, valor in linha.items():
                if chave in base.CHAVES_IDENTIFICADORAS_AGREGADO:
                    continue
                assert _iguais(r.data.metrics[chave], float(valor)), (rid, linha["model"], chave)
        esperadas: dict = {}
        for linha in metrics["por_fold"]:
            par = (linha["model"], linha["feature_set"])
            for chave, valor in linha.items():
                if chave in base.CHAVES_IDENTIFICADORAS_FOLD:
                    continue
                esperadas.setdefault(par, {}).setdefault(base.chave_por_fold(chave, linha["seed"]), {})[
                    linha["fold"]
                ] = float(valor)
        for par, por_chave in esperadas.items():
            r = filhas[par]
            registradas = {k for k in r.data.metrics if k.startswith("por_fold/")}
            assert registradas == set(por_chave), (rid, par, registradas ^ set(por_chave))
            for chave, por_step in por_chave.items():
                hist = {p.step: p.value for p in client.get_metric_history(r.info.run_id, chave)}
                assert set(hist) == set(por_step), (rid, par, chave)
                for step, valor in por_step.items():
                    assert _iguais(hist[step], valor), (rid, par, chave, step)


def test_tags_do_catalogo_e_nota(ambiente):
    runs, results = ambiente["runs"], ambiente["results"]
    manifest = json.loads((results / RUN_URG / "manifest.json").read_text(encoding="utf-8"))
    mae = _mae(runs, RUN_URG)
    t = mae.data.tags
    assert (t["papel"], t["familia"], t["base"], t["revisado"], t["fonte"]) == (
        "valida",
        "alvo_urgencia",
        "cetesb",
        "false",
        "teste",
    )
    assert t["motivo"] == f"motivo de teste para {RUN_URG}"
    assert t["commit"] == manifest["git_commit"]
    assert t["git_sujo"] == ("true" if manifest["git_sujo"] else "false")
    assert (t["modo"], t["status"], t["horizonte"], t["alvo"], t["provisorio"]) == (
        manifest["modo"],
        manifest["status"],
        "1",
        "urgencia",
        "true",
    )
    assert f"motivo de teste para {RUN_URG}" in t["mlflow.note.content"]
    assert "revisado: false" in t["mlflow.note.content"]
    assert _mae(runs, RUN_TOT).data.tags["alvo"] == "total"
    filha = next(r for r in runs if r.data.tags.get("mlflow.parentRunId") == mae.info.run_id)
    assert (filha.data.tags["papel"], filha.data.tags["base"]) == ("valida", "cetesb")


def test_datasets_com_digest_do_manifesto(ambiente):
    runs, results = ambiente["runs"], ambiente["results"]
    manifest = json.loads((results / RUN_URG / "manifest.json").read_text(encoding="utf-8"))
    mae = _mae(runs, RUN_URG)
    por_nome = {d.dataset.name: d for d in mae.inputs.dataset_inputs}
    esperados = {
        str(manifest[f"dataset_{k}"]).replace("\\", "/"): manifest[f"dataset_{k}_sha256"]
        for k in imp.DATASETS_MANIFESTO
        if f"dataset_{k}" in manifest
    }
    assert set(por_nome) == set(esperados)
    for nome, sha in esperados.items():
        d = por_nome[nome]
        assert d.dataset.digest == sha[: imp.MAX_DIGEST]
        assert json.loads(d.dataset.profile)["sha256"] == sha
        assert {t.key: t.value for t in d.tags}["sha256"] == sha


def test_artefatos_analise_interrompida_e_grupo(ambiente):
    runs, client = ambiente["runs"], ambiente["client"]
    analise = next(r for r in runs if r.data.tags.get("run_id") == ANALISE)
    assert analise.data.tags["tipo"] == "analise" and analise.data.tags["papel"] == "analise"
    assert client.get_experiment(analise.info.experiment_id).name == "analises"
    raiz = {f.path for f in client.list_artifacts(analise.info.run_id)}
    assert "RELATORIO_DM.md" in raiz and "grande.bin" not in raiz
    assert {f.path for f in client.list_artifacts(analise.info.run_id, "h1")} == {"h1/dm_contrastes.csv"}
    assert "grande.bin" in analise.data.tags["arquivos_omitidos"]

    interrompida = next(r for r in runs if r.data.tags.get("run_id") == INTERROMPIDA)
    assert client.get_experiment(interrompida.info.experiment_id).name == "interrompidas"
    assert interrompida.data.tags["arquivos_omitidos"] == "nenhum"

    grupo = next(r for r in runs if r.data.tags.get("run_id") == GRUPO)
    assert {f.path for f in client.list_artifacts(grupo.info.run_id)} == set(ARQUIVOS_GRUPO)

    mae = _mae(runs, RUN_URG)
    da_mae = {f.path for f in client.list_artifacts(mae.info.run_id)}
    assert {"config.json", "manifest.json", "metrics.json", "summary.md", "figures"} <= da_mae
    assert imp.PREVISOES not in da_mae


def test_idempotente(ambiente):
    antes = {r.info.run_id for r in ambiente["runs"]}
    r2 = _importar(ambiente["results"], ambiente["catalogo"], ambiente["uri"], ambiente["artifacts"])
    assert (r2.maes_criadas, r2.filhas_criadas, r2.analises_criadas, r2.apagadas) == (0, 0, 0, 0)
    assert r2.puladas == 5 and r2.tags_atualizadas == 0
    client = ambiente["client"]
    depois = client.search_runs([e.experiment_id for e in client.search_experiments()], max_results=10_000)
    assert {r.info.run_id for r in depois} == antes


def test_falha_alto_pasta_fora_do_catalogo(ambiente, tmp_path: Path):
    catalogo = [e for e in _catalogo_padrao() if e["run_id"] != ANALISE]
    cat = _escrever_catalogo(tmp_path / "cat.yaml", catalogo)
    with pytest.raises(imp.ErroImportacao, match="fora do catálogo"):
        _importar(ambiente["results"], cat, _uri(tmp_path), tmp_path / "a")
    assert not (tmp_path / "mlflow.db").exists() or not MlflowClient(_uri(tmp_path)).search_runs(["0"])


def test_falha_alto_catalogo_cita_inexistente(ambiente, tmp_path: Path):
    catalogo = [*_catalogo_padrao(), _entrada("nao_existe_full_1", "run", "x", "cetesb", "valida")]
    cat = _escrever_catalogo(tmp_path / "cat.yaml", catalogo)
    with pytest.raises(imp.ErroImportacao, match="inexistentes"):
        _importar(ambiente["results"], cat, _uri(tmp_path), tmp_path / "a")


def test_falha_alto_chave_ausente_e_tipo_errado(ambiente, tmp_path: Path):
    sem_chave = _catalogo_padrao()
    del sem_chave[0]["fonte"]
    with pytest.raises(imp.ErroImportacao, match="faltam chaves"):
        imp.carregar_catalogo(_escrever_catalogo(tmp_path / "a.yaml", sem_chave))
    papel_invalido = _catalogo_padrao()
    papel_invalido[0]["papel"] = "otima"
    with pytest.raises(imp.ErroImportacao, match="papel"):
        imp.carregar_catalogo(_escrever_catalogo(tmp_path / "b.yaml", papel_invalido))
    tipo_errado = _catalogo_padrao()
    tipo_errado[2]["tipo"] = "run"
    cat = imp.carregar_catalogo(_escrever_catalogo(tmp_path / "c.yaml", tipo_errado))
    with pytest.raises(imp.ErroImportacao, match="no disco"):
        imp.montar_unidades(ambiente["results"], cat)


def test_sincroniza_tags_e_recriar(ambiente, tmp_path: Path):
    """Catálogo revisado atualiza as tags sem recriar; ``recriar`` apaga e recria (só a análise, banco próprio)."""
    uri, artifacts = _uri(tmp_path), tmp_path / "artifacts"
    cat1 = _escrever_catalogo(tmp_path / "c1.yaml", _catalogo_padrao())
    _importar(ambiente["results"], cat1, uri, artifacts, runs=[ANALISE])
    revisado = _catalogo_padrao()
    revisado[2].update({"papel": "registro", "revisado": True, "motivo": "revisado"})
    cat2 = _escrever_catalogo(tmp_path / "c2.yaml", revisado)
    r = _importar(ambiente["results"], cat2, uri, artifacts, runs=[ANALISE])
    assert (r.analises_criadas, r.puladas, r.tags_atualizadas) == (0, 1, 1)
    client = MlflowClient(tracking_uri=uri)
    ids = [e.experiment_id for e in client.search_experiments()]
    (run,) = client.search_runs(ids, filter_string=f"tags.run_id = '{ANALISE}'")
    assert (run.data.tags["papel"], run.data.tags["revisado"], run.data.tags["motivo"]) == (
        "registro",
        "true",
        "revisado",
    )
    assert "revisado pelo pesquisador" in run.data.tags["mlflow.note.content"]
    r3 = _importar(ambiente["results"], cat2, uri, artifacts, runs=[ANALISE], recriar=True)
    assert (r3.apagadas, r3.analises_criadas) == (1, 1)
    (novo,) = client.search_runs(ids, filter_string=f"tags.run_id = '{ANALISE}'")
    assert novo.info.run_id != run.info.run_id


def test_metricas_por_fold_sem_semente():
    linhas = [
        {"model": "xgboost", "feature_set": "AR", "fold": f, "teste_inicio": "x", "teste_fim": "y", "MAE": 1.5 * f}
        for f in (1, 2)
    ]
    metricas, sem = imp.metricas_por_fold_pesquisa(linhas, "run", 0)
    assert sem and [(m.key, m.step, m.value) for m in metricas] == [("por_fold/MAE", 1, 1.5), ("por_fold/MAE", 2, 3.0)]
    with pytest.raises(imp.ErroImportacao):
        imp.metricas_por_fold_pesquisa([linhas[0], {**linhas[1], "seed": 42}], "run", 0)


def test_datasets_nulos_e_sem_sha():
    sha = "a" * 64
    manifest = {
        "dataset_sih": r"data\processed\sih.parquet",
        "dataset_sih_sha256": sha,
        "dataset_meteo": None,
        "dataset_meteo_sha256": None,
        "dataset_cetesb": "data/processed/cetesb_pm25_daily.csv",
    }
    datasets, sem_sha = imp.datasets_do_manifesto(manifest, "run")
    assert [(d.dataset.name, d.dataset.digest) for d in datasets] == [("data/processed/sih.parquet", sha[:36])]
    assert sem_sha == ["cetesb:data/processed/cetesb_pm25_daily.csv"]
    with pytest.raises(imp.ErroImportacao):
        imp.datasets_do_manifesto({**manifest, "dataset_sih_sha256": "xyz"}, "run")

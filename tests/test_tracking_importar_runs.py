"""Aceite do WP2: cada métrica no MLflow é idêntica (``==``) à do ``metrics.json`` de origem.

Usa ``tmp_path`` como tracking URI e uma única pasta de ``results/runs/`` para rodar em segundos.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

pytest.importorskip("mlflow", reason="dependência opcional [tracking]: mlflow")

from mlflow import MlflowClient  # noqa: E402

from tracking import importar_runs as imp  # noqa: E402

RUN_URGENCIA = "ur_h1_cetesb_cetesb_full_20261116-191534"
RUN_TOTAL = "mh_h5_cetesb_cetesb_full_20261110-211453"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "runs"


def _uri(tmp_path: Path) -> str:
    return (tmp_path / "mlruns").as_uri()


@pytest.fixture(scope="module")
def importado(tmp_path_factory: pytest.TempPathFactory):
    """Importa uma run uma vez para o módulo inteiro (MLflow file store em tmp)."""
    tmp = tmp_path_factory.mktemp("mlflow")
    uri = _uri(tmp)
    resumo = imp.importar(RESULTS_DIR, uri, runs=[RUN_URGENCIA], recriar=False, log=lambda *_: None)
    metrics = json.loads((RESULTS_DIR / RUN_URGENCIA / "metrics.json").read_text(encoding="utf-8"))
    _, runs = _runs_do_experimento(MlflowClient(tracking_uri=uri), "h1_urgencia")
    return uri, resumo, metrics, runs


def _runs_do_experimento(client: MlflowClient, nome: str):
    exp = client.get_experiment_by_name(nome)
    assert exp is not None, f"experimento {nome} não criado"
    return exp, client.search_runs([exp.experiment_id], max_results=10_000)


def _iguais(a: float, b: float) -> bool:
    """Igualdade exata; NaN só é igual a NaN (o importador registra NaN como NaN)."""
    if math.isnan(b):
        return math.isnan(a)
    return a == b


def test_experimento_e_contagem(importado):
    uri, resumo, metrics, runs = importado
    client = MlflowClient(tracking_uri=uri)
    assert resumo.experimentos == ["h1_urgencia"]
    assert resumo.criadas == len(metrics["agregado"]) == len(runs)
    assert resumo.puladas == 0 and resumo.apagadas == 0
    assert client.get_experiment_by_name("h1_total") is None


def test_metricas_agregadas_identicas(importado):
    _, _, metrics, runs = importado
    por_par = {(r.data.tags["modelo"], r.data.tags["feature_set"]): r for r in runs}
    assert len(por_par) == len(runs), "pares (modelo, feature_set) duplicados no MLflow"

    comparadas = 0
    for linha in metrics["agregado"]:
        run = por_par[(linha["model"], linha["feature_set"])]
        for chave, valor in linha.items():
            if chave in ("model", "feature_set"):
                continue
            assert chave in run.data.metrics, f"{linha['model']}/{linha['feature_set']}: métrica {chave} ausente"
            assert _iguais(run.data.metrics[chave], float(valor)), (
                f"{linha['model']}/{linha['feature_set']}: {chave} MLflow={run.data.metrics[chave]!r} json={valor!r}"
            )
            comparadas += 1
            if isinstance(valor, float) and math.isnan(valor):
                assert chave in run.data.tags["metricas_nan"].split(",")
    assert comparadas == sum(len(linha) - 2 for linha in metrics["agregado"])


def test_metricas_por_fold_identicas(importado):
    uri, _, metrics, runs = importado
    client = MlflowClient(tracking_uri=uri)
    por_par = {(r.data.tags["modelo"], r.data.tags["feature_set"]): r for r in runs}

    # historico[(modelo, fs)][chave] = {step: valor}
    historico: dict = {}
    comparadas = 0
    for linha in metrics["por_fold"]:
        par = (linha["model"], linha["feature_set"])
        run = por_par[par]
        hist_run = historico.setdefault(par, {})
        for chave, valor in linha.items():
            if chave in imp.CHAVES_IDENTIFICADORAS_FOLD:
                continue
            chave_mlflow = imp.chave_por_fold(chave, linha["seed"])
            if chave_mlflow not in hist_run:
                pontos = client.get_metric_history(run.info.run_id, chave_mlflow)
                hist_run[chave_mlflow] = {p.step: p.value for p in pontos}
                assert len(pontos) == len(hist_run[chave_mlflow]), f"{par}: steps duplicados em {chave_mlflow}"
            assert linha["fold"] in hist_run[chave_mlflow], f"{par}: fold {linha['fold']} ausente em {chave_mlflow}"
            assert _iguais(hist_run[chave_mlflow][linha["fold"]], float(valor)), (
                f"{par}: {chave_mlflow} fold {linha['fold']} MLflow={hist_run[chave_mlflow][linha['fold']]!r} json={valor!r}"
            )
            comparadas += 1
    esperado = sum(len([k for k in linha if k not in imp.CHAVES_IDENTIFICADORAS_FOLD]) for linha in metrics["por_fold"])
    assert comparadas == esperado
    # nada a mais no MLflow: toda métrica por fold registrada tem origem no json
    for par, run in por_par.items():
        registradas = {k for k in run.data.metrics if k.startswith("por_fold/")}
        assert registradas == set(historico[par]), (
            f"{par}: métricas por fold sem origem: {registradas ^ set(historico[par])}"
        )


def test_params_e_tags(importado):
    _, _, _, runs = importado
    config = json.loads((RESULTS_DIR / RUN_URGENCIA / "config.json").read_text(encoding="utf-8"))
    manifest = json.loads((RESULTS_DIR / RUN_URGENCIA / "manifest.json").read_text(encoding="utf-8"))
    xgb = [r for r in runs if r.data.tags["modelo"] == "xgboost" and r.data.tags["feature_set"] == "AR_CAL"]
    assert len(xgb) == 1
    run = xgb[0]
    assert run.data.tags["run_id"] == RUN_URGENCIA
    assert run.data.tags["commit"] == manifest["git_commit"]
    assert run.data.tags["git_sujo"] == ("true" if manifest["git_sujo"] else "false")
    assert run.data.tags["provisorio"] == "true"
    assert run.data.tags["horizonte"] == str(config["experimento"]["horizonte"])
    assert run.data.tags["alvo"] == "urgencia"
    assert run.info.status == "FINISHED"
    assert run.data.params["modelo.n_estimators"] == str(config["modelos"]["xgboost"]["n_estimators"])
    assert run.data.params["modelo.objetivo"] == config["modelos"]["xgboost"]["objetivo"]
    assert run.data.params["experimento.horizonte"] == str(config["experimento"]["horizonte"])
    assert run.data.params["split.n_folds"] == str(config["split"]["n_folds"])
    assert run.data.params["experimento.lags_alvo"] == json.dumps(config["experimento"]["lags_alvo"])


def test_idempotente(importado):
    """Segunda importação não cria nada; a run MLflow de cada par é a mesma de antes."""
    uri, _, metrics, runs = importado
    resumo2 = imp.importar(RESULTS_DIR, uri, runs=[RUN_URGENCIA], log=lambda *_: None)
    assert resumo2.criadas == 0 and resumo2.apagadas == 0
    assert resumo2.puladas == len(metrics["agregado"])
    _, depois = _runs_do_experimento(MlflowClient(tracking_uri=uri), "h1_urgencia")
    assert {r.info.run_id for r in depois} == {r.info.run_id for r in runs}


def test_recriar(importado):
    """``recriar=True`` apaga (soft delete) as runs antigas e cria novas, sem duplicar as ativas."""
    uri, resumo1, _, runs = importado
    r2 = imp.importar(RESULTS_DIR, uri, runs=[RUN_URGENCIA], recriar=True, log=lambda *_: None)
    assert r2.apagadas == resumo1.criadas and r2.criadas == resumo1.criadas and r2.puladas == 0
    _, ativas = _runs_do_experimento(MlflowClient(tracking_uri=uri), "h1_urgencia")
    assert len(ativas) == resumo1.criadas
    assert not ({r.info.run_id for r in ativas} & {r.info.run_id for r in runs}), "run antiga continua ativa"


def test_alvo_e_horizonte_sem_mlflow():
    urg = imp.carregar_run(RESULTS_DIR / RUN_URGENCIA)
    tot = imp.carregar_run(RESULTS_DIR / RUN_TOTAL)
    assert (imp.alvo_da_run(urg), imp.horizonte_da_run(urg)) == ("urgencia", 1)
    assert (imp.alvo_da_run(tot), imp.horizonte_da_run(tot)) == ("total", 5)
    assert imp.nome_experimento(5, "total") == "h5_total"


def test_falha_alto_sem_artefato(tmp_path: Path):
    pasta = tmp_path / "run_x"
    pasta.mkdir()
    (pasta / "config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(imp.ErroImportacao):
        imp.carregar_run(pasta)
    with pytest.raises(imp.ErroImportacao):
        imp.importar(RESULTS_DIR, _uri(tmp_path), runs=["nao_existe"], log=lambda *_: None)

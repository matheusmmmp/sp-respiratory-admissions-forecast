"""Registro ao vivo no MLflow pelo runner (``--mlflow``; ``tracking/registro_mlflow.py``).

Provas exigidas:

(a) sem ``--mlflow`` o runner produz os mesmos bytes que o runner de ANTES dos ganchos
    (``COMMIT_REFERENCIA``, extraído com ``git archive``) e não importa ``mlflow``;
(b) com ``--mlflow`` os mesmos arquivos saem idênticos aos da execução sem a opção;
e, no MLflow: hierarquia mãe/filhas, métricas das filhas == ``metrics.json``, um LoggedModel por
(modelo, conjunto, fold, semente) e cada modelo recarregado reproduz ``predictions.csv``.

As três execuções do runner (referência, sem e com ``--mlflow``) rodam em subprocessos, uma vez
por módulo, com uma config ainda menor que ``configs/smoke_mlflow.yaml`` (um conjunto, 2 folds de
14 dias, 2 sementes, os sete modelos, treino a partir de 2022) — 20 a 30 s cada na CPU; o módulo
inteiro leva cerca de 1,5 min. Quando o commit de referência não está no clone, a prova (a)
**falha** se a variável ``CI`` for ``true`` (o job ``pytest`` do CI faz checkout com ``fetch-depth: 0``,
então a ausência é erro de configuração) e é pulada fora do CI (clone raso local; contêiner Docker, onde o
``.git`` é excluído pelo ``.dockerignore`` e ``CI`` não é repassado ao ``docker run``).
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

mlflow = pytest.importorskip("mlflow")

RAIZ = Path(__file__).resolve().parents[1]
CONFIG_LEVE = RAIZ / "configs" / "smoke_mlflow.yaml"
#: Último commit do runner sem os ganchos do MLflow — a saída de referência da prova (a).
#: Se o runner mudar de propósito a sua saída depois deste commit, a prova (a) passa a falhar: atualize-o.
COMMIT_REFERENCIA = "2be070bedeaff286fcca4682c7d52de3ccaa4782"
NOME_RUN = "teste_runner_mlflow"
#: Arquivos comparados byte a byte entre execuções.
ARQUIVOS_IDENTICOS = (
    "metrics.json",
    "model_comparison.csv",
    "metrics_by_fold.csv",
    "folds.csv",
    "feature_ablation.csv",
)
#: Tolerância de reprodução ao recarregar (LSTM: até 1e-6; os demais: 1e-9).
TOLERANCIA = {"lstm": 1e-6}
TOLERANCIA_PADRAO = 1e-9

SCRIPT_RUNNER = r"""
import json, sys
sys.argv = ["run_preliminary", "--config", sys.argv[1], "--smoke", *sys.argv[2:]]
from src.experiments import run_preliminary as R
R.main()
mods = sorted(m for m in sys.modules if m == "mlflow" or m.startswith("mlflow.") or m == "tracking.registro_mlflow")
print("MODULOS_MLFLOW=" + json.dumps(mods))
"""


# ------------------------------------------------------------------------------------ execuções
def _config_teste(destino: Path) -> Path:
    """``smoke_mlflow.yaml`` reduzida: só AR_CAL, folds de 14 dias, treino a partir de 2022."""
    cfg = yaml.safe_load(CONFIG_LEVE.read_text(encoding="utf-8"))
    cfg["run"]["nome"] = NOME_RUN
    cfg["dados"]["inicio"] = "2022-01-01"
    cfg["smoke"].update(
        n_folds=2,
        dias_teste=14,
        dias_validacao=30,
        treino_minimo=365,
        sementes=[42, 43],
        epocas=2,
        n_estimators=20,
        feature_sets=["AR_CAL"],
    )
    caminho = destino / "teste_runner_mlflow.yaml"
    caminho.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def _rodar(raiz: Path, config: Path, *extra: str) -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "TF_CPP_MIN_LOG_LEVEL": "2", "MPLBACKEND": "Agg"}
    env.pop("MLFLOW_TRACKING_URI", None)
    proc = subprocess.run(
        [sys.executable, "-c", SCRIPT_RUNNER, str(config), *extra],
        cwd=raiz,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    if proc.returncode != 0:
        raise AssertionError(f"runner falhou (rc={proc.returncode}):\n{proc.stdout[-3000:]}\n{proc.stderr[-5000:]}")
    run_id = re.search(r"^RUN_ID: (\S+)", proc.stdout, re.M).group(1)
    modulos = json.loads(re.search(r"^MODULOS_MLFLOW=(.*)$", proc.stdout, re.M).group(1))
    return {"run_id": run_id, "pasta": raiz / "reports" / "experiments" / run_id, "modulos": modulos}


@pytest.fixture(scope="module")
def config_teste(tmp_path_factory) -> Path:
    return _config_teste(tmp_path_factory.mktemp("config"))


@pytest.fixture(scope="module")
def run_sem_mlflow(config_teste):
    r = _rodar(RAIZ, config_teste)
    yield r
    shutil.rmtree(r["pasta"], ignore_errors=True)


@pytest.fixture(scope="module")
def run_com_mlflow(config_teste, tmp_path_factory):
    base = tmp_path_factory.mktemp("mlflow")
    uri = f"sqlite:///{(base / 'mlflow.db').as_posix()}"
    r = _rodar(RAIZ, config_teste, "--mlflow", "--mlflow-uri", uri)
    r["uri"] = uri
    mlflow.set_tracking_uri(uri)
    r["client"] = mlflow.MlflowClient(uri)
    r["metrics"] = json.loads((r["pasta"] / "metrics.json").read_text(encoding="utf-8"))
    r["manifest"] = json.loads((r["pasta"] / "manifest.json").read_text(encoding="utf-8"))
    yield r
    shutil.rmtree(r["pasta"], ignore_errors=True)


@pytest.fixture(scope="module")
def run_referencia(config_teste, tmp_path_factory):
    """O runner do ``COMMIT_REFERENCIA`` (sem ganchos), extraído com ``git archive``, sem tocar o .git."""
    try:
        ok = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{COMMIT_REFERENCIA}^{{commit}}"], cwd=RAIZ, capture_output=True, timeout=30
            ).returncode
            == 0
        )
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        motivo = f"commit de referência {COMMIT_REFERENCIA[:7]} indisponível neste clone (raso? sem .git?)"
        if os.environ.get("CI", "").strip().lower() == "true":
            pytest.fail(f"{motivo}; no CI o checkout precisa de fetch-depth: 0", pytrace=False)
        pytest.skip(f"{motivo}; fora do CI a prova (a) é pulada")
    destino = tmp_path_factory.mktemp("referencia")
    tar = subprocess.run(
        ["git", "archive", "--format=tar", COMMIT_REFERENCIA, "src", "data/processed"],
        cwd=RAIZ,
        capture_output=True,
        check=True,
        timeout=300,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as arq:
        # `filter` só existe a partir do Python 3.11.4; o tar vem do próprio repositório
        extras = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
        arq.extractall(destino, **extras)
    return _rodar(destino, config_teste)


# --------------------------------------------------------------------------------- comparação
def _sem_chaves_volateis(valor, extras: frozenset = frozenset()):
    """Tira do manifesto os campos de tempo e de RUN_ID (e, se pedido, os de git)."""
    volateis = {"run_id", "timestamp", "inicio", "fim"} | set(extras)
    if isinstance(valor, dict):
        return {
            k: _sem_chaves_volateis(v, extras)
            for k, v in valor.items()
            if k not in volateis and not str(k).startswith("tempo")
        }
    if isinstance(valor, list):
        return [_sem_chaves_volateis(v, extras) for v in valor]
    return valor


def _comparar_saidas(a: dict, b: dict, ignorar_git: bool) -> None:
    for nome in ARQUIVOS_IDENTICOS:
        assert (a["pasta"] / nome).read_bytes() == (b["pasta"] / nome).read_bytes(), f"{nome} difere"
    pa = (a["pasta"] / "predictions.csv").read_text(encoding="utf-8").replace(a["run_id"], "<RUN_ID>")
    pb = (b["pasta"] / "predictions.csv").read_text(encoding="utf-8").replace(b["run_id"], "<RUN_ID>")
    assert pa == pb, "predictions.csv difere (fora a coluna run_id)"
    git = frozenset({"git_commit", "git_branch", "git_sujo", "proveniencia"}) if ignorar_git else frozenset()
    ma = _sem_chaves_volateis(json.loads((a["pasta"] / "manifest.json").read_text(encoding="utf-8")), git)
    mb = _sem_chaves_volateis(json.loads((b["pasta"] / "manifest.json").read_text(encoding="utf-8")), git)
    assert ma == mb, "manifest.json difere fora dos campos de tempo/RUN_ID"


def _igual(x: float, y: float) -> bool:
    return (math.isnan(x) and math.isnan(y)) or x == y


# ------------------------------------------------------------------------------------- provas
def test_sem_mlflow_nao_importa_mlflow(run_sem_mlflow):
    assert run_sem_mlflow["modulos"] == []


def test_sem_mlflow_identico_ao_runner_de_referencia(run_referencia, run_sem_mlflow):
    _comparar_saidas(run_referencia, run_sem_mlflow, ignorar_git=True)


def test_com_mlflow_identico_a_sem_mlflow(run_sem_mlflow, run_com_mlflow):
    assert "mlflow" in run_com_mlflow["modulos"]
    _comparar_saidas(run_sem_mlflow, run_com_mlflow, ignorar_git=False)


def _mae_e_filhas(r):
    c = r["client"]
    exp = c.get_experiment_by_name(NOME_RUN)
    assert exp is not None
    runs = c.search_runs([exp.experiment_id], filter_string=f"tags.run_id = '{r['run_id']}'", max_results=1000)
    maes = [x for x in runs if "mlflow.parentRunId" not in x.data.tags]
    assert len(maes) == 1
    filhas = [x for x in runs if x.data.tags.get("mlflow.parentRunId") == maes[0].info.run_id]
    assert len(filhas) == len(runs) - 1
    return exp, maes[0], filhas


def test_hierarquia_mae_filhas_e_artefatos(run_com_mlflow):
    r = run_com_mlflow
    c = r["client"]
    _, mae, filhas = _mae_e_filhas(r)
    man = r["manifest"]
    t = mae.data.tags
    assert mae.info.run_name == r["run_id"] and mae.info.status == "FINISHED"
    assert t["run_id"] == r["run_id"] and t["commit"] == str(man["git_commit"])
    assert t["git_sujo"] == ("true" if man["git_sujo"] else "false")
    assert (t["modo"], t["status"], t["horizonte"], t["alvo"], t["provisorio"]) == (
        "smoke",
        man["status"],
        "1",
        "total",
        "true",
    )
    assert t["config_sha256"] == man["config_sha256"]
    assert mae.data.params["run.nome"] == NOME_RUN

    pares = {(x["model"], x["feature_set"]) for x in r["metrics"]["agregado"]}
    assert {(f.data.tags["modelo"], f.data.tags["feature_set"]) for f in filhas} == pares
    assert all(f.info.status == "FINISHED" for f in filhas)

    artefatos = {a.path for a in c.list_artifacts(mae.info.run_id)}
    for nome in (
        "config.json",
        "manifest.json",
        "metrics.json",
        "summary.md",
        "predictions.csv",
        "model_comparison.csv",
        "metrics_by_fold.csv",
        "folds.csv",
        "figures",
        "modelos_registrados.json",
    ):
        assert nome in artefatos, nome

    entradas = {d.dataset.name: d.dataset for d in c.get_run(mae.info.run_id).inputs.dataset_inputs}
    for chave in ("sih", "cams", "cetesb", "meteo"):
        sha = man[f"dataset_{chave}_sha256"]
        assert entradas[chave].digest == sha[:36]
        assert json.loads(entradas[chave].profile)["sha256"] == sha


def test_metricas_das_filhas_iguais_ao_metrics_json(run_com_mlflow):
    r = run_com_mlflow
    c = r["client"]
    _, _, filhas = _mae_e_filhas(r)
    por_par = {(f.data.tags["modelo"], f.data.tags["feature_set"]): f for f in filhas}
    for linha in r["metrics"]["agregado"]:
        f = por_par[(linha["model"], linha["feature_set"])]
        for k, v in linha.items():
            if k in ("model", "feature_set"):
                continue
            assert _igual(f.data.metrics[k], float(v)), (linha["model"], k)
    for linha in r["metrics"]["por_fold"]:
        f = por_par[(linha["model"], linha["feature_set"])]
        for k, v in linha.items():
            if k in ("model", "feature_set", "seed", "fold", "teste_inicio", "teste_fim"):
                continue
            hist = c.get_metric_history(f.info.run_id, f"por_fold/seed{linha['seed']}/{k}")
            no_passo = [m.value for m in hist if m.step == linha["fold"]]
            assert len(no_passo) == 1 and _igual(no_passo[0], float(v)), (linha["model"], k, linha["fold"])


def _modelos(r):
    exp, _, filhas = _mae_e_filhas(r)
    ids_filhas = {f.info.run_id: f for f in filhas}
    mods = r["client"].search_logged_models(experiment_ids=[exp.experiment_id], max_results=10_000)
    return [m for m in mods if m.source_run_id in ids_filhas], ids_filhas


def test_um_modelo_salvo_por_fold_e_semente(run_com_mlflow):
    r = run_com_mlflow
    mods, filhas = _modelos(r)
    esperados = sorted((x["model"], x["feature_set"], x["fold"], x["seed"]) for x in r["metrics"]["por_fold"])
    salvos = sorted(
        (m.tags["modelo"], m.tags["feature_set"], int(m.tags["fold"]), int(m.tags["semente"])) for m in mods
    )
    assert salvos == esperados
    assert len(mods) == 18  # 2 folds x (naive + seasonal + sarimax + gam_nb + ingarch_nb + 2 sementes x (xgb + lstm))
    for m in mods:
        assert m.tags["run_id"] == r["run_id"]
        filha = filhas[m.source_run_id].data.tags
        assert (filha["modelo"], filha["feature_set"]) == (m.tags["modelo"], m.tags["feature_set"])
        assert str(m.status).endswith("READY")


def test_modelo_recarregado_reproduz_predictions(run_com_mlflow, capsys):
    from mlflow.models import Model

    r = run_com_mlflow
    pred = pd.read_csv(r["pasta"] / "predictions.csv", float_precision="round_trip")
    mods, _ = _modelos(r)
    desvio: dict[str, float] = {}
    for m in mods:
        t = m.tags
        local = mlflow.artifacts.download_artifacts(f"models:/{m.model_id}")
        modelo_mlflow = Model.load(local)
        assert modelo_mlflow.signature is not None
        entrada = modelo_mlflow.load_input_example(local)
        yhat = np.asarray(mlflow.pyfunc.load_model(local).predict(entrada), dtype=float).reshape(-1)
        g = pred[
            (pred["model"] == t["modelo"])
            & (pred["feature_set"] == t["feature_set"])
            & (pred["seed"] == int(t["semente"]))
            & (pred["fold"] == int(t["fold"]))
        ].sort_values("target_date")
        y_pred = g["y_pred"].to_numpy(dtype=float)
        assert yhat.shape == y_pred.shape
        d = float(np.max(np.abs(yhat - y_pred)))
        desvio[t["modelo"]] = max(desvio.get(t["modelo"], 0.0), d)
        assert d <= TOLERANCIA.get(t["modelo"], TOLERANCIA_PADRAO), (t, d)

        # o formato nativo de cada modelo carrega sozinho
        if t["modelo"] == "xgboost":
            import mlflow.xgboost as mlflow_xgboost

            nativo = mlflow_xgboost.load_model(local)
            y2 = np.asarray(nativo.predict(entrada.to_numpy(dtype=np.float32)), dtype=float)
            assert float(np.max(np.abs(y2 - y_pred))) <= TOLERANCIA_PADRAO
        elif t["modelo"] == "lstm":
            import mlflow.keras as mlflow_keras

            rede = mlflow_keras.load_model(str(Path(local) / "artifacts" / "rede_keras"))
            assert rede.input_shape[1] == 28
        elif t["modelo"] in ("sarimax", "gam_nb"):
            import mlflow.statsmodels as mlflow_statsmodels

            assert mlflow_statsmodels.load_model(str(Path(local) / "artifacts" / "resultado_statsmodels")) is not None
    assert set(desvio) == {"naive", "seasonal_naive", "xgboost", "lstm", "sarimax", "gam_nb", "ingarch_nb"}
    with capsys.disabled():
        print("\ndesvio máximo ao recarregar, por modelo:", json.dumps(desvio))


def test_cli_mlflow_exige_uri(monkeypatch, capsys):
    from src.experiments import run_preliminary as R

    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    monkeypatch.setattr(sys, "argv", ["run_preliminary", "--config", str(CONFIG_LEVE), "--smoke", "--mlflow"])
    with pytest.raises(SystemExit) as exc:
        R.main()
    assert exc.value.code == 2
    assert "MLFLOW_TRACKING_URI" in capsys.readouterr().err
    monkeypatch.setattr(sys, "argv", ["run_preliminary", "--config", str(CONFIG_LEVE), "--smoke", "--mlflow-uri", "x"])
    with pytest.raises(SystemExit):
        R.main()

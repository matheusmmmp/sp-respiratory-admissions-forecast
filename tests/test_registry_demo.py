"""Model Registry dos modelos de demonstração (``tracking/registrar_modelos_demo.py``, ``api/registro.py``).

Provas:

* o registro cria os 3 modelos ``sp-resp-forecast-xgb-h{1,7,30}``, cada um com o apelido
  ``champion`` numa versão cujas tags ``sha256_modelo``/``sha256`` batem com ``metadata.json``;
* segunda execução não cria versões nem runs novas (idempotência pelo ``sha256_modelo``);
* ``models:/...@champion`` prevê exatamente o mesmo que o ``.ubj`` (|Δ| < 1e-9) em todas as linhas
  da matriz de features de cada h;
* a API com ``MODELO_FONTE=mlflow`` responde ``/forecast`` igual ao modo padrão;
* sem ``MODELO_FONTE``, a API não importa ``mlflow`` (subprocesso limpo, ``sys.modules``);
* sha256 divergente falha alto: no registro (``.ubj`` ≠ metadata) e na API (tag ≠ metadata).

O Registry fica num SQLite em ``tmp_path`` (um por módulo); nada é escrito em ``mlruns/``.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

mlflow = pytest.importorskip("mlflow")

from fastapi.testclient import TestClient  # noqa: E402
from mlflow import MlflowClient  # noqa: E402

from models_demo import comum  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
HORIZONTES = (1, 7, 30)
NOMES = {h: f"sp-resp-forecast-xgb-h{h}" for h in HORIZONTES}
ORIGENS = ("2020-03-15", "2023-01-12", "2024-06-30")


@pytest.fixture(scope="module")
def metadata() -> dict:
    return json.loads(comum.CAMINHO_METADATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registry(tmp_path_factory):
    from tracking import registrar_modelos_demo as reg

    pasta = tmp_path_factory.mktemp("registry")
    uri = f"sqlite:///{(pasta / 'mlflow.db').as_posix()}"
    primeira = reg.registrar(uri)
    yield {"uri": uri, "primeira": primeira, "client": MlflowClient(uri)}
    mlflow.set_tracking_uri(None)


def _versoes(client, nome):
    return client.search_model_versions(f"name = '{nome}'")


def _n_runs(client) -> int:
    exp = client.get_experiment_by_name("modelos_demo")
    return len(client.search_runs([exp.experiment_id]))


def test_registro_cria_tres_modelos_com_champion(registry, metadata):
    client = registry["client"]
    assert [r["h"] for r in registry["primeira"]] == list(HORIZONTES)
    assert all(r["criada"] for r in registry["primeira"])
    registrados = {m.name for m in client.search_registered_models()}
    assert registrados == set(NOMES.values())
    for h, nome in NOMES.items():
        rm = client.get_registered_model(nome)
        assert "demonstration model, not a dissertation result" in rm.description.lower()
        assert "models_demo/MODEL_CARD.md" in rm.description
        v = client.get_model_version_by_alias(nome, "champion")
        sha = metadata["modelos"][str(h)]["arquivo_sha256"]
        assert v.tags["sha256_modelo"] == sha and v.tags["sha256"] == sha
        assert v.tags["versao_dados"] == metadata["versao"]
        run = client.get_run(v.run_id)
        assert run.data.tags["demonstracao"] == "true" and run.data.tags["provisorio"] == "true"
        assert run.data.tags["horizonte"] == str(h) and run.data.tags["sha256_modelo"] == sha
        assert run.data.tags["fonte"] == "models_demo/metadata.json"
        assert run.data.params["features"] == ",".join(metadata["modelos"][str(h)]["features"])
        assert run.data.params["versao"] == metadata["versao"]
        artefatos = {a.path for a in client.list_artifacts(v.run_id)}
        assert "MODEL_CARD.md" in artefatos


def test_segunda_execucao_nao_cria_versoes(registry):
    from tracking import registrar_modelos_demo as reg

    client = registry["client"]
    antes = {h: [v.version for v in _versoes(client, n)] for h, n in NOMES.items()}
    runs_antes = _n_runs(client)
    segunda = reg.registrar(registry["uri"])
    assert not any(r["criada"] for r in segunda)
    assert all(r["apelido"] == "mantido" for r in segunda)
    assert {h: [v.version for v in _versoes(client, n)] for h, n in NOMES.items()} == antes
    assert all(len(v) == 1 for v in antes.values())
    assert _n_runs(client) == runs_antes


@pytest.mark.parametrize("h", HORIZONTES)
def test_champion_preve_igual_ao_ubj(registry, h):
    import mlflow.xgboost

    mlflow.set_tracking_uri(registry["uri"])
    do_registry = mlflow.xgboost.load_model(f"models:/{NOMES[h]}@champion")
    do_ubj = comum.carregar_modelo(h)
    ds, colunas, _ = comum.construir_para(h)
    X = comum.matriz(ds, colunas)
    a, b = do_registry.predict(X), do_ubj.predict(X)
    assert len(a) == len(X) > 2000
    assert np.max(np.abs(a.astype(float) - b.astype(float))) < 1e-9


def test_api_modo_mlflow_igual_ao_padrao(registry, monkeypatch):
    from api.main import app

    monkeypatch.delenv("MODELO_FONTE", raising=False)
    with TestClient(app) as c:
        padrao = {(h, o): c.get("/forecast", params={"h": h, "origem": o}).json() for h in HORIZONTES for o in ORIGENS}
        saude_padrao = c.get("/health").json()

    monkeypatch.setenv("MODELO_FONTE", "mlflow")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", registry["uri"])
    with TestClient(app) as c:
        for (h, o), esperado in padrao.items():
            r = c.get("/forecast", params={"h": h, "origem": o})
            assert r.status_code == 200, r.text
            assert r.json() == esperado
        assert c.get("/health").json() == saude_padrao


def test_api_sem_modelo_fonte_nao_importa_mlflow():
    codigo = (
        "import sys\n"
        "from api.main import ServicoPrevisao\n"
        "s = ServicoPrevisao.carregar()\n"
        "assert sorted(s.por_h) == [1, 7, 30]\n"
        "assert 'mlflow' not in sys.modules, 'mlflow imported'\n"
        "assert 'api.registro' not in sys.modules, 'api.registro imported'\n"
        "print('ok')\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in ("MODELO_FONTE", "MLFLOW_TRACKING_URI")}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip().endswith("ok")


def test_registro_falha_com_sha_divergente(tmp_path, metadata):
    from tracking import registrar_modelos_demo as reg

    meta = copy.deepcopy(metadata)
    meta["modelos"]["7"]["arquivo_sha256"] = "0" * 64
    uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    with pytest.raises(RuntimeError, match="diverge de metadata.json"):
        reg.registrar(uri, meta=meta)
    # nada escrito: a conferência dos três .ubj vem antes de abrir o MLflow
    assert not (tmp_path / "mlflow.db").exists()


def test_api_falha_com_sha_da_tag_divergente(registry, metadata, monkeypatch):
    from api import registro

    monkeypatch.setenv("MODELO_FONTE", "mlflow")
    monkeypatch.setenv("MLFLOW_TRACKING_URI", registry["uri"])
    info = copy.deepcopy(metadata["modelos"]["1"])
    assert isinstance(registro.carregar_modelo(1, info), type(comum.carregar_modelo(1)))
    info["arquivo_sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="sha256_modelo"):
        registro.carregar_modelo(1, info)


def test_modelo_fonte_invalida_falha_alto(monkeypatch):
    from api import registro

    monkeypatch.setenv("MODELO_FONTE", "s3")
    with pytest.raises(RuntimeError, match="not supported"):
        registro.fonte()
    monkeypatch.setenv("MODELO_FONTE", "mlflow")
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    with pytest.raises(RuntimeError, match="requires MLFLOW_TRACKING_URI"):
        registro.carregar_modelo(1, {"arquivo_sha256": "x", "features": []})

"""Acceptance tests of the demonstration forecast API (WP4).

What is checked
---------------
* ``GET /health`` answers 200 with the model version and the horizons.
* ``GET /forecast`` returns, for every horizon, exactly the prediction of the
  saved model called directly on features built by the canonical
  ``construir_dataset`` with the lags of the dissertation config (the feature
  construction here is written independently of ``models_demo.comum`` on
  purpose, so the API and the test cannot share a mistake).
* 422 on invalid ``h``, origin outside the history, origin without enough
  history for the lags, target beyond the end of the history, bad date.
* The leakage rule ``L >= h``: every feature name that carries a lag
  (``<var>_lag<L>``) has ``L >= h``; the only unlagged features are calendar
  columns of the target date; and ``y_lag<L>`` at target ``u`` really is the
  series value at ``u - L``, i.e. observed on or before the origin.

The tests never train. They need the files in ``models_demo/`` and FAIL (not
skip) if they are missing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient
from xgboost import XGBRegressor

from src.features.forecasting_features import construir_dataset

RAIZ = Path(__file__).resolve().parents[1]
HORIZONTES = (1, 7, 30)
# written out on purpose (not imported from models_demo.comum): the test must not inherit a wrong mapping
CONFIGS = {
    1: RAIZ / "configs/h1_v02_cetesb_cetesb_classicos.yaml",
    7: RAIZ / "configs/multihorizonte/mh_h7_cetesb_cetesb.yaml",
    30: RAIZ / "configs/multihorizonte/mh_h30_cetesb_cetesb.yaml",
}
PASTA_MODELOS = RAIZ / "models_demo"
MODELOS = {h: PASTA_MODELOS / f"xgboost_ar_cal_h{h}.ubj" for h in HORIZONTES}
METADATA = PASTA_MODELOS / "metadata.json"
COLUNAS_CALENDARIO = {"dow", "mes", "feriado", "fim_de_semana", "sin1", "cos1", "sin2", "cos2"}
PADRAO_LAG = re.compile(r"_lag(\d+)$")


def _exigir_artefatos() -> None:
    faltando = [p.relative_to(RAIZ).as_posix() for p in (*MODELOS.values(), METADATA) if not p.exists()]
    if faltando:
        pytest.fail(
            "demo models missing: " + ", ".join(faltando) + ". Train them first with "
            "`uv run python -m models_demo.treinar` (a few seconds on CPU). This is a failure, not a skip."
        )


def _caminho(cfg_val: str) -> Path:
    p = Path(cfg_val)
    return p if p.is_absolute() else RAIZ / p


def _construir_direto(h: int):
    """Canonical dataset for h, built the way run_preliminary does, plus the saved model."""
    cfg = yaml.safe_load(CONFIGS[h].read_text(encoding="utf-8"))
    assert int(cfg["experimento"]["horizonte"]) == h
    assert cfg["feature_sets"]["AR_CAL"] == ["AR", "CAL"]
    d, exp = cfg["dados"], cfg["experimento"]
    ds = construir_dataset(
        caminho_sih=_caminho(d["sih"]),
        caminho_cams=_caminho(d["cams"]),
        horizonte=h,
        lags_alvo=exp["lags_alvo"],
        lags_exogenas=exp["lags_exogenas"],
        inicio=d.get("inicio"),
        fim=d.get("fim"),
        fonte_pm25=d.get("fonte_pm25", "cams"),
        caminho_cetesb=_caminho(d["cetesb"]) if d.get("cetesb") else None,
        fonte_meteo=d.get("fonte_meteo", "cams"),
        caminho_meteo=_caminho(d["meteo"]) if d.get("meteo") else None,
        blocos_customizados=cfg.get("blocos_customizados"),
        permitir_duas_fontes=bool(d.get("permitir_duas_fontes", False)),
    )
    colunas = ds.colunas(["AR", "CAL"])
    modelo = XGBRegressor()
    modelo.load_model(MODELOS[h])
    return ds, colunas, modelo


@pytest.fixture(scope="module")
def direto():
    _exigir_artefatos()
    return {h: _construir_direto(h) for h in HORIZONTES}


@pytest.fixture(scope="module")
def client():
    _exigir_artefatos()
    from api.main import app

    with TestClient(app) as c:  # the context manager runs the lifespan (models loaded once)
        yield c


@pytest.fixture(scope="module")
def metadata():
    _exigir_artefatos()
    return json.loads(METADATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ /health
def test_health_200(client, metadata):
    r = client.get("/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["modelo"] == "xgboost_ar_cal"
    assert body["versao"] == metadata["versao"] and body["versao"]
    assert body["horizontes"] == list(HORIZONTES)
    assert body["historico"] == {"inicio": "2019-01-01", "fim": "2024-12-31"}
    assert set(body["origens_validas"]) == {str(h) for h in HORIZONTES}
    assert "demonstration" in body["aviso"].lower()


# ------------------------------------------------------------------ /forecast == model
@pytest.mark.parametrize("origem", ["2020-03-15", "2023-01-12", "2024-06-30"])
@pytest.mark.parametrize("h", HORIZONTES)
def test_forecast_igual_ao_modelo_direto(client, direto, h, origem):
    r = client.get("/forecast", params={"h": h, "origem": origem})
    assert r.status_code == 200, r.text
    body = r.json()
    alvo = pd.Timestamp(origem) + pd.Timedelta(days=h)
    assert body["h"] == h
    assert body["origem"] == origem
    assert body["data_alvo"] == str(alvo.date())
    assert body["modelo"] == "xgboost_ar_cal" and body["versao"]
    assert body["aviso"].lower().startswith("demonstration model")

    ds, colunas, modelo = direto[h]
    x = ds.X.loc[[alvo], colunas].to_numpy(dtype=np.float32)
    esperado = float(modelo.predict(x)[0])
    assert np.isfinite(esperado) and esperado > 0
    assert abs(body["previsao"] - esperado) < 1e-9


@pytest.mark.parametrize("h", HORIZONTES)
def test_forecast_nas_bordas_da_janela_valida(client, direto, h):
    ds, colunas, modelo = direto[h]
    primeira_origem = ds.datas_alvo.min() - pd.Timedelta(days=h)
    ultima_origem = ds.datas_alvo.max() - pd.Timedelta(days=h)
    assert ultima_origem.date().isoformat() == (pd.Timestamp("2024-12-31") - pd.Timedelta(days=h)).date().isoformat()
    for origem in (primeira_origem, ultima_origem):
        r = client.get("/forecast", params={"h": h, "origem": origem.date().isoformat()})
        assert r.status_code == 200, r.text
        alvo = origem + pd.Timedelta(days=h)
        esperado = float(modelo.predict(ds.X.loc[[alvo], colunas].to_numpy(dtype=np.float32))[0])
        assert abs(r.json()["previsao"] - esperado) < 1e-9
    # one day outside each edge: 422 with a message that names the valid bound
    r = client.get("/forecast", params={"h": h, "origem": (primeira_origem - pd.Timedelta(days=1)).date().isoformat()})
    assert r.status_code == 422, r.text
    assert "insufficient history" in r.json()["detail"] and primeira_origem.date().isoformat() in r.json()["detail"]
    r = client.get("/forecast", params={"h": h, "origem": (ultima_origem + pd.Timedelta(days=1)).date().isoformat()})
    assert r.status_code == 422, r.text
    assert "beyond the end" in r.json()["detail"] and ultima_origem.date().isoformat() in r.json()["detail"]


# ------------------------------------------------------------------ 422
@pytest.mark.parametrize("h", [0, 2, 5, 15, 31, -1, "x", 1.5])
def test_422_horizonte_invalido(client, h):
    r = client.get("/forecast", params={"h": h, "origem": "2023-06-01"})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("origem", ["2018-12-31", "2025-01-01", "1999-01-01", "2030-12-31"])
def test_422_origem_fora_do_historico(client, origem):
    r = client.get("/forecast", params={"h": 1, "origem": origem})
    assert r.status_code == 422, r.text
    assert "outside the historical series" in r.json()["detail"]


@pytest.mark.parametrize("origem", ["2024-13-01", "01/06/2023", "2023-06", "ontem", ""])
def test_422_data_malformada(client, origem):
    r = client.get("/forecast", params={"h": 1, "origem": origem})
    assert r.status_code == 422, r.text


def test_422_parametros_ausentes(client):
    assert client.get("/forecast").status_code == 422
    assert client.get("/forecast", params={"h": 1}).status_code == 422
    assert client.get("/forecast", params={"origem": "2023-06-01"}).status_code == 422


def test_422_sem_historico_para_os_lags(client):
    # 2019-01-01 is inside the history but no horizon has lags available there
    for h in HORIZONTES:
        r = client.get("/forecast", params={"h": h, "origem": "2019-01-01"})
        assert r.status_code == 422, r.text
        assert "insufficient history" in r.json()["detail"]


def test_422_alvo_alem_do_historico(client):
    for h in (7, 30):
        r = client.get("/forecast", params={"h": h, "origem": "2024-12-31"})
        assert r.status_code == 422, r.text
        assert "beyond the end" in r.json()["detail"]
    # h=1 from the last day would need 2025-01-01, also outside
    r = client.get("/forecast", params={"h": 1, "origem": "2024-12-31"})
    assert r.status_code == 422


def test_erros_nao_expoem_caminhos_absolutos(client):
    for params in ({"h": 1, "origem": "2010-01-01"}, {"h": 30, "origem": "2019-01-01"}, {"h": 7, "origem": "2024-12-31"}):
        detail = client.get("/forecast", params=params).json()["detail"]
        assert "D:\\" not in detail and "D:/" not in detail and "/home/" not in detail and "Users" not in detail


# ------------------------------------------------------------------ leakage rule L >= h
@pytest.mark.parametrize("h", HORIZONTES)
def test_regra_L_maior_ou_igual_h(direto, metadata, h):
    ds, colunas, modelo = direto[h]
    assert colunas == metadata["modelos"][str(h)]["features"], "feature order served != feature order trained"
    assert int(modelo.n_features_in_) == len(colunas)

    lags_vistos = []
    for c in colunas:
        m = PADRAO_LAG.search(c)
        if m is None:
            assert c in COLUNAS_CALENDARIO, f"unlagged feature {c!r} that is not a calendar column"
        else:
            L = int(m.group(1))
            assert L >= h, f"feature {c!r} uses lag {L} < h={h}: information after the origin"
            lags_vistos.append(L)
    assert lags_vistos, "no lagged feature at all"
    assert min(lags_vistos) == h, f"the shortest lag for h={h} should be exactly h (got {min(lags_vistos)})"
    assert f"y_lag{h}" in colunas
    # the builder also refuses to construct lags < h
    cfg = yaml.safe_load(CONFIGS[h].read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="menores que o horizonte"):
        construir_dataset(
            caminho_sih=_caminho(cfg["dados"]["sih"]),
            caminho_cams=_caminho(cfg["dados"]["cams"]),
            horizonte=h,
            lags_alvo=[h - 1] if h > 1 else [0],
            lags_exogenas=cfg["experimento"]["lags_exogenas"],
        )


@pytest.mark.parametrize("h", HORIZONTES)
def test_features_ar_sao_valores_observados_ate_a_origem(direto, h):
    """y_lag<L> at target u equals y[u - L]; with L >= h that date is <= the origin u - h."""
    ds, colunas, _ = direto[h]
    serie = ds.serie_alvo_completa
    for alvo in (pd.Timestamp("2021-07-15"), pd.Timestamp("2024-12-31")):
        origem = alvo - pd.Timedelta(days=h)
        for c in colunas:
            m = PADRAO_LAG.search(c)
            if m is None:
                continue
            L = int(m.group(1))
            data_obs = alvo - pd.Timedelta(days=L)
            assert data_obs <= origem
            assert ds.X.loc[alvo, c] == serie.loc[data_obs]

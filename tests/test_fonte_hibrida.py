"""Testes da configuração híbrida (CETESB + CAMS lado a lado) do construtor de features.

Rodar:  pytest tests/test_fonte_hibrida.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from src.features.forecasting_features import (  # noqa: E402
    COLUNAS_METEO, COLUNAS_METEO_CETESB, COLUNAS_PM25_CETESB, PREFIXO_CAMS_HIBRIDO, construir_dataset,
)

CAMINHO_SIH = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
CAMINHO_CAMS = RAIZ / "data" / "processed" / "cams_daily_v2.csv"
CAMINHO_CETESB = RAIZ / "data" / "processed" / "cetesb_poluentes_daily.csv"
CAMINHO_METEO = RAIZ / "data" / "processed" / "cetesb_meteo_daily.csv"
TEM_DADOS = all(p.exists() for p in (CAMINHO_SIH, CAMINHO_CAMS, CAMINHO_CETESB, CAMINHO_METEO))
precisa_dados = pytest.mark.skipif(not TEM_DADOS, reason="dados processados ausentes")


def _montar(**kw):
    base = dict(caminho_sih=CAMINHO_SIH, caminho_cams=CAMINHO_CAMS, horizonte=1, lags_alvo=[1, 7],
                lags_exogenas=[1, 2], inicio="2019-01-01", fim="2024-12-31", caminho_cetesb=CAMINHO_CETESB,
                caminho_meteo=CAMINHO_METEO, permitir_duas_fontes=True)
    base.update(kw)
    return construir_dataset(**base)


@pytest.fixture(scope="module")
def ds():
    if not TEM_DADOS:
        pytest.skip("dados processados ausentes")
    return _montar(fonte_pm25="hibrida", fonte_meteo="hibrida")


@precisa_dados
def test_hibrida_traz_as_duas_fontes_em_todos_os_blocos(ds):
    r = ds.relatorio
    assert list(r["colunas_meteo"]) == list(COLUNAS_METEO_CETESB) + [PREFIXO_CAMS_HIBRIDO + c for c in COLUNAS_METEO]
    assert list(r["colunas_pm25"]) == list(COLUNAS_PM25_CETESB) + [PREFIXO_CAMS_HIBRIDO + "pm2p5"]
    assert r["colunas_poluentes"][-1] == PREFIXO_CAMS_HIBRIDO + "pm10"
    assert "so2_media" in r["poluentes_descartados"] and "so2_media" not in r["colunas_poluentes"]
    assert r["features_por_bloco"] == {"AR": 2, "CAL": 8, "METEO": 20, "PM25": 8, "POLUENTES": 10}


@precisa_dados
def test_proveniencia_coluna_a_coluna(ds):
    prov = ds.relatorio["proveniencia_colunas"]
    assert prov["temp_media"] == "cetesb" and prov["pm25_media"] == "cetesb" and prov["no2_media"] == "cetesb"
    assert prov[PREFIXO_CAMS_HIBRIDO + "t2m_c"] == "cams" and prov[PREFIXO_CAMS_HIBRIDO + "pm2p5"] == "cams"
    assert set(prov.values()) == {"cetesb", "cams"}


@precisa_dados
def test_sem_nan_e_sem_vazamento(ds):
    assert not ds.X.isna().any().any()
    cams = pd.read_csv(CAMINHO_CAMS, parse_dates=["data"]).set_index("data")["pm2p5"]
    col = ds.X[PREFIXO_CAMS_HIBRIDO + "pm2p5_lag1"]
    d = col.index[100]
    assert col.loc[d] == pytest.approx(cams.loc[d - pd.Timedelta(days=1)])  # defasagem 1 = dia anterior, nunca o próprio
    assert len(ds.X) == 2192 - 7  # warm-up = maior defasagem


@precisa_dados
def test_hibrida_exige_as_duas_fontes():
    with pytest.raises(ValueError, match="híbrida"):
        _montar(fonte_pm25="hibrida", fonte_meteo="cams")
    with pytest.raises(ValueError, match="híbrida"):
        _montar(fonte_pm25="cetesb", fonte_meteo="hibrida")


@precisa_dados
def test_hibrida_nao_altera_as_colunas_da_cetesb_rica(ds):
    rica = _montar(fonte_pm25="cetesb", fonte_meteo="cetesb")
    comuns = [c for c in rica.X.columns if c in ds.X.columns]
    assert len(comuns) == rica.X.shape[1]
    pd.testing.assert_frame_equal(rica.X[comuns], ds.X[comuns])

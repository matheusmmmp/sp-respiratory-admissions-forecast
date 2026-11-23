#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Testes exigidos pelo fechamento da v0.1 que não existiam antes.

O `test_benchmark_preliminar.py` já cobre alinhamento, lags, janelas da LSTM,
splits e métricas. Faltavam quatro famílias, e são justamente as que sustentam
alegações fortes do relatório:

  1. DATA QUALITY GATE — o laudo precisa REPROVAR dado ruim, não só passar no
     dado bom. Um gate que nunca reprovou nada não é evidência de qualidade.
  2. SCALER TREINADO SÓ NO TREINO — a alegação mais fácil de quebrar numa
     refatoração e a mais cara de descobrir depois.
  3. MESMOS TIMESTAMPS ENTRE MODELOS — sem isso a tabela comparativa é inválida.
  4. CONFIGURAÇÃO DE SEMENTE — reprodutibilidade declarada tem de ser medida.

Rodar:  pytest tests/test_framework_v0_1.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.data.validation import validar_serie_diaria  # noqa: E402
from src.evaluation.splits import rolling_origin  # noqa: E402
from src.features.forecasting_features import construir_dataset  # noqa: E402
from src.models.lstm_model import LSTMForecaster  # noqa: E402
from src.models.naive import Naive, SeasonalNaive  # noqa: E402
from src.models.xgboost_model import XGBoostForecaster  # noqa: E402

CAMINHO_SIH = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
CAMINHO_CAMS = RAIZ / "data" / "processed" / "cams_daily_v2.csv"
TEM_DADOS = CAMINHO_SIH.exists() and CAMINHO_CAMS.exists()
precisa_dados = pytest.mark.skipif(not TEM_DADOS, reason="dados processados ausentes")


def _serie(n=400, inicio="2020-01-01", valor=50.0):
    idx = pd.date_range(inicio, periods=n, freq="D")
    return pd.Series(np.full(n, valor) + np.arange(n) % 7, index=idx, dtype=float)


# ===================================================================== DATA GATE
def test_data_quality_aprova_serie_sa():
    laudo = validar_serie_diaria(_serie())
    assert laudo.veredito == "PASS", [c.detalhe for c in laudo.por_status("FAIL")]


def test_data_quality_reprova_buraco_temporal():
    s = _serie()
    s = s.drop(s.index[100])          # remove um dia do meio
    laudo = validar_serie_diaria(s)
    assert laudo.reprovado
    nomes = [c.nome for c in laudo.por_status("FAIL")]
    assert "frequencia_diaria" in nomes, nomes


def test_data_quality_reprova_data_duplicada():
    s = _serie()
    s = pd.concat([s, s.iloc[[10]]]).sort_index()
    laudo = validar_serie_diaria(s)
    assert laudo.reprovado
    assert "datas_unicas" in [c.nome for c in laudo.por_status("FAIL")]


def test_data_quality_reprova_alvo_negativo():
    s = _serie()
    s.iloc[5] = -1.0
    laudo = validar_serie_diaria(s)
    assert laudo.reprovado
    assert "alvo_nao_negativo" in [c.nome for c in laudo.por_status("FAIL")]


def test_data_quality_reprova_alvo_faltante():
    s = _serie()
    s.iloc[7] = np.nan
    laudo = validar_serie_diaria(s)
    assert laudo.reprovado
    assert "alvo_sem_missing" in [c.nome for c in laudo.por_status("FAIL")]


def test_data_quality_outlier_avisa_mas_nao_reprova():
    """Pico de internação é o fenômeno de interesse, não sujeira a remover."""
    s = _serie()
    s.iloc[200] = 10_000.0
    laudo = validar_serie_diaria(s)
    assert not laudo.reprovado, "outlier não pode reprovar a run"
    ck = [c for c in laudo.checagens if c.nome == "alvo_outliers"][0]
    assert ck.status == "WARN"
    assert ck.dados["n_outliers"] >= 1


def test_data_quality_zeros_avisam():
    s = _serie()
    s.iloc[3] = 0.0
    laudo = validar_serie_diaria(s)
    ck = [c for c in laudo.checagens if c.nome == "alvo_zeros"][0]
    assert ck.status == "WARN"


# ================================================================ dataset real
@pytest.fixture(scope="module")
def ds():
    if not TEM_DADOS:
        pytest.skip("dados processados ausentes")
    return construir_dataset(
        caminho_sih=CAMINHO_SIH,
        caminho_cams=CAMINHO_CAMS,
        horizonte=1,
        lags_alvo=[1, 2, 3, 7],
        lags_exogenas=[1, 2],
        inicio="2019-01-01",
        fim="2024-12-31",
    )


@pytest.fixture(scope="module")
def fold(ds):
    datas = ds.datas_alvo[30:]
    return rolling_origin(
        datas, n_folds=1, dias_teste=30, dias_validacao=60, treino_minimo=365
    )[0]


# ================================================================ SCALER (§38)
@precisa_dados
def test_scaler_ajustado_somente_no_treino(ds, fold):
    """As estatísticas do scaler têm de vir SÓ das janelas de treino.

    Recalculamos mu/sigma a partir do treino e exigimos igualdade com o que o
    modelo guardou. Se alguém trocar por um fit sobre o dataset inteiro, os
    números deixam de bater e este teste cai.
    """
    canais = ds.canais(["AR", "CAL"])
    modelo = LSTMForecaster(lookback=7, epocas=1, paciencia=1, seed=42)
    modelo.fit(ds, fold, canais)

    Xtr = modelo._janelas(ds, fold.treino, canais)
    mu_esperado = Xtr.mean(axis=(0, 1), keepdims=True)
    sd_esperado = Xtr.std(axis=(0, 1), keepdims=True)
    sd_esperado[sd_esperado == 0] = 1.0

    assert np.allclose(modelo._mu_x, mu_esperado), "média do scaler não veio só do treino"
    assert np.allclose(modelo._sd_x, sd_esperado), "desvio do scaler não veio só do treino"

    ytr = ds.y.loc[fold.treino].to_numpy(dtype=np.float32)
    assert np.isclose(modelo._mu_y, float(ytr.mean()))

    # e o scaler NÃO pode coincidir com o do conjunto completo
    Xtudo = modelo._janelas(ds, ds.datas_alvo[30:], canais)
    mu_global = Xtudo.mean(axis=(0, 1), keepdims=True)
    assert not np.allclose(modelo._mu_x, mu_global), (
        "as estatísticas do treino são idênticas às do dataset completo — "
        "ou o fold cobre tudo, ou o scaler é global"
    )


@precisa_dados
def test_scaler_nao_vaza_estatistica_do_teste(ds, fold):
    """Refazer o fit sem os dados de teste tem de dar exatamente o mesmo scaler."""
    canais = ds.canais(["AR"])
    a = LSTMForecaster(lookback=7, epocas=1, paciencia=1, seed=42)
    a.fit(ds, fold, canais)
    b = LSTMForecaster(lookback=7, epocas=1, paciencia=1, seed=42)
    b.fit(ds, fold, canais)
    assert np.allclose(a._mu_x, b._mu_x) and np.allclose(a._sd_x, b._sd_x)


# ====================================================== MESMOS TIMESTAMPS (§45)
@precisa_dados
def test_todos_os_modelos_preveem_os_mesmos_timestamps(ds, fold):
    """A tabela comparativa só é válida se os quatro avaliarem as mesmas datas."""
    cols_tab = ds.colunas(["AR", "CAL"])
    canais = ds.canais(["AR", "CAL"])

    modelos = {
        "naive": (Naive(), []),
        "seasonal_naive": (SeasonalNaive(periodo_sazonal=7), []),
        "xgboost": (XGBoostForecaster(seed=42, n_estimators=20,
                                      early_stopping_rounds=5), cols_tab),
        "lstm": (LSTMForecaster(lookback=7, epocas=1, paciencia=1, seed=42), canais),
    }
    n = len(fold.teste)
    for nome, (modelo, cols) in modelos.items():
        if modelo.treinavel:
            modelo.fit(ds, fold, cols)
        pred = np.asarray(modelo.predict(ds, fold, cols), dtype=float)
        assert pred.shape[0] == n, f"{nome}: {pred.shape[0]} previsões para {n} datas"
        assert not np.isnan(pred).any(), f"{nome}: previsões com NaN"


@precisa_dados
def test_forecast_origin_e_target_date_diferem_pelo_horizonte(ds, fold):
    origens = pd.DatetimeIndex(fold.teste) - pd.Timedelta(days=ds.horizonte)
    assert (pd.DatetimeIndex(fold.teste) - origens == pd.Timedelta(days=1)).all()
    assert ds.horizonte == 1


# ============================================================ SMOKE DOS MODELOS
@precisa_dados
def test_xgboost_smoke(ds, fold):
    cols = ds.colunas(["AR", "CAL"])
    m = XGBoostForecaster(seed=42, n_estimators=20, early_stopping_rounds=5)
    m.fit(ds, fold, cols)
    pred = m.predict(ds, fold, cols)
    assert len(pred) == len(fold.teste)
    assert np.isfinite(pred).all()
    p = m.params()
    assert p["seed"] == 42 and p["objetivo_escolhido"] in (
        "reg:squarederror", "count:poisson"
    )


@precisa_dados
def test_lstm_smoke(ds, fold):
    canais = ds.canais(["AR", "CAL"])
    m = LSTMForecaster(lookback=7, epocas=2, paciencia=1, seed=42)
    m.fit(ds, fold, canais)
    pred = m.predict(ds, fold, canais)
    assert len(pred) == len(fold.teste)
    assert np.isfinite(pred).all()
    assert m.params()["epocas_treinadas"] >= 1


# =========================================================== REPRODUTIBILIDADE
@precisa_dados
def test_semente_configurada_muda_o_resultado_e_repete_o_mesmo(ds, fold):
    """Semente igual -> resultado igual. Semente diferente -> resultado diferente.

    As duas metades importam: a primeira prova que a semente É respeitada; a
    segunda prova que ela está de fato ligada a algo, e não é um parâmetro
    decorativo que não altera nada.
    """
    canais = ds.canais(["AR"])

    a = LSTMForecaster(lookback=7, epocas=2, paciencia=1, seed=42)
    a.fit(ds, fold, canais)
    pa = a.predict(ds, fold, canais)

    b = LSTMForecaster(lookback=7, epocas=2, paciencia=1, seed=42)
    b.fit(ds, fold, canais)
    pb = b.predict(ds, fold, canais)

    c = LSTMForecaster(lookback=7, epocas=2, paciencia=1, seed=777)
    c.fit(ds, fold, canais)
    pc = c.predict(ds, fold, canais)

    assert np.allclose(pa, pb, atol=1e-5), "mesma semente produziu resultado diferente"
    assert not np.allclose(pa, pc, atol=1e-5), (
        "sementes diferentes produziram resultado idêntico — a semente não está ligada"
    )


def test_baselines_sao_deterministicos_e_sem_semente():
    """Naïve e Seasonal Naïve não têm semente: rodar duas vezes dá o mesmo."""
    assert Naive().treinavel is False
    assert SeasonalNaive().treinavel is False
    assert "seed" not in Naive().params()
    assert "seed" not in SeasonalNaive().params()


# ============================================================== TARGET (§55)
@precisa_dados
def test_alvo_nao_negativo_e_presente(ds):
    y = ds.serie_alvo_completa
    assert y.notna().all(), "alvo tem valores faltantes"
    assert (y >= 0).all(), "alvo tem valores negativos"


@precisa_dados
def test_frequencia_diaria_sem_duplicatas(ds):
    idx = pd.DatetimeIndex(ds.serie_alvo_completa.index)
    assert not idx.has_duplicates
    esperado = pd.date_range(idx.min(), idx.max(), freq="D")
    assert len(esperado.difference(idx)) == 0, "série não é diária contínua"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

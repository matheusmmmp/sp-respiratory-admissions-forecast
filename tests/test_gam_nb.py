"""Testes do GAM binomial negativo (trilha clássica, PROTOCOLO §0.8).

    python -m pytest tests/test_gam_nb.py -v

Cobrem: recuperação de uma relação não linear simulada, α estimado só no
treino, alinhamento com os timestamps da naïve, splines só quando o bloco
existe, falha alto fora da faixa do alvo e registro no runner.
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

from src.evaluation.splits import Fold
from src.models.gam_nb import (
    GRADE_PENALIZACAO_PADRAO, GAMNBForecaster, classificar_colunas, estimar_alpha, loglik_nb2,
)
from src.models.naive import Naive


# ------------------------------------------------------------------ fixtures
class DSFake:
    """Mínimo do contrato `DatasetExperimental` que o GAM-NB consome."""

    def __init__(self, y: pd.Series, X: pd.DataFrame | None = None, horizonte: int = 1):
        self.y = y
        self.X = X if X is not None else pd.DataFrame(index=y.index)
        self.horizonte = horizonte
        self.serie_alvo_completa = y
        self.ordem_blocos = ("AR", "CAL", "METEO", "PM25", "POLUENTES")


def _fold(idx: pd.DatetimeIndex, n_teste: int, n_val: int = 30) -> Fold:
    n = len(idx)
    return Fold(id=1, treino=idx[: n - n_teste - n_val], validacao=idx[n - n_teste - n_val: n - n_teste],
                teste=idx[n - n_teste:])


def _f_verdadeira(x: np.ndarray) -> np.ndarray:
    """Efeito não linear (em escala log) do "PM2.5": sobe, satura e cai."""
    return 0.6 * np.sin(np.pi * (x - 5.0) / 40.0)


def simular_nb_nao_linear(n: int, alpha: float = 0.05, seed: int = 11, nivel: float = 4.5):
    """y_t ~ NB2(μ_t, α), log μ_t = nivel + f(pm_{t−1}) + 0.3·dow_fim_de_semana."""
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    pm = rng.uniform(5.0, 45.0, size=n)
    dow = idx.dayofweek.to_numpy()
    eta = nivel + _f_verdadeira(pm) - 0.3 * (dow >= 5)
    mu = np.exp(eta)
    r = 1.0 / alpha
    lam = rng.gamma(shape=r, scale=mu / r)
    y = rng.poisson(lam).astype(float)
    X = pd.DataFrame({"pm25_media_lag1": pm, "dow": dow, "feriado": 0}, index=idx)
    X.loc[idx[::50], "feriado"] = 1      # alguns feriados para a coluna não ser constante
    return pd.Series(y, index=idx, name="y"), X, mu


# ------------------------------------------------------------- classificação
def test_classificacao_segue_a_especificacao():
    cols = ["y_lag1", "y_lag2", "y_lag3", "y_lag7", "y_lag14", "y_lag28",
            "dow", "mes", "feriado", "fim_de_semana", "sin1", "cos1", "sin2", "cos2",
            "temp_media_lag1", "temp_media_lag2", "temp_media_lag7", "ur_media_lag1", "ur_media_lag7",
            "pm25_media_lag1", "pm25_media_lag3", "pm10_media_lag1"]
    plano = classificar_colunas(cols, horizonte=1)
    assert plano["ar_lineares"] == ["y_lag1", "y_lag7"]
    assert plano["categoricas"] == ["dow", "feriado"]
    assert plano["fourier"] == ["sin1", "cos1", "sin2", "cos2"]
    assert [s["coluna"] for s in plano["splines"]] == ["pm25_media_lag1", "temp_media_lag1"]
    assert plano["lineares"] == sorted(["temp_media_lag2", "temp_media_lag7", "ur_media_lag1", "ur_media_lag7",
                                        "pm25_media_lag3", "pm10_media_lag1"])
    assert set(plano["descartadas"]) == {"y_lag2", "y_lag3", "y_lag14", "y_lag28", "mes", "fim_de_semana"}


def test_spline_usa_a_defasagem_mais_recente_que_respeita_L_maior_igual_h():
    cols = ["y_lag2", "y_lag7", "pm25_media_lag2", "pm25_media_lag3", "temp_media_lag3"]
    plano = classificar_colunas(cols, horizonte=2, lags_ar=(2, 7))
    assert [s["coluna"] for s in plano["splines"]] == ["pm25_media_lag2", "temp_media_lag3"]
    assert plano["lineares"] == ["pm25_media_lag3"]
    with pytest.raises(ValueError, match="pede y_lag"):
        classificar_colunas(["y_lag2", "y_lag7"], horizonte=1)        # y_lag1 ausente
    with pytest.raises(ValueError, match="L >= h"):
        classificar_colunas(["y_lag1", "y_lag7"], horizonte=2)        # y_lag1 viola L >= h


# ---------------------------------------------------------- verossimilhança
def test_loglik_nb2_bate_com_scipy_e_alpha_e_recuperado_dado_mu():
    from scipy.stats import nbinom

    rng = np.random.default_rng(0)
    mu = rng.uniform(50, 150, size=2000)
    alpha = 0.08
    r = 1.0 / alpha
    y = nbinom(n=r, p=r / (r + mu)).rvs(random_state=rng).astype(float)
    esperado = float(nbinom(n=r, p=r / (r + mu)).logpmf(y).sum())
    assert loglik_nb2(y, mu, alpha) == pytest.approx(esperado, rel=1e-10)
    assert estimar_alpha(y, mu) == pytest.approx(alpha, rel=0.15)


# ------------------------------------------------------------ recuperação
def test_recupera_relacao_nao_linear_simulada_e_alpha():
    y, X, mu = simular_nb_nao_linear(1200, alpha=0.05)
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=120)
    cols = ["pm25_media_lag1", "dow", "feriado"]
    m = GAMNBForecaster(k_splines=5)
    m.fit(ds, f, cols)
    p = m.params()
    assert [s["coluna"] for s in p["splines"]] == ["pm25_media_lag1"]
    assert p["deterministico"] is True
    # α do treino perto do verdadeiro
    assert 0.03 < p["alpha_nb"] < 0.08
    # o spline captou a curva: previsões de teste em escala log acompanham f(x)
    pred = m.predict(ds, f, cols)
    mu_teste = mu[-len(f.teste):]
    assert np.corrcoef(np.log(pred), np.log(mu_teste))[0, 1] > 0.9
    # e um ajuste puramente linear em x é pior (mesma família, mesma janela)
    import statsmodels.api as sm

    tr = f.treino_completo
    Xl = sm.add_constant(pd.DataFrame({
        "x": X.loc[tr, "pm25_media_lag1"].to_numpy(float),
        "fds": (X.loc[tr, "dow"] >= 5).astype(float).to_numpy(),
    }))
    lin = sm.GLM(y.loc[tr].to_numpy(float), Xl, family=sm.families.NegativeBinomial(alpha=p["alpha_nb"])).fit()
    Xt = sm.add_constant(pd.DataFrame({
        "x": X.loc[f.teste, "pm25_media_lag1"].to_numpy(float),
        "fds": (X.loc[f.teste, "dow"] >= 5).astype(float).to_numpy(),
    }), has_constant="add")
    erro_lin = np.mean(np.abs(np.log(lin.predict(Xt)) - np.log(mu_teste)))
    erro_gam = np.mean(np.abs(np.log(pred) - np.log(mu_teste)))
    assert erro_gam < 0.5 * erro_lin


def test_fit_e_deterministico():
    y, X, _ = simular_nb_nao_linear(600)
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=60)
    cols = ["pm25_media_lag1", "dow", "feriado"]
    m1, m2 = GAMNBForecaster(), GAMNBForecaster()
    m1.fit(ds, f, cols)
    m2.fit(ds, f, cols)
    np.testing.assert_array_equal(m1.predict(ds, f, cols), m2.predict(ds, f, cols))
    assert m1.params()["alpha_nb"] == m2.params()["alpha_nb"]
    assert m1.params()["lambdas"] == m2.params()["lambdas"]


# ------------------------------------------------------------ α só no treino
def test_alpha_e_penalizacao_dependem_so_do_treino():
    """Corromper o alvo nas datas de TESTE não muda α, λ nem as previsões."""
    y, X, _ = simular_nb_nao_linear(700)
    f = _fold(y.index, n_teste=60)
    cols = ["pm25_media_lag1", "dow", "feriado"]
    m1 = GAMNBForecaster()
    m1.fit(DSFake(y, X), f, cols)
    y2 = y.copy()
    y2.loc[f.teste] = y2.loc[f.teste] * 5 + 1000
    m2 = GAMNBForecaster()
    m2.fit(DSFake(y2, X), f, cols)
    assert m1.params()["alpha_nb"] == pytest.approx(m2.params()["alpha_nb"], rel=0, abs=1e-12)
    assert m1.params()["lambdas"] == m2.params()["lambdas"]
    assert m1.params()["llf"] == pytest.approx(m2.params()["llf"], rel=0, abs=1e-9)
    np.testing.assert_allclose(m1.predict(DSFake(y, X), f, cols), m2.predict(DSFake(y2, X), f, cols), atol=1e-9)
    assert m1.params()["janela_ajuste_fim"] == str(f.validacao.max().date())
    assert m1.params()["nobs_ajuste"] == len(f.treino_completo)


# --------------------------------------------------------------- alinhamento
def test_previsoes_alinhadas_aos_timestamps_da_naive():
    y, X, _ = simular_nb_nao_linear(500)
    X["y_lag1"] = y.shift(1)
    X["y_lag7"] = y.shift(7)
    X = X.iloc[7:]
    y = y.iloc[7:]
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=45)
    cols = ["y_lag1", "y_lag7", "dow", "feriado", "pm25_media_lag1"]
    m = GAMNBForecaster()
    m.fit(ds, f, cols)
    pred = m.predict(ds, f, cols)
    naive = Naive().predict(ds, f, [])
    assert pred.shape == (len(f.teste),) == naive.shape
    assert np.all(np.isfinite(pred)) and np.all(pred > 0)
    # AR_lineares conforme a spec; demais lags do alvo descartados quando presentes
    assert m.params()["ar_lineares"] == ["y_lag1", "y_lag7"]
    with pytest.raises(RuntimeError, match="colunas do predict"):
        m.predict(ds, f, cols[:-1])


# ---------------------------------------------------- splines só com o bloco
def test_splines_so_aparecem_quando_o_bloco_existe():
    y, X, _ = simular_nb_nao_linear(500)
    X["y_lag1"] = y.shift(1)
    X["y_lag7"] = y.shift(7)
    X["sin1"] = np.sin(2 * np.pi * X.index.dayofyear / 365.25)
    X["cos1"] = np.cos(2 * np.pi * X.index.dayofyear / 365.25)
    X["temp_media_lag1"] = 20 + 5 * X["cos1"] + np.random.default_rng(1).normal(size=len(X))
    X = X.iloc[7:]
    y = y.iloc[7:]
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=40)

    sem = GAMNBForecaster()
    sem.fit(ds, f, ["y_lag1", "y_lag7", "dow", "feriado", "sin1", "cos1"])
    assert sem.params()["splines"] == []
    assert sem.params()["lambdas"] == []
    assert sem.params()["n_combinacoes_grade"] == 0
    assert sem.params()["edf_total"] == sem.params()["n_params_parametricos"]

    com = GAMNBForecaster()
    com.fit(ds, f, ["y_lag1", "y_lag7", "dow", "feriado", "sin1", "cos1", "pm25_media_lag1", "temp_media_lag1"])
    assert [s["tipo"] for s in com.params()["splines"]] == ["pm25", "temperatura"]
    assert len(com.params()["lambdas"]) == 2
    assert com.params()["n_combinacoes_grade"] == len(GRADE_PENALIZACAO_PADRAO) ** 2
    assert all(lam in GRADE_PENALIZACAO_PADRAO for lam in com.params()["lambdas"])
    # k=5 -> 4 colunas de base por spline (constante absorvida pelo intercepto)
    assert len(com.params()["edf_por_coluna_spline"]) == 8
    assert com.params()["splines"][0]["n_basis"] == 4

    so_temp = GAMNBForecaster()
    so_temp.fit(ds, f, ["y_lag1", "y_lag7", "dow", "feriado", "temp_media_lag1"])
    assert [s["tipo"] for s in so_temp.params()["splines"]] == ["temperatura"]
    assert len(so_temp.params()["lambdas"]) == 1


def test_valores_fora_do_suporte_sao_truncados_e_contados():
    y, X, _ = simular_nb_nao_linear(500)
    f = _fold(y.index, n_teste=40)
    X2 = X.copy()
    X2.loc[f.teste[:5], "pm25_media_lag1"] = 500.0     # muito acima do suporte do treino
    ds = DSFake(y, X2)
    m = GAMNBForecaster()
    cols = ["pm25_media_lag1", "dow", "feriado"]
    m.fit(ds, f, cols)
    pred = m.predict(ds, f, cols)
    assert m.params()["n_fora_do_suporte"] == [5]
    assert np.all(np.isfinite(pred))


# -------------------------------------------------------------- falhar alto
def test_predict_falha_alto_se_previsao_sair_da_faixa_do_alvo():
    """Coluna linear com valor absurdo no teste -> exp() explode -> RuntimeError, nunca número."""
    y, X, _ = simular_nb_nao_linear(500)
    rng = np.random.default_rng(5)
    X["ur_media_lag1"] = rng.uniform(40, 80, size=len(X))
    y = pd.Series(np.round(y * np.exp(0.02 * (X["ur_media_lag1"] - 60))), index=y.index)
    f = _fold(y.index, n_teste=40)
    X.loc[f.teste[:3], "ur_media_lag1"] = 5000.0
    ds = DSFake(y, X)
    cols = ["pm25_media_lag1", "dow", "feriado", "ur_media_lag1"]
    m = GAMNBForecaster()
    m.fit(ds, f, cols)
    with pytest.raises(RuntimeError, match="excede|não finito"):
        m.predict(ds, f, cols)


def test_coluna_constante_e_alvo_negativo_falham_alto():
    y, X, _ = simular_nb_nao_linear(300)
    f = _fold(y.index, n_teste=30)
    X["const_col"] = 3.0
    with pytest.raises(RuntimeError, match="constante"):
        GAMNBForecaster().fit(DSFake(y, X), f, ["pm25_media_lag1", "dow", "feriado", "const_col"])
    y2 = y.copy()
    y2.iloc[10] = -1.0
    with pytest.raises(RuntimeError, match="negativo"):
        GAMNBForecaster().fit(DSFake(y2, X), f, ["pm25_media_lag1", "dow", "feriado"])
    with pytest.raises(RuntimeError, match="antes de fit"):
        GAMNBForecaster().predict(DSFake(y, X), f, ["pm25_media_lag1"])


def test_parametros_invalidos_no_construtor():
    with pytest.raises(ValueError):
        GAMNBForecaster(k_splines=3)
    with pytest.raises(ValueError):
        GAMNBForecaster(lags_ar=[])
    with pytest.raises(ValueError):
        GAMNBForecaster(grade_penalizacao=[0.0, 1.0])


# ------------------------------------------------------------------- runner
def test_runner_registra_gam_nb():
    from src.experiments import run_preliminary as R

    assert "gam_nb" in R.MODELOS_OPCIONAIS
    assert R.CLASSE_POR_MODELO["gam_nb"] is GAMNBForecaster
    assert GAMNBForecaster.usa_semente is False
    assert {"k_splines", "lags_ar", "grade_penalizacao", "max_iter_alpha"} <= R.CHAVES_POR_MODELO["gam_nb"]
    m = R._instanciar("gam_nb", {"ativo": True, "k_splines": 6, "lags_ar": [1, 7]}, 42, 7, 28)
    assert isinstance(m, GAMNBForecaster)
    assert m.k_splines == 6 and m.lags_ar == (1, 7)
    with pytest.raises(ValueError, match="não consumida"):
        R._instanciar("gam_nb", {"ativo": True, "k": 5}, 42, 7, 28)
    assert "scipy" in R._versoes()


def test_negativos_registrados_como_zero_por_construcao():
    y, X, _ = simular_nb_nao_linear(300)
    f = _fold(y.index, n_teste=30)
    m = GAMNBForecaster()
    cols = ["pm25_media_lag1", "dow", "feriado"]
    assert m.params()["n_previsoes_negativas"] is None
    m.fit(DSFake(y, X), f, cols)
    pred = m.predict(DSFake(y, X), f, cols)
    assert (pred >= 0).all()
    assert m.params()["n_previsoes_negativas"] == 0
    assert m.params()["truncar_negativos"] is False

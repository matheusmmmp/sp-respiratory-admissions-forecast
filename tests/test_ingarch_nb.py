"""Testes do INGARCH binomial negativo log-linear (1,1) (trilha clássica, PROTOCOLO §0.8).

    python -m pytest tests/test_ingarch_nb.py -v

Cobrem: recursão e gradiente analítico, recuperação de (β0, β1, α1, φ, γ) de
uma série simulada pelo próprio processo, verossimilhança decrescente fora do
ótimo, média constante com α1 = β1 = 0, alinhamento com os timestamps da
naïve, exclusão do bloco AR no runner, falha alto fora da faixa e registro no
runner.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import approx_fprime, minimize_scalar

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.evaluation.splits import Fold
from src.models.ingarch_nb import (
    INGARCHNBForecaster, ajustar_ingarch, desempacotar, inicializar, loglik_nb2, negloglik_e_grad, recursao_nu,
)
from src.models.naive import Naive


# ------------------------------------------------------------------ fixtures
class DSFake:
    """Mínimo do contrato `DatasetExperimental` que o INGARCH-NB consome."""

    def __init__(self, y: pd.Series, X: pd.DataFrame | None = None, horizonte: int = 1):
        self.y = y
        self.X = X if X is not None else pd.DataFrame(index=y.index)
        self.horizonte = horizonte
        self.serie_alvo_completa = y
        self.ordem_blocos = ("AR", "CAL", "METEO", "PM25", "POLUENTES")
        self.colunas_por_bloco = {
            "AR": ["y_lag1", "y_lag7"], "CAL": ["dow", "feriado"], "METEO": ["temp_media_lag1"],
            "PM25": ["pm25_media_lag1"], "POLUENTES": ["pm10_media_lag1"],
        }

    def colunas(self, blocos):
        return [c for b in self.ordem_blocos if b in blocos for c in self.colunas_por_bloco[b]]


def _fold(idx: pd.DatetimeIndex, n_teste: int, n_val: int = 30) -> Fold:
    n = len(idx)
    return Fold(id=1, treino=idx[: n - n_teste - n_val], validacao=idx[n - n_teste - n_val: n - n_teste],
                teste=idx[n - n_teste:])


def simular_ingarch(n: int, beta0: float = 1.0, beta1: float = 0.5, alpha1: float = 0.3,
                    gamma=(0.2, -0.1), phi: float = 0.05, seed: int = 3, burn: int = 300):
    """y_t ~ NB2(μ_t, φ), log μ_t = β0 + β1·log(y_{t−1}+1) + α1·log μ_{t−1} + γ'x_t — o próprio processo."""
    rng = np.random.default_rng(seed)
    gamma = np.asarray(gamma, dtype=float)
    k = gamma.size
    X = rng.normal(size=(n + burn, k)) if k else None
    y = np.zeros(n + burn)
    nu_prev = beta0 / (1.0 - alpha1 - beta1)
    y_prev = float(np.exp(nu_prev))
    r = 1.0 / phi
    for t in range(n + burn):
        nu = beta0 + beta1 * np.log(y_prev + 1.0) + alpha1 * nu_prev + (X[t] @ gamma if k else 0.0)
        mu = float(np.exp(nu))
        y[t] = rng.poisson(rng.gamma(r, mu / r))
        nu_prev, y_prev = nu, float(y[t])
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    ys = pd.Series(y[burn:], index=idx, name="y")
    Xdf = pd.DataFrame(X[burn:], index=idx, columns=[f"x{i}" for i in range(k)]) if k else None
    return ys, Xdf


def _z(y: np.ndarray) -> tuple[np.ndarray, float]:
    ybar = float(y.mean())
    return np.log(np.concatenate([[ybar], y[:-1]]) + 1.0), float(np.log(ybar))


# -------------------------------------------------------- recursão/gradiente
def test_recursao_lfilter_igual_ao_laco_explicito():
    y, X = simular_ingarch(300)
    yv, Xv = y.to_numpy(float), X.to_numpy(float)
    z, nu0 = _z(yv)
    g = np.array([0.2, -0.1])
    esperado = np.zeros_like(yv)
    prev = nu0
    for t in range(len(yv)):
        esperado[t] = 1.0 + 0.5 * z[t] + 0.3 * prev + Xv[t] @ g
        prev = esperado[t]
    np.testing.assert_allclose(recursao_nu(1.0, 0.5, 0.3, g, z, Xv, nu0), esperado, rtol=1e-12, atol=1e-12)
    np.testing.assert_allclose(recursao_nu(1.0, 0.5, 0.3, np.zeros(0), z, None, nu0),
                               recursao_nu(1.0, 0.5, 0.3, np.zeros(2), z, np.zeros((len(yv), 2)), nu0))


def test_loglik_nb2_bate_com_scipy():
    from scipy.stats import nbinom

    rng = np.random.default_rng(0)
    mu = rng.uniform(50, 150, size=1000)
    phi = 0.08
    r = 1.0 / phi
    y = nbinom(n=r, p=r / (r + mu)).rvs(random_state=rng).astype(float)
    assert loglik_nb2(y, mu, phi) == pytest.approx(float(nbinom(n=r, p=r / (r + mu)).logpmf(y).sum()), rel=1e-10)


def test_gradiente_analitico_bate_com_o_numerico():
    y, X = simular_ingarch(800)
    yv, Xv = y.to_numpy(float), X.to_numpy(float)
    z, nu0 = _z(yv)
    for theta in (inicializar(yv, z, Xv), np.array([0.8, 0.4, 0.2, 0.1, 0.0, np.log(0.1)])):
        f = lambda th: negloglik_e_grad(th, yv, z, Xv, nu0)[0]  # noqa: E731
        analitico = negloglik_e_grad(theta, yv, z, Xv, nu0)[1]
        numerico = approx_fprime(theta, f, 1e-6)
        assert np.abs(analitico - numerico).max() / np.abs(numerico).max() < 1e-3


# ------------------------------------------------------------ recuperação
def test_recupera_parametros_de_serie_simulada_pelo_proprio_processo():
    """Tolerâncias (n = 2.000, 1 realização): |Δβ1|, |Δα1| < 0,1; γ ± 0,05; φ ± 40%; β0 ± 0,3.

    β0 e α1 são os menos identificáveis (β0 compensa α1 via o nível
    β0/(1−α1−β1)); β1, γ e φ são recuperados com folga maior.
    """
    verdade = dict(beta0=1.0, beta1=0.5, alpha1=0.3, gamma=np.array([0.2, -0.1]), phi=0.05)
    y, X = simular_ingarch(2000, **verdade, seed=3)
    aj = ajustar_ingarch(y.to_numpy(float), X.to_numpy(float))
    assert aj["convergiu"] and np.isfinite(aj["llf"])
    assert abs(aj["beta1"] - verdade["beta1"]) < 0.1
    assert abs(aj["alpha1"] - verdade["alpha1"]) < 0.1
    assert abs(aj["beta0"] - verdade["beta0"]) < 0.3
    np.testing.assert_allclose(aj["gamma"], verdade["gamma"], atol=0.05)
    assert 0.6 * verdade["phi"] < aj["phi"] < 1.4 * verdade["phi"]
    assert aj["estacionario"] and not aj["alpha1_no_limite"]
    assert aj["aic"] == pytest.approx(-2 * aj["llf"] + 2 * 6)
    # sem exógenas, mesma recuperação dos três parâmetros dinâmicos
    y2, _ = simular_ingarch(2000, gamma=(), seed=5)
    aj2 = ajustar_ingarch(y2.to_numpy(float), None)
    assert abs(aj2["beta1"] - 0.5) < 0.1 and abs(aj2["alpha1"] - 0.3) < 0.1
    assert 0.6 * 0.05 < aj2["phi"] < 1.4 * 0.05 and aj2["n_params"] == 4


def test_verossimilhanca_decresce_fora_do_otimo():
    y, X = simular_ingarch(1000)
    yv, Xv = y.to_numpy(float), X.to_numpy(float)
    z, nu0 = _z(yv)
    aj = ajustar_ingarch(yv, Xv)
    theta_hat = aj["theta"]
    nll_hat = negloglik_e_grad(theta_hat, yv, z, Xv, nu0)[0]
    assert nll_hat == pytest.approx(-aj["llf"])
    rng = np.random.default_rng(1)
    for _ in range(20):
        delta = rng.normal(scale=0.05, size=theta_hat.size)
        assert negloglik_e_grad(theta_hat + delta, yv, z, Xv, nu0)[0] > nll_hat
    # perturbação em cada eixo isoladamente, nos dois sentidos
    for i in range(theta_hat.size):
        for s in (-0.1, 0.1):
            th = theta_hat.copy()
            th[i] += s
            assert negloglik_e_grad(th, yv, z, Xv, nu0)[0] > nll_hat
    # gradiente ~0 no ótimo interior
    assert np.abs(negloglik_e_grad(theta_hat, yv, z, Xv, nu0)[1]).max() < 1e-2 * max(1.0, abs(nll_hat))


def test_alpha1_beta1_zero_sem_exogenas_e_media_constante():
    """Com α1 = β1 = 0 e γ vazio, μ_t ≡ exp(β0) e o β0 ótimo é log ȳ (MLE da NB2 iid)."""
    rng = np.random.default_rng(7)
    r = 1.0 / 0.1
    y = rng.poisson(rng.gamma(r, 80.0 / r, size=1500)).astype(float)
    z, nu0 = _z(y)
    ybar = float(y.mean())
    mu = np.exp(recursao_nu(np.log(ybar), 0.0, 0.0, np.zeros(0), z, None, nu0))
    np.testing.assert_allclose(mu, ybar, rtol=1e-12)
    # perfil em β0 com α1 = β1 = 0 e φ fixo: o mínimo cai em log ȳ
    f = lambda b0: negloglik_e_grad(np.array([b0, 0.0, 0.0, np.log(0.1)]), y, z, None, nu0)[0]  # noqa: E731
    otimo = minimize_scalar(f, bounds=(np.log(ybar) - 1, np.log(ybar) + 1), method="bounded").x
    assert otimo == pytest.approx(np.log(ybar), abs=1e-4)
    # e o ajuste livre numa série iid devolve dinâmica ~nula e nível ~ȳ
    aj = ajustar_ingarch(y, None)
    assert abs(aj["beta1"]) < 0.1 and abs(aj["alpha1"]) < 0.25
    nivel = np.exp(aj["beta0"] + aj["beta1"] * np.log(ybar + 1.0)) ** (1.0 / (1.0 - aj["alpha1"]))
    assert 0.9 * ybar < nivel < 1.1 * ybar
    assert 0.06 < aj["phi"] < 0.14


# --------------------------------------------------------------- alinhamento
def test_previsoes_alinhadas_aos_timestamps_da_naive_e_recursao_continuada():
    y, X = simular_ingarch(600)
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=45)
    cols = ["x0", "x1"]
    m = INGARCHNBForecaster()
    m.fit(ds, f, cols)
    pred = m.predict(ds, f, cols)
    naive = Naive().predict(ds, f, [])
    assert pred.shape == (len(f.teste),) == naive.shape
    assert np.all(np.isfinite(pred)) and np.all(pred > 0)
    p = m.params()
    assert p["deterministico"] is True and p["n_exogenas"] == 2 and p["convergiu"] is True
    assert set(p["gamma"]) == {"x0", "x1"}
    assert p["janela_ajuste_fim"] == str(f.validacao.max().date())
    assert p["nobs_ajuste"] == len(f.treino_completo)
    for chave in ("beta0", "beta1", "alpha1", "phi", "llf", "aic", "iteracoes", "mu_0"):
        assert np.isfinite(p[chave])
    # a previsão da data u usa SÓ informação até u−1: a primeira previsão de teste
    # é a recursão a partir do fim do treino, e corromper y em datas de teste
    # posteriores a u não muda a previsão de u
    beta0, beta1, alpha1, gamma, _ = desempacotar(m._theta, 2)
    Xs = (X.loc[f.teste, cols].to_numpy(float) - m._mu_x) / m._sigma_x
    nu1 = beta0 + beta1 * np.log(y.loc[f.treino_completo].iloc[-1] + 1.0) + alpha1 * m._nu_fim_treino + Xs[0] @ gamma
    assert pred[0] == pytest.approx(np.exp(nu1))
    y2 = y.copy()
    y2.loc[f.teste[10:]] = y2.loc[f.teste[10:]] * 3 + 500
    pred2 = m.predict(DSFake(y2, X), f, cols)
    np.testing.assert_allclose(pred2[:11], pred[:11])
    assert not np.allclose(pred2[11:], pred[11:])
    with pytest.raises(RuntimeError, match="colunas do predict"):
        m.predict(ds, f, cols[:1])


def test_fit_e_deterministico_e_so_depende_do_treino():
    y, X = simular_ingarch(500)
    f = _fold(y.index, n_teste=40)
    cols = ["x0", "x1"]
    m1, m2 = INGARCHNBForecaster(), INGARCHNBForecaster()
    m1.fit(DSFake(y, X), f, cols)
    y2 = y.copy()
    y2.loc[f.teste] = y2.loc[f.teste] * 5 + 1000
    m2.fit(DSFake(y2, X), f, cols)
    np.testing.assert_array_equal(m1._theta, m2._theta)
    assert m1.params()["llf"] == m2.params()["llf"]


def test_sem_exogenas_e_horizonte_maior_que_um():
    y, _ = simular_ingarch(400, gamma=())
    ds = DSFake(y)
    f = _fold(y.index, n_teste=30)
    m = INGARCHNBForecaster()
    m.fit(ds, f, [])
    pred = m.predict(ds, f, [])
    assert pred.shape == (30,) and m.params()["n_exogenas"] == 0 and m.params()["gamma"] == {}


@pytest.mark.parametrize("h", [2, 7])
def test_horizonte_h_recursao_plug_in_e_sem_vazamento(h):
    """h>1 (PROTOCOLO §0.22): ν_{o+1} com y_o observado, depois plug-in log(μ+1); nada após a origem."""
    y, X = simular_ingarch(500)
    cols = ["x0", "x1"]
    f = _fold(y.index, n_teste=30)
    m = INGARCHNBForecaster()
    m.fit(DSFake(y, X, horizonte=h), f, cols)
    pred = m.predict(DSFake(y, X, horizonte=h), f, cols)
    # mesmos parâmetros do ajuste h=1: o horizonte não entra na estimação
    m1 = INGARCHNBForecaster()
    m1.fit(DSFake(y, X), f, cols)
    np.testing.assert_array_equal(m._theta, m1._theta)
    # recursão manual para a última data de teste
    b0, b1, a1, g, _ = desempacotar(m._theta, 2)
    datas = f.treino_completo.append(f.teste)
    Xs = (X.loc[datas, cols].to_numpy() - m._mu_x) / m._sigma_x
    yv = y.loc[datas].to_numpy()
    n_tr = len(f.treino_completo)
    ybar = float(y.loc[f.treino_completo].mean())
    nu = np.empty(len(datas))
    v_prev, y_prev = np.log(ybar), ybar
    for k in range(len(datas)):
        nu[k] = b0 + b1 * np.log(y_prev + 1.0) + a1 * v_prev + Xs[k] @ g
        v_prev, y_prev = nu[k], yv[k]
    alvo = len(datas) - 1
    v = nu[alvo - h + 1]
    for k in range(alvo - h + 2, alvo + 1):
        v = b0 + b1 * np.log(np.exp(v) + 1.0) + a1 * v + Xs[k] @ g
    assert pred[-1] == pytest.approx(np.exp(v), rel=1e-9)
    # perturbar y depois da origem não muda a previsão da última data
    y2 = y.copy()
    u = f.teste[-1]
    y2.loc[u - pd.Timedelta(days=h - 1): u] += 300.0
    np.testing.assert_allclose(m.predict(DSFake(y2, X, horizonte=h), f, cols)[-1], pred[-1], rtol=1e-12)


# ------------------------------------------------------------- bloco AR fora
def test_runner_exclui_o_bloco_ar_por_padrao():
    from src.experiments import run_preliminary as R

    y, X = simular_ingarch(100)
    ds = DSFake(y, X)
    blocos = ["AR", "CAL", "PM25"]
    assert R._colunas_para(ds, "ingarch_nb", blocos, {"ativo": True}) == ["dow", "feriado", "pm25_media_lag1"]
    assert R._colunas_para(ds, "ingarch_nb", blocos, {"ativo": True, "excluir_blocos": ["AR"]}) == \
        ["dow", "feriado", "pm25_media_lag1"]
    assert R._colunas_para(ds, "ingarch_nb", ["AR"], {"ativo": True, "excluir_blocos": ["AR"]}) == []
    # a lista vazia é explícita: o pesquisador PODE incluir o AR se quiser
    assert R._colunas_para(ds, "ingarch_nb", blocos, {"ativo": True, "excluir_blocos": []}) == \
        ["y_lag1", "y_lag7", "dow", "feriado", "pm25_media_lag1"]
    # o SARIMAX mantém o comportamento anterior (chave ausente = nada excluído)
    assert R._colunas_para(ds, "sarimax", ["AR", "CAL"], {"ativo": True}) == ["y_lag1", "y_lag7", "dow", "feriado"]
    with pytest.raises(ValueError, match="blocos desconhecidos"):
        R._colunas_para(ds, "ingarch_nb", blocos, {"ativo": True, "excluir_blocos": ["XYZ"]})


# -------------------------------------------------------------- falhar alto
def test_predict_falha_alto_se_previsao_sair_da_faixa_do_alvo():
    y, X = simular_ingarch(500)
    f = _fold(y.index, n_teste=40)
    X2 = X.copy()
    X2.loc[f.teste[:3], "x0"] = 1e4      # exógena absurda no teste -> exp() explode
    ds = DSFake(y, X2)
    m = INGARCHNBForecaster()
    m.fit(ds, f, ["x0", "x1"])
    with pytest.raises(RuntimeError, match="excede|não finito"):
        m.predict(ds, f, ["x0", "x1"])


def test_entradas_invalidas_falham_alto():
    y, X = simular_ingarch(300)
    f = _fold(y.index, n_teste=30)
    X["const_col"] = 3.0
    with pytest.raises(RuntimeError, match="constante"):
        INGARCHNBForecaster().fit(DSFake(y, X), f, ["x0", "const_col"])
    y2 = y.copy()
    y2.iloc[10] = -1.0
    with pytest.raises(RuntimeError, match="negativo"):
        INGARCHNBForecaster().fit(DSFake(y2, X), f, ["x0"])
    with pytest.raises(RuntimeError, match="antes de fit"):
        INGARCHNBForecaster().predict(DSFake(y, X), f, ["x0"])
    # otimizador sem orçamento -> não converge -> RuntimeError, nunca número
    with pytest.raises(RuntimeError, match="não convergiu"):
        INGARCHNBForecaster(maxiter=1).fit(DSFake(y, X), f, ["x0", "x1"])
    # teste descontíguo da janela de ajuste
    m = INGARCHNBForecaster()
    m.fit(DSFake(y, X), f, ["x0"])
    f_lacuna = Fold(id=2, treino=f.treino, validacao=f.validacao, teste=f.teste[5:])
    with pytest.raises(RuntimeError, match="lacuna"):
        m.predict(DSFake(y, X), f_lacuna, ["x0"])
    with pytest.raises(ValueError):
        INGARCHNBForecaster(limite_alpha1=1.5)
    with pytest.raises(ValueError):
        INGARCHNBForecaster(maxiter=0)


# ------------------------------------------------------------------- runner
def test_runner_registra_ingarch_nb():
    from src.experiments import run_preliminary as R

    assert "ingarch_nb" in R.MODELOS_OPCIONAIS
    assert R.CLASSE_POR_MODELO["ingarch_nb"] is INGARCHNBForecaster
    assert INGARCHNBForecaster.usa_semente is False
    assert {"excluir_blocos", "maxiter", "limite_alpha1", "tol"} <= R.CHAVES_POR_MODELO["ingarch_nb"]
    m = R._instanciar("ingarch_nb", {"ativo": True, "excluir_blocos": ["AR"], "maxiter": 300, "limite_alpha1": 0.95},
                      42, 7, 28)
    assert isinstance(m, INGARCHNBForecaster)
    assert m.maxiter == 300 and m.limite_alpha1 == 0.95
    with pytest.raises(ValueError, match="não consumida"):
        R._instanciar("ingarch_nb", {"ativo": True, "ordem": [1, 1]}, 42, 7, 28)
    # negativos impossíveis (ligação log): registrados como 0 para o resumo do manifesto
    y, X = simular_ingarch(300)
    f = _fold(y.index, n_teste=30)
    assert m.params()["n_previsoes_negativas"] is None
    m.fit(DSFake(y, X), f, ["x0"])
    assert (m.predict(DSFake(y, X), f, ["x0"]) >= 0).all()
    assert m.params()["n_previsoes_negativas"] == 0 and m.params()["truncar_negativos"] is False

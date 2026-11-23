"""Testes do SARIMAX (trilha clássica, PROTOCOLO §0.8).

    python -m pytest tests/test_sarimax_model.py -v

Cobrem: recuperação de ordem numa série simulada, respeito à grade, AICc só
no treino, alinhamento com os timestamps da naïve e registro de negativos.
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
from src.models.naive import Naive, SeasonalNaive
from src.models.sarimax_model import GRADE_PADRAO, SARIMAXForecaster, enumerar_grade


# ------------------------------------------------------------------ fixtures
class DSFake:
    """Mínimo do contrato `DatasetExperimental` que o SARIMAX consome."""

    def __init__(self, y: pd.Series, X: pd.DataFrame | None = None, horizonte: int = 1):
        self.y = y
        self.X = X if X is not None else pd.DataFrame(index=y.index)
        self.horizonte = horizonte
        self.serie_alvo_completa = y
        self.ordem_blocos = ("AR", "CAL")


def _fold(idx: pd.DatetimeIndex, n_teste: int, n_val: int = 30) -> Fold:
    n = len(idx)
    return Fold(id=1, treino=idx[: n - n_teste - n_val], validacao=idx[n - n_teste - n_val: n - n_teste],
                teste=idx[n - n_teste:])


def simular_sarima_100_011(n: int, phi: float = 0.6, theta_s: float = -0.6, seed: int = 7,
                           nivel: float = 100.0, sigma: float = 5.0) -> pd.Series:
    """SARIMA(1,0,0)(0,1,1)_7: w_t = y_t − y_{t−7} segue AR(1) com MA sazonal(1)."""
    rng = np.random.default_rng(seed)
    burn = 400
    m = 7
    eps = rng.normal(0, sigma, n + burn)
    w = np.zeros(n + burn)
    for t in range(1, n + burn):
        w[t] = phi * w[t - 1] + eps[t] + (theta_s * eps[t - m] if t >= m else 0.0)
    y = np.zeros(n + burn)
    y[:m] = nivel
    for t in range(m, n + burn):
        y[t] = y[t - m] + w[t]
    y = y[burn:]
    idx = pd.date_range("2020-01-01", periods=n, freq="D")
    return pd.Series(y, index=idx, name="y")


# ---------------------------------------------------------------------- grade
def test_grade_padrao_tem_124_ordens_e_respeita_soma():
    ordens = enumerar_grade(GRADE_PADRAO)
    assert len(ordens) == 124
    for (p, d, q), (P, D, Q) in ordens:
        assert p in (0, 1, 2) and q in (0, 1, 2)
        assert d in (0, 1) and P in (0, 1) and D in (0, 1) and Q in (0, 1)
        assert p + q + P + Q <= 4
    # as três combinações que a restrição elimina
    assert ((2, 0, 2), (1, 0, 1)) not in ordens
    assert ((2, 0, 2), (1, 0, 0)) not in ordens
    assert ((2, 0, 2), (0, 0, 1)) not in ordens
    assert ((1, 0, 2), (1, 0, 1)) not in ordens
    assert ((2, 0, 1), (1, 0, 1)) not in ordens
    assert ((2, 0, 2), (1, 0, 1)) not in ordens
    assert ((2, 0, 2), (0, 0, 0)) in ordens
    assert len(set(ordens)) == len(ordens)


def test_grade_rejeita_chave_desconhecida_e_enumeracao_e_deterministica():
    with pytest.raises(ValueError, match="desconhecida"):
        enumerar_grade({**GRADE_PADRAO, "r": [1]})
    with pytest.raises(ValueError, match="sem a chave"):
        enumerar_grade({"p": [0]})
    assert enumerar_grade(GRADE_PADRAO) == enumerar_grade(GRADE_PADRAO)


def test_modelo_so_ajusta_ordens_da_grade_configurada():
    grade = {"p": [0, 1], "d": [1], "q": [0], "P": [0], "D": [0], "Q": [0], "soma_maxima": 4}
    y = simular_sarima_100_011(300)
    ds = DSFake(y)
    f = _fold(y.index, n_teste=20)
    m = SARIMAXForecaster(grade=grade)
    assert len(m.ordens) == 2
    m.fit(ds, f, [])
    tab = m.tabela_grade
    assert len(tab) == 2
    assert set(map(tuple, tab["ordem"])) == {(0, 1, 0), (1, 1, 0)}
    assert tuple(m.params()["ordem"]) in {(0, 1, 0), (1, 1, 0)}
    assert m.params()["n_ordens_grade"] == 2


# ------------------------------------------------------------ recuperação
def test_recupera_ordem_de_sarima_100_011_simulada():
    """Entre as 124 ordens, o AICc no treino deve escolher (1,0,0)(0,1,1)_7."""
    y = simular_sarima_100_011(900)
    ds = DSFake(y)
    f = _fold(y.index, n_teste=30)
    m = SARIMAXForecaster(periodo_sazonal=7)
    m.fit(ds, f, [])
    p = m.params()
    assert p["ordem"] == [1, 0, 0]
    assert p["ordem_sazonal"] == [0, 1, 1, 7]
    assert p["trend"] == "n"
    assert p["n_convergentes"] >= 100
    assert p["deterministico"] is True


# ------------------------------------------------------------ AICc no treino
def test_aicc_depende_so_do_treino():
    """Mudar o alvo nas datas de TESTE não altera a seleção nem o AICc."""
    grade = {"p": [0, 1], "d": [0, 1], "q": [0, 1], "P": [0], "D": [1], "Q": [0, 1], "soma_maxima": 4}
    y = simular_sarima_100_011(400)
    f = _fold(y.index, n_teste=30)
    m1 = SARIMAXForecaster(grade=grade)
    m1.fit(DSFake(y), f, [])

    y2 = y.copy()
    y2.loc[f.teste] = y2.loc[f.teste] * 5 + 1000     # teste corrompido de propósito
    m2 = SARIMAXForecaster(grade=grade)
    m2.fit(DSFake(y2), f, [])

    assert m1.params()["ordem"] == m2.params()["ordem"]
    assert m1.params()["ordem_sazonal"] == m2.params()["ordem_sazonal"]
    assert m1.params()["aicc"] == pytest.approx(m2.params()["aicc"], rel=0, abs=1e-9)
    assert m1.params()["janela_ajuste_fim"] == str(f.validacao.max().date())
    assert m1.params()["nobs_ajuste"] == len(f.treino_completo)


# --------------------------------------------------------------- alinhamento
def test_previsoes_alinhadas_e_random_walk_reproduz_naive():
    """Com (0,1,0)(0,0,0) e sem exógenas, o SARIMAX É a naïve: ŷ[u] = y[u−1].

    Prova que a previsão um passo à frente usa só y até a origem e devolve um
    vetor alinhado às datas de teste do fold — os mesmos timestamps da naïve.
    """
    y = simular_sarima_100_011(300)
    ds = DSFake(y)
    f = _fold(y.index, n_teste=40)
    m = SARIMAXForecaster(grade={"p": [0], "d": [1], "q": [0], "P": [0], "D": [0], "Q": [0]})
    m.fit(ds, f, [])
    pred = m.predict(ds, f, [])
    naive = Naive().predict(ds, f, [])
    assert pred.shape == (len(f.teste),) == naive.shape
    np.testing.assert_allclose(pred, naive, rtol=0, atol=1e-6)


def test_seasonal_random_walk_reproduz_seasonal_naive():
    y = simular_sarima_100_011(300)
    ds = DSFake(y)
    f = _fold(y.index, n_teste=40)
    m = SARIMAXForecaster(grade={"p": [0], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [0]})
    m.fit(ds, f, [])
    pred = m.predict(ds, f, [])
    np.testing.assert_allclose(pred, SeasonalNaive(7).predict(ds, f, []), rtol=0, atol=1e-6)


def test_exogenas_entram_e_predict_exige_mesmas_colunas():
    rng = np.random.default_rng(3)
    y = simular_sarima_100_011(400)
    X = pd.DataFrame({"x_lag1": rng.normal(size=len(y)), "dow_1": (y.index.dayofweek == 1).astype(float)},
                     index=y.index)
    y = y + 8.0 * X["x_lag1"]
    ds = DSFake(y, X)
    f = _fold(y.index, n_teste=30)
    grade = {"p": [1], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [1]}
    m = SARIMAXForecaster(grade=grade)
    m.fit(ds, f, ["x_lag1", "dow_1"])
    pred = m.predict(ds, f, ["x_lag1", "dow_1"])
    assert pred.shape == (len(f.teste),)
    assert m.params()["n_exogenas"] == 2 and m.params()["n_betas"] == 2
    # com a exógena, o erro cai bem abaixo do que seria sem ela
    sem = SARIMAXForecaster(grade=grade)
    sem.fit(ds, f, [])
    mae_com = np.abs(pred - y.loc[f.teste].to_numpy()).mean()
    mae_sem = np.abs(sem.predict(ds, f, []) - y.loc[f.teste].to_numpy()).mean()
    assert mae_com < 0.7 * mae_sem
    with pytest.raises(RuntimeError, match="colunas"):
        m.predict(ds, f, ["x_lag1"])


def test_exogena_constante_no_treino_falha_alto():
    y = simular_sarima_100_011(200)
    X = pd.DataFrame({"zero": np.zeros(len(y))}, index=y.index)
    m = SARIMAXForecaster(grade={"p": [0], "d": [1], "q": [0], "P": [0], "D": [0], "Q": [0]})
    with pytest.raises(RuntimeError, match="constante"):
        m.fit(DSFake(y, X), _fold(y.index, 20), ["zero"])


@pytest.mark.parametrize("h", [2, 5, 7, 15])
def test_horizonte_h_random_walk_reproduz_naive_do_mesmo_horizonte(h):
    """(0,1,0) prevê h passos como ŷ[u] = y[u−h]: é a naïve de horizonte h (PROTOCOLO §0.22)."""
    y = simular_sarima_100_011(300)
    ds = DSFake(y, horizonte=h)
    f = _fold(y.index, n_teste=40)
    m = SARIMAXForecaster(grade={"p": [0], "d": [1], "q": [0], "P": [0], "D": [0], "Q": [0]})
    m.fit(ds, f, [])
    np.testing.assert_allclose(m.predict(ds, f, []), Naive().predict(ds, f, []), rtol=0, atol=1e-6)


@pytest.mark.parametrize("h", [5, 10])
def test_horizonte_h_seasonal_random_walk_reproduz_seasonal_naive(h):
    """(0,0,0)(0,1,0)_7 prevê ŷ[u] = y[u − 7⌈h/7⌉], a seasonal naïve de horizonte h."""
    y = simular_sarima_100_011(300)
    ds = DSFake(y, horizonte=h)
    f = _fold(y.index, n_teste=40)
    m = SARIMAXForecaster(grade={"p": [0], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [0]})
    m.fit(ds, f, [])
    np.testing.assert_allclose(m.predict(ds, f, []), SeasonalNaive(7).predict(ds, f, []), rtol=0, atol=1e-6)


def test_horizonte_h_nao_usa_y_posterior_a_origem():
    """Mudar y entre a origem u−h e u não muda a previsão de u; mudar y na origem muda."""
    h = 5
    y = simular_sarima_100_011(300)
    f = _fold(y.index, n_teste=30)
    grade = {"p": [1], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [1]}
    m = SARIMAXForecaster(grade=grade)
    m.fit(DSFake(y, horizonte=h), f, [])
    base = m.predict(DSFake(y, horizonte=h), f, [])
    j = 20
    u = f.teste[j]
    y_pos = y.copy()
    y_pos.loc[u - pd.Timedelta(days=h - 1): u] += 500.0     # datas u−h+1 .. u: depois da origem
    pert = m.predict(DSFake(y_pos, horizonte=h), f, [])
    assert pert[j] == pytest.approx(base[j], abs=1e-9)
    y_org = y.copy()
    y_org.loc[u - pd.Timedelta(days=h)] += 500.0             # a própria origem
    assert abs(m.predict(DSFake(y_org, horizonte=h), f, [])[j] - base[j]) > 1.0


# ------------------------------------------------------------- negativos
def test_contagem_de_negativos_registrada_e_truncamento_por_config():
    """Série que cai para baixo de zero: random walk prevê negativos.

    A contagem é registrada nas duas configurações; só `truncar_negativos`
    leva as previsões a zero.
    """
    idx = pd.date_range("2021-01-01", periods=120, freq="D")
    # rampa com ruído: sem o ruído, σ² do random walk seria 0 e o ajuste,
    # corretamente, rejeitado como degenerado (ver teste abaixo)
    rng = np.random.default_rng(3)
    y = pd.Series(np.linspace(30, -30, 120) + rng.normal(0, 1.0, 120), index=idx)
    ds = DSFake(y)
    f = _fold(idx, n_teste=30, n_val=20)
    grade = {"p": [0], "d": [1], "q": [0], "P": [0], "D": [0], "Q": [0]}

    livre = SARIMAXForecaster(grade=grade, truncar_negativos=False)
    livre.fit(ds, f, [])
    p_livre = livre.predict(ds, f, [])
    assert (p_livre < 0).sum() > 0
    assert livre.params()["n_previsoes_negativas"] == int((p_livre < 0).sum())
    assert livre.params()["n_previsoes_truncadas"] == 0

    trunc = SARIMAXForecaster(grade=grade, truncar_negativos=True)
    trunc.fit(ds, f, [])
    p_trunc = trunc.predict(ds, f, [])
    assert (p_trunc >= 0).all()
    assert trunc.params()["n_previsoes_negativas"] == livre.params()["n_previsoes_negativas"]
    assert trunc.params()["n_previsoes_truncadas"] == trunc.params()["n_previsoes_negativas"]
    assert trunc.params()["truncar_negativos"] is True
    # onde não era negativo, nada muda
    np.testing.assert_allclose(p_trunc[p_livre >= 0], p_livre[p_livre >= 0])


# ------------------------------------------------------------------- runner
def test_runner_registra_sarimax():
    from src.experiments import run_preliminary as R

    assert "sarimax" in R.CHAVES_POR_MODELO
    assert "sarimax" in R.MODELOS_OPCIONAIS
    assert R.CLASSE_POR_MODELO["sarimax"].usa_semente is False
    assert R.CLASSE_POR_MODELO["xgboost"].usa_semente is True
    m = R._instanciar("sarimax", {"ativo": True, "truncar_negativos": True, "n_jobs": 1}, 42, 7, 28)
    assert isinstance(m, SARIMAXForecaster) and m.truncar_negativos is True
    with pytest.raises(ValueError, match="não consumida"):
        R._instanciar("sarimax", {"ativo": True, "ordem": [1, 0, 0]}, 42, 7, 28)

    class DS:
        ordem_blocos = ("AR", "CAL", "METEO", "PM25", "POLUENTES")

        def colunas(self, blocos):
            return [f"{b}_c" for b in blocos]

    assert R._colunas_para(DS(), "sarimax", ["AR", "CAL"], {"excluir_blocos": ["AR"]}) == ["CAL_c"]
    assert R._colunas_para(DS(), "sarimax", ["AR"], {"excluir_blocos": ["AR"]}) == []
    with pytest.raises(ValueError, match="desconhecidos"):
        R._colunas_para(DS(), "sarimax", ["AR"], {"excluir_blocos": ["XPTO"]})


# ------------------------------------------- ajustes degenerados e faixa do alvo
# Motivado pela run h1_v02_cetesbmin_cetesbmin_classicos_full_20261021-090501: na
# dobra 4 do COMPLETO, (1,0,0)(1,0,0)_7 "convergiu" com sigma2 ~ 0 (llf -76,9), o
# AICc a escolheu e a previsao explodiu ate 664.353. Nenhum desses caminhos pode
# voltar a passar em silencio.
from src.models.sarimax_model import (  # noqa: E402
    FATOR_FAIXA, FRACAO_SIGMA2_MIN, ajustar_ordem, diagnosticar_degenerado, verificar_faixa,
)


def test_diagnostico_de_sigma2_degenerado():
    var_alvo = 1700.0  # ordem de grandeza da serie de internacoes
    assert diagnosticar_degenerado(0.14, var_alvo) is not None          # o caso real da dobra 4
    assert diagnosticar_degenerado(FRACAO_SIGMA2_MIN * var_alvo * 0.99, var_alvo) is not None
    assert diagnosticar_degenerado(FRACAO_SIGMA2_MIN * var_alvo * 1.01, var_alvo) is None
    assert diagnosticar_degenerado(350.0, var_alvo) is None             # residuo tipico
    assert diagnosticar_degenerado(float("nan"), var_alvo) is not None
    assert diagnosticar_degenerado(None, var_alvo) is not None
    assert diagnosticar_degenerado(0.0, None) is None                   # sem referencia nao julga


def test_verificar_faixa_aceita_normal_e_rejeita_explosao_e_nao_finito():
    assert verificar_faixa(np.array([50.0, 269.0, 0.0]), 269.0, "x") is None
    assert verificar_faixa(np.array([FATOR_FAIXA * 269.0]), 269.0, "x") is None
    assert "excede" in verificar_faixa(np.array([100.0, 664352.6]), 269.0, "x")
    assert "finito" in verificar_faixa(np.array([100.0, np.inf]), 269.0, "x")
    assert "finito" in verificar_faixa(np.array([np.nan]), 269.0, "x")
    assert verificar_faixa(np.array([]), 269.0, "x") is not None


def test_ajuste_com_sigma2_zero_e_rejeitado_como_degenerado():
    """Rampa determinista: o random walk ajusta com sigma2 = 0. Isso e degenerado, nao 'convergente'."""
    y = np.linspace(30.0, -30.0, 120)
    linha = ajustar_ordem(y, None, ((0, 1, 0), (0, 0, 0)), 7, var_ref=float(np.var(y)))
    assert linha["convergiu"] is False
    assert linha["degenerado"] is True
    assert "degenerado" in str(linha["motivo"])
    # sem var_ref o mesmo ajuste passaria: a referencia e o que torna o criterio relativo
    sem_ref = ajustar_ordem(y, None, ((0, 1, 0), (0, 0, 0)), 7)
    assert sem_ref["degenerado"] is False


def test_fit_falha_alto_quando_toda_a_grade_e_degenerada():
    """Padrão semanal exato: a diferença sazonal é zero, sigma2 colapsa (~1e-10) e a
    verossimilhança fica positiva — o mesmo sintoma da dobra 4 do COMPLETO. O fit
    não pode escolher esse ajuste nem seguir em silêncio."""
    idx = pd.date_range("2021-01-01", periods=140, freq="D")
    y = pd.Series(100.0 + np.tile(np.array([0.0, 5.0, 10.0, 5.0, 0.0, -5.0, -10.0]), 20), index=idx)
    ds = DSFake(y)
    f = _fold(idx, n_teste=28, n_val=21)
    fc = SARIMAXForecaster(grade={"p": [0], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [0]})
    with pytest.raises(RuntimeError, match="nenhuma das 1 ordens convergiu"):
        fc.fit(ds, f, [])
    tabela = fc.tabela_grade
    assert (~tabela["convergiu"]).all() and tabela["degenerado"].all()


def test_predict_falha_alto_se_previsao_sair_da_faixa_do_alvo():
    y = simular_sarima_100_011(400)
    ds = DSFake(y)
    f = _fold(y.index, n_teste=30, n_val=30)
    fc = SARIMAXForecaster(grade={"p": [1], "d": [0], "q": [0], "P": [0], "D": [1], "Q": [1]})
    fc.fit(ds, f, [])
    assert fc.params()["n_rejeitados_insample"] == 0 and fc.params()["n_degenerados"] == 0
    pred = fc.predict(ds, f, [])
    assert np.isfinite(pred).all()
    # a mesma previsao, avaliada contra uma faixa artificialmente estreita, tem de derrubar a run
    fc._y_max_ajuste = 0.0
    with pytest.raises(RuntimeError, match="excede"):
        fc.predict(ds, f, [])
    assert "rejeicao_de_ajustes_degenerados" in fc.params()

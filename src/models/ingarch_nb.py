"""INGARCH binomial negativo log-linear (1,1) — terceiro modelo da trilha clássica
(PROTOCOLO §0.8, RUNBOOK Fase 3).

Especificação (cap_5.tex v1.3, PROTOCOLO §0.8):

    ν_t = log μ_t = β0 + β1·log(y_{t−1} + 1) + α1·ν_{t−1} + γ'x_t
    y_t | F_{t−1} ~ NB2(μ_t, φ),   Var(y_t | F_{t−1}) = μ_t + φ·μ_t²,   φ > 0

(modelo log-linear de Fokianos & Tjøstheim, 2011, com resposta binomial
negativa como em Christou & Fokianos, 2014). Implementação PRÓPRIA em numpy
+ scipy — não via R/tscount —, como pede o §0.8.

  - exógenas x_t = colunas do conjunto de features JÁ defasadas pelo construtor
    (`L ≥ h` garantido em `forecasting_features.py`), padronizadas pelas
    estatísticas da janela de ajuste; o modelo não constrói feature própria;
  - o bloco AR tabular NÃO entra como exógena por padrão
    (`modelos.ingarch_nb.excluir_blocos: [AR]` no runner): o termo
    β1·log(y_{t−1}+1) e a realimentação α1·ν_{t−1} já são a memória do alvo —
    mesma lógica do `excluir_blocos: [AR]` do SARIMAX (PROTOCOLO §0.18);
  - refit por fold, na janela `fold.treino_completo` (treino + validação): não
    há parada antecipada nem hiperparâmetro escolhido na validação;
  - previsão h=1 nas datas de teste: a recursão de ν continua a partir dos
    valores OBSERVADOS até a origem, com os parâmetros congelados. Para a data
    de teste u, μ_u usa y_{u−1} (observado), ν_{u−1} (recursão sobre dados até
    u−1) e x_u (defasagens ≥ 1): exatamente a informação da origem u−1, a mesma
    de Naïve, XGBoost e LSTM.
  - previsão h>1 (PROTOCOLO §0.22): para a data de teste u, origem o = u−h.
    ν_{o+1} usa só y_o e x_{o+1} (conhecidos na origem); nos passos seguintes,
    o y não observado entra pela média condicional prevista (plug-in
    z_{o+s} = log(μ̂_{o+s−1}+1)), e x_{o+s} já está defasado ≥ h. Nenhum y
    posterior à origem é usado. Com h=1 o caminho é o mesmo de antes, bit a bit.

Estimação (decisões numéricas, registradas no manifesto e no PROTOCOLO §0.20
[PROPOSTO]):

  1. **Máxima verossimilhança condicional** da NB2 sobre a janela de ajuste,
     por `scipy.optimize.minimize(method="L-BFGS-B")` com gradiente ANALÍTICO:
     ∂ℓ_t/∂ν_t = (y_t − μ_t)·r/(r + μ_t), r = 1/φ, e a sensibilidade de ν_t aos
     parâmetros segue a mesma recursão de ν (S_t = b_t + α1·S_{t−1}), calculada
     com `scipy.signal.lfilter`. Sem gradiente numérico.
  2. **Reparametrização**: φ = exp(ψ), ψ otimizado livremente (φ > 0 por
     construção, limitado a [1e-8, 1e3] só por segurança numérica); α1 fica em
     caixa |α1| ≤ `limite_alpha1` (0,99) pelos próprios limites do L-BFGS-B —
     escolhida em vez de tanh(·) porque o valor registrado é o próprio parâmetro
     e o gradiente não degenera perto do limite. β0, β1 e γ são livres. A
     condição de estacionariedade do modelo log-linear
     (max{|α1|, |β1|, |α1+β1|} < 1; Fokianos & Tjøstheim, 2011) NÃO é imposta,
     só diagnosticada e registrada (`estacionario`).
  3. **Inicialização determinística**: (β0, β1, γ) por mínimos quadrados de
     log(y_t+1) sobre [1, log(y_{t−1}+1), x_t]; α1 = 0; φ pelo estimador de
     momentos dos resíduos dessa regressão, limitado a [1e-4, 10].
  4. **Valores iniciais da recursão**: μ_0 = ȳ (média do alvo na janela de
     ajuste) e, como não há y_0 dentro da janela, y_0 := ȳ também — o mesmo
     que o `init.method = "marginal"` do tscount. O efeito decai como α1^t.
  5. Falha alto (CLAUDE.md §4.3) se o otimizador não reportar sucesso, se a
     verossimilhança ou algum parâmetro for não finito, se o ajuste in-sample
     ou a previsão saírem de `5 × max|alvo|` (`verificar_faixa` do SARIMAX,
     reutilizada), ou se uma exógena for constante na janela de ajuste.

Determinístico: não há semente. O runner executa uma vez por fold e conjunto e
registra o modelo em `modelos_deterministicos`. Ligação log: previsão negativa
é impossível; `n_previsoes_negativas` é registrado como 0 para o resumo do
manifesto (PROTOCOLO §0.18).
"""
from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.signal import lfilter, lfiltic
from scipy.special import digamma, gammaln

from .base import Forecaster
from .sarimax_model import FATOR_FAIXA, verificar_faixa

__all__ = [
    "INGARCHNBForecaster", "recursao_nu", "loglik_nb2", "negloglik_e_grad",
    "ajustar_ingarch", "inicializar", "desempacotar", "LIMITE_ALPHA1_PADRAO",
]

#: caixa de α1 no L-BFGS-B (|α1| ≤ limite). Qualquer alteração vem do YAML.
LIMITE_ALPHA1_PADRAO = 0.99
#: limites de ψ = log φ, só para segurança numérica (φ ∈ [1e-8, 1e3]).
_LIM_LOG_PHI = (np.log(1e-8), np.log(1e3))
#: penalidade devolvida ao otimizador quando a verossimilhança não é finita.
_PENALIDADE = 1e100


# ------------------------------------------------------------------ núcleo
def desempacotar(theta: np.ndarray, n_exog: int) -> tuple[float, float, float, np.ndarray, float]:
    """θ = (β0, β1, α1, γ_1..γ_k, ψ=log φ) -> (β0, β1, α1, γ, φ)."""
    theta = np.asarray(theta, dtype=float)
    if theta.shape != (4 + n_exog,):
        raise ValueError(f"theta com {theta.shape[0]} entradas para {n_exog} exógenas (esperado {4 + n_exog})")
    return float(theta[0]), float(theta[1]), float(theta[2]), theta[3:3 + n_exog].copy(), float(np.exp(theta[-1]))


def recursao_nu(beta0: float, beta1: float, alpha1: float, gamma: np.ndarray,
                z: np.ndarray, X: np.ndarray | None, nu0: float) -> np.ndarray:
    """ν_t = β0 + β1·z_t + α1·ν_{t−1} + γ'x_t, t = 1..T, com ν_0 = nu0.

    `z_t = log(y_{t−1}+1)` já deslocado pelo chamador. Implementado como filtro
    IIR de primeira ordem (`lfilter`), idêntico ao laço explícito.
    """
    c = beta0 + beta1 * z
    if X is not None and X.shape[1]:
        c = c + X @ gamma
    zi = lfiltic([1.0], [1.0, -alpha1], y=[nu0])
    nu, _ = lfilter([1.0], [1.0, -alpha1], c, zi=zi)
    return np.asarray(nu, dtype=float)


def loglik_nb2(y: np.ndarray, mu: np.ndarray, phi: float) -> float:
    """Σ log NB2(y_t | μ_t, φ), r = 1/φ, p = r/(r+μ)."""
    r = 1.0 / phi
    return float(np.sum(
        gammaln(y + r) - gammaln(r) - gammaln(y + 1.0)
        + r * (np.log(r) - np.log(r + mu)) + y * (np.log(mu) - np.log(r + mu))
    ))


def negloglik_e_grad(theta: np.ndarray, y: np.ndarray, z: np.ndarray, X: np.ndarray | None,
                     nu0: float) -> tuple[float, np.ndarray]:
    """−ℓ(θ) e seu gradiente analítico. Devolve (penalidade, 0) se algo não for finito."""
    n_exog = 0 if X is None else X.shape[1]
    beta0, beta1, alpha1, gamma, phi = desempacotar(theta, n_exog)
    nu = recursao_nu(beta0, beta1, alpha1, gamma, z, X, nu0)
    if not np.all(np.isfinite(nu)) or np.abs(nu).max() > 300.0:
        return _PENALIDADE, np.zeros_like(theta)
    mu = np.exp(nu)
    r = 1.0 / phi
    ll = loglik_nb2(y, mu, phi)
    if not np.isfinite(ll):
        return _PENALIDADE, np.zeros_like(theta)

    # ∂ℓ_t/∂ν_t
    d_nu = (y - mu) * r / (r + mu)
    # sensibilidades: S_t = b_t + α1·S_{t−1}, b_t = [1, z_t, ν_{t−1}, x_t], S_0 = 0
    nu_prev = np.concatenate([[nu0], nu[:-1]])
    partes = [np.ones_like(nu), z, nu_prev]
    if n_exog:
        partes.append(X)
    B = np.column_stack(partes)
    S, _ = lfilter([1.0], [1.0, -alpha1], B, axis=0, zi=np.zeros((1, B.shape[1])))
    grad_theta = d_nu @ S
    # ∂ℓ/∂r, depois ∂r/∂ψ = −r
    d_r = np.sum(digamma(y + r) - digamma(r) + np.log(r) - np.log(r + mu) + 1.0 - (y + r) / (r + mu))
    d_psi = -r * d_r
    grad = np.concatenate([grad_theta, [d_psi]])
    if not np.all(np.isfinite(grad)):
        return _PENALIDADE, np.zeros_like(theta)
    return -ll, -grad


def inicializar(y: np.ndarray, z: np.ndarray, X: np.ndarray | None) -> np.ndarray:
    """θ inicial determinístico (decisão 3 do cabeçalho)."""
    n_exog = 0 if X is None else X.shape[1]
    partes = [np.ones_like(z), z]
    if n_exog:
        partes.append(X)
    D = np.column_stack(partes)
    coef, *_ = np.linalg.lstsq(D, np.log(y + 1.0), rcond=None)
    mu0 = np.exp(D @ coef)
    phi0 = float(np.sum((y - mu0) ** 2 - mu0) / np.sum(mu0 ** 2))
    phi0 = float(np.clip(phi0, 1e-4, 10.0))
    theta = np.concatenate([[coef[0], coef[1], 0.0], coef[2:], [np.log(phi0)]])
    if not np.all(np.isfinite(theta)):
        raise RuntimeError("ingarch_nb: inicialização não finita (alvo ou exógenas degenerados)")
    return theta


def ajustar_ingarch(y: np.ndarray, X: np.ndarray | None, maxiter: int = 2000,
                    limite_alpha1: float = LIMITE_ALPHA1_PADRAO, tol: float = 1e-9) -> dict:
    """MLE do INGARCH-NB(1,1) log-linear. Devolve resumo serializável; falha alto se não convergir."""
    y = np.asarray(y, dtype=float)
    if y.ndim != 1 or y.size < 10:
        raise ValueError(f"ingarch_nb: alvo precisa ser 1-D com >= 10 observações, recebido shape {y.shape}")
    if X is not None:
        X = np.asarray(X, dtype=float)
        if X.shape[0] != y.shape[0]:
            raise ValueError(f"ingarch_nb: X tem {X.shape[0]} linhas para {y.shape[0]} observações")
        if X.shape[1] == 0:
            X = None
    n_exog = 0 if X is None else X.shape[1]
    ybar = float(y.mean())
    if not np.isfinite(ybar) or ybar <= 0:
        raise RuntimeError(f"ingarch_nb: média do alvo na janela de ajuste é {ybar}; o modelo exige ȳ > 0")
    nu0 = float(np.log(ybar))
    # y_0 := ȳ (decisão 4): z_1 = log(ȳ+1); z_t = log(y_{t−1}+1) para t ≥ 2
    z = np.log(np.concatenate([[ybar], y[:-1]]) + 1.0)

    theta0 = inicializar(y, z, X)
    bounds = [(None, None), (None, None), (-abs(limite_alpha1), abs(limite_alpha1))]
    bounds += [(None, None)] * n_exog + [_LIM_LOG_PHI]
    theta0[2] = float(np.clip(theta0[2], bounds[2][0], bounds[2][1]))
    theta0[-1] = float(np.clip(theta0[-1], *_LIM_LOG_PHI))

    t0 = time.perf_counter()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = minimize(
            negloglik_e_grad, theta0, args=(y, z, X, nu0), method="L-BFGS-B", jac=True,
            bounds=bounds, options={"maxiter": int(maxiter), "maxfun": int(50 * maxiter), "ftol": tol, "gtol": 1e-6},
        )
    tempo = time.perf_counter() - t0
    llf = -float(res.fun)
    theta = np.asarray(res.x, dtype=float)
    if not res.success:
        raise RuntimeError(
            f"ingarch_nb: L-BFGS-B não convergiu em {res.nit} iterações ({res.nfev} avaliações): "
            f"{str(res.message)[:160]}"
        )
    if not np.isfinite(llf) or llf <= -_PENALIDADE / 2 or not np.all(np.isfinite(theta)):
        raise RuntimeError(f"ingarch_nb: verossimilhança ou parâmetros não finitos no ótimo (llf={llf})")
    beta0, beta1, alpha1, gamma, phi = desempacotar(theta, n_exog)
    nu = recursao_nu(beta0, beta1, alpha1, gamma, z, X, nu0)
    mu = np.exp(nu)
    n_params = 4 + n_exog
    return {
        "theta": theta, "beta0": beta0, "beta1": beta1, "alpha1": alpha1, "gamma": gamma, "phi": phi,
        "llf": llf, "aic": float(-2.0 * llf + 2.0 * n_params), "n_params": n_params, "nobs": int(y.size),
        "convergiu": bool(res.success), "iteracoes": int(res.nit), "n_avaliacoes": int(res.nfev),
        "mensagem": str(res.message), "tempo_s": round(tempo, 3), "nu0": nu0, "ybar": ybar,
        "mu_insample": mu, "nu_insample": nu, "theta_inicial": theta0,
        "alpha1_no_limite": bool(abs(abs(alpha1) - abs(limite_alpha1)) < 1e-6),
        "estacionario": bool(max(abs(alpha1), abs(beta1), abs(alpha1 + beta1)) < 1.0),
    }


# ------------------------------------------------------------------ modelo
class INGARCHNBForecaster(Forecaster):
    nome = "ingarch_nb"
    treinavel = True
    usa_semente = False

    def __init__(self, maxiter: int = 2000, limite_alpha1: float = LIMITE_ALPHA1_PADRAO, tol: float = 1e-9):
        self.maxiter = int(maxiter)
        if self.maxiter < 1:
            raise ValueError(f"maxiter deve ser >= 1, recebido {maxiter}")
        self.limite_alpha1 = float(limite_alpha1)
        if not (0.0 < self.limite_alpha1 < 1.0):
            raise ValueError(f"limite_alpha1 deve estar em (0, 1), recebido {limite_alpha1}")
        self.tol = float(tol)
        if not (0.0 < self.tol < 1e-2):
            raise ValueError(f"tol deve estar em (0, 1e-2), recebido {tol}")

        self._colunas: list[str] | None = None
        self._mu_x: np.ndarray | None = None
        self._sigma_x: np.ndarray | None = None
        self._ajuste: dict = {}
        self._theta: np.ndarray | None = None
        self._nu_fim_treino: float = float("nan")
        self._y_fim_treino: float = float("nan")
        self._y_max_ajuste: float = float("nan")

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _y(ds, datas: pd.DatetimeIndex) -> np.ndarray:
        y = ds.y.loc[datas].to_numpy(dtype=float)
        if np.isnan(y).any():
            raise RuntimeError(f"ingarch_nb: {int(np.isnan(y).sum())} NaN no alvo da janela pedida")
        if (y < 0).any():
            raise RuntimeError("ingarch_nb: alvo negativo — contagem não pode ser negativa")
        return y

    def _exog(self, ds, datas: pd.DatetimeIndex, colunas: list[str], ajustar: bool) -> np.ndarray | None:
        if not colunas:
            return None
        X = ds.X.loc[datas, colunas]
        if X.isna().any().any():
            ruins = X.columns[X.isna().any()].tolist()
            raise RuntimeError(
                f"ingarch_nb: NaN nas exógenas {ruins[:8]} — o construtor de features deveria ter falhado antes"
            )
        Xv = X.to_numpy(dtype=float)
        if ajustar:
            mu = Xv.mean(axis=0)
            sigma = Xv.std(axis=0, ddof=0)
            constantes = [c for c, s in zip(colunas, sigma) if not np.isfinite(s) or s == 0.0]
            if constantes:
                raise RuntimeError(
                    f"ingarch_nb: exógena(s) constante(s) na janela de ajuste: {constantes}. "
                    f"Colineares com o intercepto; o conjunto de features precisa ser revisto."
                )
            self._mu_x, self._sigma_x = mu, sigma
        if self._mu_x is None or self._sigma_x is None:
            raise RuntimeError("ingarch_nb: exógenas pedidas antes do fit")
        return (Xv - self._mu_x) / self._sigma_x

    # ----------------------------------------------------------------- API
    def fit(self, ds, fold, colunas) -> None:
        if int(ds.horizonte) < 1:
            raise ValueError(f"ingarch_nb: horizonte inválido h={ds.horizonte}")
        datas = fold.treino_completo
        if not datas.is_monotonic_increasing:
            raise ValueError("ingarch_nb: janela de ajuste fora de ordem")
        if len(datas) > 1 and not (np.diff(datas.to_numpy()) == np.timedelta64(1, "D")).all():
            raise RuntimeError("ingarch_nb: janela de ajuste não é contígua (a recursão exige série diária)")
        colunas = list(colunas)
        y = self._y(ds, datas)
        X = self._exog(ds, datas, colunas, ajustar=True)
        self._colunas = colunas

        aj = ajustar_ingarch(y, X, maxiter=self.maxiter, limite_alpha1=self.limite_alpha1, tol=self.tol)
        y_max = float(np.abs(y).max())
        motivo = verificar_faixa(aj["mu_insample"], y_max, "ajuste in-sample")
        if motivo is not None:
            raise RuntimeError(
                f"ingarch_nb com {len(colunas)} exógenas, janela {datas.min().date()}..{datas.max().date()}: {motivo}"
            )

        self._theta = aj["theta"]
        self._nu_fim_treino = float(aj["nu_insample"][-1])
        self._nu_insample = np.asarray(aj["nu_insample"], dtype=float)
        self._X_ajuste = X
        self._y_fim_treino = float(y[-1])
        self._y_max_ajuste = y_max
        self._ajuste = {
            "beta0": aj["beta0"],
            "beta1": aj["beta1"],
            "alpha1": aj["alpha1"],
            "phi": aj["phi"],
            "gamma": {c: float(g) for c, g in zip(colunas, aj["gamma"])},
            "llf": aj["llf"],
            "aic": aj["aic"],
            "n_params": aj["n_params"],
            "convergiu": aj["convergiu"],
            "iteracoes": aj["iteracoes"],
            "n_avaliacoes": aj["n_avaliacoes"],
            "mensagem_otimizador": aj["mensagem"],
            "alpha1_no_limite": aj["alpha1_no_limite"],
            "estacionario": aj["estacionario"],
            "mu_0": aj["ybar"],
            "theta_inicial": [float(v) for v in aj["theta_inicial"]],
            "nobs_ajuste": aj["nobs"],
            "janela_ajuste": "treino+validacao",
            "janela_ajuste_inicio": str(datas.min().date()),
            "janela_ajuste_fim": str(datas.max().date()),
            "tempo_ajuste_s": aj["tempo_s"],
        }

    def predict(self, ds, fold, colunas) -> np.ndarray:
        if self._theta is None:
            raise RuntimeError("predict chamado antes de fit")
        colunas = list(colunas)
        if colunas != self._colunas:
            raise RuntimeError("ingarch_nb: colunas do predict diferem das do fit")
        treino = fold.treino_completo
        teste = fold.teste
        if treino.max() >= teste.min():
            raise ValueError("ingarch_nb: teste não sucede a janela de ajuste")
        lacuna = (teste.min() - treino.max()).days
        if lacuna != 1:
            raise RuntimeError(
                f"ingarch_nb: lacuna de {lacuna} dias entre o fim do ajuste ({treino.max().date()}) e o "
                f"início do teste ({teste.min().date()}); a recursão exige série contígua"
            )
        if len(teste) > 1 and not (np.diff(teste.to_numpy()) == np.timedelta64(1, "D")).all():
            raise RuntimeError("ingarch_nb: bloco de teste não é contíguo")

        y_teste = self._y(ds, teste)
        X_teste = self._exog(ds, teste, colunas, ajustar=False)
        beta0, beta1, alpha1, gamma, _ = desempacotar(self._theta, len(colunas))
        # z_u = log(y_{u−1}+1): o último y do treino para a primeira data de teste,
        # depois os y observados do próprio bloco de teste até a origem u−1
        z = np.log(np.concatenate([[self._y_fim_treino], y_teste[:-1]]) + 1.0)
        nu = recursao_nu(beta0, beta1, alpha1, gamma, z, X_teste, self._nu_fim_treino)
        h = int(ds.horizonte)
        if h == 1:
            pred = np.exp(nu)
        else:
            pred = self._prever_h_passos(nu, X_teste, h, beta0, beta1, alpha1, gamma)
        if pred.shape[0] != len(teste):
            raise RuntimeError(f"ingarch_nb: {pred.shape[0]} previsões para {len(teste)} datas de teste")
        motivo = verificar_faixa(pred, self._y_max_ajuste, "previsão de teste")
        if motivo is not None:
            raise RuntimeError(
                f"ingarch_nb com {len(colunas)} exógenas, teste {teste.min().date()}..{teste.max().date()}: {motivo}"
            )
        return pred

    def _prever_h_passos(self, nu_teste, X_teste, h, beta0, beta1, alpha1, gamma) -> np.ndarray:
        """Recursão multi-passo a partir da origem o = u − h (PROTOCOLO §0.22).

        `nu_obs[k]` é ν na posição k da série treino+teste com y OBSERVADO até k−1;
        ν_{o+1} = nu_obs[o+1] só usa y_o. Depois, s = 2..h:
        ν_{o+s} = β0 + β1·log(exp(ν_{o+s−1})+1) + α1·ν_{o+s−1} + γ'x_{o+s}.
        """
        nu_obs = np.concatenate([self._nu_insample, nu_teste])
        X_full = None
        if X_teste is not None and X_teste.shape[1]:
            X_full = np.vstack([self._X_ajuste, X_teste])
        n_tr = len(self._nu_insample)
        if n_tr < h:
            raise RuntimeError(f"ingarch_nb: janela de ajuste ({n_tr}) menor que o horizonte h={h}")
        pred = np.empty(len(nu_teste))
        for j in range(len(nu_teste)):
            alvo = n_tr + j
            o = alvo - h
            v = nu_obs[o + 1]
            for k in range(o + 2, alvo + 1):
                c = beta0 + beta1 * np.log(np.exp(v) + 1.0) + alpha1 * v
                if X_full is not None:
                    c = c + float(X_full[k] @ gamma)
                v = c
            pred[j] = np.exp(v)
        return pred

    def params(self) -> dict:
        return {
            "deterministico": True,
            "modelo": "INGARCH log-linear (1,1), resposta NB2 (Var = mu + phi*mu^2)",
            "ligacao": "log",
            "ordem": [1, 1],
            "maxiter": self.maxiter,
            "limite_alpha1": self.limite_alpha1,
            "tol": self.tol,
            "otimizador": "scipy L-BFGS-B, gradiente analítico; phi = exp(psi); |alpha1| <= limite_alpha1 por caixa",
            "inicializacao": "OLS de log(y+1) em [1, log(y_lag1+1), x]; alpha1 = 0; phi por momentos",
            "valores_iniciais_recursao": "mu_0 = y_0 = média do alvo na janela de ajuste",
            "previsao_h_passos": "h=1: recursão com y observado; h>1: plug-in z = log(mu_prevista+1) "
                                 "nos passos não observados entre a origem e a data-alvo (PROTOCOLO §0.22)",
            "n_exogenas": None if self._colunas is None else len(self._colunas),
            "exogenas": list(self._colunas or []),
            "exogenas_padronizadas": True,
            "fator_faixa": FATOR_FAIXA,
            # ligação log: negativo impossível; registrado como 0 para o resumo do manifesto (§0.18)
            "truncar_negativos": False,
            "n_previsoes_negativas": 0 if self._theta is not None else None,
            "n_previsoes_truncadas": 0 if self._theta is not None else None,
            **self._ajuste,
        }

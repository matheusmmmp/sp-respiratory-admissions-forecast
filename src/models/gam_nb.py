"""GAM binomial negativo — segundo modelo da trilha clássica (PROTOCOLO §0.8, RUNBOOK Fase 3).

Especificação (cap_5.tex v1.3, PROTOCOLO §0.8):
  - ligação log, família binomial negativa (NB2) com α estimado no treino do fold;
  - `y_{t−1}` e `y_{t−7}` como termos LINEARES (colunas `y_lag1`, `y_lag7` do bloco AR);
  - dia da semana e feriado CATEGÓRICOS (`dow` vira seis indicadoras, referência
    segunda-feira; `feriado` já é 0/1);
  - Fourier anual K=2 (`sin1, cos1, sin2, cos2` do bloco CAL), linear;
  - splines penalizados (B-splines cúbicos, dimensão máxima `k_splines`=5) para o
    PM2.5 e a temperatura MAIS RECENTES disponíveis na origem — a coluna de menor
    defasagem `L ≥ h` entre as do conjunto —, SÓ quando o conjunto contém esses blocos;
  - as demais colunas do conjunto (outras defasagens, umidade, vento, PM10...)
    entram lineares.

O que fica FORA, e por quê (registrado em `params()["colunas_descartadas"]`):
  - `y_lag2, y_lag3, y_lag14, y_lag28`: a especificação diz y_{t−1} e y_{t−7};
    `lags_ar` no YAML permite outra escolha, mas a padrão é a do PROTOCOLO;
  - `fim_de_semana`: combinação linear exata das indicadoras de `dow`;
  - `mes`: a sazonalidade anual já é o Fourier K=2; como inteiro linear não tem
    interpretação.

Janela de ajuste: `fold.treino_completo` (treino + validação), como no SARIMAX —
não há parada antecipada nem hiperparâmetro escolhido na validação.

Decisões numéricas (todas [PROPOSTO] no PROTOCOLO §0.19 até homologação):
  1. α (dispersão NB2, Var = μ + αμ²) por verossimilhança perfilada alternada
     — o "theta.ml" do MASS::glm.nb: dado α, o GAM é ajustado por PIRLS; dado
     μ̂, α maximiza a log-verossimilhança NB2 em 1-D (`minimize_scalar`, log α
     limitado a [ln 1e-4, ln 10]); repete até |Δ log α| < 1e-3 (máx.
     `max_iter_alpha`). Valor inicial: estimador de momentos a partir de um GLM
     Poisson com a parte paramétrica. Verificado no fold 4/COMPLETO em
     2026-10-21: α̂ = 0,0182 contra 0,0184 da MLE conjunta do
     `sm.NegativeBinomial` sem splines.
  2. Penalização dos splines por GRADE fixa (`grade_penalizacao`, padrão
     10^{-2..8}, 11 valores por spline, produto cartesiano), escolhida pelo AIC
     com graus de liberdade efetivos (−2·llf + 2·Σedf) na janela de ajuste, com α
     fixo em cada iteração. `GLMGam.select_penweight` não foi usado: o padrão
     (`basinhopping`) é estocástico e o método chama `self.scale` antes do fit
     (AttributeError no 0.14.6). A grade é determinística e registrada.
  3. Valores de PM2.5/temperatura de TESTE fora do suporte do treino são
     truncados à faixa [mín, máx] do treino (o `BSplines` do statsmodels
     levanta `NotImplementedError` fora dos nós; o mgcv extrapolaria
     linearmente). A contagem fica em `params()["n_fora_do_suporte"]`.
  4. Colunas lineares são padronizadas pelas estatísticas da janela de ajuste
     (condicionamento numérico do PIRLS; não muda a previsão). Coluna constante
     na janela falha alto, como no SARIMAX.

Negativos: impossíveis pela ligação log (PROTOCOLO §0.18 não se aplica); a
contagem é registrada como 0 para o resumo do manifesto. Previsão não finita
ou acima de `FATOR_FAIXA` × max|alvo| da janela de ajuste falha alto
(`verificar_faixa` do SARIMAX, reutilizada), e o ajuste in-sample passa pela
mesma barreira.

Determinístico: PIRLS, grade e otimização 1-D não têm semente. O runner executa
uma vez por fold e conjunto (`usa_semente = False`).
"""
from __future__ import annotations

import itertools
import re
import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import gammaln

from .base import Forecaster
from .sarimax_model import FATOR_FAIXA, verificar_faixa

try:
    import statsmodels.api as sm
    from statsmodels.gam.api import BSplines, GLMGam
except ImportError as exc:  # pragma: no cover - ambiente sem statsmodels
    raise ImportError(
        "statsmodels é obrigatório para o GAM-NB e não está instalado. "
        "A execução deve falhar em vez de pular o modelo em silêncio. "
        "O venv oficial (env/.venv311) tem statsmodels==0.14.6."
    ) from exc

__all__ = [
    "GAMNBForecaster", "GRADE_PENALIZACAO_PADRAO", "LAGS_AR_PADRAO",
    "classificar_colunas", "loglik_nb2", "estimar_alpha",
]

#: λ por spline; produto cartesiano entre os splines. Alterável por `modelos.gam_nb.grade_penalizacao`.
GRADE_PENALIZACAO_PADRAO: tuple[float, ...] = tuple(10.0 ** k for k in range(-2, 9))
#: defasagens do alvo que entram lineares (PROTOCOLO §0.8: y_{t−1}, y_{t−7}).
LAGS_AR_PADRAO: tuple[int, ...] = (1, 7)
#: K do Fourier anual (PROTOCOLO §0.8: K=2); as colunas `sin{k}`, `cos{k}` com k ≤ K entram.
FOURIER_K = 2
#: bases (nome antes de `_lag{L}`) que recebem spline — CETESB e CAMS.
BASES_SPLINE_PM25: tuple[str, ...] = ("pm25_media", "pm2p5")
BASES_SPLINE_TEMPERATURA: tuple[str, ...] = ("temp_media", "t2m_c")
#: colunas do bloco CAL que NÃO entram (ver docstring).
CAL_DESCARTADAS: tuple[str, ...] = ("mes", "fim_de_semana")
#: limites de α na otimização 1-D (escala log).
ALPHA_MIN, ALPHA_MAX = 1e-4, 10.0
#: níveis de `dow` (0 = segunda-feira, referência).
NIVEIS_DOW = tuple(range(7))

_RE_LAG = re.compile(r"^(?P<base>.+)_lag(?P<lag>\d+)$")


# ------------------------------------------------------------ classificação
def classificar_colunas(colunas: list[str], horizonte: int, lags_ar=LAGS_AR_PADRAO,
                        fourier_k: int = FOURIER_K) -> dict:
    """Separa as colunas do conjunto em lineares, categóricas, splines e descartadas.

    Spline recebe, por base em `BASES_SPLINE_*`, a coluna de MENOR defasagem
    `L ≥ h` presente no conjunto; as outras defasagens da mesma base ficam
    lineares. Se o conjunto não contém a base, não há spline para ela — o
    modelo nunca inventa feature.
    """
    colunas = list(colunas)
    if len(set(colunas)) != len(colunas):
        raise ValueError("gam_nb: colunas duplicadas no conjunto")
    lags_ar = [int(L) for L in lags_ar]
    y_lags = {}
    por_base: dict[str, dict[int, str]] = {}
    lineares: list[str] = []
    categoricas: list[str] = []
    descartadas: dict[str, str] = {}
    fourier: list[str] = []

    for c in colunas:
        m = _RE_LAG.match(c)
        if m and m.group("base") == "y":
            y_lags[int(m.group("lag"))] = c
            continue
        if c == "dow":
            categoricas.append(c)
            continue
        if c == "feriado":
            categoricas.append(c)
            continue
        if c in CAL_DESCARTADAS:
            descartadas[c] = ("colinear com as indicadoras de dow" if c == "fim_de_semana"
                              else "sazonalidade anual já é o Fourier K=%d" % fourier_k)
            continue
        mf = re.match(r"^(sin|cos)(\d+)$", c)
        if mf:
            if int(mf.group(2)) <= fourier_k:
                fourier.append(c)
            else:
                descartadas[c] = f"harmônico acima de K={fourier_k}"
            continue
        if m:
            base, lag = m.group("base"), int(m.group("lag"))
            if base in BASES_SPLINE_PM25 + BASES_SPLINE_TEMPERATURA:
                por_base.setdefault(base, {})[lag] = c
                continue
        lineares.append(c)

    # AR: só as defasagens pedidas, e elas precisam existir se o bloco AR veio
    ar_lineares: list[str] = []
    if y_lags:
        faltando = [L for L in lags_ar if L not in y_lags]
        if faltando:
            raise ValueError(
                f"gam_nb: lags_ar={lags_ar} pede y_lag{faltando} e o conjunto só tem "
                f"{sorted(y_lags.values())}. Ajuste experimento.lags_alvo ou modelos.gam_nb.lags_ar."
            )
        for L in lags_ar:
            if L < horizonte:
                raise ValueError(f"gam_nb: y_lag{L} viola L >= h com h={horizonte}")
            ar_lineares.append(y_lags[L])
        for L, c in sorted(y_lags.items()):
            if L not in lags_ar:
                descartadas[c] = f"PROTOCOLO §0.8: só y_{{t-{','.join(map(str, lags_ar))}}} entram (lags_ar)"

    splines: list[dict] = []
    for base, lags in por_base.items():
        validos = {L: c for L, c in lags.items() if L >= horizonte}
        if not validos:
            raise ValueError(f"gam_nb: nenhuma defasagem de {base!r} respeita L >= h={horizonte}")
        L0 = min(validos)
        tipo = "pm25" if base in BASES_SPLINE_PM25 else "temperatura"
        splines.append({"coluna": validos[L0], "base": base, "lag": L0, "tipo": tipo})
        for L, c in sorted(lags.items()):
            if L != L0:
                lineares.append(c)
    # ordem estável: pm25 antes de temperatura, depois por nome
    splines.sort(key=lambda s: (s["tipo"] != "pm25", s["coluna"]))

    return {
        "ar_lineares": ar_lineares,
        "fourier": fourier,
        "categoricas": categoricas,
        "lineares": sorted(lineares),
        "splines": splines,
        "descartadas": descartadas,
    }


# ------------------------------------------------------------------ α (NB2)
def loglik_nb2(y: np.ndarray, mu: np.ndarray, alpha: float) -> float:
    """Log-verossimilhança NB2 (Var = μ + αμ²) somada, dado μ."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if alpha <= 0 or not np.isfinite(alpha):
        raise ValueError(f"alpha deve ser > 0 e finito, recebido {alpha}")
    r = 1.0 / alpha
    amu = alpha * mu
    return float(np.sum(
        gammaln(y + r) - gammaln(r) - gammaln(y + 1.0)
        + y * np.log(amu / (1.0 + amu)) - r * np.log1p(amu)
    ))


def estimar_alpha(y: np.ndarray, mu: np.ndarray) -> float:
    """α que maximiza a log-verossimilhança NB2 dado μ (1-D, em log α, limitado)."""
    opt = minimize_scalar(
        lambda la: -loglik_nb2(y, mu, float(np.exp(la))),
        bounds=(np.log(ALPHA_MIN), np.log(ALPHA_MAX)), method="bounded",
        options={"xatol": 1e-6},
    )
    if not opt.success or not np.isfinite(opt.x):
        raise RuntimeError(f"gam_nb: otimização de alpha falhou: {opt.message}")
    return float(np.exp(opt.x))


def alpha_momentos(y: np.ndarray, mu: np.ndarray) -> float:
    """Estimador de momentos α = Σ[(y−μ)² − μ] / Σμ², limitado a [ALPHA_MIN, ALPHA_MAX]."""
    num = float(np.sum((y - mu) ** 2 - mu))
    den = float(np.sum(mu ** 2))
    if den <= 0 or not np.isfinite(num / den):
        return ALPHA_MIN
    return float(np.clip(num / den, ALPHA_MIN, ALPHA_MAX))


# ------------------------------------------------------------------- modelo
class GAMNBForecaster(Forecaster):
    nome = "gam_nb"
    treinavel = True
    usa_semente = False

    def __init__(
        self,
        k_splines: int = 5,
        lags_ar=LAGS_AR_PADRAO,
        grade_penalizacao=GRADE_PENALIZACAO_PADRAO,
        max_iter_alpha: int = 10,
        tol_alpha: float = 1e-3,
    ):
        if int(k_splines) < 4:
            raise ValueError(f"k_splines deve ser >= 4 (B-spline cúbico); recebido {k_splines}")
        self.k_splines = int(k_splines)
        self.lags_ar = tuple(int(L) for L in lags_ar)
        if not self.lags_ar or any(L < 1 for L in self.lags_ar):
            raise ValueError(f"lags_ar deve ser lista de inteiros >= 1, recebido {lags_ar!r}")
        grade = sorted({float(g) for g in grade_penalizacao})
        if not grade or any((g <= 0) or not np.isfinite(g) for g in grade):
            raise ValueError(f"grade_penalizacao deve conter valores > 0 finitos, recebido {grade_penalizacao!r}")
        self.grade_penalizacao = tuple(grade)
        self.max_iter_alpha = int(max_iter_alpha)
        if self.max_iter_alpha < 1:
            raise ValueError("max_iter_alpha deve ser >= 1")
        self.tol_alpha = float(tol_alpha)

        self._colunas: list[str] | None = None
        self._plano: dict | None = None
        self._res = None
        self._smoother = None
        self._mu: pd.Series | None = None
        self._sigma: pd.Series | None = None
        self._colunas_design: list[str] | None = None
        self._suporte: list[tuple[float, float]] = []
        self._alpha: float = float("nan")
        self._lambdas: list[float] = []
        self._ajuste: dict = {}
        self._y_max_ajuste: float = float("nan")
        self._n_fora_suporte: list[int] | None = None

    # ------------------------------------------------------------- design
    @staticmethod
    def _y(ds, datas: pd.DatetimeIndex) -> np.ndarray:
        y = ds.y.loc[datas].to_numpy(dtype=float)
        if np.isnan(y).any():
            raise RuntimeError(f"gam_nb: {int(np.isnan(y).sum())} NaN no alvo da janela pedida")
        if (y < 0).any():
            raise RuntimeError("gam_nb: alvo negativo — contagem não pode ser negativa")
        return y

    def _frame(self, ds, datas: pd.DatetimeIndex, colunas: list[str]) -> pd.DataFrame:
        if not colunas:
            return pd.DataFrame(index=datas)
        X = ds.X.loc[datas, colunas]
        if X.isna().any().any():
            ruins = X.columns[X.isna().any()].tolist()
            raise RuntimeError(
                f"gam_nb: NaN nas colunas {ruins[:8]} — o construtor de features deveria ter falhado antes"
            )
        return X

    def _parametrico(self, X: pd.DataFrame, ajustar: bool) -> pd.DataFrame:
        """Parte paramétrica: intercepto, lineares padronizadas, Fourier, indicadoras."""
        plano = self._plano
        assert plano is not None
        partes: list[pd.DataFrame] = []
        num_cols = plano["ar_lineares"] + plano["fourier"] + plano["lineares"]
        if num_cols:
            Z = X[num_cols].astype(float)
            if ajustar:
                mu = Z.mean()
                sigma = Z.std(ddof=0)
                constantes = [c for c in num_cols if not np.isfinite(sigma[c]) or sigma[c] == 0.0]
                if constantes:
                    raise RuntimeError(
                        f"gam_nb: coluna(s) constante(s) na janela de ajuste: {constantes}. "
                        f"Colineares com o intercepto; o conjunto de features precisa ser revisto."
                    )
                self._mu, self._sigma = mu, sigma
            if self._mu is None or self._sigma is None:
                raise RuntimeError("gam_nb: design pedido antes do fit")
            partes.append((Z - self._mu) / self._sigma)
        for c in plano["categoricas"]:
            v = X[c].to_numpy()
            if c == "dow":
                niveis = NIVEIS_DOW
                desconhecidos = sorted(set(np.unique(v)) - set(niveis))
                if desconhecidos:
                    raise RuntimeError(f"gam_nb: dow com níveis fora de 0..6: {desconhecidos}")
                partes.append(pd.DataFrame(
                    {f"dow_{k}": (v == k).astype(float) for k in niveis[1:]}, index=X.index
                ))
            else:  # feriado: indicadora 0/1
                vals = set(np.unique(v))
                if not vals <= {0, 1}:
                    raise RuntimeError(f"gam_nb: {c} deveria ser 0/1, recebido {sorted(vals)[:5]}")
                partes.append(pd.DataFrame({c: v.astype(float)}, index=X.index))
        D = pd.concat(partes, axis=1) if partes else pd.DataFrame(index=X.index)
        D.insert(0, "const", 1.0)
        if ajustar:
            self._colunas_design = list(D.columns)
        elif list(D.columns) != self._colunas_design:
            raise RuntimeError("gam_nb: design de previsão difere do design de ajuste")
        return D

    def _x_splines(self, X: pd.DataFrame, ajustar: bool) -> np.ndarray | None:
        plano = self._plano
        assert plano is not None
        if not plano["splines"]:
            return None
        xs = X[[s["coluna"] for s in plano["splines"]]].to_numpy(dtype=float)
        if ajustar:
            self._suporte = [(float(xs[:, j].min()), float(xs[:, j].max())) for j in range(xs.shape[1])]
            for (lo, hi), s in zip(self._suporte, plano["splines"]):
                if not hi > lo:
                    raise RuntimeError(f"gam_nb: {s['coluna']} constante na janela de ajuste; spline impossível")
            self._n_fora_suporte = None
            return xs
        # Fora do suporte do treino: truncar e registrar (decisão 3 da docstring).
        fora = np.zeros(xs.shape[1], dtype=int)
        xc = xs.copy()
        for j, (lo, hi) in enumerate(self._suporte):
            fora[j] = int(((xs[:, j] < lo) | (xs[:, j] > hi)).sum())
            xc[:, j] = np.clip(xs[:, j], lo, hi)
        self._n_fora_suporte = fora.tolist()
        return xc

    # ---------------------------------------------------------------- ajuste
    def _fit_uma(self, y: np.ndarray, D: np.ndarray, xs: np.ndarray | None, alpha: float,
                 lambdas: list[float]):
        fam = sm.families.NegativeBinomial(alpha=alpha)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if xs is None:
                res = sm.GLM(y, D, family=fam).fit()
                edf = float(D.shape[1])
            else:
                res = GLMGam(y, exog=D, smoother=self._smoother, alpha=list(lambdas), family=fam).fit()
                edf = float(np.sum(res.edf))
        llf = float(res.llf)
        if not np.isfinite(llf) or not np.all(np.isfinite(np.asarray(res.params, dtype=float))):
            raise RuntimeError(f"gam_nb: ajuste com verossimilhança ou parâmetros não finitos (alpha={alpha:g}, lambdas={lambdas})")
        return res, llf, edf

    def _selecionar_lambdas(self, y, D, xs, alpha: float) -> tuple[object, list[float], float, float, list[dict]]:
        n_s = 0 if xs is None else xs.shape[1]
        if n_s == 0:
            res, llf, edf = self._fit_uma(y, D, None, alpha, [])
            return res, [], llf, edf, []
        tabela: list[dict] = []
        melhor = None
        for lambdas in itertools.product(self.grade_penalizacao, repeat=n_s):
            lambdas = list(lambdas)
            res, llf, edf = self._fit_uma(y, D, xs, alpha, lambdas)
            aic = -2.0 * llf + 2.0 * edf
            tabela.append({"lambdas": lambdas, "llf": llf, "edf": edf, "aic": aic})
            # menor AIC; empate -> maior penalização (mais simples); ordem da grade
            chave = (aic, -float(np.sum(np.log(lambdas))))
            if melhor is None or chave < melhor[0]:
                melhor = (chave, res, lambdas, llf, edf)
        _, res, lambdas, llf, edf = melhor
        return res, lambdas, llf, edf, tabela

    def fit(self, ds, fold, colunas) -> None:
        datas = fold.treino_completo
        if not datas.is_monotonic_increasing:
            raise ValueError("gam_nb: janela de ajuste fora de ordem")
        colunas = list(colunas)
        self._colunas = colunas
        self._plano = classificar_colunas(colunas, int(ds.horizonte), self.lags_ar)
        y = self._y(ds, datas)
        X = self._frame(ds, datas, colunas)
        D = self._parametrico(X, ajustar=True)
        xs = self._x_splines(X, ajustar=True)
        if xs is not None:
            n_s = xs.shape[1]
            self._smoother = BSplines(
                xs, df=[self.k_splines] * n_s, degree=[3] * n_s, include_intercept=False,
                variable_names=[s["coluna"] for s in self._plano["splines"]],
            )
        else:
            self._smoother = None
        Dv = D.to_numpy(dtype=float)

        t0 = time.perf_counter()
        # valor inicial de α: momentos a partir de um GLM Poisson da parte paramétrica
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mu0 = np.asarray(sm.GLM(y, Dv, family=sm.families.Poisson()).fit().fittedvalues, dtype=float)
        alpha = alpha_momentos(y, mu0)
        alpha_inicial = alpha
        historico: list[dict] = []
        convergiu = False
        res = lambdas = llf = edf = tabela = None
        for it in range(1, self.max_iter_alpha + 1):
            res, lambdas, llf, edf, tabela = self._selecionar_lambdas(y, Dv, xs, alpha)
            mu = np.asarray(res.fittedvalues, dtype=float)
            alpha_novo = estimar_alpha(y, mu)
            historico.append({"iteracao": it, "alpha_entrada": alpha, "alpha_saida": alpha_novo,
                              "lambdas": lambdas, "llf": llf, "edf": edf,
                              "llf_nb2_alpha_saida": loglik_nb2(y, mu, alpha_novo)})
            delta = abs(np.log(alpha_novo) - np.log(alpha))
            alpha = alpha_novo
            if delta < self.tol_alpha:
                convergiu = True
                break
        if not convergiu:
            raise RuntimeError(
                f"gam_nb: alpha não convergiu em {self.max_iter_alpha} iterações "
                f"(último Δlog α = {delta:.3g}); janela {datas.min().date()}..{datas.max().date()}"
            )
        # ajuste final com o α convergido e os λ da última seleção (os parâmetros
        # registrados são exatamente os do modelo que prevê)
        res, llf, edf = self._fit_uma(y, Dv, xs, alpha, lambdas)
        tempo = time.perf_counter() - t0

        y_max = float(np.abs(y).max())
        motivo = verificar_faixa(np.asarray(res.fittedvalues, dtype=float), y_max, "ajuste in-sample")
        if motivo is not None:
            raise RuntimeError(
                f"gam_nb com {len(colunas)} colunas, janela {datas.min().date()}..{datas.max().date()}: {motivo}"
            )

        self._res = res
        self._alpha = float(alpha)
        self._lambdas = list(lambdas)
        self._y_max_ajuste = y_max
        edf_por_spline = (
            [float(v) for v in np.asarray(res.edf, dtype=float)[-self._smoother.dim_basis:]]
            if xs is not None else []
        )
        self._ajuste = {
            "alpha_nb": float(alpha),
            "alpha_inicial_momentos": float(alpha_inicial),
            "n_iteracoes_alpha": len(historico),
            "historico_alpha": historico,
            "lambdas": list(lambdas),
            "n_combinacoes_grade": len(tabela),
            "llf": float(llf),
            "edf_total": float(edf),
            "aic_edf": float(-2.0 * llf + 2.0 * edf),
            "edf_por_coluna_spline": edf_por_spline,
            "n_params_parametricos": int(Dv.shape[1]),
            "colunas_design": list(self._colunas_design or []),
            "splines": [dict(s, suporte_treino=list(sup), n_basis=self._smoother.dim_basis // len(self._plano["splines"]))
                        for s, sup in zip(self._plano["splines"], self._suporte)],
            "ar_lineares": list(self._plano["ar_lineares"]),
            "fourier": list(self._plano["fourier"]),
            "categoricas": list(self._plano["categoricas"]),
            "lineares": list(self._plano["lineares"]),
            "colunas_descartadas": dict(self._plano["descartadas"]),
            "nobs_ajuste": int(len(y)),
            "janela_ajuste": "treino+validacao",
            "janela_ajuste_inicio": str(datas.min().date()),
            "janela_ajuste_fim": str(datas.max().date()),
            "tempo_ajuste_s": round(tempo, 2),
        }
        self._n_fora_suporte = None

    # --------------------------------------------------------------- previsão
    def predict(self, ds, fold, colunas) -> np.ndarray:
        if self._res is None or self._plano is None:
            raise RuntimeError("predict chamado antes de fit")
        colunas = list(colunas)
        if colunas != self._colunas:
            raise RuntimeError("gam_nb: colunas do predict diferem das do fit")
        teste = fold.teste
        if fold.treino_completo.max() >= teste.min():
            raise ValueError("gam_nb: teste não sucede a janela de ajuste")
        X = self._frame(ds, teste, colunas)
        D = self._parametrico(X, ajustar=False).to_numpy(dtype=float)
        xs = self._x_splines(X, ajustar=False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if xs is None:
                pred = self._res.predict(D)
            else:
                pred = self._res.predict(exog=D, exog_smooth=xs, transform=True)
        pred = np.asarray(pred, dtype=float)
        if pred.shape[0] != len(teste):
            raise RuntimeError(f"gam_nb: {pred.shape[0]} previsões para {len(teste)} datas de teste")
        motivo = verificar_faixa(pred, self._y_max_ajuste, "previsão de teste")
        if motivo is not None:
            raise RuntimeError(
                f"gam_nb com {len(colunas)} colunas, teste {teste.min().date()}..{teste.max().date()}: {motivo}"
            )
        return pred

    def params(self) -> dict:
        return {
            "deterministico": True,
            "familia": "NegativeBinomial (NB2, Var = mu + alpha*mu^2)",
            "ligacao": "log",
            "k_splines": self.k_splines,
            "grau_spline": 3,
            "lags_ar": list(self.lags_ar),
            "fourier_k": FOURIER_K,
            "grade_penalizacao": list(self.grade_penalizacao),
            "criterio_penalizacao": "AIC com graus de liberdade efetivos (-2 llf + 2 edf), janela de ajuste",
            "estimacao_alpha": "verossimilhança perfilada alternada (PIRLS dado alpha; alpha 1-D dado mu)",
            "max_iter_alpha": self.max_iter_alpha,
            "tol_alpha": self.tol_alpha,
            "fora_do_suporte": "valores de teste truncados ao [min, max] do treino",
            "n_fora_do_suporte": self._n_fora_suporte,
            "fator_faixa": FATOR_FAIXA,
            "n_colunas_conjunto": None if self._colunas is None else len(self._colunas),
            # ligação log: negativo é impossível; registrado para o resumo do manifesto
            "truncar_negativos": False,
            "n_previsoes_negativas": 0 if self._res is not None else None,
            "n_previsoes_truncadas": 0 if self._res is not None else None,
            **self._ajuste,
        }

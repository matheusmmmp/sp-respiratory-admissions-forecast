"""SARIMAX — primeiro modelo da trilha clássica (PROTOCOLO §0.8, RUNBOOK Fase 3).

Especificação (cap_5.tex v1.3, PROTOCOLO §0.8):
  - `(p,d,q)×(P,D,Q)_m` com m = `periodo_sazonal` (7), grade `p,q∈{0,1,2}`,
    `d,P,D,Q∈{0,1}`, `p+q+P+Q≤4` — 124 ordens;
  - entre os ajustes CONVERGENTES, o de menor AICc, calculado SOMENTE na janela
    de ajuste do fold (nunca no teste);
  - exógenas = as colunas do conjunto de features, JÁ defasadas pelo construtor
    (`L ≥ h` garantido em `forecasting_features.py`); o modelo não constrói
    nenhuma feature própria;
  - refit por fold: a grade inteira é reavaliada em cada fold;
  - previsão h passos à frente nas datas de teste, usando os valores observados
    até a origem — mesma informação que Naïve, XGBoost e LSTM.

Janela de ajuste: `fold.treino_completo` (treino + validação). O SARIMAX não
tem parada antecipada nem hiperparâmetro escolhido fora da verossimilhança, e
`Fold.treino_completo` existe exatamente para esse caso. Fica registrado em
`params()` como `janela_ajuste`.

Estimação (decisão numérica, registrada no manifesto):
  Com 30–40 exógenas quase colineares (defasagens 1, 2, 3, 7, 14 da mesma
  variável), a MLE conjunta de β e dos parâmetros ARMA pelo L-BFGS não converge
  (falha de busca linear, 30–70 s por ordem). Por isso os coeficientes de
  regressão são estimados pelo filtro de Kalman como estados fixos com
  inicialização difusa (`mle_regression=False` do statsmodels, equivalente a
  mínimos quadrados recursivos/GLS dados os parâmetros ARMA), e o otimizador só
  vê intercepto, ARMA e σ². O AICc dessa verossimilhança conta só esses
  parâmetros; como o offset é o mesmo para todas as ordens de um conjunto, a
  ordem escolhida não muda. Para prever, β é CONGELADO no último valor filtrado
  do treino e o conjunto (β, ARMA, σ²) é posto num SARIMAX padrão via
  `.filter(params)` — nenhum parâmetro muda dentro do bloco de teste, como nos
  demais modelos (refit por fold). Verificado em 2026-10-20 no fold 4, conjunto
  CAL: llf −8649,9 contra −8649,6 da MLE conjunta; MAE de teste 19,49 contra 19,47.

Determinístico: não há semente. O runner executa uma vez por fold e conjunto,
como faz com os baselines, e o manifesto registra o modelo em
`modelos_deterministicos`.

Previsões negativas: a contagem é SEMPRE registrada (`n_previsoes_negativas`);
o truncamento em zero só acontece com `truncar_negativos=True` (PROTOCOLO §0.18,
[PROPOSTO]). A contagem é medida ANTES de truncar.

Como a previsão um passo à frente é obtida: o modelo congelado é aplicado à
série treino+teste com `MLEResults.apply(refit=False)`, e o filtro de Kalman
produz, para cada data de teste u, E[y_u | y_{<u}, x_u]. Como x_u já contém só
informação até u−h, com h=1 isso é exatamente a previsão da origem u−1.
Para h>1 (PROTOCOLO §0.22) a previsão de cada data u é a previsão DINÂMICA de
h passos a partir da origem o = u−h: `get_prediction(start=o+1, end=u,
dynamic=True)` sobre o mesmo modelo congelado, que usa y só até o e as
exógenas x_{o+1..u} (já defasadas ≥ h). Com h=1 o caminho é o de antes, bit a bit.
"""
from __future__ import annotations

import itertools
import time
import warnings

import numpy as np
import pandas as pd

from .base import Forecaster

try:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
except ImportError as exc:  # pragma: no cover - ambiente sem statsmodels
    raise ImportError(
        "statsmodels é obrigatório para o SARIMAX e não está instalado. "
        "A execução deve falhar em vez de pular o modelo em silêncio. "
        "O venv oficial (env/.venv311) tem statsmodels==0.14.6."
    ) from exc

__all__ = ["SARIMAXForecaster", "GRADE_PADRAO", "enumerar_grade", "ajustar_ordem"]

#: Grade do PROTOCOLO §0.8. Qualquer alteração vem do YAML (`modelos.sarimax.grade`).
GRADE_PADRAO: dict = {
    "p": [0, 1, 2],
    "d": [0, 1],
    "q": [0, 1, 2],
    "P": [0, 1],
    "D": [0, 1],
    "Q": [0, 1],
    "soma_maxima": 4,
}

Ordem = tuple[tuple[int, int, int], tuple[int, int, int]]

# ------------------------------------------------------- ajustes degenerados
#
# Constatado na run h1_v02_cetesbmin_cetesbmin_classicos_full_20261021-090501
# (2026-10-21): na dobra 4 do conjunto COMPLETO (33 exógenas), a ordem
# (1,0,0)(1,0,0)_7 "convergiu" com llf −76,9 — as demais dobras ficam entre
# −6.000 e −7.700 — porque σ² colapsou para ~0 (verossimilhança gaussiana
# espúria). O AICc a escolheu e a previsão explodiu até 664.353 internações/dia.
# Um ajuste assim não é "convergente" no sentido do PROTOCOLO §0.8; é descartado
# ANTES da seleção, com motivo registrado, e a previsão é vigiada depois
# (CLAUDE.md §4.3: falhar alto, nunca seguir em silêncio).
#
#: σ² estimado abaixo desta fração da variância do alvo na janela de ajuste é degenerado.
FRACAO_SIGMA2_MIN = 1e-3
#: previsão (ou ajuste in-sample) com |valor| acima deste múltiplo do máximo do alvo é inválida.
FATOR_FAIXA = 5.0


def diagnosticar_degenerado(sigma2, var_ref) -> str | None:
    """Motivo da rejeição (ou None) para um σ² estimado, dada a variância de referência do alvo."""
    if sigma2 is None or not np.isfinite(sigma2):
        return "sigma2 não finito"
    if var_ref is None or not np.isfinite(var_ref) or var_ref <= 0:
        return None
    if sigma2 < FRACAO_SIGMA2_MIN * var_ref:
        return (f"ajuste degenerado: sigma2={sigma2:.4g} < {FRACAO_SIGMA2_MIN:g} x variância do alvo "
                f"({var_ref:.4g}) — verossimilhança espúria")
    return None


def verificar_faixa(valores: np.ndarray, y_max: float, rotulo: str, fator: float = FATOR_FAIXA) -> str | None:
    """Motivo (ou None) se algum valor não for finito ou exceder `fator` x max|y| da janela de ajuste."""
    v = np.asarray(valores, dtype=float)
    if v.size == 0:
        return f"{rotulo}: vazio"
    if not np.all(np.isfinite(v)):
        return f"{rotulo}: {int((~np.isfinite(v)).sum())} valor(es) não finito(s)"
    limite = fator * max(1.0, float(y_max))
    pior = float(np.abs(v).max())
    if pior > limite:
        return (f"{rotulo}: |valor| máximo {pior:.1f} excede {fator:g} x max|alvo| da janela de ajuste "
                f"({limite:.1f}) — ajuste inválido")
    return None


def _lista_int(grade: dict, chave: str) -> list[int]:
    if chave not in grade:
        raise ValueError(
            f"grade do SARIMAX sem a chave {chave!r}; chaves exigidas: p, d, q, P, D, Q (soma_maxima opcional)"
        )
    vals = grade[chave]
    if isinstance(vals, (int, np.integer)):
        vals = [vals]
    vals = sorted({int(v) for v in vals})
    if not vals or any(v < 0 for v in vals):
        raise ValueError(f"grade do SARIMAX: {chave} deve ser lista de inteiros >= 0, recebido {grade[chave]!r}")
    return vals


def enumerar_grade(grade: dict | None = None) -> list[Ordem]:
    """Todas as ordens `((p,d,q),(P,D,Q))` da grade, em ordem determinística.

    A restrição `p+q+P+Q ≤ soma_maxima` limita a complexidade do polinômio
    ARMA; `d` e `D` não contam. Com a grade padrão são 124 ordens.
    """
    g = dict(GRADE_PADRAO if grade is None else grade)
    desconhecidas = set(g) - set(GRADE_PADRAO)
    if desconhecidas:
        raise ValueError(f"grade do SARIMAX com chave(s) desconhecida(s): {sorted(desconhecidas)}")
    soma_max = int(g.get("soma_maxima", GRADE_PADRAO["soma_maxima"]))
    p, d, q, P, D, Q = (_lista_int(g, k) for k in ("p", "d", "q", "P", "D", "Q"))
    ordens: list[Ordem] = []
    for pi, di, qi, Pi, Di, Qi in itertools.product(p, d, q, P, D, Q):
        if pi + qi + Pi + Qi > soma_max:
            continue
        ordens.append(((pi, di, qi), (Pi, Di, Qi)))
    if not ordens:
        raise ValueError("grade do SARIMAX vazia depois da restrição de soma")
    return ordens


def _trend_para(ordem: Ordem) -> str:
    """Constante só quando não há diferenciação — como o auto.arima faz.

    Sem diferença, a série tem nível (~90 internações/dia) e precisa de
    intercepto; com uma diferença o nível já foi removido e a constante viraria
    deriva linear, que não faz sentido para contagem diária.
    """
    (_, d, _), (_, D, _) = ordem
    return "c" if d + D == 0 else "n"


def _novo_modelo(y: np.ndarray, X: np.ndarray | None, ordem: Ordem, periodo: int,
                 betas_no_estado: bool) -> SARIMAX:
    (p, d, q), (P, D, Q) = ordem
    return SARIMAX(
        endog=y,
        exog=X,
        order=(p, d, q),
        seasonal_order=(P, D, Q, periodo),
        trend=_trend_para(ordem),
        enforce_stationarity=True,
        enforce_invertibility=True,
        # sem exógenas a opção não se aplica; com exógenas, β vai para o estado
        mle_regression=not (betas_no_estado and X is not None),
    )


def ajustar_ordem(y: np.ndarray, X: np.ndarray | None, ordem: Ordem, periodo: int,
                  maxiter: int = 200, var_ref: float | None = None) -> dict:
    """Ajusta UMA ordem e devolve um resumo serializável (sem o objeto de resultado).

    `convergiu=False` cobre: otimizador não convergiu, verossimilhança ou
    parâmetros não finitos, exceção numérica, ou **ajuste degenerado** (σ²
    abaixo de `FRACAO_SIGMA2_MIN` x `var_ref`, a variância do alvo na janela de
    ajuste). Nenhum desses casos entra na seleção por AICc; o motivo fica
    registrado na tabela da grade.

    Devolve `params` (nomeados: intercepto, ARMA, σ²) e `betas` (coeficientes
    das exógenas, último estado filtrado do treino), ambos na escala das
    exógenas padronizadas.
    """
    t0 = time.perf_counter()
    saida = {
        "ordem": list(ordem[0]), "ordem_sazonal": list(ordem[1]), "trend": _trend_para(ordem),
        "convergiu": False, "aicc": float("nan"), "aic": float("nan"), "llf": float("nan"),
        "n_params": None, "nobs": None, "iteracoes": None, "params": None, "betas": None,
        "motivo": None, "tempo_s": None, "degenerado": False,
    }
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod = _novo_modelo(y, X, ordem, periodo, betas_no_estado=True)
            res = mod.fit(method="lbfgs", maxiter=int(maxiter), maxfun=int(50 * maxiter), disp=False)
        convergiu = bool(res.mle_retvals.get("converged", False))
        params = np.asarray(res.params, dtype=float)
        idx_beta = [i for i, n in enumerate(mod.state_names) if n.startswith("beta.")]
        betas = np.asarray(res.filtered_state[idx_beta, -1], dtype=float) if idx_beta else np.zeros(0)
        finito = bool(
            np.isfinite(res.llf) and np.isfinite(res.aicc)
            and np.all(np.isfinite(params)) and np.all(np.isfinite(betas))
        )
        pdict = dict(zip(mod.param_names, params.tolist()))
        degenerado = diagnosticar_degenerado(pdict.get("sigma2"), var_ref) if finito else None
        valido = convergiu and finito and degenerado is None
        saida.update(
            aicc=float(res.aicc), aic=float(res.aic), llf=float(res.llf),
            n_params=int(len(params)), nobs=int(res.nobs),
            iteracoes=res.mle_retvals.get("iterations"),
            params=pdict, betas=betas.tolist(),
            convergiu=valido,
            degenerado=degenerado is not None,
            motivo=None if valido else (
                "otimizador não convergiu" if not convergiu
                else ("valor não finito" if not finito else degenerado)
            ),
        )
    except Exception as exc:  # noqa: BLE001 - uma ordem que explode não derruba a grade
        saida["motivo"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    saida["tempo_s"] = round(time.perf_counter() - t0, 3)
    return saida


def _chave_selecao(linha: dict) -> tuple:
    """Menor AICc; empate -> menos parâmetros -> ordem de enumeração. Determinístico."""
    return (linha["aicc"], linha["n_params"], linha["indice_grade"])


class SARIMAXForecaster(Forecaster):
    nome = "sarimax"
    treinavel = True
    usa_semente = False

    def __init__(
        self,
        periodo_sazonal: int = 7,
        grade: dict | None = None,
        truncar_negativos: bool = False,
        maxiter: int = 200,
        n_jobs: int = 1,
    ):
        if periodo_sazonal < 2:
            raise ValueError(f"periodo_sazonal deve ser >= 2, recebido {periodo_sazonal}")
        self.periodo_sazonal = int(periodo_sazonal)
        self.grade = dict(GRADE_PADRAO if grade is None else grade)
        self.ordens = enumerar_grade(self.grade)
        self.truncar_negativos = bool(truncar_negativos)
        self.maxiter = int(maxiter)
        self.n_jobs = int(n_jobs)
        if self.n_jobs == 0 or self.n_jobs < -1:
            raise ValueError(f"n_jobs deve ser >= 1 ou -1, recebido {n_jobs}")

        self._res = None
        self._ordem: Ordem | None = None
        self._colunas: list[str] | None = None
        self._mu: np.ndarray | None = None
        self._sigma: np.ndarray | None = None
        self._ajuste: dict = {}
        self._tabela_grade: list[dict] = []
        self._n_negativas: int | None = None
        self._n_truncadas: int | None = None
        self._y_max_ajuste: float = float("nan")

    # ------------------------------------------------------------------ helpers
    def _exog(self, ds, datas: pd.DatetimeIndex, colunas: list[str], ajustar: bool) -> np.ndarray | None:
        if not colunas:
            return None
        X = ds.X.loc[datas, colunas]
        if X.isna().any().any():
            ruins = X.columns[X.isna().any()].tolist()
            raise RuntimeError(
                f"sarimax: NaN nas exógenas {ruins[:8]} — o construtor de features deveria ter falhado antes"
            )
        Xv = X.to_numpy(dtype=float)
        if ajustar:
            # padronização pelas estatísticas da janela de AJUSTE; não muda a
            # previsão, só o condicionamento numérico
            mu = Xv.mean(axis=0)
            sigma = Xv.std(axis=0, ddof=0)
            constantes = [c for c, s in zip(colunas, sigma) if not np.isfinite(s) or s == 0.0]
            if constantes:
                raise RuntimeError(
                    f"sarimax: exógena(s) constante(s) na janela de ajuste: {constantes}. "
                    f"Colineares com o intercepto; o conjunto de features precisa ser revisto."
                )
            self._mu, self._sigma = mu, sigma
        if self._mu is None or self._sigma is None:
            raise RuntimeError("sarimax: exógenas pedidas antes do fit")
        return (Xv - self._mu) / self._sigma

    @staticmethod
    def _y(ds, datas: pd.DatetimeIndex) -> np.ndarray:
        y = ds.y.loc[datas].to_numpy(dtype=float)
        if np.isnan(y).any():
            raise RuntimeError(f"sarimax: {int(np.isnan(y).sum())} NaN no alvo da janela pedida")
        return y

    def _ajustar_grade(self, y: np.ndarray, X: np.ndarray | None) -> list[dict]:
        var_ref = float(np.var(y))
        if self.n_jobs == 1:
            return [ajustar_ordem(y, X, o, self.periodo_sazonal, self.maxiter, var_ref) for o in self.ordens]
        from joblib import Parallel, delayed  # sklearn já traz joblib

        return Parallel(n_jobs=self.n_jobs, prefer="processes")(
            delayed(ajustar_ordem)(y, X, o, self.periodo_sazonal, self.maxiter, var_ref) for o in self.ordens
        )

    def _verificar_insample(self, res, y: np.ndarray) -> str | None:
        """Ajuste congelado precisa prever a própria janela de ajuste dentro da faixa do alvo.

        Os primeiros `max(2m, 28)` passos são ignorados: com estado difuso (β e
        componentes integradas) o filtro ainda está aprendendo o nível.
        """
        ajustadas = np.asarray(res.fittedvalues, dtype=float)
        burn = min(len(ajustadas) - 1, max(2 * self.periodo_sazonal, 28))
        return verificar_faixa(ajustadas[burn:], float(np.abs(y).max()), "ajuste in-sample")

    def _congelar(self, y: np.ndarray, X: np.ndarray | None, ordem: Ordem, linha: dict):
        """SARIMAX padrão com (intercepto, β, ARMA, σ²) fixos — sem otimizar de novo."""
        mod = _novo_modelo(y, X, ordem, self.periodo_sazonal, betas_no_estado=False)
        valores = dict(linha["params"])
        nomes_exog = [n for n in mod.param_names if n not in valores]
        betas = list(linha["betas"] or [])
        if len(nomes_exog) != len(betas):
            raise RuntimeError(
                f"sarimax: {len(betas)} betas para {len(nomes_exog)} parâmetros de exógenas ({nomes_exog[:5]}...)"
            )
        valores.update(zip(nomes_exog, betas))
        params = np.asarray([valores[n] for n in mod.param_names], dtype=float)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return mod.filter(params)

    # ---------------------------------------------------------------------- API
    def fit(self, ds, fold, colunas) -> None:
        if int(ds.horizonte) < 1:
            raise ValueError(f"sarimax: horizonte inválido h={ds.horizonte}")
        datas = fold.treino_completo
        if not datas.is_monotonic_increasing:
            raise ValueError("sarimax: janela de ajuste fora de ordem")
        colunas = list(colunas)
        y = self._y(ds, datas)
        X = self._exog(ds, datas, colunas, ajustar=True)
        self._colunas = colunas

        t0 = time.perf_counter()
        tabela = self._ajustar_grade(y, X)
        tempo = time.perf_counter() - t0
        for i, linha in enumerate(tabela):
            linha["indice_grade"] = i
        self._tabela_grade = tabela  # disponível para diagnóstico mesmo quando o fit falha alto

        convergentes = [l for l in tabela if l["convergiu"]]
        if not convergentes:
            motivos = sorted({str(l["motivo"]) for l in tabela})[:5]
            raise RuntimeError(
                f"sarimax: nenhuma das {len(tabela)} ordens convergiu na janela "
                f"{datas.min().date()}..{datas.max().date()} com {len(colunas)} exógenas. Motivos: {motivos}"
            )

        # Seleção por AICc com segunda barreira: o ajuste congelado precisa
        # reproduzir a própria janela de ajuste dentro da faixa do alvo. Um
        # candidato que falha é rejeitado (motivo registrado) e o próximo da
        # ordem de AICc é tentado. Sem candidato válido, a run falha alto.
        melhor = None
        res = None
        rejeitados_insample = 0
        for cand in sorted(convergentes, key=_chave_selecao):
            ordem_c: Ordem = (tuple(cand["ordem"]), tuple(cand["ordem_sazonal"]))
            res_c = self._congelar(y, X, ordem_c, cand)
            motivo = self._verificar_insample(res_c, y)
            if motivo is None:
                melhor, res = cand, res_c
                break
            cand.update(convergiu=False, degenerado=True, motivo=motivo)
            rejeitados_insample += 1
        if melhor is None:
            raise RuntimeError(
                f"sarimax: todas as {len(convergentes)} ordens convergentes produziram ajuste in-sample fora "
                f"da faixa do alvo na janela {datas.min().date()}..{datas.max().date()} com {len(colunas)} "
                f"exógenas. Nenhum modelo válido; a run não pode seguir."
            )
        convergentes = [l for l in tabela if l["convergiu"]]
        ordem: Ordem = (tuple(melhor["ordem"]), tuple(melhor["ordem_sazonal"]))

        self._res = res
        self._y_max_ajuste = float(np.abs(y).max())
        self._ordem = ordem
        self._tabela_grade = tabela
        self._ajuste = {
            "ordem": list(ordem[0]),
            "ordem_sazonal": list(ordem[1]) + [self.periodo_sazonal],
            "trend": melhor["trend"],
            "aicc": melhor["aicc"],
            "aic": melhor["aic"],
            "llf": melhor["llf"],
            "n_params_otimizados": melhor["n_params"],
            "n_betas": len(melhor["betas"] or []),
            "nobs_ajuste": int(len(y)),
            "janela_ajuste": "treino+validacao",
            "janela_ajuste_inicio": str(datas.min().date()),
            "janela_ajuste_fim": str(datas.max().date()),
            "n_ordens_grade": len(tabela),
            "n_convergentes": len(convergentes),
            "n_nao_convergentes": len(tabela) - len(convergentes),
            "n_degenerados": int(sum(1 for l in tabela if l.get("degenerado"))),
            "n_rejeitados_insample": rejeitados_insample,
            "tempo_grade_s": round(tempo, 2),
            "top5_aicc": [
                {"ordem": l["ordem"], "ordem_sazonal": l["ordem_sazonal"], "aicc": round(l["aicc"], 3)}
                for l in sorted(convergentes, key=_chave_selecao)[:5]
            ],
        }
        self._n_negativas = None
        self._n_truncadas = None

    def predict(self, ds, fold, colunas) -> np.ndarray:
        if self._res is None or self._ordem is None:
            raise RuntimeError("predict chamado antes de fit")
        colunas = list(colunas)
        if colunas != self._colunas:
            raise RuntimeError("sarimax: colunas do predict diferem das do fit")
        treino = fold.treino_completo
        teste = fold.teste
        if treino.max() >= teste.min():
            raise ValueError("sarimax: teste não sucede a janela de ajuste")
        lacuna = (teste.min() - treino.max()).days
        if lacuna != 1:
            raise RuntimeError(
                f"sarimax: lacuna de {lacuna} dias entre o fim do ajuste ({treino.max().date()}) e o "
                f"início do teste ({teste.min().date()}); o filtro exige série contígua"
            )
        if len(teste) > 1 and not (np.diff(teste.to_numpy()) == np.timedelta64(1, "D")).all():
            raise RuntimeError("sarimax: bloco de teste não é contíguo")

        datas = treino.append(teste)
        y_full = self._y(ds, datas)
        X_full = self._exog(ds, datas, colunas, ajustar=False)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res_full = self._res.apply(endog=y_full, exog=X_full, refit=False)
            n_tr = len(treino)
            h = int(ds.horizonte)
            if h == 1:
                pred = res_full.get_prediction(start=n_tr, end=len(datas) - 1, dynamic=False).predicted_mean
            else:
                if n_tr < h:
                    raise RuntimeError(f"sarimax: janela de ajuste ({n_tr}) menor que o horizonte h={h}")
                pred = np.empty(len(teste))
                for j in range(len(teste)):
                    alvo = n_tr + j
                    origem = alvo - h
                    pr = res_full.get_prediction(start=origem + 1, end=alvo, dynamic=True).predicted_mean
                    pred[j] = float(np.asarray(pr, dtype=float)[-1])
        pred = np.asarray(pred, dtype=float)
        if pred.shape[0] != len(teste):
            raise RuntimeError(f"sarimax: {pred.shape[0]} previsões para {len(teste)} datas de teste")
        if np.isnan(pred).any():
            raise RuntimeError(f"sarimax: {int(np.isnan(pred).sum())} previsões NaN")
        # Falhar alto (CLAUDE.md §4.3): previsão fora da faixa física do alvo é
        # ajuste inválido, não resultado. Medido ANTES do truncamento de negativos.
        motivo = verificar_faixa(pred, self._y_max_ajuste, "previsão de teste")
        if motivo is not None:
            raise RuntimeError(
                f"sarimax {self._ordem} com {len(colunas)} exógenas, teste "
                f"{teste.min().date()}..{teste.max().date()}: {motivo}"
            )

        # contagem SEMPRE registrada, medida antes de qualquer truncamento
        self._n_negativas = int((pred < 0).sum())
        if self.truncar_negativos:
            pred = np.maximum(pred, 0.0)
            self._n_truncadas = self._n_negativas
        else:
            self._n_truncadas = 0
        return pred

    def params(self) -> dict:
        return {
            "deterministico": True,
            "periodo_sazonal": self.periodo_sazonal,
            "grade": self.grade,
            "maxiter": self.maxiter,
            "n_jobs": self.n_jobs,
            "n_exogenas": None if self._colunas is None else len(self._colunas),
            "exogenas_padronizadas": True,
            "estimacao_betas": "filtro de Kalman (estado difuso, mle_regression=False); congelados no fim do treino",
            "aicc_conta_betas": False,
            "rejeicao_de_ajustes_degenerados": {
                "fracao_sigma2_min": FRACAO_SIGMA2_MIN,
                "fator_faixa": FATOR_FAIXA,
                "regra": "sigma2 < fracao x var(alvo) rejeitado antes do AICc; ajuste in-sample e previsão "
                         "com |valor| > fator x max|alvo| rejeitados/falham alto",
            },
            "previsao_h_passos": "h=1: um passo (filtro); h>1: dinâmica de h passos a partir da origem "
                                 "u-h com o modelo congelado (PROTOCOLO §0.22)",
            "truncar_negativos": self.truncar_negativos,
            "n_previsoes_negativas": self._n_negativas,
            "n_previsoes_truncadas": self._n_truncadas,
            **self._ajuste,
        }

    @property
    def tabela_grade(self) -> pd.DataFrame:
        """Todas as ordens do último fit, com AICc e convergência — para diagnóstico."""
        return pd.DataFrame(self._tabela_grade).drop(columns=["params", "betas"], errors="ignore")

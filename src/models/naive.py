"""Baselines determinísticos: Naïve e Seasonal Naïve.

Nenhum dos dois é uma regressão. Não têm parâmetros, não têm treinamento e não
têm semente — leem diretamente a série do desfecho.

Naïve para horizonte h:            ŷ[u] = y[u − h]
Seasonal naïve, período m:         ŷ[u] = y[u − m·⌈h/m⌉]

Com h=1 e m=7 isso dá ŷ[u]=y[u−1] e ŷ[u]=y[u−7], que são exatamente as colunas
`y_lag1` e `y_lag7` do dataset — usado como verificação cruzada nos testes.

Ambos leem de `ds.serie_alvo_completa`, não do X do fold, para poderem alcançar
valores anteriores ao início do bloco de teste sem que isso seja vazamento: o
valor em `u−h` é passado em relação à origem `t = u−h`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import Forecaster

__all__ = ["Naive", "SeasonalNaive"]


def _buscar_defasado(serie: pd.Series, datas: pd.DatetimeIndex, defasagem: int) -> np.ndarray:
    if defasagem < 1:
        raise ValueError(f"defasagem deve ser >= 1, recebido {defasagem}")
    origem = datas - pd.Timedelta(days=defasagem)
    ausentes = origem.difference(serie.index)
    if len(ausentes):
        raise RuntimeError(
            f"baseline: {len(ausentes)} datas de origem fora da série "
            f"(defasagem={defasagem}), ex.: {[str(d.date()) for d in ausentes[:5]]}"
        )
    vals = serie.reindex(origem).to_numpy(dtype=float)
    if np.isnan(vals).any():
        raise RuntimeError(f"baseline: {int(np.isnan(vals).sum())} valores NaN na origem")
    return vals


class Naive(Forecaster):
    nome = "naive"
    treinavel = False
    usa_semente = False

    def fit(self, ds, fold, colunas):  # noqa: D102 - baseline não treina
        return None

    def predict(self, ds, fold, colunas) -> np.ndarray:
        return _buscar_defasado(ds.serie_alvo_completa, fold.teste, ds.horizonte)

    def params(self) -> dict:
        return {"tipo": "persistencia", "defasagem": "h"}


class SeasonalNaive(Forecaster):
    nome = "seasonal_naive"
    treinavel = False
    usa_semente = False

    def __init__(self, periodo_sazonal: int = 7):
        if periodo_sazonal < 2:
            raise ValueError(f"periodo_sazonal deve ser >= 2, recebido {periodo_sazonal}")
        self.periodo_sazonal = int(periodo_sazonal)

    def fit(self, ds, fold, colunas):  # noqa: D102 - baseline não treina
        return None

    def predict(self, ds, fold, colunas) -> np.ndarray:
        m = self.periodo_sazonal
        # menor múltiplo de m que é >= h, para nunca olhar depois da origem
        defasagem = m * int(np.ceil(ds.horizonte / m))
        return _buscar_defasado(ds.serie_alvo_completa, fold.teste, defasagem)

    def params(self) -> dict:
        return {"tipo": "sazonal", "periodo_sazonal": self.periodo_sazonal}

"""Interface mínima dos forecasters do benchmark.

Deliberadamente pequena: `fit` e `predict`. O runner não conhece o interior de
nenhum modelo, e nenhum modelo conhece splits ou métricas.

Contrato de `predict`: devolver um vetor alinhado, na ordem, a `fold.teste`.
Comprimento diferente é erro e o runner levanta.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

__all__ = ["Forecaster"]


class Forecaster(ABC):
    nome: str = "abstrato"
    #: baselines determinísticos não têm treinamento nem semente
    treinavel: bool = True
    #: False para modelos determinísticos (baselines, SARIMAX): o runner executa
    #: UMA vez por fold e conjunto, em vez de uma por semente, e registra o
    #: modelo em `modelos_deterministicos` no manifesto.
    usa_semente: bool = True

    @abstractmethod
    def fit(self, ds, fold, colunas: list[str]) -> None:
        """Ajusta usando SOMENTE fold.treino (e fold.validacao, se precisar)."""

    @abstractmethod
    def predict(self, ds, fold, colunas: list[str]) -> np.ndarray:
        """Previsões para fold.teste, na mesma ordem do índice."""

    def params(self) -> dict:
        """Hiperparâmetros efetivamente usados, para o manifesto."""
        return {}

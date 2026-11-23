"""XGBoost como forecaster de primeira classe do benchmark.

Diferenças em relação ao código anterior (`src/models/join_and_lstm.py`):
  - o import NÃO é opcional. Ausência de xgboost levanta, não emite warning e
    pula o modelo (era o comportamento antigo, linhas 73-77).
  - features vêm do dataset compartilhado, já defasadas; o modelo não constrói
    as próprias.
  - early stopping usa `fold.validacao`, nunca o teste.
  - a escolha entre `reg:squarederror` e `count:poisson` é decidida na
    VALIDAÇÃO, jamais no teste.

Não precisa de scaler: árvores são invariantes a transformação monotônica.
"""
from __future__ import annotations

import numpy as np

from .base import Forecaster

try:
    from xgboost import XGBRegressor
except ImportError as exc:  # pragma: no cover - ambiente sem xgboost
    raise ImportError(
        "xgboost é obrigatório para este benchmark e não está instalado. "
        "A execução deve falhar em vez de pular o modelo em silêncio. "
        "Instale com: pip install 'xgboost>=1.7,<2.1'"
    ) from exc

__all__ = ["XGBoostForecaster"]

OBJETIVOS_PERMITIDOS = ("reg:squarederror", "count:poisson")


class XGBoostForecaster(Forecaster):
    nome = "xgboost"

    def __init__(
        self,
        objetivo: str = "reg:squarederror",
        selecionar_objetivo: bool = False,
        seed: int = 42,
        n_estimators: int = 600,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: float = 5.0,
        reg_lambda: float = 1.0,
        early_stopping_rounds: int = 50,
    ):
        if objetivo not in OBJETIVOS_PERMITIDOS:
            raise ValueError(f"objetivo {objetivo!r} não permitido; use um de {OBJETIVOS_PERMITIDOS}")
        self.objetivo = objetivo
        self.selecionar_objetivo = bool(selecionar_objetivo)
        self.seed = int(seed)
        self.hp = dict(
            n_estimators=int(n_estimators),
            max_depth=int(max_depth),
            learning_rate=float(learning_rate),
            subsample=float(subsample),
            colsample_bytree=float(colsample_bytree),
            min_child_weight=float(min_child_weight),
            reg_lambda=float(reg_lambda),
        )
        self.early_stopping_rounds = int(early_stopping_rounds)
        self._modelo: XGBRegressor | None = None
        self._objetivo_escolhido: str | None = None
        self._melhor_iteracao: int | None = None

    # ------------------------------------------------------------------ helpers
    def _novo(self, objetivo: str) -> XGBRegressor:
        return XGBRegressor(
            objective=objetivo,
            random_state=self.seed,
            n_jobs=4,
            tree_method="hist",
            early_stopping_rounds=self.early_stopping_rounds,
            **self.hp,
        )

    @staticmethod
    def _mae_val(modelo: XGBRegressor, Xv, yv) -> float:
        return float(np.abs(modelo.predict(Xv) - yv).mean())

    # ---------------------------------------------------------------------- API
    def fit(self, ds, fold, colunas) -> None:
        Xtr = ds.X.loc[fold.treino, colunas].to_numpy(dtype=np.float32)
        ytr = ds.y.loc[fold.treino].to_numpy(dtype=np.float32)
        Xv = ds.X.loc[fold.validacao, colunas].to_numpy(dtype=np.float32)
        yv = ds.y.loc[fold.validacao].to_numpy(dtype=np.float32)

        if self.selecionar_objetivo:
            # decidido SOMENTE na validação
            candidatos = {}
            for obj in OBJETIVOS_PERMITIDOS:
                m = self._novo(obj)
                m.fit(Xtr, ytr, eval_set=[(Xv, yv)], verbose=False)
                candidatos[obj] = (self._mae_val(m, Xv, yv), m)
            self._objetivo_escolhido = min(candidatos, key=lambda k: candidatos[k][0])
            self._modelo = candidatos[self._objetivo_escolhido][1]
        else:
            self._objetivo_escolhido = self.objetivo
            self._modelo = self._novo(self.objetivo)
            self._modelo.fit(Xtr, ytr, eval_set=[(Xv, yv)], verbose=False)

        self._melhor_iteracao = getattr(self._modelo, "best_iteration", None)

    def predict(self, ds, fold, colunas) -> np.ndarray:
        if self._modelo is None:
            raise RuntimeError("predict chamado antes de fit")
        Xte = ds.X.loc[fold.teste, colunas].to_numpy(dtype=np.float32)
        return np.asarray(self._modelo.predict(Xte), dtype=float)

    def params(self) -> dict:
        return {
            "objetivo_configurado": self.objetivo,
            "objetivo_escolhido": self._objetivo_escolhido,
            "selecao_de_objetivo_na_validacao": self.selecionar_objetivo,
            "seed": self.seed,
            "early_stopping_rounds": self.early_stopping_rounds,
            "melhor_iteracao": self._melhor_iteracao,
            **self.hp,
        }

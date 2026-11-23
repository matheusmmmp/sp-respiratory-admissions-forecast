"""Métricas de avaliação — IMPLEMENTAÇÃO ÚNICA do projeto.

Nenhum modelo pode definir a própria versão de MAE/RMSE/R². Todos importam daqui.
É isso que sustenta a alegação de comparação padronizada.

Convenções fixadas:
  - MASE usa como denominador o MAE de um baseline de referência calculado
    SOBRE OS MESMOS TIMESTAMPS de teste. MASE < 1 significa "melhor que o
    baseline". O baseline de referência é passado explicitamente; não há
    default mágico.
  - skill = (erro_baseline - erro_modelo) / erro_baseline. Positivo = melhor.
  - R² usa a variância do próprio conjunto avaliado.

Falha alto: entradas com NaN, tamanhos diferentes ou vazias levantam.
"""
from __future__ import annotations

import numpy as np

__all__ = ["mae", "rmse", "r2", "mase", "skill", "compute_all", "METRIC_NAMES"]

METRIC_NAMES = ("MAE", "RMSE", "R2", "MASE")


def _validar(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    yt = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_pred, dtype=float).ravel()
    if yt.size == 0:
        raise ValueError("conjunto vazio: nada a avaliar")
    if yt.shape != yp.shape:
        raise ValueError(f"tamanhos diferentes: y_true={yt.shape}, y_pred={yp.shape}")
    if np.isnan(yt).any():
        raise ValueError(f"y_true contém {int(np.isnan(yt).sum())} NaN")
    if np.isnan(yp).any():
        raise ValueError(f"y_pred contém {int(np.isnan(yp).sum())} NaN")
    return yt, yp


def mae(y_true, y_pred) -> float:
    yt, yp = _validar(y_true, y_pred)
    return float(np.abs(yp - yt).mean())


def rmse(y_true, y_pred) -> float:
    yt, yp = _validar(y_true, y_pred)
    return float(np.sqrt(((yp - yt) ** 2).mean()))


def r2(y_true, y_pred) -> float:
    yt, yp = _validar(y_true, y_pred)
    sst = float(((yt - yt.mean()) ** 2).sum())
    if sst == 0.0:
        raise ValueError("variância zero em y_true: R² indefinido")
    sse = float(((yp - yt) ** 2).sum())
    return 1.0 - sse / sst


def mase(y_true, y_pred, y_pred_baseline) -> float:
    """MAE(modelo) / MAE(baseline), ambos sobre os MESMOS timestamps."""
    denom = mae(y_true, y_pred_baseline)
    if denom == 0.0:
        raise ValueError("MAE do baseline é zero: MASE indefinido")
    return mae(y_true, y_pred) / denom


def skill(erro_modelo: float, erro_baseline: float) -> float:
    """Melhoria relativa. > 0 = modelo melhor que o baseline."""
    if erro_baseline == 0.0:
        raise ValueError("erro do baseline é zero: skill indefinido")
    return (erro_baseline - erro_modelo) / erro_baseline


def compute_all(y_true, y_pred, y_pred_baseline=None) -> dict[str, float]:
    """Bloco padrão de métricas. Se o baseline for dado, inclui MASE e skills."""
    out = {
        "MAE": mae(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
        "R2": r2(y_true, y_pred),
    }
    if y_pred_baseline is not None:
        base_mae = mae(y_true, y_pred_baseline)
        base_rmse = rmse(y_true, y_pred_baseline)
        out["MASE"] = out["MAE"] / base_mae if base_mae else float("nan")
        out["skill_MAE"] = skill(out["MAE"], base_mae)
        out["skill_RMSE"] = skill(out["RMSE"], base_rmse)
    return out

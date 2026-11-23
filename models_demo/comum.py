"""Shared construction code for the demonstration models and the API.

The point of this module is that training (``models_demo/treinar.py``), serving
(``api/main.py``) and the acceptance tests (``tests/test_api_forecast.py``) all
build features through exactly one path: the canonical
``src.features.forecasting_features.construir_dataset`` with the lags declared
in the dissertation configs. Nothing here re-implements a feature.

Conventions inherited from the feature builder (read its docstring):

* the feature frame is indexed by the TARGET date ``u``; for horizon ``h`` the
  forecast origin is ``t = u - h``;
* every lagged column is named ``<var>_lag<L>`` with ``L >= h`` (checked with
  ``raise`` inside the builder);
* calendar columns (``dow``, ``mes``, ``feriado``, ``fim_de_semana``, ``sin1``,
  ``cos1``, ``sin2``, ``cos2``) describe the target date and carry no lag.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from xgboost import XGBRegressor

from src.features.forecasting_features import DatasetExperimental, construir_dataset
from src.models.xgboost_model import XGBoostForecaster

RAIZ = Path(__file__).resolve().parents[1]
PASTA_MODELOS = RAIZ / "models_demo"
CAMINHO_METADATA = PASTA_MODELOS / "metadata.json"

#: Horizons served by the API, each tied to the dissertation config whose lags it reproduces.
HORIZONTES: tuple[int, ...] = (1, 7, 30)
CONFIG_POR_HORIZONTE: dict[int, str] = {
    1: "configs/h1_v02_cetesb_cetesb_classicos.yaml",
    7: "configs/multihorizonte/mh_h7_cetesb_cetesb.yaml",
    30: "configs/multihorizonte/mh_h30_cetesb_cetesb.yaml",
}
#: Reference runs (full ids) whose ``model_comparison.csv`` the model card cites.
RUN_REFERENCIA_POR_HORIZONTE: dict[int, str] = {
    1: "h1_v02_cetesb_cetesb_classicos_full_20261022-211834",
    7: "mh_h7_cetesb_cetesb_full_20261111-030322",
    30: "mh_h30_cetesb_cetesb_full_20261113-104814",
}
NOME_MODELO = "xgboost_ar_cal"
FEATURE_SET = "AR_CAL"
BLOCOS_FEATURE_SET: tuple[str, ...] = ("AR", "CAL")
COLUNAS_CALENDARIO: tuple[str, ...] = ("dow", "mes", "feriado", "fim_de_semana", "sin1", "cos1", "sin2", "cos2")
AVISO = (
    "demonstration model: trained on the whole 2019-2024 history with a single seed for the API demo; "
    "not a dissertation result. Reference evaluation: models_demo/MODEL_CARD.md."
)
PADRAO_LAG = re.compile(r"_lag(\d+)$")


def caminho_modelo(h: int) -> Path:
    return PASTA_MODELOS / f"{NOME_MODELO}_h{h}.ubj"


def caminho_relativo(p: Path) -> str:
    """Repository-relative POSIX path, so that no absolute path leaks into artefacts or messages."""
    p = Path(p).resolve()
    return p.relative_to(RAIZ).as_posix() if p.is_relative_to(RAIZ) else p.name


def sha256_arquivo(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_config(h: int) -> dict:
    if h not in CONFIG_POR_HORIZONTE:
        raise ValueError(f"horizon h={h} is not served; available: {list(HORIZONTES)}")
    p = RAIZ / CONFIG_POR_HORIZONTE[h]
    cfg = yaml.safe_load(p.read_text(encoding="utf-8"))
    if int(cfg["experimento"]["horizonte"]) != h:
        raise RuntimeError(
            f"{CONFIG_POR_HORIZONTE[h]} declares horizonte={cfg['experimento']['horizonte']}, expected {h}"
        )
    if list(cfg["feature_sets"].get(FEATURE_SET, [])) != list(BLOCOS_FEATURE_SET):
        raise RuntimeError(f"{CONFIG_POR_HORIZONTE[h]}: feature set {FEATURE_SET} must be {list(BLOCOS_FEATURE_SET)}")
    return cfg


def _caminho_dados(caminho: str) -> Path:
    """Same rule as ``run_preliminary._caminho_dados``: relative paths resolve against the repo root."""
    p = Path(caminho)
    return p if p.is_absolute() else RAIZ / p


def arquivos_de_dados(cfg: dict) -> dict[str, Path]:
    """Every data file the feature builder opens for this config (even if not used as a feature)."""
    d = cfg["dados"]
    out = {"sih": _caminho_dados(d["sih"]), "cams": _caminho_dados(d["cams"])}
    if d.get("cetesb"):
        out["cetesb"] = _caminho_dados(d["cetesb"])
    if d.get("meteo"):
        out["meteo"] = _caminho_dados(d["meteo"])
    return out


def construir_para(h: int, cfg: dict | None = None) -> tuple[DatasetExperimental, list[str], dict]:
    """Build the canonical dataset for horizon ``h`` exactly as the runner does.

    Returns ``(ds, colunas, cfg)`` where ``colunas`` is the ordered list of
    ``AR_CAL`` feature columns (``ds.colunas(["AR", "CAL"])``), the same call
    ``run_preliminary._colunas_para`` makes for XGBoost.
    """
    cfg = cfg or carregar_config(h)
    exp = cfg["experimento"]
    d = cfg["dados"]
    arquivos = arquivos_de_dados(cfg)
    for nome, p in arquivos.items():
        if not p.exists():
            raise RuntimeError(f"data file '{nome}' missing: {caminho_relativo(p)}")
    ds = construir_dataset(
        caminho_sih=arquivos["sih"],
        caminho_cams=arquivos["cams"],
        horizonte=int(exp["horizonte"]),
        lags_alvo=exp["lags_alvo"],
        lags_exogenas=exp["lags_exogenas"],
        inicio=d.get("inicio"),
        fim=d.get("fim"),
        fonte_pm25=d.get("fonte_pm25", "cams"),
        caminho_cetesb=arquivos.get("cetesb"),
        fonte_meteo=d.get("fonte_meteo", "cams"),
        caminho_meteo=arquivos.get("meteo"),
        blocos_customizados=cfg.get("blocos_customizados"),
        permitir_duas_fontes=bool(d.get("permitir_duas_fontes", False)),
    )
    colunas = ds.colunas(list(BLOCOS_FEATURE_SET))
    return ds, colunas, cfg


def forecaster_da_config(cfg: dict, seed: int) -> XGBoostForecaster:
    """Instantiate the canonical forecaster with the keys the runner reads (``_instanciar``)."""
    m = cfg["modelos"]["xgboost"]
    return XGBoostForecaster(
        objetivo=m.get("objetivo", "reg:squarederror"),
        selecionar_objetivo=m.get("selecionar_objetivo", False),
        seed=seed,
        n_estimators=m.get("n_estimators", 600),
        max_depth=m.get("max_depth", 5),
        learning_rate=m.get("learning_rate", 0.05),
        subsample=m.get("subsample", 0.8),
        colsample_bytree=m.get("colsample_bytree", 0.8),
        min_child_weight=m.get("min_child_weight", 5),
        reg_lambda=m.get("reg_lambda", 1.0),
        early_stopping_rounds=m.get("early_stopping_rounds", 50),
    )


def regressor_sem_early_stopping(f: XGBoostForecaster) -> XGBRegressor:
    """Same estimator as ``XGBoostForecaster._novo`` minus early stopping.

    The benchmark stops early on a 180-day validation window of each fold. The
    demo trains on the whole history, so there is no held-out window: the number
    of trees is fixed at ``n_estimators`` from the config. Every other argument
    (objective, seed, ``n_jobs=4``, ``tree_method="hist"`` and the
    hyper-parameters in ``f.hp``) is identical.
    """
    if f.selecionar_objetivo:
        raise ValueError("the demo trains with a fixed objective; selecionar_objetivo must be false")
    return XGBRegressor(
        objective=f.objetivo,
        random_state=f.seed,
        n_jobs=4,
        tree_method="hist",
        **f.hp,
    )


def matriz(ds: DatasetExperimental, colunas: list[str], datas=None) -> np.ndarray:
    """Feature matrix in the dtype the runner feeds to XGBoost (float32)."""
    X = ds.X[colunas] if datas is None else ds.X.loc[datas, colunas]
    return X.to_numpy(dtype=np.float32)


def carregar_modelo(h: int) -> XGBRegressor:
    p = caminho_modelo(h)
    if not p.exists():
        raise FileNotFoundError(
            f"demo model for h={h} not found at {caminho_relativo(p)}; train it with "
            "`uv run python -m models_demo.treinar`"
        )
    m = XGBRegressor()
    m.load_model(p)
    return m


def prever_direto(modelo: XGBRegressor, ds: DatasetExperimental, colunas: list[str], data_alvo) -> float:
    """Point forecast for one target date, straight from the model (no API)."""
    x = matriz(ds, colunas, [pd.Timestamp(data_alvo)])
    return float(modelo.predict(x)[0])


def lags_das_colunas(colunas: list[str]) -> dict[str, int | None]:
    """Lag carried by each feature name (``None`` for calendar columns)."""
    out: dict[str, int | None] = {}
    for c in colunas:
        m = PADRAO_LAG.search(c)
        out[c] = int(m.group(1)) if m else None
    return out

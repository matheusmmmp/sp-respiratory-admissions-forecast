"""Train the demonstration XGBoost ``AR_CAL`` models for h in {1, 7, 30}.

Usage::

    uv run python -m models_demo.treinar

What it does, per horizon:

1. builds the canonical dataset with ``construir_dataset`` and the lags of the
   dissertation config for that horizon (``models_demo/comum.py``);
2. fits an ``XGBRegressor`` with the config hyper-parameters
   (``count:poisson``, 600 trees, depth 5, eta 0.05, seed 42) on EVERY row of
   the 2019-01-01..2024-12-31 history that survives the lag warm-up, with the
   number of trees fixed (no early stopping: there is no validation window);
3. saves ``models_demo/xgboost_ar_cal_h{h}.ubj``.

Then writes ``models_demo/metadata.json`` (model version, feature order, lags,
sha256 of the inputs and of the saved models, library versions) and
``models_demo/MODEL_CARD.md``. Every number in the model card is read from a
file in ``results/runs/`` and the file is cited next to it.

These models are an engineering demonstration for the API. They are NOT a
dissertation result and no metric computed here is a result.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import xgboost

from models_demo import comum

SEED = 42


def _metricas_de_referencia(h: int) -> dict:
    """XGBoost AR_CAL and Naive rows of the reference run's model_comparison.csv."""
    run_id = comum.RUN_REFERENCIA_POR_HORIZONTE[h]
    rel = f"results/runs/{run_id}/model_comparison.csv"
    p = comum.RAIZ / rel
    if not p.exists():
        raise FileNotFoundError(f"reference run file missing: {rel}")
    tab = pd.read_csv(p)
    xgb = tab[(tab["model"] == "xgboost") & (tab["feature_set"] == comum.FEATURE_SET)]
    naive = tab[(tab["model"] == "naive")]
    if len(xgb) != 1 or len(naive) != 1:
        raise RuntimeError(f"{rel}: expected exactly one xgboost/{comum.FEATURE_SET} row and one naive row")
    x, n = xgb.iloc[0], naive.iloc[0]
    return {
        "run_id": run_id,
        "arquivo": rel,
        "xgboost_ar_cal": {
            "MAE_medio": float(x["MAE_medio"]),
            "MAE_std_fold": float(x["MAE_std_fold"]),
            "RMSE_medio": float(x["RMSE_medio"]),
            "MASE_medio": float(x["MASE_medio"]),
            "n_folds": int(x["n_folds"]),
            "n_sementes": int(x["n_sementes"]),
        },
        "naive": {"MAE_medio": float(n["MAE_medio"])},
    }


def treinar_horizonte(h: int) -> dict:
    t0 = time.perf_counter()
    ds, colunas, cfg = comum.construir_para(h)
    X = comum.matriz(ds, colunas)
    y = ds.y.to_numpy(dtype=np.float32)
    if not np.isfinite(X).all() or not np.isfinite(y).all():
        raise RuntimeError(f"h={h}: non-finite values in X or y")

    f = comum.forecaster_da_config(cfg, seed=SEED)
    modelo = comum.regressor_sem_early_stopping(f)
    modelo.fit(X, y)

    destino = comum.caminho_modelo(h)
    modelo.save_model(destino)
    tamanho = destino.stat().st_size
    if tamanho > 5 * 1024 * 1024:
        raise RuntimeError(f"{comum.caminho_relativo(destino)} is {tamanho / 1e6:.1f} MB; limit is 5 MB")

    # round-trip check: the file on disk must reproduce the in-memory model
    recarregado = comum.carregar_modelo(h)
    if not np.array_equal(modelo.predict(X[:64]), recarregado.predict(X[:64])):
        raise RuntimeError(f"h={h}: predictions differ after save/load")

    segundos = time.perf_counter() - t0
    datas = ds.datas_alvo
    print(
        f"h={h:>2}  rows={len(y):>5}  features={len(colunas):>2}  trees={f.hp['n_estimators']}  "
        f"targets {datas.min().date()}..{datas.max().date()}  {segundos:5.1f}s  "
        f"{comum.caminho_relativo(destino)}  {tamanho / 1e6:.2f} MB  sha256={comum.sha256_arquivo(destino)}",
        flush=True,
    )
    return {
        "horizonte": h,
        "config": comum.CONFIG_POR_HORIZONTE[h],
        "arquivo": comum.caminho_relativo(destino),
        "arquivo_sha256": comum.sha256_arquivo(destino),
        "arquivo_bytes": tamanho,
        "feature_set": comum.FEATURE_SET,
        "blocos": list(comum.BLOCOS_FEATURE_SET),
        "features": list(colunas),
        "lags_alvo": list(ds.relatorio["lags_alvo"]),
        "lags_exogenas": list(ds.relatorio["lags_exogenas"]),
        "lag_minimo_das_features": min(v for v in comum.lags_das_colunas(colunas).values() if v is not None),
        "n_linhas_treino": int(len(y)),
        "primeira_data_alvo": str(datas.min().date()),
        "ultima_data_alvo": str(datas.max().date()),
        "primeira_origem_valida": str((datas.min() - pd.Timedelta(days=h)).date()),
        "ultima_origem_valida": str((datas.max() - pd.Timedelta(days=h)).date()),
        "linhas_removidas_warmup": int(ds.relatorio["linhas_removidas"]),
        "hiperparametros": {
            "objective": f.objetivo,
            "seed": f.seed,
            "tree_method": "hist",
            "n_jobs": 4,
            "early_stopping": False,
            **f.hp,
        },
        "segundos_treino": round(segundos, 2),
        "referencia": _metricas_de_referencia(h),
    }


def escrever_model_card(meta: dict) -> None:
    linhas_tab = []
    for h in comum.HORIZONTES:
        m = meta["modelos"][str(h)]
        r = m["referencia"]
        x = r["xgboost_ar_cal"]
        linhas_tab.append(
            f"| {h} | `{r['run_id']}` | {x['MAE_medio']:.2f} ± {x['MAE_std_fold']:.2f} | "
            f"{x['RMSE_medio']:.2f} | {x['MASE_medio']:.3f} | {r['naive']['MAE_medio']:.2f} | "
            f"{x['n_folds']} × {x['n_sementes']} | `{r['arquivo']}` |"
        )
    feats = {h: meta["modelos"][str(h)] for h in comum.HORIZONTES}
    texto = (
        f"""# Model card — demonstration XGBoost `AR_CAL` (h = 1, 7, 30)

> **Demonstration, not a dissertation result.** These models exist so that the
> API in `api/` has something to serve. They are trained on the whole
> 2019–2024 history with one seed, which is not the dissertation protocol
> (4 rolling-origin folds × 180 test days × 5 seeds). No metric computed on
> them is a result. The evaluation below is a *reference* to identified runs
> of the dissertation benchmark and is labelled **provisional (pre-defence)**.

Generated by `models_demo/treinar.py` on {meta["data_treino"]} (UTC).
Model version: `{meta["versao"]}` (short sha256 of the target parquet + training date).

## Model details

| | |
|---|---|
| Model | XGBoost regressor, objective `count:poisson` (`src/models/xgboost_model.py` hyper-parameters) |
| Feature set | `AR_CAL`: autoregressive lags of the target + calendar of the target date |
| Horizons | 1, 7 and 30 days ahead, one model per horizon |
| Trees / depth / eta | {feats[1]["hiperparametros"]["n_estimators"]} / {feats[1]["hiperparametros"]["max_depth"]} / {feats[1]["hiperparametros"]["learning_rate"]} ; subsample {feats[1]["hiperparametros"]["subsample"]}, colsample_bytree {feats[1]["hiperparametros"]["colsample_bytree"]}, min_child_weight {feats[1]["hiperparametros"]["min_child_weight"]}, reg_lambda {feats[1]["hiperparametros"]["reg_lambda"]} |
| Seed | {SEED} (single seed) |
| Early stopping | **No.** The benchmark stops early on a 180-day validation window inside each fold; the demo has no held-out window, so the number of trees is fixed at the config value. |
| Files | `models_demo/xgboost_ar_cal_h1.ubj`, `_h7.ubj`, `_h30.ubj` (XGBoost UBJSON, `save_model`) |
| Libraries | xgboost {meta["ambiente"]["xgboost"]}, numpy {meta["ambiente"]["numpy"]}, pandas {meta["ambiente"]["pandas"]}, Python {meta["ambiente"]["python"]} |

## Data

* **Target**: daily count of distinct hospital admissions (AIH, `N_AIH`) with a
  respiratory principal diagnosis (ICD-10 J00–J99), residents of São Paulo city
  (`MUNIC_RES` 355030), by admission date (`DT_INTER`), from SIH/SUS (DATASUS,
  AIH-RD microdata). File: `data/processed/sih_daily_lookahead.parquet`
  (definition and provenance in `data/processed/sih_daily_lookahead.meta.json`).
  sha256 `{meta["entradas"]["sih"]["sha256"]}`.
* **Period**: {meta["entradas"]["periodo"][0]} to {meta["entradas"]["periodo"][1]} (2 192 days, no gaps).
  The COVID-19 years are included without special treatment.
* **Other files opened by the feature builder** (for the date axis only; none
  of their columns enters an `AR_CAL` feature): `data/processed/cams_daily_v2.csv`,
  `data/processed/cetesb_poluentes_daily.csv`, `data/processed/cetesb_meteo_daily.csv`
  (sha256 in `models_demo/metadata.json`).
* The series is aggregated by day; no microdata and no identifier is stored here.

## Features

Built by the canonical `src/features/forecasting_features.py::construir_dataset`
with the lags of the dissertation config of each horizon. The frame is indexed
by the **target date** `u`; for horizon `h` the forecast origin is `t = u − h`,
and every lagged feature `<var>_lag<L>` satisfies `L ≥ h` (the builder raises
otherwise), so a forecast made at origin `t` uses only values observed up to `t`.
Calendar columns describe the target date and are known in advance.

| h | config | AR lags (`y_lag<L>`) | calendar columns | n features | training rows (after warm-up) | first..last target date |
|---|---|---|---|---|---|---|
"""
        + "\n".join(
            f"| {h} | `{feats[h]['config']}` | {feats[h]['lags_alvo']} | {', '.join(c for c in feats[h]['features'] if comum.PADRAO_LAG.search(c) is None)} | "
            f"{len(feats[h]['features'])} | {feats[h]['n_linhas_treino']} | {feats[h]['primeira_data_alvo']}..{feats[h]['ultima_data_alvo']} |"
            for h in comum.HORIZONTES
        )
        + """

The exogenous lags of the configs (`lags_exogenas`) only matter for the warm-up
length here: `AR_CAL` has no environmental block.

## Evaluation (reference, provisional — pre-defence)

The numbers below are **not** measured on the demo models. They are the
dissertation benchmark figures for XGBoost `AR_CAL` at each horizon, taken
from the `model_comparison.csv` of the run cited in each row (mean over
4 rolling-origin folds × 5 seeds; MAE ± std across folds; MASE = MAE(model) /
MAE(Naïve) on the same test dates, so it is only comparable within a horizon).
The demo models share the feature construction and hyper-parameters of those
runs, but not the training scheme (whole history, no early stopping, one seed).

| h | run id | MAE (admissions/day) | RMSE | MASE | Naïve MAE | folds × seeds | source file |
|---|---|---|---|---|---|---|---|
"""
        + "\n".join(linhas_tab)
        + f"""

## Intended use

Serving `GET /forecast?h=&origem=` in `api/main.py` to demonstrate the
engineering path data → canonical features → model → HTTP, with the same
leakage rule as the benchmark. Nothing else.

## Limitations

* **In-sample by construction.** The demo is trained on the entire history and
  the canonical feature builder only materialises rows for target dates that
  exist in that history. Every forecast the API returns is therefore for a date
  the model has seen in training; it is a demonstration of the serving path,
  not an out-of-sample forecast. Origins are limited to those whose target
  `t + h` lies on or before {meta["entradas"]["periodo"][1]} (see
  `primeira_origem_valida` / `ultima_origem_valida` in `metadata.json`).
* Single seed; the dissertation reports mean ± dispersion over five seeds.
* Point forecast only; no predictive interval.
* No environmental covariate: `AR_CAL` is the common comparison set of the
  dissertation. Whether PM2.5 or weather add skill is a dissertation question
  and is not answered by this demo.
* Not validated for clinical, operational or policy use.

## Reproduce

```
uv run python -m models_demo.treinar
```

prints, per horizon, the number of rows, training time and sha256 of the
saved file; `metadata.json` records the sha256 of every input and output.
"""
    )
    (comum.PASTA_MODELOS / "MODEL_CARD.md").write_text(texto, encoding="utf-8")


def main() -> None:
    t0 = time.perf_counter()
    cfg1 = comum.carregar_config(1)
    arquivos = comum.arquivos_de_dados(cfg1)
    entradas = {
        nome: {"arquivo": comum.caminho_relativo(p), "sha256": comum.sha256_arquivo(p)} for nome, p in arquivos.items()
    }
    entradas["periodo"] = [str(cfg1["dados"]["inicio"]), str(cfg1["dados"]["fim"])]
    hoje = date.today()
    versao = f"{entradas['sih']['sha256'][:8]}-{hoje:%Y%m%d}"

    modelos = {str(h): treinar_horizonte(h) for h in comum.HORIZONTES}

    meta = {
        "modelo": comum.NOME_MODELO,
        "versao": versao,
        "data_treino": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aviso": comum.AVISO,
        "feature_set": comum.FEATURE_SET,
        "horizontes": list(comum.HORIZONTES),
        "seed": SEED,
        "entradas": entradas,
        "ambiente": {
            "python": platform.python_version(),
            "xgboost": xgboost.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "modelos": modelos,
    }
    comum.CAMINHO_METADATA.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    escrever_model_card(meta)
    print(
        f"\nversion {versao}  ·  total {time.perf_counter() - t0:.1f}s  ·  wrote "
        f"{comum.caminho_relativo(comum.CAMINHO_METADATA)} and models_demo/MODEL_CARD.md",
        flush=True,
    )


if __name__ == "__main__":
    sys.exit(main())

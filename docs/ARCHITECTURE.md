# Architecture

The code is a curated copy of the dissertation repository (file-by-file provenance in `docs/INVENTARIO_FASE0.tsv`). Module and variable names are in Portuguese; this document is in English. The design has one rule: **every model consumes the same dataset, the same folds and the same metric functions, and anything unexpected raises**. No silent `dropna`, no imputation, no default baseline.

## Layout

```
src/
  ingestion/      build the daily series from raw sources (SIH FTP, CETESB QUALAR exports, CAMS NetCDF)
  data/           validation.py  -> data quality gate (FAIL aborts the run)
  features/       forecasting_features.py -> the shared dataset: blocks, lags, the L >= h rule
  evaluation/     splits.py (folds) and metrics.py (MAE, RMSE, R2, MASE, skill): single implementations
  models/         base.py (Forecaster) and one module per model
  experiments/    run_preliminary.py (runner), preflight.py, teste_dm_v02.py, teste_dm_fontes.py,
                  analise_multihorizonte.py, selecao_progressiva.py
  viz/            figures for the dissertation (not used by the app)
configs/          YAML per run; "no scientific decision outside this file"
tests/            pytest suite
results/          copied artefacts of identified runs and analyses (read-only)
data/             daily aggregates and station metadata (see data/README.md)
app/ api/ tracking/ models_demo/   portfolio layers (Streamlit, FastAPI, MLflow import, demo models)
```

## Data flow

1. **Target.** `src/ingestion/sih_build_lookahead.py` downloads the monthly AIH-RD files from the DATASUS FTP, keeps `MUNIC_RES` starting with 355030 and `DIAG_PRINC` starting with "J", deduplicates by `N_AIH` (first occurrence across monthly files), counts per `DT_INTER`, and reads six extra months (look-ahead) so late filings are captured. `--carater nao_eletivo` builds the urgent target (`CAR_INT` in 02 to 06). Writes a parquet with columns `internacoes` and `linhas_brutas` plus a `.meta.json` with every rule and count. It never writes inside `data/` of the repository and exits with code 2 if the rebuilt series diverges from the reference.
2. **Environmental series.** `cetesb_build_poluentes.py` and `cetesb_build_meteo.py` parse QUALAR exports (`cetesb_qualar_parser.py`), keep stations of the municipality (`cetesb_estacoes.py`, QUALAR as the authority), require at least 18 valid hours of 24 for a station-day, and aggregate across stations into `<var>_media`, `<var>_n_estacoes` and, for pollutants, `<var>_dt` (dispersion across stations). `cams_download_chunked.py` and `cams_rebuild_daily.py` handle the CAMS alternative source.
3. **Quality gate.** `src/data/validation.py::validar_serie_diaria` produces `data_quality.json`, one line per check (date index, monotonic, unique, daily frequency without gaps, period covered, no missing target, non-negative, zeros, outliers flagged but never removed, coverage of each environmental file). Any `FAIL` aborts the run; `WARN` is recorded and must be read. Example: the h = 1 run has one WARN, `cobertura_cetesb_poluentes` (88 NaN cells, all in SO2), and PASS elsewhere.
4. **Shared dataset.** `src/features/forecasting_features.py::construir_dataset` indexes the frame by the target date `u`. For horizon `h`, every lagged feature `var_lag<L>` is `var[u - L]` and the code raises if any `L < h`; calendar features of `u` (day of week, holiday) enter without lag. Blocks: `AR` (target lags), `CAL`, `METEO`, `PM25` (PM2.5 only, so hypothesis H2 can be tested in isolation), `POLUENTES` (other pollutants), plus custom blocks declared in the config (for example `PM25_MEDIA`, the PM2.5 mean alone). A pollutant column with any NaN in the period is dropped and the drop is recorded in the dataset report (`manifest.json`, key `relatorio_dataset.poluentes_descartados`); nothing is imputed. The h = 1 run has 79 features: AR 6, CAL 8, METEO 30, PM25 15, POLUENTES 20, PM25_MEDIA 5.
5. **Folds.** `src/evaluation/splits.py::rolling_origin` builds expanding-window folds from the target dates; each fold has `treino`, `validacao` (the final 180 days of the training window, used only for early stopping or model selection) and `teste`. The `Fold` dataclass raises on empty partitions, overlaps or wrong order. Every model receives the same `Fold` objects.
6. **Models.** `src/models/base.py::Forecaster` is the contract: `fit(ds, fold, colunas)` may use only `fold.treino` (and `fold.validacao`), `predict(ds, fold, colunas)` returns a vector aligned to `fold.teste`; a different length is an error. `usa_semente = False` marks deterministic models (baselines, SARIMAX, GAM-NB, INGARCH-NB), which the runner executes once per fold and feature set instead of once per seed. Models: `naive.py` (Naïve, Seasonal Naïve), `xgboost_model.py`, `lstm_model.py`, `sarimax_model.py`, `gam_nb.py`, `ingarch_nb.py`. New models inherit `Forecaster` and are registered in `CHAVES_POR_MODELO` in the runner, which rejects any config key a constructor would ignore.
7. **Metrics.** `src/evaluation/metrics.py`: `mae`, `rmse`, `r2`, `mase(y, yhat, yhat_baseline)` (MAE ratio on the same timestamps; the baseline is passed explicitly), `skill`. NaN or mismatched lengths raise. MASE = 1 - skill_MAE by construction.
8. **Runner.** `src/experiments/run_preliminary.py` is the only entry point (`--smoke`, `--screening`, `--full`; `--data-mode cache|rebuild`). It captures `git_commit`, branch and `git status --porcelain` **before** any work, validates the config keys, runs the gate, builds the dataset, builds and validates the folds, loops models × feature sets × seeds × folds, checks that all models predicted exactly the same timestamps, and writes to `reports/experiments/<RUN_ID>/`: `config.json` (the config as executed), `manifest.json` (provenance, dataset hashes, folds, seeds, versions, `n_predicoes`), `metrics.json`, `metrics_by_fold.csv`, `model_comparison.csv`, `predictions.csv`, `folds.csv`, `data_quality.json`, `environment.txt` (pip freeze), `summary.md`, figures. The runs in `results/runs/` are copies of those folders without `predictions.csv` (size) and with the same hashes listed in `docs/INVENTARIO_FASE0.tsv`.
9. **Paired tests.** `src/experiments/teste_dm_v02.py --run <RUN_ID>` recomputes every metric from `predictions.csv` (raises if it differs from the run's CSV by more than 1e-6), builds the per-date absolute loss (mean over seeds for stochastic models), and runs Diebold–Mariano per fold (T = 180) and pooled (T = 720) with Newey–West HAC variance, the Harvey–Leybourne–Newbold small-sample correction and Holm correction inside each family (all model pairs on `AR_CAL`; ablation contrasts per model). Output: `results/testes_dm/TESTES_DM_<RUN_ID>/{RELATORIO_DM.md, dm_contrastes.csv, dm_detalhe.json, validacao_metricas.json}`. `teste_dm_fontes.py` does the same between runs of different sources.
10. **Multi-horizon analysis.** `src/experiments/analise_multihorizonte.py` reads runs fixed by full id (never "the latest"), checks integrity (full mode, clean tree, gate PASS, horizon matches, lags shifted by h, `n_predicoes` equals the number of prediction rows, MASE of the Naïve equals 1 in every fold) and writes the tables in `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/` with a `proveniencia.json` carrying the sha256 of each input. It uses MASE only within a horizon and MAE/skill across horizons.

## Portfolio layers (built in parallel; see each folder)

- `app/` (Streamlit, port 8501): reads `results/` and `notebooks/dados_painel/`; every figure on screen comes from a file.
- `api/` (FastAPI, port 8000): `GET /health`, `GET /forecast`; serves demonstration XGBoost `AR_CAL` models from `models_demo/` (one seed, whole series, no fold protocol; `models_demo/MODEL_CARD.md`).
- `tracking/importar_runs.py`: copies `config.json`, `manifest.json` and `metrics.json` of each run into an MLflow file store (`./mlruns`); no recomputation.
- `Dockerfile` and `docker-compose.yml`: one image, three services (`app`, `api`, `mlflow`).

## Fail-loud rules you will hit

- A lag smaller than the horizon: `ValueError` in `construir_dataset`.
- A config key the model constructor does not consume: `ValueError` in `_validar_chaves` (the runner).
- A pollutant column with NaN: dropped and recorded, never imputed; a meteorological column with NaN: `RuntimeError`.
- A `FAIL` in the quality gate: the run aborts and `data_quality.json` is still written.
- A model that returns the wrong number of predictions, or models whose test timestamps differ: `RuntimeError` in the runner.
- A SARIMAX forecast outside 5 × max of the target, or a degenerate fit: excluded or raised (`sarimax_model.py`).
- A metric computed on NaN or on mismatched vectors: `ValueError` in `metrics.py`.

## Optional MLflow logging during a run

`src/experiments/run_preliminary.py` accepts `--mlflow --mlflow-uri <uri> [--mlflow-experimento <name>]`. The flag only logs. All the logic lives in `tracking/registro_mlflow.py`, and `mlflow` is imported only when the flag is set. `tests/test_runner_mlflow.py` compares the outputs with and without the flag, and without the flag against the runner before the hooks (commit `2be070b`): `metrics.json`, `model_comparison.csv`, `metrics_by_fold.csv`, `folds.csv` and `feature_ablation.csv` are byte-identical; `predictions.csv` is identical once the run id in its `run_id` column is masked, and `manifest.json` is identical except for the run id and the timestamps and durations (and, against the pre-hook runner, the git fields).

With the flag, the runner creates one parent run per execution, one nested run per model and feature set with the same metrics as `metrics.json`, and one MLflow model per model, feature set, fold and seed. XGBoost uses the native flavor. LSTM, SARIMAX and GAM-NB use a pyfunc wrapper around the native artefact, because standardisation and refitting live outside the native object. INGARCH-NB and the baselines use pyfunc. Each model reloaded from MLflow reproduces the predictions of its fold and seed.

The flag exists only in this portfolio copy of the runner; the dissertation runner is unchanged (decision D9 in `docs/DECISOES.md`). Light test config: `configs/smoke_mlflow.yaml` (never a result). The full research history is imported separately by `tracking/importar_pesquisa.py`.

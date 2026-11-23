# Reproducibility

What can be rerun from this repository, how, and what cannot. All results are provisional (pre-defence).

## 1. Environment

- Python 3.11 (`.python-version`); dependencies pinned in `pyproject.toml` and `uv.lock` to the versions that executed the dissertation runs: numpy 2.4.1, pandas 3.0.0, xgboost 3.2.0, tensorflow 2.20.0, scikit-learn 1.8.0, statsmodels 0.14.6, scipy 1.17.0 (the same versions are recorded in each run's `manifest.json`, key `versoes`, and the full `pip freeze` of the executing machine is in `results/runs/<RUN_ID>/environment.txt`).
- The original lock of the executed environment is kept verbatim in `docs/requirements-executado-20260727-163313.txt`.
- The runs were executed on Windows (`manifest.json`, `versoes.plataforma`). TensorFlow and XGBoost results can differ at the last decimals across operating systems and CPU instruction sets; the protocol reports means across five seeds for that reason.

```bash
uv sync
uv run pytest -q
```

## 2. Rerunning an identified run from its `config.json`

The runner reads the config with `yaml.safe_load` (`src/experiments/run_preliminary.py`, function `executar`), and JSON is valid YAML, so the `config.json` saved by a run can be passed back unchanged:

```bash
uv run python -m src.experiments.run_preliminary \
    --config results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json \
    --full --data-mode cache
```

What this does: reads the data files named in the config from `data/processed/` (paths are relative to the repository root), runs the quality gate, builds the same 79 features, the same 4 folds (`folds.csv` of the original run is the reference: test windows 2023-01-12 to 2023-07-10, 2023-07-11 to 2024-01-06, 2024-01-07 to 2024-07-04, 2024-07-05 to 2024-12-31), the same seeds (42 to 46), and writes a new folder `reports/experiments/<nome>_full_<timestamp>/`. `reports/` is git-ignored; the runs shown in this repository live in `results/runs/` and are never overwritten.

Before a `--full` run, the dissertation rule applies here as well: commit first and start from a clean tree (`git status --porcelain` empty). The runner records `git_commit_no_inicio` and `git_sujo_no_inicio` in `manifest.json` before any computation; a run with `git_sujo: true` is a record, not a result (`docs/LESSONS.md`, story 4).

Expected wall time for a full seven-model run on a laptop CPU: several hours (the h = 1 run started 2026-10-22 21:18:34 and finished 23:43:02, `manifest.json`, key `proveniencia`). `--smoke` with `configs/smoke.yaml` takes about a minute and is never a result.

Checking a rerun against the original: compare `model_comparison.csv` and `metrics_by_fold.csv`. Deterministic models (Naïve, Seasonal Naïve, SARIMAX, GAM-NB, INGARCH-NB) should match to floating-point precision on the same platform; XGBoost and LSTM should match per seed on the same platform and library versions, and in mean across seeds elsewhere within the seed dispersion reported in `model_comparison.csv` (`MAE_std_semente`).

The multi-horizon configs are in `configs/multihorizonte/` and `configs/alvo_urgencia/`; each run's `config.json` is the authoritative version of what executed.

## 3. Recomputing the paired tests and the analyses

`src/experiments/teste_dm_v02.py` needs `predictions.csv`, which is not copied into `results/runs/` (size). After a rerun, point it at the new folder:

```bash
uv run python -m src.experiments.teste_dm_v02 --run <NEW_RUN_ID>
```

The copied `results/testes_dm/TESTES_DM_<RUN_ID>/` folders contain the reports and `dm_contrastes.csv` of the original runs; `validacao_metricas.json` records that the metrics recomputed from `predictions.csv` matched the run's CSV to about 1e-14.

`src/experiments/analise_multihorizonte.py` has the run ids hard-coded by full id and reads them from `reports/experiments/`; to rerun it on the copied artefacts, copy `results/runs/*` into `reports/experiments/` (it also needs `predictions.csv` and the DM folders).

## 4. Rebuilding the data

- **Target.** `uv run python -m src.ingestion.sih_build_lookahead --destino <folder outside the repo>` downloads the 78 monthly AIH-RD files for SP (2019-01 to 2025-06) from the DATASUS FTP, rebuilds `sih_daily_lookahead.parquet` day by day and compares it with the file in `data/processed/` (exit code 2 on divergence). `--carater nao_eletivo` rebuilds the urgent target. The dissertation validated this reconstruction on 2026-10-19 (its `CLAUDE.md` §5a); the reconstruction depends on the FTP still serving the same files.
- **CETESB.** `cetesb_build_poluentes.py` and `cetesb_build_meteo.py` need the CSV exports of the QUALAR "Exportar Dados Avançado" screen, which require a (free) QUALAR account and manual export; the exports are not in this repository. The `.meta.json` files record how many export files were used and ignored, the stations kept and the deduplication counts.
- **CAMS.** `cams_download_chunked.py` needs Copernicus ADS credentials (`.env.example` shows the variables; never commit `.env` or `.cdsapirc`). See section 5.

## 5. What is not reproducible, and why

| Item | Status |
|---|---|
| `data/processed/cams_daily_v2.csv` | **Not reproducible with the current ADS.** The file merges two interpolated points returned by the old ADS for a box around São Paulo; the current ADS refuses the box and returns a different grid node with materially different PM2.5 levels (dissertation PROTOCOLO §0.17; `docs/LESSONS.md`, story 2). The file is kept as the historical "CAMS v2" used by the CAMS runs. |
| SIH/SUS microdata | Not redistributed. Only daily aggregates are here (`docs/DECISOES.md`, D2). The FTP download rebuilds them. |
| QUALAR hourly exports | Not redistributed (manual exports, terms to be confirmed). Only daily aggregates and station metadata are here. |
| `predictions.csv` of each run | Not copied (size). Rerun to regenerate. |
| Runs of other sources and arms | The CAMS, CETESB-mirror, hybrid and COVID-arm runs cited in the dissertation are not copied; `results/analise_multihorizonte/.../proveniencia.json` lists their ids for reference only. |
| Bit-identical LSTM/XGBoost numbers on another OS | Not guaranteed; the protocol reports mean ± dispersion over five seeds. |

## 6. Provenance of the copied artefacts

`docs/INVENTARIO_FASE0.tsv` lists, for every file copied from the dissertation repository, its origin path, destination path and sha256. The analysis folders carry their own `proveniencia.json` with the sha256 of each input artefact, the commit and the library versions at generation time.

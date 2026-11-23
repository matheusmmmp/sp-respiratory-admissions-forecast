# Lessons: four things that went wrong or surprised us

Each story below is told with the file that proves it. Numbers come only from files in this repository (`results/`, `notebooks/dados_painel/`, `data/processed/*.meta.json`, `src/`); the narrative context comes from the dissertation's working documents (`CLAUDE.md`, `docs/PROTOCOLO.md` §0.17 and §0.23, `docs/CHANGELOG.md`), which are not copied here. Where a number lives only in those documents, the text says so instead of repeating it. Everything is provisional (pre-defence).

## 1. The Saturday problem: elective surgeries in one hospital were driving the forecast error

**What we saw.** On the total target, every model's worst weekday is Saturday, and by a wide margin. At h = 1, run `h1_v02_cetesb_cetesb_classicos_full_20261022-211834`, feature set `AR_CAL`:

| Model | MAE on Saturdays | MAE on other days | Ratio |
|---|---:|---:|---:|
| XGBoost | 33.31 | 16.09 | 2.07 |
| SARIMAX | 37.08 | 15.89 | 2.33 |
| LSTM | 33.79 | 16.54 | 2.04 |
| INGARCH-NB | 35.86 | 16.82 | 2.13 |
| GAM-NB | 43.72 | 18.26 | 2.39 |

Source: `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` (columns `MAE_sab`, `MAE_demais`, `razao`; 2 decimals). Saturdays are 103 of the 720 test dates (`saida.txt`, section C, same folder).

**Why.** The Saturday excess is not epidemiological. The admission records split by `CAR_INT` (admission character: elective vs. urgent) show that, from 2022 on, elective admissions concentrate on Saturdays and most of them come from a single establishment, CNES 2091550 (named in `notebooks/dados_painel/estabelecimentos_ano.csv`). The aggregated panel in `notebooks/dados_painel/` shows it:

- `estabelecimentos_ano.csv`: for CNES 2091550 the number of elective admissions on Saturdays goes from 244 (2019) and 302 (2021) to 1,291 (2022), 1,562 (2023) and 1,343 (2024). In those years every admission of that establishment in the target is elective (`total == eletivas`).
- `perfil.csv`: the "elective, Saturday, CNES 2091550" slice has 6,870 admissions, median age 9 years, 69.8% under 15, median stay 0 days, 99.7% with stay of at most 1 day and 0.0% deaths. The "non-elective" slice has median stay 5 days and 10.2% deaths. These are day-surgery batches, not acute illness.
- `grupos_cid.csv`: the ICD-10 group J30 to J39 (chronic upper-airway disease, including tonsil and adenoid surgery) has 39,243 admissions, 35,958 of them elective; 11,206 of those come from CNES 2091550 (`eletivas_cema`). In the groups with a plausible pollution mechanism (J00 to J06, J09 to J11, J12 to J18, J20 to J22, J40 to J47) the elective share is small (for example J12 to J18: 4,811 elective out of 153,309).
- `diario.csv`: the elective fraction of the daily total is 12% to 14% from 2019 to 2024 (sum of `eletivo` over sum of `total` per year), rising afterwards.

The dissertation's PROTOCOLO §0.23 (not copied here) records the diagnosis and the alternatives that were rejected: dropping CNES 2091550 (a sample-specific rule that would not generalise), dropping J34/J35 (would remove real urgent cases), a calendar flag for surgery batches (not known at forecast origin), or trimming outliers (would erase epidemic peaks).

**What we did.** A second target, the **urgent** series: distinct `N_AIH` with `CAR_INT` in {02, 03, 04, 05, 06}, same deduplication and look-ahead (`data/processed/sih_daily_lookahead_urgencia.meta.json`, key `filtro_carater_internacao`; 263,399 admissions kept, 39,896 elective excluded). On that target the Saturday ratio drops below 1 for every model (XGBoost 13.64 on Saturdays vs. 15.08 on other days, ratio 0.90; same `erro_sabado_h1.csv`). The two targets are reported side by side and have different roles: total for demand forecasting, urgent for the air-pollution question. Runs: `ur_h{1,5,7,15,30}_cetesb_cetesb_full_*` in `results/runs/`.

**Lesson.** Look at the error by weekday before tuning anything. The outlier was an administrative process (a surgical backlog scheduled on Saturdays), visible only in a field we had not been using.

## 2. The canonical CAMS file cannot be re-downloaded

**What we saw.** `data/processed/cams_daily_v2.csv` (2,192 days, aggregated from 3-hourly fields; `n_obs` = 8 on 2,191 days and 7 on one day) was built from Copernicus ADS downloads made in 2025 and early 2026 for a small box around São Paulo. When we re-ran the download in October 2026 to prove reproducibility, the ADS refused the box and returned a different grid node. The dissertation's PROTOCOLO §0.17 records that the canonical file merges two interpolated points south-west of the city centre, that the current ADS returns a node north-east of it, and that the new file has materially higher PM2.5 levels with a high daily correlation to the old one; the exact percentages are in that document, not here.

**Evidence in this repository.** `src/ingestion/cams_rebuild_daily.py` (header) documents the defects fixed during the 2026 audit (partial edge days from the UTC shift, missing `d2m` in one download, unit conversion) and its `--comparar` mode, which exits with code 2 when a rebuilt file diverges from the canonical one. `src/features/forecasting_features.py` documents why CAMS cannot provide surface NO2, O3, CO or SO2 (EAC4 single-level has total columns, not surface concentrations).

**What we did.** CAMS is the **alternative** source; the main source is CETESB/QUALAR (surface measurements, 2,192 days, several stations per pollutant). A sensitivity run with the newly downloaded CAMS file is described in PROTOCOLO §0.17; its numbers are not in this repository and are not cited here. In `data/README.md` the CAMS file is described with its real provenance, never as "the São Paulo grid point".

**Lesson.** A reanalysis download is not reproducible by default: record the request, the API version and the returned coordinates, and keep the raw NetCDF. We now do.

## 3. The BigQuery shortcut counted the wrong thing

**What we saw.** The first attempt at the target used the public BigQuery mirror of SIH/SUS (`basedosdados.br_ms_sih.servicos_profissionais`) through a script that is kept in the dissertation repository as legacy (`src/ingestion/fetch_sih_bq_enriquecido.py`, not copied here). Its query had two problems visible in its header: the table has one row per professional service inside an admission, not one row per admission, so counting rows overstates admissions; and it filtered by the municipality of the establishment (`id_municipio_estabelecimento_aih`), not by the municipality of residence.

**What we did.** The target was rebuilt from the AIH-RD microdata on the DATASUS FTP by `src/ingestion/sih_build_lookahead.py` (header documents the rule): distinct `N_AIH` per `DT_INTER`, `MUNIC_RES` starting with 355030, `DIAG_PRINC` starting with "J", first occurrence across monthly files wins, six extra monthly files of look-ahead because an AIH can be filed months after the admission. The resulting series was checked against TabNet/DATASUS (monthly, 72 months, correlation 0.999983, constant bias of -0.34%; `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json`, key `dados.alvo.validacao`). The meta file records 303,295 distinct admissions, 77 duplicates across monthly files and 29,700 records outside the period (`data/processed/sih_daily_lookahead.meta.json`).

**Lesson.** "Admissions" is not a column; it is a rule (which identifier, which date, which deduplication, which spatial criterion, how long you wait for late records). Write the rule in the meta file next to the data.

## 4. A run with a dirty tree does not close a version

**What we saw.** The first full benchmark of July 2026 (`preliminar_h1_full_20260727-163313`, kept only in the dissertation repository) had three defects recorded in the dissertation's `CLAUDE.md` §5 and `CHANGELOG.md`: the working tree was dirty when it started, the XGBoost objective had been chosen on the validation window, and the manifest recorded the commit at the end of the run, after a commit made while it was running. The runner itself documents the last problem for a sibling run: see the comment above the `proveniencia` block in `src/experiments/run_preliminary.py` ("Capturado ANTES de qualquer trabalho ... A run `preliminar_h1_full_20260727-161742` tem exatamente esse defeito").

**What we did.** Three rules, all enforced by code or by the manifest:

1. `--full` only with a clean tree and a commit made before starting; the runner captures `git_commit_no_inicio` and `git_sujo_no_inicio` before any work and records `git_commit_no_fim`, `git_sujo_no_fim` and `repositorio_mudou_durante_a_run` at the end (`manifest.json`, key `proveniencia`).
2. The XGBoost objective is fixed in the config (`count:poisson`, `selecionar_objetivo: false`; `results/runs/<RUN_ID>/config.json`).
3. A run with `git_sujo: true` stays on disk as a record but never becomes a result; nothing under the results folders is edited or deleted.

**Evidence.** All ten runs shown in the README have `git_sujo: false` and `repositorio_mudou_durante_a_run: false`, read from their `manifest.json` by `docs/scripts/conferir_numeros.py`:

| Run id | `git_commit` | `git_sujo` | repo changed during run |
|---|---|---|---|
| `h1_v02_cetesb_cetesb_classicos_full_20261022-211834` | `e6a63c3` | false | false |
| `mh_h5_cetesb_cetesb_full_20261110-211453` | `5436606` | false | false |
| `mh_h7_cetesb_cetesb_full_20261111-030322` | `49c2188` | false | false |
| `mh_h15_cetesb_cetesb_full_20261111-070926` | `b5bb35f` | false | false |
| `mh_h30_cetesb_cetesb_full_20261113-104814` | `e4828bc` | false | false |
| `ur_h1_cetesb_cetesb_full_20261116-191534` | `eeeef00` | false | false |
| `ur_h5_cetesb_cetesb_full_20261116-222823` | `8325cee` | false | false |
| `ur_h7_cetesb_cetesb_full_20261117-073926` | `dfc3c57` | false | false |
| `ur_h15_cetesb_cetesb_full_20261117-190532` | `1252ad5` | false | false |
| `ur_h30_cetesb_cetesb_full_20261117-221426` | `8be599e` | false | false |

(The commits refer to the dissertation repository, where the runs were executed; this repository is a curated copy, see `docs/INVENTARIO_FASE0.tsv`.)

**Lesson.** Provenance is captured at the start, not at the end, and a result that cannot name its commit is not a result.

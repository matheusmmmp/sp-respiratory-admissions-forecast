# Data card

Only daily aggregates and station metadata are redistributed here (author decision D2 in `docs/DECISOES.md`). No microdata, no hourly station records, no admission identifier. Every number below is read from the `.meta.json` next to each file or from the file itself; the audit list is `docs/CONFERENCIA_NUMEROS_WP5.md`. Provenance (origin path and sha256 of each copied file): `docs/INVENTARIO_FASE0.tsv`.

| File | Rows | Period | Source | Licence |
|---|---:|---|---|---|
| `processed/sih_daily_lookahead.parquet` | 2,192 days | 2019-01-01 to 2024-12-31 | SIH/SUS, DATASUS (AIH-RD microdata, aggregated here) | Public data of the Brazilian Ministry of Health (DATASUS open access); aggregated counts only |
| `processed/sih_daily_lookahead_urgencia.parquet` | 2,192 days | same | same, non-elective admissions only | same |
| `processed/cetesb_poluentes_daily.csv` | 2,192 days | same | CETESB / QUALAR station exports, aggregated here | CETESB/QUALAR: terms to be confirmed (attribution kept; redistribution of daily aggregates pending confirmation) |
| `processed/cetesb_meteo_daily.csv` | 2,192 days | same | CETESB / QUALAR, aggregated here | same |
| `processed/cams_daily_v2.csv` | 2,192 days | same | CAMS global reanalysis (EAC4), Copernicus Atmosphere Monitoring Service, ECMWF, aggregated here | Copernicus licence (ECMWF/CAMS data policy): free use with attribution; this file is a derived daily product |
| `cetesb/*.csv` | station lists | | CETESB station registry (QUALAR, ArcGIS service), compiled by the author | same as CETESB above |

Attribution lines to keep when reusing:

- "Generated using Copernicus Atmosphere Monitoring Service information [2025, 2026]; neither the European Commission nor ECMWF is responsible for any use that may be made of it."
- "Dados de qualidade do ar e meteorologia: CETESB, sistema QUALAR."
- "Internações: Ministério da Saúde, SIH/SUS, DATASUS."

## 1. Target: `processed/sih_daily_lookahead.parquet` (+ `.meta.json`)

- **Definition.** Daily count of distinct hospital admission authorisations (`N_AIH`) in the AIH-RD files (SIH/SUS, group RD, state SP) with `MUNIC_RES` (municipality of residence) starting with 355030, `DIAG_PRINC` starting with "J" (ICD-10 J00 to J99), dated by `DT_INTER` (admission date). The same `N_AIH` seen in two monthly files counts once (first occurrence wins).
- **Look-ahead.** Monthly files from 2019-01 to 2025-06 are read (78 files): the epidemiological period plus six extra months, because an AIH can be filed months after the admission. The meta file records that four later months already capture 99.8% of a month's admissions.
- **Columns.** Index `data` (daily, no gaps); `internacoes` (distinct `N_AIH`, the target); `linhas_brutas` (rows before deduplication).
- **Counts** (`sih_daily_lookahead.meta.json`): 303,295 distinct admissions; 77 duplicates across monthly files; 29,700 records outside the period; 0 invalid dates; 0 days with zero admissions. Annual totals 2019 to 2024: 52,335; 39,482; 43,941; 52,718; 56,640; 58,179.
- **Validation.** Compared with TabNet/DATASUS (monthly, by residence, 72 months): correlation 0.999983, constant bias of -0.34% left open (`results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json`, key `dados.alvo.validacao`).
- **Rebuild.** `src/ingestion/sih_build_lookahead.py` (see `docs/REPRODUCIBILITY.md`).

### `processed/sih_daily_lookahead_urgencia.parquet` (+ `.meta.json`)

Same rule, restricted to **non-elective** admissions: `CAR_INT` (admission character) in {02 urgency, 03 to 06 accidents and injuries}, as coded by Portaria SAS/MS 719/2007; the first occurrence of the `N_AIH` decides both the date and the character; an empty code or a code outside 01 to 06 fails loudly. Counts: 263,399 admissions kept, 39,896 elective (`CAR_INT` 01) excluded; in this extract only codes 01 and 02 occur. Annual totals 2019 to 2024: 45,197; 34,734; 38,445; 46,159; 48,893; 49,971. This target was built on 2026-11-16 and has not yet been validated against TabNet (its runs carry status `PRELIMINARY_UNVALIDATED_TARGET`). Why it exists: `docs/LESSONS.md`, story 1.

## 2. CETESB pollutants: `processed/cetesb_poluentes_daily.csv` (+ `.meta.json`)

- **Source.** CETESB QUALAR, screen "Exportar Dados Avançado", hourly values per station, exported manually (191 export files used, 14 ignored); stations restricted to the municipality of São Paulo (21 stations of other municipalities excluded, listed in the meta file). Hourly records deduplicated across overlapping exports (3,954,672 before, 3,722,808 after).
- **Daily rule.** For each station and day, the mean of the valid hours, requiring at least 18 of 24; then across stations: `<pol>_media` (mean of station means), `<pol>_n_estacoes` (stations with a valid day), `<pol>_dt` (sample standard deviation across stations divided by the mean, requiring at least 2 stations). The "Avançado" screen does not carry the QUALAR "Válido" flag; whether it already excludes invalid hours is an open point recorded in the meta file.
- **Columns.** `data`, then for each of `co`, `no2`, `o3`, `pm10`, `pm25`, `so2`: `_media`, `_n_estacoes`, `_dt`. Units as exported by QUALAR (µg/m³ for PM and gases, ppm for CO).
- **Coverage** (meta, `por_poluente`): stations with data and mean stations per day: PM2.5 18 (10.6/day), PM10 14 (9.5/day), NO2 10 (7.3/day), O3 15 (12.8/day), CO 9 (7.4/day), SO2 7 (3.1/day). All pollutants cover 2,192 days except SO2 (2,190 days with a mean, 2,108 with `_dt`).
- **What is excluded in the runs and why.** The feature builder drops any pollutant column with a NaN in the period rather than imputing it. SO2 has 2 days without a valid station (2021-01-10 and 2021-01-11) and 84 days without `_dt`, so the `POLUENTES` block uses PM10, NO2, O3 and CO only (`results/runs/<RUN_ID>/manifest.json`, key `relatorio_dataset.poluentes_descartados`). The quality gate records this as a WARN (`cobertura_cetesb_poluentes`, 88 NaN cells, all in the SO2 columns).

## 3. CETESB meteorology: `processed/cetesb_meteo_daily.csv` (+ `.meta.json`)

- **Source.** Same QUALAR screen (54 export files used, 14 ignored); municipality of São Paulo only (5 metropolitan stations excluded). Spatial coverage is poor and is a property of the network: few stations measure temperature and humidity over the whole period (see `src/ingestion/cetesb_build_meteo.py` header and `cetesb/disponibilidade_meteo.csv`).
- **Daily rule.** Station-day mean/min/max of valid hours, at least 18 of 24; then mean across stations. No dispersion index for meteorology (it would measure topography and heat island, not exposure).
- **Columns.** `data`, `temp_media`, `temp_n_estacoes`, `temp_min`, `temp_max`, `temp_amplitude` (max minus min, intraday range), `ur_media`, `ur_n_estacoes` (relative humidity), `vv_media`, `vv_n_estacoes` (wind speed).
- **Coverage** (meta, `por_variavel`): temperature 6 stations (4.2/day on average), humidity 6 (3.6/day), wind 10 (7.5/day); 2,192 days each, no NaN. The meta key `dias_descartados_por_cobertura` records the station-day entries dropped by the 18-of-24 rule: temperature 524, humidity 454, wind 483.

## 4. CAMS: `processed/cams_daily_v2.csv`

- **Source.** CAMS global reanalysis EAC4 (single-level), Copernicus ADS, 3-hourly fields downloaded in 2025 and early 2026 for a box around São Paulo and aggregated to local days (`America/Sao_Paulo`) by `src/ingestion/cams_rebuild_daily.py`.
- **Columns.** `data`, `d2m`, `pm10`, `pm2p5`, `sp`, `t2m`, `u10`, `v10` (as returned, SI units, PM converted to µg/m³), derived `t2m_c`, `d2m_c` (°C), `rh` (relative humidity from the Magnus formula), `ws10` (wind speed), `n_obs` (3-hourly observations in the day: 8 on 2,191 days, 7 on one day). 2,192 rows, no NaN.
- **Provenance warning.** The file merges two points interpolated by the former ADS to the edge of the request box, south-west of the city centre; it is **not** a grid node "at São Paulo", and the current ADS returns a different node with materially different PM2.5 levels. It is kept as the historical "CAMS v2" used by the CAMS runs of the dissertation; details in `docs/LESSONS.md`, story 2, and in the dissertation's PROTOCOLO §0.17. CAMS is the **alternative** environmental source in this project; CETESB is the main one.
- **What CAMS cannot provide.** Surface NO2, O3, CO and SO2 (EAC4 single-level has vertical total columns only), documented in `src/features/forecasting_features.py`. In the runs shown here CAMS is opened only for the date axis; none of its columns enters a feature (`manifest.json`, `fonte_pm25` and `fonte_meteo` equal `cetesb`).

## 5. Station metadata: `cetesb/`

| File | Content |
|---|---|
| `estacoes_municipio_sp.csv` | 23 QUALAR stations in the municipality of São Paulo with QUALAR code, name, whether PM2.5 is in the station's registry (19 of 23), ArcGIS code where known, latitude/longitude. Compiled from the QUALAR export screens on 2026-07-27 (`src/ingestion/cetesb_estacoes.py`, which explains two earlier wrong versions of this list). "Measures" means the parameter exists in the registry, not that there is data in 2019 to 2024. |
| `disponibilidade_qualar.csv` | For the 19 PM2.5 stations and six parameters (MP2.5, MP10, NO2, O3, CO, SO2), a 0/1 availability flag per year 2019 to 2024, as shown by QUALAR. Semicolon-separated. |
| `disponibilidade_meteo.csv` | Per station, the number of available hourly records in 2024 for temperature, humidity and wind, and the spatial cut (`municipio_sp` or metropolitan region). Semicolon-separated. |
| `stations_bbox.csv` | Stations returned by the CETESB ArcGIS service for the bounding box, with that service's codes (different from QUALAR codes; see `src/ingestion/cetesb_qualar_parser.py`). Kept for coordinates only. |
| `stations_sp_pm25.csv` | One reference point (label `SP`) used by the early CAMS download; not a station list. |

## 6. What is not here

- SIH/SUS microdata and any per-admission field (`N_AIH`, dates, establishment, age). The Saturday panel in `notebooks/dados_painel/` is aggregated (establishment × year with fewer than 5 admissions suppressed; `manifest.json` in that folder).
- Hourly station records from QUALAR (`data/cetesb/hourly_*` are git-ignored).
- Raw CAMS NetCDF files (`data/raw/` is git-ignored).
- Any other municipality or period.

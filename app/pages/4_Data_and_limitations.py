"""Data and limitations — sources, construction rules, what is (and is not) in this repository."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dados  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402

ui.configurar_pagina("Data and limitations", "📚")
st.title("Data and limitations")
ui.aviso_provisorio()

meta_t = dados.carregar_meta_alvo("total")
meta_u = dados.carregar_meta_alvo("urgencia")
meta_p = dados.carregar_meta_poluentes()

st.header("Sources")
st.markdown(
    "- **Target — SIH/SUS, AIH-RD (DATASUS).** Hospital admission records of the Brazilian public health system, "
    "downloaded as public microdata (FTP of DATASUS) and aggregated to one count per day. Only the daily aggregates "
    "are in this repository.\n"
    "- **Environmental covariates — CETESB/QUALAR** (main source): PM2.5, PM10, NO2, O3, CO and meteorology from the "
    "monitoring stations inside São Paulo city, aggregated per day.\n"
    "- **CAMS (Copernicus)** — alternative source used only for sensitivity analysis in the dissertation; the daily "
    "file is in `data/processed/cams_daily_v2.csv` with the Copernicus licence."
)

st.header("How the target is built")
st.markdown(
    f"- One count per day of **distinct AIH** (`N_AIH`), residents of São Paulo city "
    f"(`{meta_t['criterio_espacial']}`), main diagnosis in chapter J (`{meta_t['regra_cid']}`), dated by "
    f"`{meta_t['campo_data']}`.\n"
    f"- **Look-ahead of {meta_t['look_ahead_competencias']} billing competences** after the epidemiological period "
    f"({meta_t['periodo_epidemiologico'][0]} to {meta_t['periodo_epidemiologico'][1]}; administrative files "
    f"{meta_t['periodo_administrativo'][0]}–{meta_t['periodo_administrativo'][1]}), because an admission can be billed "
    f"months later. {meta_t['look_ahead_justificativa']}.\n"
    f"- **Urgent target**: same rule restricted to the non-elective admission character "
    f"(`{meta_u['regra_contagem']}`; filter `CAR_INT` 02–06)."
)
comp = pd.DataFrame(
    {
        "total target": {
            "rows summed": meta_t["total_linhas_somadas"],
            "distinct AIH": meta_t["total_aih_distintas"],
            "duplicates across competences": meta_t["duplicatas_entre_competencias"],
            "invalid DT_INTER": meta_t["dt_inter_invalidas"],
            "days": meta_t["dias"],
            "days with zero": meta_t["dias_com_zero"],
            "extracted": meta_t["extraido_em"],
        },
        "urgent target": {
            "rows summed": meta_u["total_linhas_somadas"],
            "distinct AIH": meta_u["total_aih_distintas"],
            "duplicates across competences": meta_u["duplicatas_entre_competencias"],
            "invalid DT_INTER": meta_u["dt_inter_invalidas"],
            "days": meta_u["dias"],
            "days with zero": meta_u["dias_com_zero"],
            "extracted": meta_u["extraido_em"],
        },
    }
)
st.dataframe(comp, width="stretch")
ui.fonte(dados.rel_meta_alvo("total"), dados.rel_meta_alvo("urgencia"))

st.header("How the CETESB series are built")
st.markdown(
    f"- Source: {meta_p['fonte']}; daily rule: **{meta_p['regra_diaria']}**; spatial dispersion D_t: "
    f"{meta_p['regra_dt']}.\n"
    f"- Pollutants present: {', '.join(meta_p['poluentes_presentes'])}. Known limitation: {meta_p['limitacao_valido']}.\n"
    "- SO2 is excluded from the models by the coverage rule of the feature builder (days without a valid station); "
    "it is never imputed silently."
)
pp = pd.DataFrame(meta_p["por_poluente"]).set_index("poluente")
ui.tabela(pp, casas=2, width="stretch")
ui.fonte(dados.REL_META_POLUENTES)

st.header("Evaluation protocol")
run_ref = dados.run_de("total", 1)
cfg = dados.carregar_config(run_ref)
st.markdown(
    f"- Rolling-origin validation: **{cfg['split']['n_folds']} folds × {cfg['split']['dias_teste']} test days**, "
    f"{cfg['split']['dias_validacao']} validation days, minimum training of {cfg['split']['treino_minimo']} days; "
    f"same folds, same dates and same information for every model (`src/evaluation/splits.py`).\n"
    f"- Target lags {cfg['experimento']['lags_alvo']}, exogenous lags {cfg['experimento']['lags_exogenas']}, "
    f"seasonal period {cfg['experimento']['periodo_sazonal']}; every lag L satisfies L ≥ h (checked with an exception).\n"
    f"- Seeds {cfg['run']['sementes']} for XGBoost and LSTM; every seed is reported as a mean, never the best one.\n"
    "- Metrics: MAE, RMSE, MASE = MAE(model) / MAE(Naïve) on the same test dates; Diebold–Mariano with Holm.\n"
    "- A data-quality gate runs before every run; FAIL aborts the run."
)
ui.fonte(dados.rel_run(run_ref, "config.json"), run=run_ref)

st.header("Runs in this repository")
runs = dados.resumo_runs()
st.dataframe(runs, hide_index=True, width="stretch")
ui.fonte(
    f"{dados.DIR_RUNS}/<run_id>/manifest.json",
    f"{dados.DIR_RUNS}/<run_id>/config.json",
    f"{dados.DIR_RUNS}/<run_id>/data_quality.json",
)
st.markdown(
    "`status` is the runner's own label: the total target was validated monthly against TabNet/DATASUS "
    "(`PRELIMINARY_VALIDATED_TARGET`); the urgent target has not been validated against an official aggregate yet "
    "(`PRELIMINARY_UNVALIDATED_TARGET`). `dirty_tree` must be false for a run to count."
)

st.header("What is not here, and other limitations")
st.markdown(
    "- **Only aggregates.** No microdata, no `N_AIH`, no patient-level record. Establishment × year cells with fewer "
    "than 5 admissions are suppressed in the Saturday panel.\n"
    "- **Everything is provisional (pre-defense).** Numbers can change until the dissertation is defended; each one "
    "carries the full id of the run that produced it.\n"
    "- **The forecasting API in this repository is an engineering demonstration**, trained on the whole history for "
    "serving; its forecasts are **not** results of the dissertation and must not be read as such.\n"
    "- **CETESB coverage varies** (number of valid stations per day changes over the years); the rich PM2.5 "
    "representation (mean + station count + dispersion) hurts the LSTM for that reason.\n"
    "- **The canonical CAMS file is not reproducible** from the current ADS endpoint (different grid point); it is kept "
    "as the alternative source used in the dissertation, not as a reference product.\n"
    "- **Urgent target not yet checked against TabNet**; 2025–2026 data in the Saturday panel are also unchecked.\n"
    "- Not executed: TCN, TCN–LSTM, TFT, SHAP; no claims are made about them."
)

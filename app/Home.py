"""Home — daily forecasting of respiratory hospital admissions in São Paulo city (ICD-10 J00–J99)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dados  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402

ui.configurar_pagina("Home", "🏥")

st.title("Respiratory admissions in São Paulo — 1 to 30 days ahead")
st.markdown(
    "Daily forecasting of respiratory hospital admissions (ICD-10 J00–J99) of residents of São Paulo city, "
    "2019–2024, with **seven models** (Naïve, Seasonal Naïve m = 7, XGBoost, LSTM, SARIMAX, GAM-NB, INGARCH-NB) "
    "evaluated under **one protocol**: 4 rolling-origin folds × 180 test days, 5 seeds for the stochastic models, "
    "Diebold–Mariano tests with Holm correction. Two targets: **total** admissions and **urgent** (non-elective) "
    "admissions. Environmental covariates come from CETESB/QUALAR (PM2.5, other pollutants, meteorology)."
)
ui.aviso_provisorio()

# --- Key figures (every one read from a file) -------------------------------------------------
meta_total = dados.carregar_meta_alvo("total")
meta_urg = dados.carregar_meta_alvo("urgencia")
arcal = dados.tabela_arcal("total")
h1 = arcal[(arcal["h"] == 1) & (~arcal["modelo"].isin(["Naïve", "Seasonal Naïve"]))].sort_values("MAE")
melhor = h1.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Days in the series", f"{meta_total['dias']:,}")
c2.metric("Distinct AIH (total target)", f"{meta_total['total_aih_distintas']:,}")
c3.metric("Distinct AIH (urgent target)", f"{meta_urg['total_aih_distintas']:,}")
c4.metric(
    f"Best MAE at h = 1 ({melhor['modelo']}, AR_CAL)",
    f"{melhor['MAE']:.2f}",
    f"MASE {melhor['MASE']:.3f}",
    delta_color="off",
)
ui.fonte(
    dados.rel_meta_alvo("total"),
    dados.rel_meta_alvo("urgencia"),
    dados.REL_ARCAL_DOIS_ALVOS,
    run=melhor["run"],
)

# --- Navigation ------------------------------------------------------------------------------
st.subheader("Pages")
st.page_link("pages/1_Overview.py", label="Overview — target series, fold test windows and PM2.5", icon="📈")
st.page_link(
    "pages/2_Models_by_horizon.py", label="Models by horizon — MAE, MASE, skill, ablation and DM tests", icon="📊"
)
st.page_link("pages/3_The_Saturday_case.py", label="The Saturday case — why the urgent target exists", icon="📅")
st.page_link(
    "pages/4_Data_and_limitations.py", label="Data and limitations — sources, rules, what is not here", icon="📚"
)

st.subheader("Runs behind the numbers")
runs = dados.carregar_runs_por_horizonte()
tab = (
    dados.pd.DataFrame(
        [{"target": alvo, "h": h, "run_id": run} for alvo, por_h in runs.items() for h, run in por_h.items()]
    )
    .sort_values(["target", "h"])
    .reset_index(drop=True)
)
st.dataframe(tab, hide_index=True, width="stretch")
ui.fonte(dados.REL_PROVENIENCIA_URG)

st.markdown(
    "**How to read the metrics.** MASE divides a model's MAE by the Naïve MAE *of the same horizon*, so it compares "
    "models **within** one h only. Across horizons use MAE and *skill vs. reference* "
    "(1 − MAE / min(MAE Naïve, MAE Seasonal Naïve))."
)

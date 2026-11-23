"""Home — daily forecasting of respiratory hospital admissions in São Paulo city (ICD-10 J00–J99)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dados  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402
from i18n import fmt_num, t  # noqa: E402

ui.configurar_pagina("home.titulo_aba", "🏥")

st.title(t("home.titulo"))
st.markdown(t("home.intro"))
ui.aviso_provisorio()

# --- Key figures (every one read from a file) -------------------------------------------------
meta_total = dados.carregar_meta_alvo("total")
meta_urg = dados.carregar_meta_alvo("urgencia")
arcal = dados.tabela_arcal("total")
h1 = arcal[(arcal["h"] == 1) & (~arcal["modelo"].isin(["Naïve", "Seasonal Naïve"]))].sort_values("MAE")
melhor = h1.iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric(t("home.kpi_dias"), fmt_num(meta_total["dias"], 0))
c2.metric(t("home.kpi_aih_total"), fmt_num(meta_total["total_aih_distintas"], 0))
c3.metric(t("home.kpi_aih_urg"), fmt_num(meta_urg["total_aih_distintas"], 0))
c4.metric(
    t("home.kpi_melhor", modelo=melhor["modelo"]),
    fmt_num(melhor["MAE"], 2),
    f"MASE {fmt_num(melhor['MASE'], 3)} · AR_CAL",
    delta_color="off",
)
ui.fonte(
    dados.rel_meta_alvo("total"),
    dados.rel_meta_alvo("urgencia"),
    dados.REL_ARCAL_DOIS_ALVOS,
    run=melhor["run"],
)

# --- Navigation ------------------------------------------------------------------------------
st.subheader(t("home.paginas"))
st.page_link("pages/1_Overview.py", label=t("home.link_overview"), icon="📈")
st.page_link("pages/2_Models_by_horizon.py", label=t("home.link_modelos"), icon="📊")
st.page_link("pages/3_The_Saturday_case.py", label=t("home.link_sabado"), icon="📅")
st.page_link("pages/4_Data_and_limitations.py", label=t("home.link_dados"), icon="📚")

st.subheader(t("home.runs"))
runs = dados.carregar_runs_por_horizonte()
col_alvo = t("home.col_target")
tab = (
    dados.pd.DataFrame(
        [{col_alvo: alvo, "h": h, "run_id": run} for alvo, por_h in runs.items() for h, run in por_h.items()]
    )
    .sort_values([col_alvo, "h"])
    .reset_index(drop=True)
)
st.dataframe(tab, hide_index=True, width="stretch")
ui.fonte(dados.REL_PROVENIENCIA_URG)

st.markdown(t("home.como_ler"))

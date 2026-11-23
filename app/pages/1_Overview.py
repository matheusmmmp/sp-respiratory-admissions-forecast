"""Overview — target series, fold test windows and PM2.5."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dados  # noqa: E402
import graficos as g  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402

ui.configurar_pagina("Overview", "📈")
st.title("Overview — the target series and the test windows")
ui.aviso_provisorio()

m = g.modo()
c = g.CHROME[m]

alvo = st.radio("Target", options=list(dados.ALVOS), format_func=dados.ALVOS.get, horizontal=True, key="ov_alvo")
serie = dados.carregar_alvo(alvo)
meta = dados.carregar_meta_alvo(alvo)
run_h1 = dados.run_de(alvo, 1)
folds = dados.carregar_folds(run_h1)

# --- Key figures ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Days", f"{meta['dias']:,}")
c2.metric("Distinct AIH (2019–2024)", f"{meta['total_aih_distintas']:,}")
c3.metric("Mean admissions / day", f"{serie['internacoes'].mean():.1f}")
c4.metric("Days with zero admissions", f"{meta['dias_com_zero']:,}")
ui.fonte(dados.rel_alvo(alvo), dados.rel_meta_alvo(alvo), nota="mean computed from the parquet series")

# --- Daily series with fold test windows ----------------------------------------------------
st.subheader("Daily admissions and the four fold test windows")
fig = go.Figure()
cor_alvo = g.cores_series(m)["nao_eletivo" if alvo == "urgencia" else "total"]
if alvo == "total":
    cor_alvo = g.SLOTS[m][0]
fig.add_scatter(
    x=serie.index,
    y=serie["internacoes"],
    name="Admissions / day",
    mode="lines",
    line=dict(color=cor_alvo, width=1.5),
    hovertemplate="%{y} admissions<extra></extra>",
)
for _, f in folds.iterrows():
    fig.add_vrect(
        x0=f["teste_inicio"],
        x1=f["teste_fim"],
        fillcolor=g.SLOTS[m][1],
        opacity=0.10 if int(f["fold"]) % 2 else 0.18,
        line_width=0,
        annotation_text=f"fold {int(f['fold'])}",
        annotation_position="top left",
        annotation_font=dict(color=c["text2"], size=11),
    )
g.layout(fig, y="Admissions / day", hover="x unified", altura=400, legenda=False, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_serie")
ui.fonte(
    dados.rel_alvo(alvo),
    dados.rel_run(run_h1, "folds.csv"),
    run=run_h1,
    nota="shaded = test window of each fold (same dates in every run)",
)

with st.expander("Fold table (training / validation / test dates)"):
    st.dataframe(folds, hide_index=True, width="stretch")
    ui.fonte(dados.rel_run(run_h1, "folds.csv"), run=run_h1)

# --- Annual totals -----------------------------------------------------------------------
st.subheader("Admissions per year")
anuais = pd.Series(meta["totais_anuais"]).rename_axis("year").reset_index(name="admissions")
fig = go.Figure(
    go.Bar(
        x=anuais["year"].astype(str),
        y=anuais["admissions"],
        marker=dict(color=cor_alvo, cornerradius=4),
        width=0.22,
        text=[f"{v:,}" for v in anuais["admissions"]],
        textposition="outside",
        textfont=dict(color=c["text2"]),
        hovertemplate="%{x}: %{y:,} admissions<extra></extra>",
    )
)
g.layout(fig, y="Admissions / year", hover="closest", altura=320, legenda=False, m=m)
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_anuais")
ui.fonte(dados.rel_meta_alvo(alvo), nota="field `totais_anuais`")

# --- PM2.5 -------------------------------------------------------------------------------
st.subheader("PM2.5 — daily mean over CETESB stations in São Paulo city")
pm = dados.carregar_pm25()
meta_pm = dados.carregar_meta_poluentes()
fig = go.Figure()
fig.add_scatter(
    x=pm.index,
    y=pm["pm25_media"],
    name="PM2.5 daily mean (µg/m³)",
    mode="lines",
    line=dict(color=g.SLOTS[m][2], width=1.5),
    customdata=pm["pm25_n_estacoes"],
    hovertemplate="%{y:.1f} µg/m³ · %{customdata} stations<extra></extra>",
)
g.layout(fig, y="PM2.5 (µg/m³)", hover="x unified", altura=340, legenda=False, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_pm25")
ui.fonte(dados.REL_POLUENTES, dados.REL_META_POLUENTES, nota=f"daily rule: {meta_pm['regra_diaria']}")

c1, c2, c3 = st.columns(3)
c1.metric("Mean PM2.5 (µg/m³)", f"{pm['pm25_media'].mean():.1f}")
c2.metric("Mean stations / day", f"{pm['pm25_n_estacoes'].mean():.1f}")
c3.metric("Days without a valid station", f"{int(pm['pm25_media'].isna().sum()):,}")
ui.fonte(dados.REL_POLUENTES, nota="computed from the csv columns pm25_media and pm25_n_estacoes")

# --- How the series were built -------------------------------------------------------------
with st.expander("How the target series is built (from the .meta.json next to the parquet)"):
    chaves = [
        "fonte",
        "dataset",
        "criterio_espacial",
        "campo_data",
        "campo_cid",
        "regra_cid",
        "regra_contagem",
        "periodo_epidemiologico",
        "periodo_administrativo",
        "look_ahead_competencias",
        "look_ahead_justificativa",
        "total_linhas_somadas",
        "total_aih_distintas",
        "duplicatas_entre_competencias",
        "registros_fora_do_periodo",
        "dias",
        "dias_com_zero",
        "extraido_em",
    ]
    if "filtro_carater_internacao" in meta:
        chaves.insert(7, "filtro_carater_internacao")
    st.json({k: meta[k] for k in chaves if k in meta})
    ui.fonte(dados.rel_meta_alvo(alvo))

with st.expander("How the PM2.5 series is built (from cetesb_poluentes_daily.meta.json)"):
    pm25_info = [p for p in meta_pm.get("por_poluente", []) if p.get("poluente") == "pm25"]
    st.json(
        {
            "fonte": meta_pm["fonte"],
            "regra_diaria": meta_pm["regra_diaria"],
            "regra_dt": meta_pm["regra_dt"],
            "limitacao_valido": meta_pm["limitacao_valido"],
            "extraido_em": meta_pm["extraido_em"],
            "pm25": pm25_info,
        }
    )
    ui.fonte(dados.REL_META_POLUENTES)

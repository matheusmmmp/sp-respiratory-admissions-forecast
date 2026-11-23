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
from i18n import fmt_num, t  # noqa: E402

ui.configurar_pagina("ov.titulo_aba", "📈")
st.title(t("ov.titulo"))
ui.aviso_provisorio()

m = g.modo()
c = g.CHROME[m]

alvo = st.radio(
    t("alvo.rotulo"),
    options=list(dados.ALVOS),
    format_func={a: t(f"alvo.{a}") for a in dados.ALVOS}.get,
    horizontal=True,
    key="ov_alvo",
)
serie = dados.carregar_alvo(alvo)
meta = dados.carregar_meta_alvo(alvo)
run_h1 = dados.run_de(alvo, 1)
folds = dados.carregar_folds(run_h1)

# --- Key figures ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric(t("ov.kpi_dias"), fmt_num(meta["dias"], 0))
c2.metric(t("ov.kpi_aih"), fmt_num(meta["total_aih_distintas"], 0))
c3.metric(t("ov.kpi_media"), fmt_num(serie["internacoes"].mean(), 1))
c4.metric(t("ov.kpi_zero"), fmt_num(meta["dias_com_zero"], 0))
ui.fonte(dados.rel_alvo(alvo), dados.rel_meta_alvo(alvo), nota=t("ov.nota_media"))

# --- Daily series with fold test windows ----------------------------------------------------
st.subheader(t("ov.sub_serie"))
fig = go.Figure()
cor_alvo = g.cores_series(m)["nao_eletivo" if alvo == "urgencia" else "total"]
if alvo == "total":
    cor_alvo = g.SLOTS[m][0]
fig.add_scatter(
    x=serie.index,
    y=serie["internacoes"],
    name=t("unid.internacoes_dia"),
    mode="lines",
    line=dict(color=cor_alvo, width=1.5),
    hovertemplate=t("ov.hover_serie") + "<extra></extra>",
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
g.layout(fig, y=t("unid.internacoes_dia"), hover="x unified", altura=400, legenda=False, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_serie")
ui.fonte(dados.rel_alvo(alvo), dados.rel_run(run_h1, "folds.csv"), run=run_h1, nota=t("ov.nota_folds"))

with st.expander(t("ov.exp_folds")):
    st.dataframe(folds, hide_index=True, width="stretch")
    ui.fonte(dados.rel_run(run_h1, "folds.csv"), run=run_h1)

# --- Annual totals -----------------------------------------------------------------------
st.subheader(t("ov.sub_anual"))
anuais = pd.Series(meta["totais_anuais"]).rename_axis("year").reset_index(name="admissions")
fig = go.Figure(
    go.Bar(
        x=anuais["year"].astype(str),
        y=anuais["admissions"],
        marker=dict(color=cor_alvo, cornerradius=4),
        width=0.22,
        text=[fmt_num(v, 0) for v in anuais["admissions"]],
        textposition="outside",
        textfont=dict(color=c["text2"]),
        hovertemplate=t("ov.hover_anual") + "<extra></extra>",
    )
)
g.layout(fig, y=t("ov.eixo_anual"), hover="closest", altura=320, legenda=False, m=m)
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_anuais")
ui.fonte(dados.rel_meta_alvo(alvo), nota=t("ov.nota_anual"))

# --- PM2.5 -------------------------------------------------------------------------------
st.subheader(t("ov.sub_pm25"))
pm = dados.carregar_pm25()
meta_pm = dados.carregar_meta_poluentes()
fig = go.Figure()
fig.add_scatter(
    x=pm.index,
    y=pm["pm25_media"],
    name=t("ov.serie_pm25"),
    mode="lines",
    line=dict(color=g.SLOTS[m][2], width=1.5),
    customdata=pm["pm25_n_estacoes"],
    hovertemplate=t("ov.hover_pm25") + "<extra></extra>",
)
g.layout(fig, y=t("ov.eixo_pm25"), hover="x unified", altura=340, legenda=False, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="ov_pm25")
ui.fonte(dados.REL_POLUENTES, dados.REL_META_POLUENTES, nota=t("ov.nota_regra", regra=meta_pm["regra_diaria"]))

c1, c2, c3 = st.columns(3)
c1.metric(t("ov.kpi_pm25"), fmt_num(pm["pm25_media"].mean(), 1))
c2.metric(t("ov.kpi_estacoes"), fmt_num(pm["pm25_n_estacoes"].mean(), 1))
c3.metric(t("ov.kpi_sem_estacao"), fmt_num(int(pm["pm25_media"].isna().sum()), 0))
ui.fonte(dados.REL_POLUENTES, nota=t("ov.nota_pm25"))

# --- How the series were built -------------------------------------------------------------
with st.expander(t("ov.exp_alvo")):
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

with st.expander(t("ov.exp_pm25")):
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

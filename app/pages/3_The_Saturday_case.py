"""The Saturday case — elective surgery campaigns on Saturdays and why the urgent target exists.

Port of the sections of `notebooks/gerar_notebook.py` (panel `painel_carater_internacao.ipynb`), reading only
the aggregates in `notebooks/dados_painel/`. Decision D7 (extended 2026-11-23): the establishment may be cited by
name and CNES code together ("Instituto CEMA", CNES 2091550); the name is read from the csv, never typed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dados  # noqa: E402
import graficos as g  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402
from i18n import fmt_num, t  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

ui.configurar_pagina("sab.titulo_aba", "📅")
st.title(t("sab.titulo"))
ui.aviso_provisorio()
st.markdown(t("sab.intro"))

m = g.modo()
c = g.CHROME[m]
cs = g.cores_series(m)
cm = g.cores_modelos(m)
DOW = t("dow")
MESES = t("meses")
NEUTRO = c["muted"]

D = dados.carregar_painel_diario().copy()
MAN = dados.carregar_painel_manifest()
D["total_sem_cema"] = D["total"] - D["cema"]
D["dow"] = D.index.dayofweek
REL_DIARIO = dados.rel_painel("diario.csv")
REL_MANIFEST = dados.rel_painel("manifest.json")


def razao(s: pd.Series) -> pd.Series:
    """y / local level (centred 29-day rolling median, >= 15 obs)."""
    return s / s.rolling(29, center=True, min_periods=15).median()


# --- 1. Overview ---------------------------------------------------------------------------
st.header(t("sab.h1"))
r_tot, r_ne = razao(D["total"]), razao(D["nao_eletivo"])
sab22 = (D["dow"] == 5) & (D.index.year >= 2022)
k1, k2, k3, k4 = st.columns(4)
k1.metric(t("sab.kpi_total"), fmt_num(int(D["total"].sum()), 0))
k2.metric(t("sab.kpi_media"), fmt_num(D["total"].mean(), 1))
k3.metric(t("sab.kpi_eletivas"), fmt_num(100 * D["eletivo"].sum() / D["total"].sum(), 1) + "%")
k4.metric(t("sab.kpi_atipicos"), f"{int((r_tot[sab22] > 1.3).sum())} → {int((r_ne[sab22] > 1.3).sum())}")
ui.fonte(REL_DIARIO, nota=t("sab.nota_atipicos"))

s = D[["total", "nao_eletivo", "eletivo"]].resample("W").mean()
fig = go.Figure()
for col in ["total", "nao_eletivo", "eletivo"]:
    fig.add_scatter(
        x=s.index,
        y=s[col],
        name=t(f"serie.{col}"),
        mode="lines",
        line=dict(color=cs[col], width=2),
        hovertemplate="%{y:.1f}<extra>" + t(f"serie.{col}") + "</extra>",
    )
g.layout(fig, titulo=t("sab.fig_semanal"), y=t("unid.internacoes_dia"), altura=380, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_semanal")
ui.fonte(REL_DIARIO, nota=t("sab.nota_painel", quando=MAN["gerado_em"]))

# --- 2. Day of week -------------------------------------------------------------------------
st.header(t("sab.h2"))
anual = D.groupby([D.index.year, "dow"])["total"].mean().unstack()
fig = go.Figure(
    go.Heatmap(
        z=anual.values,
        x=DOW,
        y=[str(a) for a in anual.index],
        colorscale=g.escala_sequencial(m),
        xgap=2,
        ygap=2,
        text=anual.round(0).values,
        texttemplate="%{text:.0f}",
        textfont=dict(size=11),
        colorbar=dict(title=t("unid.adm_dia_curto"), tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate=t("sab.hover_dow") + "<extra></extra>",
    )
)
g.layout(fig, titulo=t("sab.fig_dow"), hover="closest", altura=360, legenda=False, m=m)
fig.update_layout(margin=dict(l=70))
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="sab_heat_dow")
ui.fonte(REL_DIARIO)

PERIODOS = {"per_2022": ("2022", "2026"), "per_2019": ("2019", "2021"), "per_tudo": ("2019", "2026")}
periodo = st.radio(
    t("sab.periodo"),
    options=list(PERIODOS),
    format_func={p: t(f"sab.{p}") for p in PERIODOS}.get,
    horizontal=True,
    key="sab_periodo",
)
ini, fim = PERIODOS[periodo]
linhas = []
for col in ["total", "nao_eletivo"]:
    r = razao(D[col])[ini:fim]
    for i, dn in enumerate(DOW):
        x = r[r.index.dayofweek == i]
        linhas.append(dict(dia=dn, serie=col, iqr=x.quantile(0.75) - x.quantile(0.25), atipicos=int((x > 1.3).sum())))
tt = pd.DataFrame(linhas)
fig = go.Figure()
for col in ["total", "nao_eletivo"]:
    d = tt[tt["serie"] == col]
    fig.add_bar(
        x=d["dia"],
        y=d["iqr"],
        name=t(f"serie.{col}"),
        marker=dict(color=cs[col], cornerradius=4),
        customdata=d["atipicos"],
        hovertemplate=t("sab.hover_iqr") + "<extra>" + t(f"serie.{col}") + "</extra>",
    )
g.layout(
    fig, titulo=t("sab.fig_iqr", periodo=t(f"sab.{periodo}")), y=t("sab.eixo_iqr"), hover="closest", altura=360, m=m
)
fig.update_layout(barmode="group", bargap=0.4)
g.mostrar(fig, key="sab_iqr")
ui.fonte(REL_DIARIO, nota=t("sab.nota_iqr"))

# --- 3. Saturdays and CNES 2091550 ----------------------------------------------------------
st.header(t("sab.h3"))
sab = D[D["dow"] == 5]
fig = go.Figure()
fig.add_scatter(
    x=sab.index,
    y=sab["total_sem_cema"],
    name=t("sab.sem_cema"),
    mode="lines",
    line=dict(color=cs["nao_eletivo"], width=2),
    hovertemplate="%{y}<extra>" + t("sab.sem_cema") + "</extra>",
)
fig.add_scatter(
    x=sab.index,
    y=sab["total"],
    name=t("sab.todos_estab"),
    mode="lines",
    fill="tonexty",
    fillcolor=cs["cema"] + "33",
    line=dict(color=cs["total"], width=2),
    hovertemplate="%{y}<extra>" + t("sab.todos_estab") + "</extra>",
)
g.layout(fig, titulo=t("sab.fig_cema"), y=t("sab.eixo_sabado"), altura=380, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_cema_serie")
ui.fonte(REL_DIARIO, nota=t("sab.nota_cema", cnes=MAN["cnes_destacado"]))

rs = razao(D["total"])[D["dow"] == 5].to_frame("r")
rs["semana"] = (rs.index.day - 1) // 7 + 1
rs["periodo"] = np.where(rs.index.year <= 2021, "per_2019", "per_2022")
tt = rs.groupby(["periodo", "semana"])["r"].median().reset_index()
fig = go.Figure()
for per, cor in [("per_2019", NEUTRO), ("per_2022", cs["eletivo"])]:
    d = tt[tt["periodo"] == per]
    fig.add_bar(
        x=[t(f"sab.ord{int(k)}") for k in d["semana"]],
        y=d["r"],
        name=t(f"sab.{per}"),
        marker=dict(color=cor, cornerradius=4),
        hovertemplate=t("sab.hover_razao") + "<extra>" + t(f"sab.{per}") + "</extra>",
    )
fig.add_hline(y=1, line=dict(color=c["axis"], width=1))
g.layout(fig, titulo=t("sab.fig_semana_mes"), y=t("sab.eixo_razao"), hover="closest", altura=340, m=m)
fig.update_layout(barmode="group", bargap=0.4)
g.mostrar(fig, key="sab_semana_mes")
ui.fonte(REL_DIARIO, nota=t("sab.nota_razao"))

cal = sab[["cema"]].rename(columns={"cema": "n"}).copy()
cal["ano"] = cal.index.year.astype(str)
cal["coluna"] = [f"{MESES[d.month - 1]}-{(d.day - 1) // 7 + 1}" for d in cal.index]
ordem = [f"{mm}-{k}" for mm in MESES for k in range(1, 6)]
piv = cal.pivot_table(index="ano", columns="coluna", values="n", aggfunc="sum").reindex(
    columns=[o for o in ordem if o in set(cal["coluna"])]
)
fig = go.Figure(
    go.Heatmap(
        z=piv.values,
        x=piv.columns,
        y=piv.index,
        colorscale=g.escala_sequencial(m, "laranja"),
        xgap=2,
        ygap=2,
        colorbar=dict(title=t("sab.colorbar_int"), tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate=t("sab.hover_cal") + "<extra></extra>",
    )
)
g.layout(fig, titulo=t("sab.fig_cal"), hover="closest", altura=320, legenda=False, m=m)
fig.update_xaxes(showgrid=False, tickangle=-90, tickfont=dict(size=9))
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="sab_calendario")
ui.fonte(REL_DIARIO, nota=t("sab.nota_cal"))

st.markdown(t("sab.atraso"))
at = dados.carregar_painel_atraso().copy()
at.index = DOW[: len(at)]
ui.tabela(at.rename(columns=lambda k: t("sab.col_meses", k=k)), casas=1, width="stretch")
ui.fonte(dados.rel_painel("atraso_registro_2022_mais.csv"))

# --- 4. Character of admission and ICD groups ----------------------------------------------
st.header(t("sab.h4"))
G = dados.carregar_painel_grupos_cid().copy()
G["pct"] = 100 * G["eletivas"] / G["total"]
G = G.sort_values("pct")
fig = go.Figure()
for sens, nome, cor in [(True, t("sab.mecanismo"), cs["nao_eletivo"]), (False, t("sab.outros_grupos"), NEUTRO)]:
    d = G[G["sensivel"] == sens]
    fig.add_bar(
        x=d["pct"],
        y=d["grupo"],
        orientation="h",
        name=nome,
        marker=dict(color=cor, cornerradius=4),
        width=0.6,
        customdata=np.stack([d["eletivas"], d["total"], d["eletivas_cema"]], axis=1),
        hovertemplate=t("sab.hover_cid") + "<extra>" + nome + "</extra>",
    )
g.layout(fig, titulo=t("sab.fig_cid"), x=t("sab.eixo_cid"), hover="closest", altura=460, m=m)
fig.update_xaxes(range=[0, 100], ticksuffix="%")
fig.update_layout(barmode="overlay", margin=dict(l=300))
g.mostrar(fig, key="sab_cid")
sens = G[G["sensivel"]]
st.markdown(
    t(
        "sab.texto_sensiveis",
        eletivas=fmt_num(int(sens["eletivas"].sum()), 0),
        total=fmt_num(int(sens["total"].sum()), 0),
        pct=fmt_num(100 * sens["eletivas"].sum() / sens["total"].sum(), 1),
        cema=fmt_num(int(sens["eletivas_cema"].sum()), 0),
    )
)
ui.fonte(dados.rel_painel("grupos_cid.csv"))

mm_ = D[["sens_nao_eletivo", "sens_eletivo"]].resample("MS").mean()
corr = mm_["2019":"2024"].corr().iloc[0, 1]
fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.10,
    subplot_titles=(t("sab.sub_nao_eletivas"), t("sab.sub_eletivas")),
)
fig.add_scatter(
    x=mm_.index,
    y=mm_["sens_nao_eletivo"],
    row=1,
    col=1,
    name=t("sab.nao_eletivas"),
    mode="lines",
    line=dict(color=cs["nao_eletivo"], width=2),
    hovertemplate="%{y:.1f}<extra>" + t("sab.nao_eletivas") + "</extra>",
)
fig.add_scatter(
    x=mm_.index,
    y=mm_["sens_eletivo"],
    row=2,
    col=1,
    name=t("sab.eletivas"),
    mode="lines",
    line=dict(color=cs["eletivo"], width=2),
    hovertemplate="%{y:.1f}<extra>" + t("sab.eletivas") + "</extra>",
)
g.layout(fig, titulo=t("sab.fig_sens", corr=fmt_num(corr, 2)), altura=480, legenda=False, m=m)
fig.update_yaxes(rangemode="tozero", title_text=t("unid.adm_dia_curto"))
fig.update_xaxes(tickformat="%m/%Y")
for ann in fig.layout.annotations:
    ann.font.color = c["text2"]
g.mostrar(fig, key="sab_sens")
ui.fonte(REL_DIARIO, nota=t("sab.nota_sens"))

st.markdown(t("sab.perfil"))
P = dados.carregar_painel_perfil().rename(
    columns={
        "internacoes": t("sab.col_internacoes"),
        "idade_mediana": t("sab.col_idade"),
        "pct_menor_15": t("sab.col_menor15"),
        "permanencia_mediana": t("sab.col_permanencia"),
        "pct_permanencia_ate_1_dia": t("sab.col_perm1"),
        "pct_obito": t("sab.col_obito"),
    }
)
ui.tabela(P, casas=1, width="stretch")
ui.fonte(dados.rel_painel("perfil.csv"))

# --- 5. Establishments ---------------------------------------------------------------------
st.header(t("sab.h5"))
E = dados.carregar_painel_estabelecimentos()
METRICAS_ESTAB = {"met_eletivas_sab": "eletivas_sabado", "met_eletivas": "eletivas", "met_total": "total"}
metrica = st.radio(
    t("metrica"),
    options=list(METRICAS_ESTAB),
    format_func={k: t(f"sab.{k}") for k in METRICAS_ESTAB}.get,
    horizontal=True,
    key="sab_estab",
)
col = METRICAS_ESTAB[metrica]
nome_metrica = t(f"sab.{metrica}")
fig = go.Figure()
for cnes, d in E.sort_values("ano").groupby("CNES"):
    destaque = cnes == MAN["cnes_destacado"]
    fig.add_scatter(
        x=d["ano"].astype(str),
        y=d[col],
        name=f"CNES {cnes}",
        mode="lines+markers",
        line=dict(color=cs["cema"] if destaque else NEUTRO, width=3 if destaque else 1.5),
        marker=dict(size=8 if destaque else 6, line=dict(width=2, color=c["surface"])),
        opacity=1 if destaque else 0.55,
        hovertemplate="%{y:,}<extra>CNES " + cnes + "</extra>",
    )
g.layout(
    fig,
    titulo=t("sab.fig_estab", metrica=nome_metrica, cnes=MAN["cnes_destacado"]),
    y=t("sab.eixo_estab", metrica=nome_metrica),
    hover="closest",
    altura=440,
    m=m,
)
fig.update_layout(legend=dict(orientation="v", x=1.01, y=1, yanchor="top"))
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_estab_fig")
nome_destaque = E.loc[E["CNES"] == MAN["cnes_destacado"], "nome"].iloc[0]
ui.fonte(dados.rel_painel("estabelecimentos_ano.csv"), nota=t("sab.nota_estab", nome=nome_destaque))

# --- 6. Effect on the models ----------------------------------------------------------------
st.header(t("sab.h6"))
M = dados.carregar_painel_erros_modelos().copy()
M["dow"] = M["target_date"].dt.dayofweek
M["mutirao"] = (M["dow"] == 5) & ((M["target_date"].dt.day - 1) // 7 < 3) & (M["target_date"].dt.year >= 2022)
c1, c2 = st.columns(2)
h_sel = c1.radio(
    t("horizonte"), options=sorted(M["h"].unique()), format_func=lambda h: f"h = {h}", horizontal=True, key="sab_h"
)
metr = c2.radio(
    t("metrica"),
    options=["met_mae", "met_vies"],
    format_func={k: t(f"sab.{k}") for k in ("met_mae", "met_vies")}.get,
    horizontal=True,
    key="sab_metr",
)
x = M[M["h"] == h_sel]
run_x = x["run"].iloc[0]
if metr == "met_mae":
    tt = x.assign(v=x["erro"].abs()).groupby(["modelo", "dow"])["v"].mean().reset_index()
    rot = t("mh.eixo_mae")
else:
    tt = x.groupby(["modelo", "dow"])["erro"].mean().reset_index().rename(columns={"erro": "v"})
    rot = t("sab.eixo_vies")
fig = go.Figure()
for nome in g.ORDEM_MODELOS:
    d = tt[tt["modelo"] == nome].sort_values("dow")
    if d.empty:
        continue
    fig.add_bar(
        x=[DOW[i] for i in d["dow"]],
        y=d["v"],
        name=nome,
        marker=dict(color=cm[nome], cornerradius=3),
        hovertemplate="%{y:.2f}<extra>" + nome + "</extra>",
    )
g.layout(fig, titulo=t("sab.fig_modelos", metrica=t(f"sab.{metr}"), h=h_sel), y=rot, hover="closest", altura=400, m=m)
fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.1)
g.mostrar(fig, key="sab_modelos")
ui.fonte(dados.rel_painel("erros_modelos_ar_cal.csv"), run=run_x, nota=t("sab.nota_modelos"))

# Nota sobre a definição do MAE: os quatro números são lidos/calculados dos arquivos, nunca digitados.
es_bruto = dados.carregar_erro_sabado_h1()
arcal_h1 = dados.carregar_arcal_dois_alvos()
ref_sab = es_bruto[(es_bruto["alvo"] == "total") & (es_bruto["modelo"] == "XGBoost")]["MAE_sab"].iloc[0]
ref_geral = arcal_h1[(arcal_h1["alvo"] == "total") & (arcal_h1["h"] == 1) & (arcal_h1["modelo"] == "XGBoost")][
    "MAE"
].iloc[0]
x1 = M[(M["h"] == 1) & (M["modelo"] == "XGBoost")]
aqui_geral = x1["erro"].abs().mean()
aqui_sab = x1.loc[x1["dow"] == 5, "erro"].abs().mean()
st.caption(
    t(
        "sab.nota_mae_def",
        ref_geral=fmt_num(ref_geral, 2),
        ref_sab=fmt_num(ref_sab, 2),
        aqui_geral=fmt_num(aqui_geral, 2),
        aqui_sab=fmt_num(aqui_sab, 2),
    )
)

part = (
    x.assign(a=x["erro"].abs())
    .groupby("modelo")
    .apply(
        lambda d: pd.Series(
            {
                "MAE": d["a"].mean(),
                t("sab.col_mae_fora"): d["a"][~d["mutirao"]].mean(),
                t("sab.col_pct_erro"): 100 * d["a"][d["mutirao"]].sum() / d["a"].sum(),
                t("sab.col_pct_datas"): 100 * d["mutirao"].mean(),
            }
        ),
        include_groups=False,
    )
    .reindex([n for n in g.ORDEM_MODELOS if n in set(tt["modelo"])])
)
st.markdown(t("sab.quanto_erro"))
ui.tabela(part, casas=1, width="stretch")
ui.fonte(dados.rel_painel("erros_modelos_ar_cal.csv"), run=run_x)

st.markdown(t("sab.erro_h1"))
es = es_bruto.rename(
    columns={
        "alvo": t("sab.col_alvo"),
        "modelo": t("sab.col_modelo"),
        "MAE_sab": t("sab.col_mae_sab"),
        "MAE_demais": t("sab.col_mae_demais"),
        "frac_erro_sab": t("sab.col_frac"),
        "razao": t("sab.col_razao"),
    }
)
ui.tabela(es, casas=3, hide_index=True, width="stretch")
runs_h1 = dados.carregar_runs_por_horizonte()
ui.fonte(
    dados.REL_ERRO_SABADO_H1, nota=t("sab.nota_erro_h1", total=runs_h1["total"][1], urgencia=runs_h1["urgencia"][1])
)

# --- 7. The decision -----------------------------------------------------------------------
st.header(t("sab.h7"))
st.markdown(t("sab.decisao"))
with st.expander(t("sab.exp_manifest")):
    st.json(MAN)
    ui.fonte(REL_MANIFEST)

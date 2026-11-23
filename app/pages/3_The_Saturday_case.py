"""The Saturday case — elective surgery campaigns on Saturdays and why the urgent target exists.

Port of the sections of `notebooks/gerar_notebook.py` (panel `painel_carater_internacao.ipynb`), reading only
the aggregates in `notebooks/dados_painel/`. Decision D7: the establishment is cited by its CNES code (2091550).
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
from plotly.subplots import make_subplots  # noqa: E402

ui.configurar_pagina("The Saturday case", "📅")
st.title("The Saturday case")
ui.aviso_provisorio()
st.markdown(
    "Since 2022 the daily count of respiratory admissions shows **Saturday spikes** that no environmental or "
    "epidemiological signal explains. They are **elective surgery campaigns** (mostly tonsils/adenoids, J35, and "
    "nasal septum, J34) concentrated in one establishment, **CNES 2091550**. The admission character recorded in "
    "the AIH (`CAR_INT`) separates them cleanly, which is why a second target — **urgent = non-elective** — exists. "
    "Descriptive reading, no formal test. For 2025–2026 the target has not yet been checked against TabNet."
)

m = g.modo()
c = g.CHROME[m]
cs = g.cores_series(m)
cm = g.cores_modelos(m)
DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MESES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
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
st.header("1. Three series in one target")
r_tot, r_ne = razao(D["total"]), razao(D["nao_eletivo"])
sab22 = (D["dow"] == 5) & (D.index.year >= 2022)
k1, k2, k3, k4 = st.columns(4)
k1.metric("Admissions (Jan 2019 – Feb 2026)", f"{int(D['total'].sum()):,}")
k2.metric("Mean per day", f"{D['total'].mean():.1f}")
k3.metric("Elective share of the total target", f"{100 * D['eletivo'].sum() / D['total'].sum():.1f}%")
k4.metric(
    "Atypical Saturdays 2022+ (total → urgent)", f"{int((r_tot[sab22] > 1.3).sum())} → {int((r_ne[sab22] > 1.3).sum())}"
)
ui.fonte(REL_DIARIO, nota="atypical = 30% or more above the local level (centred 29-day rolling median)")

s = D[["total", "nao_eletivo", "eletivo"]].resample("W").mean()
fig = go.Figure()
for col in ["total", "nao_eletivo", "eletivo"]:
    fig.add_scatter(
        x=s.index,
        y=s[col],
        name=g.NOME_SERIE[col],
        mode="lines",
        line=dict(color=cs[col], width=2),
        hovertemplate="%{y:.1f}<extra>" + g.NOME_SERIE[col] + "</extra>",
    )
g.layout(fig, titulo="Weekly mean of admissions per day", y="Admissions / day", altura=380, m=m)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_semanal")
ui.fonte(REL_DIARIO, nota=f"panel generated {MAN['gerado_em']}")

# --- 2. Day of week -------------------------------------------------------------------------
st.header("2. Day of the week")
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
        colorbar=dict(title="Adm./day", tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate="%{y} · %{x}: %{z:.1f} admissions/day<extra></extra>",
    )
)
g.layout(
    fig,
    titulo="Mean admissions per day, by weekday and year (total target)",
    hover="closest",
    altura=360,
    legenda=False,
    m=m,
)
fig.update_layout(margin=dict(l=70))
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="sab_heat_dow")
ui.fonte(REL_DIARIO)

periodo = st.radio("Period", options=["2022–Feb 2026", "2019–2021", "All"], horizontal=True, key="sab_periodo")
ini, fim = {"2019–2021": ("2019", "2021"), "2022–Feb 2026": ("2022", "2026"), "All": ("2019", "2026")}[periodo]
linhas = []
for col in ["total", "nao_eletivo"]:
    r = razao(D[col])[ini:fim]
    for i, dn in enumerate(DOW):
        x = r[r.index.dayofweek == i]
        linhas.append(dict(dia=dn, serie=col, iqr=x.quantile(0.75) - x.quantile(0.25), atipicos=int((x > 1.3).sum())))
t = pd.DataFrame(linhas)
fig = go.Figure()
for col in ["total", "nao_eletivo"]:
    d = t[t["serie"] == col]
    fig.add_bar(
        x=d["dia"],
        y=d["iqr"],
        name=g.NOME_SERIE[col],
        marker=dict(color=cs[col], cornerradius=4),
        customdata=d["atipicos"],
        hovertemplate="IQR %{y:.3f} · %{customdata} days ≥ 30% above<extra>" + g.NOME_SERIE[col] + "</extra>",
    )
g.layout(
    fig,
    titulo=f"How much each weekday oscillates around the local level ({periodo})",
    y="Interquartile range of y / local level",
    hover="closest",
    altura=360,
    m=m,
)
fig.update_layout(barmode="group", bargap=0.4)
g.mostrar(fig, key="sab_iqr")
ui.fonte(REL_DIARIO, nota="ratio = y / centred 29-day rolling median; computed from diario.csv")

# --- 3. Saturdays and CNES 2091550 ----------------------------------------------------------
st.header("3. Saturdays and CNES 2091550")
sab = D[D["dow"] == 5]
fig = go.Figure()
fig.add_scatter(
    x=sab.index,
    y=sab["total_sem_cema"],
    name="Without CNES 2091550",
    mode="lines",
    line=dict(color=cs["nao_eletivo"], width=2),
    hovertemplate="%{y}<extra>without CNES 2091550</extra>",
)
fig.add_scatter(
    x=sab.index,
    y=sab["total"],
    name="All establishments",
    mode="lines",
    fill="tonexty",
    fillcolor=cs["cema"] + "33",
    line=dict(color=cs["total"], width=2),
    hovertemplate="%{y}<extra>all establishments</extra>",
)
g.layout(
    fig, titulo="Admissions on each Saturday (shaded = CNES 2091550)", y="Admissions per Saturday", altura=380, m=m
)
fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06), tickformat="%m/%Y")
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_cema_serie")
ui.fonte(REL_DIARIO, nota=f"highlighted establishment: CNES {MAN['cnes_destacado']} (manifest.json)")

rs = razao(D["total"])[D["dow"] == 5].to_frame("r")
rs["semana"] = (rs.index.day - 1) // 7 + 1
rs["periodo"] = np.where(rs.index.year <= 2021, "2019–2021", "2022–Feb 2026")
t = rs.groupby(["periodo", "semana"])["r"].median().reset_index()
fig = go.Figure()
for per, cor in [("2019–2021", NEUTRO), ("2022–Feb 2026", cs["eletivo"])]:
    d = t[t["periodo"] == per]
    fig.add_bar(
        x=[f"{int(s)}{'st' if s == 1 else 'nd' if s == 2 else 'rd' if s == 3 else 'th'} Saturday" for s in d["semana"]],
        y=d["r"],
        name=per,
        marker=dict(color=cor, cornerradius=4),
        hovertemplate="median ratio %{y:.2f}<extra>" + per + "</extra>",
    )
fig.add_hline(y=1, line=dict(color=c["axis"], width=1))
g.layout(
    fig,
    titulo="The peak falls on the first three Saturdays of the month (since 2022)",
    y="Median ratio (1 = ordinary day)",
    hover="closest",
    altura=340,
    m=m,
)
fig.update_layout(barmode="group", bargap=0.4)
g.mostrar(fig, key="sab_semana_mes")
ui.fonte(REL_DIARIO, nota="median of y / local level over the Saturdays of each rank within the month")

cal = sab[["cema"]].rename(columns={"cema": "n"}).copy()
cal["ano"] = cal.index.year.astype(str)
cal["coluna"] = [f"{MESES[d.month - 1]}-{(d.day - 1) // 7 + 1}" for d in cal.index]
ordem = [f"{mm}-{s}" for mm in MESES for s in range(1, 6)]
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
        colorbar=dict(title="Admissions", tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate="%{y} · %{x}: %{z} admissions<extra></extra>",
    )
)
g.layout(
    fig,
    titulo="Calendar: admissions of CNES 2091550 on each Saturday (month–rank of the Saturday)",
    hover="closest",
    altura=320,
    legenda=False,
    m=m,
)
fig.update_xaxes(showgrid=False, tickangle=-90, tickfont=dict(size=9))
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="sab_calendario")
ui.fonte(REL_DIARIO, nota="column `cema` = admissions of CNES 2091550")

st.markdown(
    "**Registration delay since 2022** — % of AIH by months between admission and the billing competence "
    "(4 = four or more). Saturday is not registered later than the other days:"
)
at = dados.carregar_painel_atraso().copy()
at.index = DOW[: len(at)]
ui.tabela(at.rename(columns=lambda k: f"{k} month(s)"), casas=1, width="stretch")
ui.fonte(dados.rel_painel("atraso_registro_2022_mais.csv"))

# --- 4. Character of admission and ICD groups ----------------------------------------------
st.header("4. Admission character and ICD-10 groups")
G = dados.carregar_painel_grupos_cid().copy()
G["pct"] = 100 * G["eletivas"] / G["total"]
G = G.sort_values("pct")
fig = go.Figure()
for sens, nome, cor in [
    (True, "Plausible mechanism of pollution effect", cs["nao_eletivo"]),
    (False, "Other groups", NEUTRO),
]:
    d = G[G["sensivel"] == sens]
    fig.add_bar(
        x=d["pct"],
        y=d["grupo"],
        orientation="h",
        name=nome,
        marker=dict(color=cor, cornerradius=4),
        width=0.6,
        customdata=np.stack([d["eletivas"], d["total"], d["eletivas_cema"]], axis=1),
        hovertemplate="%{x:.1f}% elective · %{customdata[0]:,} of %{customdata[1]:,} · %{customdata[2]:,} elective at CNES 2091550<extra>"
        + nome
        + "</extra>",
    )
g.layout(
    fig,
    titulo="What the urgent target excludes, by ICD-10 group (% elective in the group)",
    x="% elective in the group (leaves the urgent target)",
    hover="closest",
    altura=460,
    m=m,
)
fig.update_xaxes(range=[0, 100], ticksuffix="%")
fig.update_layout(barmode="overlay", margin=dict(l=300))
g.mostrar(fig, key="sab_cid")
sens = G[G["sensivel"]]
st.markdown(
    f"Groups with a plausible pollution mechanism: **{int(sens['eletivas'].sum()):,}** elective admissions out of "
    f"**{int(sens['total'].sum()):,}** ({100 * sens['eletivas'].sum() / sens['total'].sum():.1f}%); "
    f"**{int(sens['eletivas_cema'].sum()):,}** of them at CNES 2091550."
)
ui.fonte(dados.rel_painel("grupos_cid.csv"))

mm_ = D[["sens_nao_eletivo", "sens_eletivo"]].resample("MS").mean()
corr = mm_["2019":"2024"].corr().iloc[0, 1]
fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.10,
    subplot_titles=("Non-elective (stay in the urgent target)", "Elective (leave the target)"),
)
fig.add_scatter(
    x=mm_.index,
    y=mm_["sens_nao_eletivo"],
    row=1,
    col=1,
    name="Non-elective",
    mode="lines",
    line=dict(color=cs["nao_eletivo"], width=2),
    hovertemplate="%{y:.1f}<extra>non-elective</extra>",
)
fig.add_scatter(
    x=mm_.index,
    y=mm_["sens_eletivo"],
    row=2,
    col=1,
    name="Elective",
    mode="lines",
    line=dict(color=cs["eletivo"], width=2),
    hovertemplate="%{y:.1f}<extra>elective</extra>",
)
g.layout(
    fig,
    titulo=f"Pollution-sensitive groups: monthly mean per day (correlation 2019–2024: {corr:.2f})",
    altura=480,
    legenda=False,
    m=m,
)
fig.update_yaxes(rangemode="tozero", title_text="Adm./day")
fig.update_xaxes(tickformat="%m/%Y")
for ann in fig.layout.annotations:
    ann.font.color = c["text2"]
g.mostrar(fig, key="sab_sens")
ui.fonte(REL_DIARIO, nota="columns sens_nao_eletivo and sens_eletivo; correlation computed from the monthly means")

st.markdown("**Profile of the two subsets** (age in years, length of stay in days):")
P = dados.carregar_painel_perfil().rename(
    columns={
        "internacoes": "admissions",
        "idade_mediana": "median age",
        "pct_menor_15": "% under 15",
        "permanencia_mediana": "median stay",
        "pct_permanencia_ate_1_dia": "% stay ≤ 1 day",
        "pct_obito": "% death",
    }
)
ui.tabela(P, casas=1, width="stretch")
ui.fonte(dados.rel_painel("perfil.csv"))

# --- 5. Establishments ---------------------------------------------------------------------
st.header("5. Establishments with most elective admissions on Saturdays")
E = dados.carregar_painel_estabelecimentos()
metrica = st.radio(
    "Metric", options=["Elective on Saturdays", "Elective (all days)", "Total"], horizontal=True, key="sab_estab"
)
col = {"Elective on Saturdays": "eletivas_sabado", "Elective (all days)": "eletivas", "Total": "total"}[metrica]
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
    titulo=f"{metrica} per year — 15 establishments with most elective Saturday admissions (highlight: CNES {MAN['cnes_destacado']})",
    y=metrica + " / year",
    hover="closest",
    altura=440,
    m=m,
)
fig.update_layout(legend=dict(orientation="v", x=1.01, y=1, yanchor="top"))
fig.update_yaxes(rangemode="tozero")
g.mostrar(fig, key="sab_estab_fig")
ui.fonte(
    dados.rel_painel("estabelecimentos_ano.csv"),
    nota="cells with fewer than 5 admissions are suppressed at the source (gaps in the lines); names: consult CNES/DATASUS",
)

# --- 6. Effect on the models ----------------------------------------------------------------
st.header("6. Effect on the models (common set AR_CAL, CETESB base)")
M = dados.carregar_painel_erros_modelos().copy()
M["dow"] = M["target_date"].dt.dayofweek
M["mutirao"] = (M["dow"] == 5) & ((M["target_date"].dt.day - 1) // 7 < 3) & (M["target_date"].dt.year >= 2022)
c1, c2 = st.columns(2)
h_sel = c1.radio(
    "Horizon", options=sorted(M["h"].unique()), format_func=lambda h: f"h = {h}", horizontal=True, key="sab_h"
)
metr = c2.radio("Metric", options=["MAE", "Bias"], horizontal=True, key="sab_metr")
x = M[M["h"] == h_sel]
run_x = x["run"].iloc[0]
if metr == "MAE":
    t = x.assign(v=x["erro"].abs()).groupby(["modelo", "dow"])["v"].mean().reset_index()
    rot = "MAE (admissions / day)"
else:
    t = x.groupby(["modelo", "dow"])["erro"].mean().reset_index().rename(columns={"erro": "v"})
    rot = "Bias (observed − predicted)"
fig = go.Figure()
for nome in g.ORDEM_MODELOS:
    d = t[t["modelo"] == nome].sort_values("dow")
    if d.empty:
        continue
    fig.add_bar(
        x=[DOW[i] for i in d["dow"]],
        y=d["v"],
        name=nome,
        marker=dict(color=cm[nome], cornerradius=3),
        hovertemplate="%{y:.2f}<extra>" + nome + "</extra>",
    )
g.layout(fig, titulo=f"{metr} by weekday — h = {h_sel}", y=rot, hover="closest", altura=400, m=m)
fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.1)
g.mostrar(fig, key="sab_modelos")
ui.fonte(
    dados.rel_painel("erros_modelos_ar_cal.csv"), run=run_x, nota="seed-mean predictions per target date, total target"
)

part = (
    x.assign(a=x["erro"].abs())
    .groupby("modelo")
    .apply(
        lambda d: pd.Series(
            {
                "MAE": d["a"].mean(),
                "MAE outside campaign Saturdays": d["a"][~d["mutirao"]].mean(),
                "% of absolute error on campaign Saturdays": 100 * d["a"][d["mutirao"]].sum() / d["a"].sum(),
                "% of dates": 100 * d["mutirao"].mean(),
            }
        ),
        include_groups=False,
    )
    .reindex([n for n in g.ORDEM_MODELOS if n in set(t["modelo"])])
)
st.markdown("**How much of the error comes from the 1st–3rd Saturday of the month (2022+)**, total target:")
ui.tabela(part, casas=1, width="stretch")
ui.fonte(dados.rel_painel("erros_modelos_ar_cal.csv"), run=run_x)

st.markdown(
    "**Saturday error at h = 1, both targets** — MAE on Saturdays vs. the other days, share of the absolute "
    "error on Saturdays and the ratio MAE_sat / MAE_other:"
)
es = dados.carregar_erro_sabado_h1().rename(
    columns={
        "alvo": "target",
        "modelo": "model",
        "MAE_sab": "MAE Saturdays",
        "MAE_demais": "MAE other days",
        "frac_erro_sab": "share of abs. error on Saturdays",
        "razao": "ratio",
    }
)
ui.tabela(es, casas=3, hide_index=True, width="stretch")
runs_h1 = dados.carregar_runs_por_horizonte()
ui.fonte(dados.REL_ERRO_SABADO_H1, nota=f"runs: total `{runs_h1['total'][1]}`; urgent `{runs_h1['urgencia'][1]}`")

# --- 7. The decision -----------------------------------------------------------------------
st.header("7. The decision under discussion (PROTOCOLO §0.23, proposed)")
st.markdown(
    "- **Non-elective (urgent) target** for the PM2.5 question: the criterion is the admission character recorded "
    "in the AIH, applied equally to every day, hospital and ICD code, without excluding any establishment.\n"
    "- **Total target** stays for hospital-demand forecasting (a bed occupied by an elective admission still counts).\n"
    "- What leaves: mostly scheduled upper-airway surgery (J30–J39). In the groups with a plausible pollution "
    "mechanism the elective share is small (section 4) and does not follow the seasonality.\n"
    "- Open point for the advisor: which of the two targets is the main outcome of the dissertation."
)
with st.expander("Provenance of the panel data (manifest.json)"):
    st.json(MAN)
    ui.fonte(REL_MANIFEST)

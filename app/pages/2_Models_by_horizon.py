"""Models by horizon — MAE, MASE, skill, feature-set ablation and Diebold–Mariano tests."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import dados  # noqa: E402
import graficos as g  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
import ui  # noqa: E402

ui.configurar_pagina("Models by horizon", "📊")
st.title("Models by horizon")
ui.aviso_provisorio()
st.markdown(
    "All models use the common feature set **AR_CAL** (autoregressive lags + calendar) unless stated otherwise. "
    "**MASE only compares models within the same horizon** (it uses the Naïve of that h); across horizons read "
    "**MAE** and **skill vs. reference** = 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve)."
)

m = g.modo()
c = g.CHROME[m]
cores = g.cores_modelos(m)
MODELOS = g.ORDEM_MODELOS
MODELOS_SEM_BASE = [x for x in MODELOS if x not in ("Naïve", "Seasonal Naïve")]

alvo = st.radio("Target", options=list(dados.ALVOS), format_func=dados.ALVOS.get, horizontal=True, key="mh_alvo")
tab = dados.tabela_arcal(alvo)
runs_alvo = dados.carregar_runs_por_horizonte()[alvo]
fontes_tab = [dados.REL_ARCAL_DOIS_ALVOS] + ([dados.REL_MODELOS_POR_H] if alvo == "total" else [])
nota_skill = (
    "skill_vs_ref read from A_modelos_por_h.csv"
    if alvo == "total"
    else "skill computed as 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve) of the same h, from the csv"
)
hx = [f"h = {h}" for h in dados.HORIZONTES]


def linhas_por_modelo(df: pd.DataFrame, coluna: str, modelos: list[str], y: str, fmt: str) -> go.Figure:
    fig = go.Figure()
    for nome in modelos:
        d = df[df["modelo"] == nome].sort_values("h")
        if d.empty:
            continue
        base = nome in ("Naïve", "Seasonal Naïve")
        fig.add_scatter(
            x=[f"h = {h}" for h in d["h"]],
            y=d[coluna],
            name=nome,
            mode="lines+markers",
            line=dict(color=cores[nome], width=2, dash="dot" if base else "solid"),
            marker=dict(size=9, color=cores[nome], line=dict(width=2, color=c["surface"])),
            hovertemplate="%{y:" + fmt + "}<extra>" + nome + "</extra>",
        )
    g.layout(fig, y=y, hover="x unified", altura=400, m=m)
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=hx)
    return fig


# --- MAE across horizons --------------------------------------------------------------------
st.subheader("MAE by horizon (AR_CAL)")
g.mostrar(linhas_por_modelo(tab, "MAE", MODELOS, "MAE (admissions / day)", ".2f"), key="mh_mae")
ui.fonte(*fontes_tab, nota="runs: " + "; ".join(f"h={h}: `{r}`" for h, r in sorted(runs_alvo.items())))

# --- Skill across horizons -------------------------------------------------------------
st.subheader("Skill vs. reference by horizon")
fig = linhas_por_modelo(tab, "skill_vs_ref", MODELOS_SEM_BASE, "1 − MAE / MAE(best naïve of the same h)", ".3f")
fig.add_hline(y=0, line=dict(color=c["axis"], width=1))
fig.update_yaxes(tickformat=".0%")
g.mostrar(fig, key="mh_skill")
ui.fonte(*fontes_tab, nota=nota_skill)

# --- MASE within one horizon -------------------------------------------------------------
st.subheader("MASE within one horizon")
h_sel = st.radio("Horizon", options=dados.HORIZONTES, format_func=lambda h: f"h = {h}", horizontal=True, key="mh_h")
d = tab[tab["h"] == h_sel].sort_values("MASE", ascending=False)
fig = go.Figure(
    go.Bar(
        x=d["MASE"],
        y=d["modelo"].astype(str),
        orientation="h",
        marker=dict(color=[cores[n] for n in d["modelo"].astype(str)], cornerradius=4),
        width=0.55,
        text=[f"{v:.3f}" for v in d["MASE"]],
        textposition="outside",
        textfont=dict(color=c["text2"]),
        hovertemplate="MASE %{x:.3f} · MAE %{customdata:.2f}<extra>%{y}</extra>",
        customdata=d["MAE"],
    )
)
fig.add_vline(
    x=1.0,
    line=dict(color=c["axis"], width=1),
    annotation_text="Naïve = 1",
    annotation_position="top",
    annotation_font=dict(color=c["text2"], size=11),
)
g.layout(
    fig, x=f"MASE at h = {h_sel} (MAE / MAE Naïve of h = {h_sel})", hover="closest", altura=330, legenda=False, m=m
)
fig.update_xaxes(rangemode="tozero")
g.mostrar(fig, key="mh_mase")
ui.fonte(*fontes_tab, run=runs_alvo[h_sel])

with st.expander("Table — MAE, MASE, skill and reference MAEs for every h and model"):
    cols = ["h", "modelo", "MAE", "MASE", "skill_vs_ref", "naive", "snaive"]
    if "dp_fold" in tab.columns:
        cols += ["dp_fold", "dp_sem"]
    ui.tabela(tab[cols + ["run"]], casas=3, hide_index=True, width="stretch")
    ui.fonte(*fontes_tab, nota="dp_fold / dp_sem = std of MAE across folds / seeds (total target only)")

# --- Ablation: every feature set of one run -----------------------------------------------
st.divider()
st.subheader("Feature-set ablation (all feature sets of one run)")
st.markdown(
    "Blocks: `AR` lags of the target · `CAL` calendar · `METEO` meteorology · `PM25` PM2.5 (mean, station count, "
    "spatial dispersion) · `PM25MEDIA` PM2.5 mean only · `POLUENTES` PM10, NO2, O3, CO · `COMPLETO` all blocks. "
    "`baseline` is the feature set of the naïve models."
)
h_ab = st.radio(
    "Horizon (ablation)", options=dados.HORIZONTES, format_func=lambda h: f"h = {h}", horizontal=True, key="ab_h"
)
run_ab = runs_alvo[h_ab]
mc = dados.carregar_model_comparison(run_ab)
metrica = st.radio("Metric", options=["MAE_medio", "MASE_medio", "RMSE_medio"], horizontal=True, key="ab_metrica")
piv = mc[~mc["modelo"].isin(["Naïve", "Seasonal Naïve"])].pivot(index="modelo", columns="feature_set", values=metrica)
ordem_fs = [
    "baseline",
    "AR",
    "AR_CAL",
    "AR_CAL_PM25MEDIA",
    "AR_CAL_PM25",
    "AR_CAL_POLUENTES",
    "AR_CAL_METEO",
    "AR_CAL_METEO_PM25MEDIA",
    "AR_CAL_METEO_PM25",
    "AR_CAL_METEO_POLUENTES",
    "COMPLETO",
]
piv = piv.reindex(index=[x for x in MODELOS if x in piv.index], columns=[x for x in ordem_fs if x in piv.columns])
fig = go.Figure(
    go.Heatmap(
        z=piv.values,
        x=piv.columns,
        y=piv.index,
        colorscale=g.escala_sequencial(m),
        xgap=2,
        ygap=2,
        text=[[("" if pd.isna(v) else f"{v:.2f}") for v in row] for row in piv.values],
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorbar=dict(title=metrica.replace("_medio", ""), tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate="%{y} · %{x}: %{z:.3f}<extra></extra>",
    )
)
g.layout(fig, hover="closest", altura=340, legenda=False, m=m)
fig.update_layout(margin=dict(l=110))
fig.update_xaxes(showgrid=False, tickangle=-30)
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="ab_heat")
base_mc = mc[mc["modelo"].isin(["Naïve", "Seasonal Naïve"])].set_index("modelo")[metrica]
ui.fonte(
    dados.rel_run(run_ab, "model_comparison.csv"),
    run=run_ab,
    nota="mean over 4 folds (and 5 seeds for XGBoost/LSTM); empty cell = model not run on that set; "
    + "baselines (feature set `baseline`): "
    + ", ".join(f"{k} {v:.2f}" for k, v in base_mc.items()),
)
with st.expander("Table — model_comparison.csv of this run"):
    ui.tabela(mc.drop(columns=["modelo"]), casas=3, hide_index=True, width="stretch")
    ui.fonte(dados.rel_run(run_ab, "model_comparison.csv"), run=run_ab)

# --- Diebold–Mariano -----------------------------------------------------------------------
st.divider()
st.subheader("Which pairs of models are distinguishable? (Diebold–Mariano, Holm)")
st.markdown(
    "Loss = absolute error per target date (seed mean for XGBoost and LSTM), feature set AR_CAL, grouped over the "
    "four folds (T = 720), Newey–West long-run variance, Harvey–Leybourne–Newbold correction, Holm within the family "
    "of 21 contrasts. **DM < 0 favours A.** A pair is *distinguishable* when Holm-adjusted p < 0.05."
)
h_dm = st.radio("Horizon (DM)", options=dados.HORIZONTES, format_func=lambda h: f"h = {h}", horizontal=True, key="dm_h")
run_dm = runs_alvo[h_dm]
dm = dados.dm_modelos_arcal(run_dm)

# Matrix view: Holm p for every pair (symmetric), only among the five non-naive models and the baselines.
mat = pd.DataFrame(index=MODELOS, columns=MODELOS, dtype=float)
for _, r in dm.iterrows():
    mat.loc[r["A_nome"], r["B_nome"]] = r["p_holm"]
    mat.loc[r["B_nome"], r["A_nome"]] = r["p_holm"]
sig = mat < 0.05
fig = go.Figure(
    go.Heatmap(
        z=mat.values,
        x=mat.columns,
        y=mat.index,
        zmin=0,
        zmax=1,
        colorscale=g.escala_sequencial(m, "laranja")[::-1],
        xgap=2,
        ygap=2,
        text=[[("" if pd.isna(v) else f"{v:.3f}") for v in row] for row in mat.values],
        texttemplate="%{text}",
        textfont=dict(size=11),
        colorbar=dict(title="Holm p", tickfont=dict(color=c["muted"]), outlinewidth=0),
        hovertemplate="%{y} vs %{x}: Holm p = %{z:.3f}<extra></extra>",
    )
)
g.layout(fig, hover="closest", altura=380, legenda=False, m=m)
fig.update_layout(margin=dict(l=110))
fig.update_xaxes(showgrid=False, tickangle=-30)
fig.update_yaxes(showgrid=False, autorange="reversed")
g.mostrar(fig, key="dm_heat")
ui.fonte(dados.rel_dm(run_dm, "dm_contrastes.csv"), run=run_dm, nota="family modelos_AR_CAL, grouped scope (T = 720)")

entre_modelos = dm[dm["A_nome"].isin(MODELOS_SEM_BASE) & dm["B_nome"].isin(MODELOS_SEM_BASE)]
dist = entre_modelos[entre_modelos["distinguishable_holm"]]
if dist.empty:
    st.info(f"h = {h_dm}: no pair among the five models is distinguishable after Holm.")
else:
    st.info(
        f"h = {h_dm}: {len(dist)} of {len(entre_modelos)} pairs among the five models are distinguishable after Holm — "
        + "; ".join(
            f"{r['A_nome']} vs {r['B_nome']} (favours {r['favors']}, Holm p = {r['p_holm']:.3f})"
            for _, r in dist.iterrows()
        )
        + "."
    )
with st.expander("Table — the 21 grouped contrasts of this run"):
    ui.tabela(
        dm[["A_nome", "B_nome", "d_medio", "DM", "p", "p_holm", "distinguishable_holm", "favors"]].rename(
            columns={"A_nome": "A", "B_nome": "B", "d_medio": "mean loss diff (A − B)"}
        ),
        casas=4,
        hide_index=True,
        width="stretch",
    )
    ui.fonte(dados.rel_dm(run_dm, "dm_contrastes.csv"), run=run_dm)
with st.expander("Full DM report of this run (RELATORIO_DM.md, in Portuguese)"):
    st.markdown(dados.carregar_dm_relatorio(run_dm))
    ui.fonte(dados.rel_dm(run_dm, "RELATORIO_DM.md"), run=run_dm)

st.subheader("DM summary across horizons")
res = dados.carregar_dm_resumo_por_h()
res = res[res["target"] == alvo][
    ["h", "run", "lider_nome", "n_pares", "n_sig_holm", "n_sig_entre_modelos", "sig_entre_modelos"]
]
res = res.rename(
    columns={
        "lider_nome": "nominal leader",
        "n_pares": "contrasts",
        "n_sig_holm": "sig. after Holm (all)",
        "n_sig_entre_modelos": "sig. among the 5 models",
        "sig_entre_modelos": "which pairs",
    }
)
st.dataframe(res, hide_index=True, width="stretch")
ui.fonte(dados.REL_DM_RESUMO_POR_H)

"""Análise da rodada multi-horizonte (PROTOCOLO §0.22) e do alvo de urgência (§0.23) — só lê artefatos; falha alto.

    python -m src.experiments.analise_multihorizonte [--saida <pasta>]

Lê, de runs fixadas abaixo pelo id completo (nada de "a mais recente"):
- `manifest.json`, `config.json`, `folds.csv`, `metrics_by_fold.csv`, `model_comparison.csv`, `predictions.csv`;
- DM entre modelos e ablação dentro de cada run: `TESTES_DM_<run>/dm_contrastes.csv` (`teste_dm_v02.py`);
- DM entre bases por h: `TESTES_DM_FONTES_V04_20261024` (h = 1) e `TESTES_DM_FONTES_MH_V01_20261118/h<h>` (h > 1);
- DM entre braços COVID: `TESTES_DM_COVID_V01_20261118/h<h>` (`teste_dm_fontes.py --testar-sem-ambiente`).

Seções da saída (`saida.txt` + CSVs): 0 integridade (laudo PASS/FAIL, `integridade.csv`); A modelos × h; A2 DM entre modelos;
A3 vencedor por fold e viés por fold; B covariáveis × h (critério por fold + DM/Holm); C bases × h; D COVID A × B;
E robustez e custo. `proveniencia.json` grava o sha256 de cada artefato lido, o commit e as versões.

Dois critérios por fold aparecem e NÃO são o mesmo (registrado em docs/RESULTADOS_MULTIHORIZONTE_20261118.md):
- `criterio_fold` (aqui, igual a `compara_fontes_v02.parear`): por fold, Δ = média das sementes da diferença pareada;
  ruído = max(dp entre sementes de A, de B); regular = Δ do mesmo sinal e |Δ| > ruído em ≥ 3 de 4 folds (2 de 2 nos braços COVID);
- `criterio_0_7_folds` de `teste_dm_v02.py` (usado nos pares de modelos e na ablação): nº de folds com o mesmo sinal do fold 1.
Para pares de modelos vale o DM de `teste_dm_v02`; o `criterio_fold` só entra nas tabelas descritivas.

MASE usa o Naïve do mesmo horizonte; não se compara MASE entre h. Entre h usa-se MAE e skill = 1 − MAE/min(Naïve, Seasonal Naïve).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from src.experiments import compara_fontes_v02 as cf

RAIZ = Path(__file__).resolve().parents[2]
EXP = RAIZ / "reports" / "experiments"
SAIDA_PADRAO = EXP / "ANALISE_MULTIHORIZONTE_V02_20261118"  # V01: registro (sem E2)
DM_FONTES = {1: EXP / "TESTES_DM_FONTES_V04_20261024"} | {h: EXP / "TESTES_DM_FONTES_MH_V01_20261118" / f"h{h}" for h in (5, 7, 15, 30)}
DM_COVID = {h: EXP / "TESTES_DM_COVID_V01_20261118" / f"h{h}" for h in (1, 5, 7, 15, 30)}
HS = [1, 5, 7, 15, 30]
BASES = {
    "cetesb": {1: "h1_v02_cetesb_cetesb_classicos_full_20261022-211834", 5: "mh_h5_cetesb_cetesb_full_20261110-211453",
               7: "mh_h7_cetesb_cetesb_full_20261111-030322", 15: "mh_h15_cetesb_cetesb_full_20261111-070926",
               30: "mh_h30_cetesb_cetesb_full_20261113-104814"},
    "espelho": {1: "h1_v02_cetesbmin_cetesbmin_classicos_full_20261022-092503", 5: "mh_h5_cetesbmin_cetesbmin_full_20261114-055302",
                7: "mh_h7_cetesbmin_cetesbmin_full_20261114-064037", 15: "mh_h15_cetesbmin_cetesbmin_full_20261114-072915",
                30: "mh_h30_cetesbmin_cetesbmin_full_20261114-081453"},
    "cams": {1: "h1_v02_cams_cams_classicos_full_20261023-002643", 5: "mh_h5_cams_cams_full_20261114-090118",
             7: "mh_h7_cams_cams_full_20261114-095706", 15: "mh_h15_cams_cams_full_20261114-105441",
             30: "mh_h30_cams_cams_full_20261114-114939"},
    # híbrida: não há h = 30 (a run não foi feita; ver CHANGELOG)
    "hibrida": {1: "h1_v02_hibrida_classicos_full_20261023-081916", 5: "mh_h5_hibrida_full_20261114-124407",
                7: "mh_h7_hibrida_full_20261114-183928", 15: "mh_h15_hibrida_full_20261115-172349"},
    "urgencia": {1: "ur_h1_cetesb_cetesb_full_20261116-191534", 5: "ur_h5_cetesb_cetesb_full_20261116-222823",
                 7: "ur_h7_cetesb_cetesb_full_20261117-073926", 15: "ur_h15_cetesb_cetesb_full_20261117-190532",
                 30: "ur_h30_cetesb_cetesb_full_20261117-221426"},
    "covidA": {1: "mh_h1_covidA_cetesb_full_20261113-170838", 5: "mh_h5_covidA_cetesb_full_20261113-194721",
               7: "mh_h7_covidA_cetesb_full_20261113-222503", 15: "mh_h15_covidA_cetesb_full_20261114-010038",
               30: "mh_h30_covidA_cetesb_full_20261114-032811"},
    "covidB": {1: "mh_h1_covidB_cetesb_full_20261113-190311", 5: "mh_h5_covidB_cetesb_full_20261113-214056",
               7: "mh_h7_covidB_cetesb_full_20261114-001740", 15: "mh_h15_covidB_cetesb_full_20261114-024705",
               30: "mh_h30_covidB_cetesb_full_20261114-051337"},
}
COM_DM_MODELOS = ("cetesb", "urgencia")  # bases com TESTES_DM_<run> exigido em todo h
MOD = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb"]
BASEL = ["naive", "seasonal_naive"]
AMB = ["AR_CAL_PM25", "AR_CAL_PM25MEDIA", "AR_CAL_METEO", "AR_CAL_POLUENTES", "AR_CAL_METEO_PM25",
       "AR_CAL_METEO_PM25MEDIA", "AR_CAL_METEO_POLUENTES", "COMPLETO"]
DESLOC_ALVO = [0, 1, 2, 6, 13, 27]
DESLOC_EXOG = [0, 1, 2, 6, 13]
LAGS_AR_PADRAO_H1 = [1, 7]  # src/models/gam_nb.py::LAGS_AR_PADRAO, inalterado desde 7103685

LIDOS: dict[str, str] = {}
CACHE: dict[str, dict] = {}
L: list[str] = []


def p(*a) -> None:
    s = " ".join(str(x) for x in a)
    print(s)
    L.append(s)


def _sha(f: Path) -> str:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _arq(f: Path) -> Path:
    if not f.exists():
        raise FileNotFoundError(f)
    LIDOS.setdefault(str(f.relative_to(RAIZ)).replace("\\", "/"), _sha(f))
    return f


def ler(run: str) -> dict:
    if run not in CACHE:
        r = EXP / run
        if not r.is_dir():
            raise FileNotFoundError(f"run não encontrada: {r}")
        man = json.loads(_arq(r / "manifest.json").read_text(encoding="utf-8"))
        mbf = pd.read_csv(_arq(r / "metrics_by_fold.csv"))
        if mbf[["MAE", "RMSE", "MASE"]].isna().any().any():
            raise RuntimeError(f"{run}: NaN em metrics_by_fold")
        if not (r / "metrics.json").exists():
            raise FileNotFoundError(f"{run}: sem metrics.json")
        _arq(r / "metrics.json")
        CACHE[run] = dict(man=man, mbf=mbf, mc=pd.read_csv(_arq(r / "model_comparison.csv")),
                          folds=pd.read_csv(_arq(r / "folds.csv")),
                          cfg=json.loads(_arq(r / "config.json").read_text(encoding="utf-8")))
    return CACHE[run]


def pred(run: str) -> pd.DataFrame:
    d = ler(run)
    if "pred" not in d:
        d["pred"] = pd.read_csv(_arq(EXP / run / "predictions.csv"), parse_dates=["target_date"])
    return d["pred"]


def fs_de(model: str, fs: str) -> str:
    return "baseline" if model in BASEL else fs


def por_fold(run: str, model: str, fs: str) -> pd.DataFrame:
    m = ler(run)["mbf"]
    g = m[(m.model == model) & (m.feature_set == fs_de(model, fs))]
    if g.empty:
        raise KeyError(f"{run}: {model}/{fs} ausente")
    return g


def criterio_fold(run_a, ma, fa, run_b, mb, fb, nmin) -> dict:
    """Δ = A − B por fold (pareado por semente quando os dois têm sementes); regra de `compara_fontes_v02.parear`."""
    A, B = por_fold(run_a, ma, fa), por_fold(run_b, mb, fb)
    out = []
    for f in sorted(A.fold.unique()):
        a, b = A[A.fold == f], B[B.fold == f]
        if a.seed.nunique() > 1 and b.seed.nunique() > 1:
            j = a.set_index("seed").MAE - b.set_index("seed").MAE
            if j.isna().any():
                raise RuntimeError(f"sementes não pareiam: {run_a}/{ma}/{fa} × {run_b}/{mb}/{fb}")
            d = j.mean()
        else:
            d = a.MAE.mean() - b.MAE.mean()
        ruido = max(a.MAE.std(ddof=1) if len(a) > 1 else 0.0, b.MAE.std(ddof=1) if len(b) > 1 else 0.0)
        out.append((d, abs(d) > ruido))
    ds = np.array([o[0] for o in out])
    ex = np.array([o[1] for o in out])
    melhor, pior = int(((ds < 0) & ex).sum()), int(((ds > 0) & ex).sum())
    ver = "A<B" if melhor >= nmin else ("A>B" if pior >= nmin else "~")
    return dict(dMAE=ds.mean(), folds_A_melhor=melhor, folds_A_pior=pior, n_folds=len(ds), veredito=ver)


def mc(run: str) -> pd.DataFrame:
    return ler(run)["mc"].set_index(["model", "feature_set"])


def dm_run(run: str) -> pd.DataFrame:
    d = pd.read_csv(_arq(EXP / f"TESTES_DM_{run}" / "dm_contrastes.csv"))
    return d[d.escopo == "agrupado"]


def dm_entre(pasta: Path) -> pd.DataFrame:
    d = pd.read_csv(_arq(pasta / "dm_entre_bases.csv"))
    return d[d.escopo == "agrupado"]


# ===================================================================================== 0. integridade
def integridade() -> pd.DataFrame:
    p("== 0. Integridade (todas as runs; FAIL aborta)")
    linhas = []
    for base, R in BASES.items():
        for h, run in R.items():
            d = ler(run)
            man, cfg = d["man"], d["cfg"]
            rel = man.get("relatorio_dataset", {})
            exp = cfg.get("experimento", {})
            gam = cfg.get("modelos", {}).get("gam_nb", {})
            nb = d["mbf"][d["mbf"].model == "naive"].MASE
            n_pred = len(pred(run))
            prov = man.get("proveniencia") or {}
            linhas.append(dict(
                base=base, h=h, run=run, modo=man.get("modo"), git_sujo=man.get("git_sujo"),
                commit=str(man.get("git_commit"))[:7], horizonte=rel.get("horizonte"),
                gate=(man.get("data_quality") or {}).get("veredito"),
                lags_alvo_ok=list(exp.get("lags_alvo", [])) == [h + k for k in DESLOC_ALVO],
                lags_exog_ok=list(exp.get("lags_exogenas", [])) == [h + k for k in DESLOC_EXOG],
                # runs h = 1 de outubro não gravam lags_ar: vale o padrão do código, LAGS_AR_PADRAO = (1, 7) = [h, h+6]
                gam_lags_ok=(list(gam.get("lags_ar", LAGS_AR_PADRAO_H1 if h == 1 else [])) == [h, h + 6]
                             if gam.get("ativo") else True),
                n_pred_manifesto=man.get("n_predicoes"), n_pred_csv=n_pred,
                n_folds=d["folds"].shape[0], naive_MASE_1=bool(np.allclose(nb, 1)),
                teste=f"{d['folds'].teste_inicio.iloc[0]}..{d['folds'].teste_fim.iloc[-1]}",
                max_iter_alpha=gam.get("max_iter_alpha"), inicio=prov.get("inicio"), fim=prov.get("fim"),
                status_alvo=man.get("status")))
    I = pd.DataFrame(linhas)
    I["ok"] = ((I.modo == "full") & (I.git_sujo == False) & (I.horizonte == I.h) & (I.gate == "PASS")  # noqa: E712
               & I.naive_MASE_1 & I.lags_alvo_ok & I.lags_exog_ok & I.gam_lags_ok & (I.n_pred_manifesto == I.n_pred_csv))
    p(I.drop(columns=["run", "inicio", "fim"]).to_string(index=False))
    if not I.ok.all():
        raise SystemExit("integridade FAIL:\n" + I[~I.ok].to_string())
    for h in HS:
        rs = [BASES[b][h] for b in ("cetesb", "espelho", "cams", "hibrida") if h in BASES[b]]
        f0 = ler(rs[0])["folds"][["teste_inicio", "teste_fim"]]
        n0 = por_fold(rs[0], "naive", "baseline").sort_values("fold").MAE.values
        for r in rs[1:]:
            if not ler(r)["folds"][["teste_inicio", "teste_fim"]].equals(f0):
                raise SystemExit(f"datas de teste diferem: {r} × {rs[0]}")
            if not np.allclose(por_fold(r, "naive", "baseline").sort_values("fold").MAE.values, n0, atol=1e-9):
                raise SystemExit(f"Naïve difere: {r} × {rs[0]}")
        if not ler(BASES["urgencia"][h])["folds"][["teste_inicio", "teste_fim"]].equals(f0):
            raise SystemExit(f"datas de teste da urgência diferem em h={h}")
        fa, fb = ler(BASES["covidA"][h])["folds"], ler(BASES["covidB"][h])["folds"]
        if not fa[["teste_inicio", "teste_fim"]].equals(fb[["teste_inicio", "teste_fim"]]):
            raise SystemExit(f"datas de teste COVID A × B diferem em h={h}")
    p("integridade PASS; datas de teste e Naïve idênticos entre bases (por h), urgência no mesmo teste, braços COVID no mesmo teste")
    return I


# ===================================================================================== A. modelos por h
def tabela_modelos(base: str) -> pd.DataFrame:
    rows = []
    for h, run in BASES[base].items():
        m = mc(run)
        nv, sn = m.loc[("naive", "baseline")].MAE_medio, m.loc[("seasonal_naive", "baseline")].MAE_medio
        for k in MOD:
            ar = m.loc[(k, "AR_CAL")]
            sub = m.loc[k]
            best = sub.MAE_medio.idxmin()
            rows.append(dict(base=base, h=h, run=run, modelo=k, MAE_ARCAL=ar.MAE_medio, RMSE_ARCAL=ar.RMSE_medio,
                             MASE_ARCAL=ar.MASE_medio, dp_fold=ar.MAE_std_fold, dp_sem=ar.MAE_std_semente,
                             MAE_AR=m.loc[(k, "AR")].MAE_medio, melhor_conj=best, MAE_melhor=sub.loc[best].MAE_medio,
                             naive=nv, snaive=sn, skill_vs_ref=1 - ar.MAE_medio / min(nv, sn)))
    return pd.DataFrame(rows)


def secao_A(saida: Path) -> pd.DataFrame:
    A = pd.concat([tabela_modelos(b) for b in BASES], ignore_index=True)
    A.to_csv(saida / "A_modelos_por_h.csv", index=False)
    for base in ("cetesb", "urgencia", "covidA", "covidB"):
        t = A[A.base == base]
        p(f"\n== A. {base}: MAE AR_CAL por modelo × h (e Naïve, Seasonal Naïve do mesmo h)")
        pv = t.pivot_table(index="modelo", columns="h", values="MAE_ARCAL").loc[MOD]
        ref = t.drop_duplicates("h").set_index("h")[["naive", "snaive"]].T
        p(pd.concat([pv, ref]).round(2).to_string())
        p("-- RMSE AR_CAL")
        p(t.pivot_table(index="modelo", columns="h", values="RMSE_ARCAL").loc[MOD].round(2).to_string())
        p("-- MASE AR_CAL (Naïve do MESMO h; não comparar entre colunas)")
        p(t.pivot_table(index="modelo", columns="h", values="MASE_ARCAL").loc[MOD].round(3).to_string())
        p("-- skill vs melhor ingênuo do mesmo h (1 − MAE/min(Naïve, SNaïve))")
        p(t.pivot_table(index="modelo", columns="h", values="skill_vs_ref").loc[MOD].round(3).to_string())
        p("-- ganho do calendário (MAE AR − MAE AR_CAL)")
        p(t.assign(g=t.MAE_AR - t.MAE_ARCAL).pivot_table(index="modelo", columns="h", values="g").loc[MOD].round(2).to_string())
        p("-- melhor conjunto por modelo (MAE)")
        p(t.assign(x=t.apply(lambda r: f"{r.MAE_melhor:.2f} {r.melhor_conj}", axis=1))
          .pivot_table(index="modelo", columns="h", values="x", aggfunc="first").loc[MOD].to_string())
        p("-- ranking por MAE AR_CAL")
        p(" | ".join(f"h={h}: " + " < ".join(g.sort_values("MAE_ARCAL").modelo) for h, g in t.groupby("h")))
    return A


def secao_A2(A: pd.DataFrame, saida: Path) -> None:
    p("\n== A2. Pares de modelos em AR_CAL: DM (teste_dm_v02, Holm na família modelos_AR_CAL) e critério por fold")
    rows = []
    for base in COM_DM_MODELOS:
        for h, run in BASES[base].items():
            d = dm_run(run)
            d = d[d.familia == "modelos_AR_CAL"]
            lider = A[(A.base == base) & (A.h == h)].sort_values("MAE_ARCAL").modelo.iloc[0]
            sig = d[d.p_holm < 0.05]
            ent = sig[sig.A.str.split(":").str[0].isin(MOD) & sig.B.str.split(":").str[0].isin(MOD)]
            rows.append(dict(base=base, h=h, run=run, lider=lider, n_pares=len(d), n_sig_holm=len(sig),
                             n_sig_entre_modelos=len(ent), sig_entre_modelos="; ".join(ent.contraste)))
            for k in MOD:
                if k == lider:
                    continue
                c = criterio_fold(run, lider, "AR_CAL", run, k, "AR_CAL", 3)
                q = d[(d.contraste == f"{lider} − {k}") | (d.contraste == f"{k} − {lider}")]
                rows[-1][f"vs_{k}"] = (f"{c['dMAE']:+.2f} f{c['folds_A_melhor']}/4 "
                                       + (f"pHolm={q.p_holm.iloc[0]:.3f}" if len(q) else "sem DM"))
    R = pd.DataFrame(rows)
    R.to_csv(saida / "A2_dm_modelos_por_h.csv", index=False)
    p(R.drop(columns="run").to_string(index=False))


def secao_A3(saida: Path) -> None:
    p("\n== A3. Vencedor por fold (AR_CAL, MAE médio das sementes) e viés médio (ŷ − y) por fold, alvo total CETESB rica")
    rows = []
    for base in ("cetesb", "urgencia"):
        for h, run in BASES[base].items():
            m = ler(run)["mbf"]
            g = m[(m.feature_set == "AR_CAL") & m.model.isin(MOD)].groupby(["fold", "model"]).MAE.mean().unstack()
            p(f"{base:8s} h={h:2d}: " + " ".join(f"f{f}={g.loc[f].idxmin()}" for f in g.index))
            pr = pred(run)
            q = pr[(pr.feature_set == "AR_CAL") & pr.model.isin(MOD)]
            v = q.assign(vies=q.y_pred - q.y_true).groupby(["model", "fold"]).agg(MAE=("abs_error", "mean"), vies=("vies", "mean"))
            for (k, f), r in v.iterrows():
                rows.append(dict(base=base, h=h, run=run, modelo=k, fold=f, MAE=r.MAE, vies=r.vies))
    V = pd.DataFrame(rows)
    V.to_csv(saida / "A3_vies_por_fold.csv", index=False)
    t = V[V.base == "cetesb"]
    p("-- viés médio por fold (cetesb, AR_CAL; negativo = subprevisão)")
    p(t.pivot_table(index=["modelo"], columns=["h", "fold"], values="vies").loc[MOD].round(1).to_string())
    sih = _arq(RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet")
    s = pd.read_parquet(sih)
    s.index = pd.to_datetime(s.index)
    ano = s.internacoes.groupby(s.index.year).mean()
    ano.rename("media_diaria").to_frame().to_csv(saida / "A3_alvo_media_anual.csv")
    p("-- média diária do alvo total por ano (sih_daily_lookahead.parquet): "
      + ", ".join(f"{a}: {v:.1f}" for a, v in ano.items()))
    p("-- fim do treino por fold (cetesb h=1): " + ", ".join(
        f"f{r.fold}: {r.treino_fim}" for r in ler(BASES['cetesb'][1])["folds"].itertuples()))


# ===================================================================================== B. covariáveis
def secao_B(saida: Path) -> None:
    p("\n== B. Covariáveis: conjunto ambiental − AR_CAL por modelo × h (critério por fold)")
    BR = []
    for base in ("cetesb", "espelho", "cams", "hibrida", "urgencia", "covidA", "covidB"):
        nmin = 2 if base.startswith("covid") else 3
        for h, run in BASES[base].items():
            fsets = set(ler(run)["man"]["feature_sets"])
            for k in MOD:
                for fs in AMB:
                    if fs in fsets:
                        BR.append(dict(base=base, h=h, modelo=k, conjunto=fs,
                                       **criterio_fold(run, k, fs, run, k, "AR_CAL", nmin)))
    BR = pd.DataFrame(BR)
    BR.to_csv(saida / "B_covariaveis_por_h.csv", index=False)
    p("-- nº de (modelo, conjunto) com melhora regular / piora regular / total, sobre AR_CAL")
    p(BR.groupby(["base", "h"]).apply(
        lambda g: f"{(g.veredito == 'A<B').sum()}+/{(g.veredito == 'A>B').sum()}-/{len(g)}", include_groups=False)
      .unstack().to_string())
    p("-- melhor ΔMAE ambiental por modelo × h, CETESB rica (conjunto, folds melhores)")
    cb = BR[BR.base == "cetesb"].sort_values("dMAE").groupby(["modelo", "h"]).head(1)
    p(cb.assign(x=cb.apply(lambda r: f"{r.dMAE:+.2f} {r.conjunto} ({r.folds_A_melhor}/4)", axis=1))
      .pivot_table(index="modelo", columns="h", values="x", aggfunc="first").loc[MOD].to_string())

    p("\n== B2. Ablação com DM (teste_dm_v02; Holm por família ablacao_<modelo>): contrastes com p_holm < 0,05")
    rows = []
    for base in COM_DM_MODELOS:
        for h, run in BASES[base].items():
            d = dm_run(run)
            d = d[d.familia.str.startswith("ablacao_")]
            for r in d.itertuples():
                rows.append(dict(base=base, h=h, run=run, familia=r.familia, contraste=r.contraste, d_medio=r.d_medio,
                                 DM=r.DM, p=r.p, p_holm=r.p_holm, largura_HAC=r.largura_HAC,
                                 folds=r.criterio_0_7_folds, criterio_0_7=r.criterio_0_7))
    D = pd.DataFrame(rows)
    D.to_csv(saida / "B2_dm_ablacao_por_h.csv", index=False)
    s = D[D.p_holm < 0.05]
    p("-- contagem por base × h: melhora (d<0) / piora (d>0) com p_holm<0,05 [entre colchetes: e critério §0.7]")
    for (base, h), g in D.groupby(["base", "h"]):
        gs = g[g.p_holm < 0.05]
        p(f"{base:8s} h={h:2d}: {(gs.d_medio < 0).sum()} melhora / {(gs.d_medio > 0).sum()} piora de {g.p.notna().sum()} testes "
          f"[{((gs.d_medio < 0) & (gs.criterio_0_7 == True)).sum()}/{((gs.d_medio > 0) & (gs.criterio_0_7 == True)).sum()}]; "  # noqa: E712
          f"HAC = {sorted(g.largura_HAC.dropna().astype(int).unique().tolist())}")
    p("-- melhoras com p_holm < 0,05")
    p(s[s.d_medio < 0].drop(columns="run").round(4).to_string(index=False))
    p("-- pioras com p_holm < 0,05")
    p(s[s.d_medio > 0].drop(columns="run").round(4).to_string(index=False))


# ===================================================================================== C. bases
def secao_C(saida: Path) -> None:
    p("\n== C. Bases por h (referência = CETESB rica; compara_fontes_v02, conjuntos comuns; Δ = base − CETESB rica)")
    CR = []
    for h in HS:
        ref = cf._ler_run(BASES["cetesb"][h])
        outros_b = [b for b in ("espelho", "cams", "hibrida") if h in BASES[b]]
        outros = [cf._ler_run(BASES[b][h]) for b in outros_b]
        rot = {BASES["cetesb"][h]: "cetesb"} | {BASES[b][h]: b for b in outros_b}
        av = cf.verificar_pareamento(ref, outros, estrito=True, conjuntos_comuns=True)
        _, res = cf.parear(cf.tabela_longa(ref, outros, rot), "cetesb")
        res.insert(0, "h", h)
        CR.append(res)
        for a in av:
            if "features contra" not in a:
                p(f"  aviso h={h}: {a}")
    CR = pd.concat(CR, ignore_index=True)
    CR.to_csv(saida / "C_bases_por_h.csv", index=False)
    af = CR[CR.afetado_pela_troca]
    p("-- critério por fold (só conjuntos afetados pela troca): melhor/pior/indistinguível que CETESB rica")
    p(af.groupby(["base", "h"]).veredito.apply(
        lambda s: f"{s.str.startswith('MELHOR').sum()}M/{s.str.startswith('PIOR').sum()}P/{s.str.startswith('indist').sum()}~")
      .unstack().to_string())
    nctrl = CR[(~CR.afetado_pela_troca) & (CR.max_abs_delta > 1e-9)].shape[0]
    p(f"-- controles com Δ ≠ 0 (tem de ser 0): {nctrl}")
    if nctrl:
        raise SystemExit("controle entre bases com Δ ≠ 0")

    p("\n== C2. DM entre bases (teste_dm_fontes; Holm por família base × modelo; DM < 0 favorece a base comparada)")
    rows = []
    for h in HS:
        d = dm_entre(DM_FONTES[h])
        if d.run_referencia.unique().tolist() != [BASES["cetesb"][h]]:
            raise SystemExit(f"DM entre bases h={h}: referência {d.run_referencia.unique()} ≠ {BASES['cetesb'][h]}")
        ctrl = d[d.tipo == "controle"]
        if len(ctrl) and ctrl.max_abs_d.max() != 0:
            raise SystemExit(f"DM entre bases h={h}: controle com d ≠ 0")
        t = d[d.tipo == "teste"]
        for (b, k), g in t.groupby(["base", "modelo"]):
            gs = g[g.p_holm < 0.05]
            rows.append(dict(h=h, base=b, modelo=k, testes=int(g.p.notna().sum()), melhor=int((gs.DM < 0).sum()),
                             pior=int((gs.DM > 0).sum()),
                             conjuntos_melhor="; ".join(gs[gs.DM < 0].conjunto), conjuntos_pior="; ".join(gs[gs.DM > 0].conjunto)))
    R = pd.DataFrame(rows)
    R.to_csv(saida / "C2_dm_bases_por_h.csv", index=False)
    p("-- base comparada melhor/pior que CETESB rica (p_holm < 0,05), por h")
    p(R.groupby(["base", "h"]).apply(lambda g: f"{g.melhor.sum()}+/{g.pior.sum()}-/{g.testes.sum()}", include_groups=False)
      .unstack().to_string())
    p("-- detalhe por modelo (só onde há significância)")
    p(R[(R.melhor + R.pior) > 0].to_string(index=False))


# ===================================================================================== D. COVID
def secao_D(saida: Path) -> None:
    p("\n== D. COVID: braço B (treino desde 2023) − braço A (desde 2019); teste 2025-03-06..2026-02-28 (2 folds)")
    p("   alvo 2025–2026 = PRELIMINARY_UNVALIDATED_TARGET (sem conferência TabNet); B também treina com menos dados")
    for h in HS:
        fa, fb = ler(BASES["covidA"][h])["folds"], ler(BASES["covidB"][h])["folds"]
        p(f"h={h:2d} n_treino A={list(fa.n_treino)} B={list(fb.n_treino)}; status alvo A={ler(BASES['covidA'][h])['man'].get('status')}")
    DR = []
    for h in HS:
        for k in MOD:
            for fs in ["AR_CAL"] + AMB:
                DR.append(dict(h=h, modelo=k, conjunto=fs,
                               **criterio_fold(BASES["covidB"][h], k, fs, BASES["covidA"][h], k, fs, 2)))
    DR = pd.DataFrame(DR)
    d0 = DR[DR.conjunto == "AR_CAL"]
    p("-- ΔMAE B − A em AR_CAL (critério por fold, 2/2)")
    p(d0.assign(x=d0.apply(lambda r: f"{r.dMAE:+.2f}({r.veredito})", axis=1))
      .pivot_table(index="modelo", columns="h", values="x", aggfunc="first").loc[MOD].to_string())
    p("-- MAE AR_CAL por braço")
    for br in ("covidA", "covidB"):
        p(br + ": " + " | ".join(f"h={h}: " + ", ".join(f"{k} {mc(BASES[br][h]).loc[(k, 'AR_CAL')].MAE_medio:.2f}" for k in MOD)
                                 for h in HS))

    p("\n== D2. DM B × A (teste_dm_fontes --testar-sem-ambiente; AR e AR_CAL testados; Holm por modelo; DM < 0 favorece B)")
    rows = []
    for h in HS:
        d = dm_entre(DM_COVID[h])
        if (d.run_base.unique().tolist() != [BASES["covidB"][h]] or d.run_referencia.unique().tolist() != [BASES["covidA"][h]]):
            raise SystemExit(f"DM COVID h={h}: runs não conferem")
        if set(d[d.tipo == "controle"].conjunto) != {"baseline"}:
            raise SystemExit(f"DM COVID h={h}: gerado sem --testar-sem-ambiente")
        t = d[d.tipo == "teste"]
        for r in t.itertuples():
            rows.append(dict(h=h, modelo=r.modelo, conjunto=r.conjunto, MAE_B=r.MAE_base, MAE_A=r.MAE_ref, d_medio=r.d_medio,
                             DM=r.DM, p=r.p, p_holm=r.p_holm))
    R = pd.DataFrame(rows)
    R = R.merge(DR[["h", "modelo", "conjunto", "veredito"]].rename(columns={"veredito": "criterio_fold"}),
                on=["h", "modelo", "conjunto"], how="left")
    R.to_csv(saida / "D_covid_B_menos_A.csv", index=False)
    p("-- por h: B melhor / B pior (p_holm < 0,05) / testes  [B melhor também no critério por fold]")
    for h, g in R.groupby("h"):
        gs = g[g.p_holm < 0.05]
        p(f"h={h:2d}: {(gs.DM < 0).sum()} / {(gs.DM > 0).sum()} / {g.p.notna().sum()}  "
          f"[{((gs.DM < 0) & (gs.criterio_fold == 'A<B')).sum()}]")
    p("-- AR_CAL: d̄ (B − A), p_holm")
    a0 = R[R.conjunto == "AR_CAL"]
    p(a0.assign(x=a0.apply(lambda r: f"{r.d_medio:+.2f} p={r.p_holm:.3f}", axis=1))
      .pivot_table(index="modelo", columns="h", values="x", aggfunc="first").loc[MOD].to_string())
    p("-- PM2,5 rico × média nos braços (MAE AR_CAL_PM25 − AR_CAL_PM25MEDIA, LSTM e INGARCH-NB)")
    for br in ("covidA", "covidB"):
        p(br + ": " + " | ".join(
            f"h={h}: " + ", ".join(f"{k} {mc(BASES[br][h]).loc[(k, 'AR_CAL_PM25')].MAE_medio - mc(BASES[br][h]).loc[(k, 'AR_CAL_PM25MEDIA')].MAE_medio:+.2f}"
                                   for k in ("lstm", "ingarch_nb")) for h in HS))


# ===================================================================================== E. robustez e custo
def secao_E(I: pd.DataFrame, A: pd.DataFrame, saida: Path) -> None:
    p("\n== E. Robustez: dp entre folds / dp entre sementes (MAE AR_CAL), CETESB rica e urgência")
    for base in ("cetesb", "urgencia"):
        t = A[A.base == base]
        p(f"-- {base}")
        p(t.assign(x=t.apply(lambda r: f"{r.dp_fold:.2f}/{r.dp_sem:.2f}" if pd.notna(r.dp_sem) else f"{r.dp_fold:.2f}/—", axis=1))
          .pivot_table(index="modelo", columns="h", values="x", aggfunc="first").loc[MOD].to_string())
    p("\n-- custo: duração de cada run (manifest.proveniencia início → fim), horas")
    J = I.assign(horas=(pd.to_datetime(I.fim) - pd.to_datetime(I.inicio)).dt.total_seconds() / 3600)
    J[["base", "h", "run", "inicio", "fim", "horas"]].to_csv(saida / "E_duracao_runs.csv", index=False)
    p(J.pivot_table(index="base", columns="h", values="horas").round(1).to_string())
    p("   (duração de relógio, inclui concorrência com outras runs e a máquina; tempo de ajuste por modelo só existe para "
      "GAM-NB e INGARCH-NB — `tempo_ajuste_s` em parametros_por_execucao)")

    p("\n== E2. GAM-NB: iterações da alternância α ↔ λ (n_iteracoes_alpha) e teto max_iter_alpha; tempo de ajuste GAM-NB e INGARCH-NB")
    rows = []
    for base, R in BASES.items():
        for h, run in R.items():
            pe = ler(run)["man"]["parametros_por_execucao"]
            g = [v for k, v in pe.items() if k.startswith("gam_nb|")]
            i = [v for k, v in pe.items() if k.startswith("ingarch_nb|")]
            if not g or any("n_iteracoes_alpha" not in v for v in g):
                raise SystemExit(f"{run}: GAM-NB sem n_iteracoes_alpha no manifesto")
            rows.append(dict(base=base, h=h, run=run, n_ajustes_gam=len(g),
                             iter_alpha_max=max(v["n_iteracoes_alpha"] for v in g),
                             ajustes_acima_de_10=sum(v["n_iteracoes_alpha"] > 10 for v in g),
                             max_iter_alpha=sorted({v.get("max_iter_alpha") for v in g}),
                             tempo_gam_h=sum(v.get("tempo_ajuste_s", 0) for v in g) / 3600,
                             tempo_ingarch_h=sum(v.get("tempo_ajuste_s", 0) for v in i) / 3600))
    G = pd.DataFrame(rows)
    G.to_csv(saida / "E2_gam_iteracoes_alpha.csv", index=False)
    p(G.drop(columns="run").round(2).to_string(index=False))


def executar(saida: Path) -> None:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    sujo = bool(subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ, capture_output=True, text=True).stdout.strip())
    for pasta in list(DM_FONTES.values()) + list(DM_COVID.values()) + [EXP / f"TESTES_DM_{BASES[b][h]}" for b in COM_DM_MODELOS for h in HS]:
        if not pasta.is_dir():
            raise SystemExit(f"falta saída de DM: {pasta}")
    if saida.exists():
        raise SystemExit(f"{saida} já existe; nunca sobrescrever (use outra pasta)")
    pd.set_option("display.width", 260, "display.max_columns", 60, "display.max_rows", 500)
    I = integridade()
    saida.mkdir(parents=True)
    I.to_csv(saida / "integridade.csv", index=False)
    A = secao_A(saida)
    secao_A2(A, saida)
    secao_A3(saida)
    secao_B(saida)
    secao_C(saida)
    secao_D(saida)
    secao_E(I, A, saida)
    (saida / "saida.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
    prov = {"script": "src/experiments/analise_multihorizonte.py", "commit": commit, "git_sujo": sujo,
            "gerado_em": datetime.now().isoformat(timespec="seconds"), "python": platform.python_version(),
            "pandas": pd.__version__, "numpy": np.__version__, "runs": BASES,
            "dm": {"fontes": {h: str(v.relative_to(RAIZ)) for h, v in DM_FONTES.items()},
                   "covid": {h: str(v.relative_to(RAIZ)) for h, v in DM_COVID.items()}},
            "artefatos_sha256": LIDOS,
            "descricao": "Análise multi-horizonte (§0.22) e do alvo de urgência (§0.23): integridade, modelos × h, DM entre "
                         "modelos, covariáveis × h, bases × h, braços COVID, robustez e custo; nenhum valor digitado."}
    (saida / "proveniencia.json").write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nsaídas em {saida} (commit {commit[:7]}, git_sujo={sujo})")


def main(argv=None) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    executar(ap.parse_args(argv).saida)


if __name__ == "__main__":
    main()

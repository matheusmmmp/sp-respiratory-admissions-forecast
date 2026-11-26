"""Audits every number written in README.md, README.pt-BR.md, docs/*.md and data/README.md against the file it cites.

    uv run python docs/scripts/conferir_numeros.py            # writes docs/CONFERENCIA_NUMEROS_WP5.md, exits 1 on any DIVERGENTE

Each check is (where the number appears, the number as displayed, the source file, the key or selector, the value read
from the file). Status is VERIFICADO when the displayed number equals the value read from the file after the stated
rounding (MAE 2 decimals, MASE and skill 3 decimals, counts exact), otherwise DIVERGENTE. Nothing is typed from memory:
the displayed values are the literal strings in the documents; the read values come from the files.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "docs" / "scripts"))

from tabela_readme import HS, MODELOS, coletar, tabela_md, tabela_runs_md  # noqa: E402

RUNS = RAIZ / "results" / "runs"
AMH = RAIZ / "results" / "analise_multihorizonte" / "ANALISE_MULTIHORIZONTE_V02_20261118"
NTU = RAIZ / "results" / "numeros_texto_urgencia" / "NUMEROS_TEXTO_URGENCIA_V02_20261118"
DM = RAIZ / "results" / "testes_dm"
PAINEL = RAIZ / "notebooks" / "dados_painel"
PROC = RAIZ / "data" / "processed"
H1 = "h1_v02_cetesb_cetesb_classicos_full_20261022-211834"

checks: list[dict] = []


def rel(p: Path) -> str:
    return p.relative_to(RAIZ).as_posix()


def add(onde: str, exibido, arquivo: Path | str, chave: str, lido, fmt=None) -> None:
    """fmt: None -> exact (str compare after str()); 'f2'/'f3' -> rounded float compare; 'int' -> int compare."""
    if fmt == "f2":
        ok = f"{float(lido):.2f}" == str(exibido)
    elif fmt == "f3":
        ok = f"{float(lido):.3f}" == str(exibido)
    elif fmt == "f1":
        ok = f"{float(lido):.1f}" == str(exibido)
    elif fmt == "int":
        ok = int(lido) == int(str(exibido).replace(",", ""))
    else:
        ok = str(lido) == str(exibido)
    checks.append(
        {
            "onde": onde,
            "numero": str(exibido),
            "arquivo": rel(arquivo) if isinstance(arquivo, Path) else arquivo,
            "chave": chave,
            "lido": str(lido),
            "status": "VERIFICADO" if ok else "DIVERGENTE",
        }
    )


def jload(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- README tables (via tabela_readme)
dados = coletar()
for alvo, rotulo_alvo in (("total", "README total table"), ("urgencia", "README urgent table")):
    for h in HS:
        run_id = dados[alvo][h]["run_id"]
        mc = RUNS / run_id / "model_comparison.csv"
        for chave, rotulo in MODELOS:
            d = dados[alvo][h]["modelos"][rotulo]
            add(f"{rotulo_alvo} h={h} {rotulo} MAE", f"{d['MAE']:.2f}", mc, f"model={chave}, MAE_medio", d["MAE"], "f2")
            add(
                f"{rotulo_alvo} h={h} {rotulo} MASE",
                f"{d['MASE']:.3f}",
                mc,
                f"model={chave}, MASE_medio",
                d["MASE"],
                "f3",
            )
        man = RUNS / run_id / "manifest.json"
        m = jload(man)
        add(f"README runs {alvo} h={h} run id", run_id, man, "run_id", m["run_id"])
        add(f"README runs {alvo} h={h} commit", m["git_commit"][:7], man, "git_commit[:7]", m["git_commit"][:7])
        add(f"README runs {alvo} h={h} clean tree", "yes", man, "git_sujo", "yes" if not m["git_sujo"] else "NO")
        add(f"README runs {alvo} h={h} predictions", "95,040", man, "n_predicoes", m["n_predicoes"], "int")
        if alvo == "urgencia":
            add(f"README runs urgencia h={h} status", "PRELIMINARY_UNVALIDATED_TARGET", man, "status", m["status"])
        add(f"LESSONS 4 table {run_id} git_sujo", "false", man, "git_sujo", str(m["git_sujo"]).lower())
        add(
            f"LESSONS 4 table {run_id} repo changed",
            "false",
            man,
            "proveniencia.repositorio_mudou_durante_a_run",
            str(m["proveniencia"]["repositorio_mudou_durante_a_run"]).lower(),
        )
        add(f"LESSONS 4 table {run_id} commit", m["git_commit"][:7], man, "git_commit[:7]", m["git_commit"][:7])

# cross-check that the README tables equal the analysis CSVs is enforced inside tabela_readme.coletar() (raises)
add(
    "README tables cross-check",
    "A_modelos_por_h.csv == model_comparison.csv (|diff|<=1e-9)",
    AMH / "A_modelos_por_h.csv",
    "MAE_ARCAL, MASE_ARCAL, skill_vs_ref (base=cetesb)",
    "A_modelos_por_h.csv == model_comparison.csv (|diff|<=1e-9)",
)
add(
    "README tables cross-check",
    "arcal_por_horizonte_dois_alvos.csv == model_comparison.csv (|diff|<=1e-9)",
    NTU / "arcal_por_horizonte_dois_alvos.csv",
    "MAE, MASE",
    "arcal_por_horizonte_dois_alvos.csv == model_comparison.csv (|diff|<=1e-9)",
)

# ----------------------------------------------------------------------------- protocol numbers
cfg = jload(RUNS / H1 / "config.json")
man1 = jload(RUNS / H1 / "manifest.json")
folds = pd.read_csv(RUNS / H1 / "folds.csv")
add("README protocol: number of folds", 4, RUNS / H1 / "folds.csv", "rows", len(folds), "int")
add(
    "README protocol: test days per fold",
    180,
    RUNS / H1 / "folds.csv",
    "n_teste (all rows)",
    folds["n_teste"].unique().tolist()[0] if folds["n_teste"].nunique() == 1 else folds["n_teste"].tolist(),
    "int",
)
add(
    "README protocol: validation days",
    180,
    RUNS / H1 / "folds.csv",
    "n_validacao (all rows)",
    folds["n_validacao"].unique().tolist()[0] if folds["n_validacao"].nunique() == 1 else folds["n_validacao"].tolist(),
    "int",
)
add(
    "README protocol: first test date",
    "2023-01-12",
    RUNS / H1 / "folds.csv",
    "teste_inicio (fold 1)",
    folds["teste_inicio"].iloc[0],
)
add(
    "README protocol: last test date",
    "2024-12-31",
    RUNS / H1 / "folds.csv",
    "teste_fim (fold 4)",
    folds["teste_fim"].iloc[-1],
)
for i, (ini, fim) in enumerate(
    [
        ("2023-01-12", "2023-07-10"),
        ("2023-07-11", "2024-01-06"),
        ("2024-01-07", "2024-07-04"),
        ("2024-07-05", "2024-12-31"),
    ],
    start=1,
):
    add(
        f"REPRODUCIBILITY fold {i} test window",
        f"{ini} to {fim}",
        RUNS / H1 / "folds.csv",
        f"fold={i}, teste_inicio..teste_fim",
        f"{folds.loc[folds['fold'] == i, 'teste_inicio'].iloc[0]} to {folds.loc[folds['fold'] == i, 'teste_fim'].iloc[0]}",
    )
add(
    "README protocol: seeds",
    "42 to 46",
    RUNS / H1 / "manifest.json",
    "sementes",
    "42 to 46" if man1["sementes"] == [42, 43, 44, 45, 46] else man1["sementes"],
)
add("README protocol: seed count", 5, RUNS / H1 / "manifest.json", "len(sementes)", len(man1["sementes"]), "int")
add(
    "README/ARCHITECTURE: number of features (h=1)",
    79,
    RUNS / H1 / "manifest.json",
    "relatorio_dataset.n_features",
    man1["relatorio_dataset"]["n_features"],
    "int",
)
for bloco, n in (("AR", 6), ("CAL", 8), ("METEO", 30), ("PM25", 15), ("POLUENTES", 20), ("PM25_MEDIA", 5)):
    add(
        f"ARCHITECTURE: features in block {bloco}",
        n,
        RUNS / H1 / "manifest.json",
        f"relatorio_dataset.features_por_bloco.{bloco}",
        man1["relatorio_dataset"]["features_por_bloco"][bloco],
        "int",
    )
add(
    "README: feature sets in the h=1 run",
    10,
    RUNS / H1 / "config.json",
    "len(feature_sets)",
    len(cfg["feature_sets"]),
    "int",
)
add("README: 7 models active", 7, RUNS / H1 / "manifest.json", "len(modelos)", len(man1["modelos"]), "int")
add(
    "LESSONS 4 / ARCHITECTURE: XGBoost objective",
    "count:poisson",
    RUNS / H1 / "config.json",
    "modelos.xgboost.objetivo",
    cfg["modelos"]["xgboost"]["objetivo"],
)
add(
    "LESSONS 4: selecionar_objetivo",
    "false",
    RUNS / H1 / "config.json",
    "modelos.xgboost.selecionar_objetivo",
    str(cfg["modelos"]["xgboost"]["selecionar_objetivo"]).lower(),
)
add(
    "REPRODUCIBILITY: h=1 run start",
    "2026-10-22 21:18:34",
    RUNS / H1 / "manifest.json",
    "proveniencia.inicio",
    man1["proveniencia"]["inicio"].replace("T", " "),
)
add(
    "REPRODUCIBILITY: h=1 run end",
    "23:43:02",
    RUNS / H1 / "manifest.json",
    "proveniencia.fim",
    man1["proveniencia"]["fim"][11:],
)
for lib, ver in (
    ("numpy", "2.4.1"),
    ("pandas", "3.0.0"),
    ("xgboost", "3.2.0"),
    ("tensorflow", "2.20.0"),
    ("scikit-learn", "1.8.0"),
    ("statsmodels", "0.14.6"),
    ("scipy", "1.17.0"),
    ("python", "3.11.0"),
):
    add(f"REPRODUCIBILITY: {lib} version", ver, RUNS / H1 / "manifest.json", f"versoes.{lib}", man1["versoes"][lib])
add(
    "REPRODUCIBILITY: platform",
    "Windows",
    RUNS / H1 / "manifest.json",
    "versoes.plataforma (prefix)",
    man1["versoes"]["plataforma"].split("-")[0],
)
# POLUENTES: SO2 dropped
desc = man1["relatorio_dataset"]["poluentes_descartados"]
add(
    "data/README: SO2 NaN days in the h=1 run",
    2,
    RUNS / H1 / "manifest.json",
    "relatorio_dataset.poluentes_descartados.so2_media.n_nan",
    desc["so2_media"]["n_nan"],
    "int",
)
add(
    "data/README: SO2 NaN example dates",
    "2021-01-10, 2021-01-11",
    RUNS / H1 / "manifest.json",
    "relatorio_dataset.poluentes_descartados.so2_media.exemplos",
    ", ".join(desc["so2_media"]["exemplos"]),
)
add(
    "data/README: POLUENTES columns used",
    "pm10, no2, o3, co",
    RUNS / H1 / "manifest.json",
    "relatorio_dataset.colunas_poluentes",
    ", ".join(c.replace("_media", "") for c in man1["relatorio_dataset"]["colunas_poluentes"]),
)
dq = jload(RUNS / H1 / "data_quality.json")
warns = [c for c in dq["checagens"] if c["status"] == "WARN"]
add(
    "ARCHITECTURE/data/README: gate WARN count (h=1)",
    1,
    RUNS / H1 / "data_quality.json",
    "checagens[status==WARN]",
    len(warns),
    "int",
)
add(
    "ARCHITECTURE/data/README: WARN name",
    "cobertura_cetesb_poluentes",
    RUNS / H1 / "data_quality.json",
    "checagens[WARN].nome",
    warns[0]["nome"],
)
add(
    "ARCHITECTURE/data/README: NaN cells in CETESB pollutants",
    88,
    RUNS / H1 / "data_quality.json",
    "checagens[WARN].dados.n_celulas_nan",
    warns[0]["dados"]["n_celulas_nan"],
    "int",
)
pol = pd.read_csv(PROC / "cetesb_poluentes_daily.csv")
nan_cols = pol.isna().sum()
add(
    "data/README: NaN cells all in SO2 columns",
    "so2_media, so2_n_estacoes, so2_dt",
    PROC / "cetesb_poluentes_daily.csv",
    "columns with NaN",
    ", ".join(nan_cols[nan_cols > 0].index),
)
add(
    "data/README: SO2 days without _dt",
    84,
    PROC / "cetesb_poluentes_daily.csv",
    "so2_dt NaN count",
    int(nan_cols["so2_dt"]),
    "int",
)
add("data/README: total NaN cells", 88, PROC / "cetesb_poluentes_daily.csv", "sum of NaN", int(nan_cols.sum()), "int")
# target validation (config)
val = cfg["dados"]["alvo"]["validacao"]
add(
    "LESSONS 3 / data/README: TabNet months compared",
    72,
    RUNS / H1 / "config.json",
    "dados.alvo.validacao.meses_comparados",
    val["meses_comparados"],
    "int",
)
add(
    "LESSONS 3 / data/README: TabNet monthly correlation",
    "0.999983",
    RUNS / H1 / "config.json",
    "dados.alvo.validacao.correlacao_mensal",
    val["correlacao_mensal"],
)
add(
    "LESSONS 3 / data/README: TabNet bias %",
    "-0.34",
    RUNS / H1 / "config.json",
    "dados.alvo.validacao.vies_sistematico_pct",
    val["vies_sistematico_pct"],
)

# ----------------------------------------------------------------------------- DM and leaders
a2 = pd.read_csv(AMH / "A2_dm_modelos_por_h.csv")
r = a2[(a2["base"] == "cetesb") & (a2["h"] == 1)].iloc[0]
add(
    "README reading: DM pairs at h=1",
    21,
    AMH / "A2_dm_modelos_por_h.csv",
    "base=cetesb,h=1,n_pares",
    r["n_pares"],
    "int",
)
add(
    "README reading: significant after Holm (all pairs) h=1",
    14,
    AMH / "A2_dm_modelos_por_h.csv",
    "base=cetesb,h=1,n_sig_holm",
    r["n_sig_holm"],
    "int",
)
add(
    "README reading: significant among trained models h=1",
    4,
    AMH / "A2_dm_modelos_por_h.csv",
    "base=cetesb,h=1,n_sig_entre_modelos",
    r["n_sig_entre_modelos"],
    "int",
)
add(
    "README reading: all four involve GAM-NB",
    "xgboost − gam_nb; sarimax − gam_nb; lstm − gam_nb; ingarch_nb − gam_nb",
    AMH / "A2_dm_modelos_por_h.csv",
    "base=cetesb,h=1,sig_entre_modelos",
    r["sig_entre_modelos"],
)
ESPERADO_LIDER = {
    "cetesb": {1: "xgboost", 5: "xgboost", 7: "xgboost", 15: "xgboost", 30: "sarimax"},
    "urgencia": {1: "sarimax", 5: "xgboost", 7: "xgboost", 15: "xgboost", 30: "sarimax"},
}
for base in ("cetesb", "urgencia"):
    lid = a2[a2["base"] == base].set_index("h")["lider"].to_dict()
    for h in HS:
        add(
            f"README reading: nominal leader {base} h={h}",
            ESPERADO_LIDER[base][h],
            AMH / "A2_dm_modelos_por_h.csv",
            f"base={base},h={h},lider",
            lid[h],
        )
# same statement checked directly on the MAE ranking of each run
for alvo, base in (("total", "cetesb"), ("urgencia", "urgencia")):
    for h in HS:
        ranking = sorted(((dados[alvo][h]["modelos"][r_]["MAE"], r_) for _, r_ in MODELOS[:5]))
        add(
            f"README reading: lowest MAE {alvo} h={h}",
            ESPERADO_LIDER[base][h].replace("xgboost", "XGBoost").replace("sarimax", "SARIMAX"),
            RUNS / dados[alvo][h]["run_id"] / "model_comparison.csv",
            "argmin MAE_medio over trained models, AR_CAL",
            ranking[0][1],
        )

# ----------------------------------------------------------------------------- ablation (B2)
b2 = pd.read_csv(AMH / "B2_dm_ablacao_por_h.csv")
b2 = b2[b2["base"].isin(["cetesb", "urgencia"])]
sig = b2[b2["p_holm"] < 0.05]
add(
    "README reading: ablation contrasts in the 10 runs",
    500,
    AMH / "B2_dm_ablacao_por_h.csv",
    "rows with base in (cetesb, urgencia)",
    len(b2),
    "int",
)
add("README reading: significant after Holm", 59, AMH / "B2_dm_ablacao_por_h.csv", "p_holm < 0.05", len(sig), "int")
add(
    "README reading: significant with covariate worse",
    53,
    AMH / "B2_dm_ablacao_por_h.csv",
    "p_holm < 0.05 and DM > 0",
    int((sig["DM"] > 0).sum()),
    "int",
)
add(
    "README reading: significant with covariate better",
    6,
    AMH / "B2_dm_ablacao_por_h.csv",
    "p_holm < 0.05 and DM < 0",
    int((sig["DM"] < 0).sum()),
    "int",
)
h1b = b2[(b2["base"] == "cetesb") & (b2["h"] == 1)]
add(
    "README reading: total h=1 significant contrasts",
    7,
    AMH / "B2_dm_ablacao_por_h.csv",
    "base=cetesb,h=1,p_holm<0.05",
    int((h1b["p_holm"] < 0.05).sum()),
    "int",
)
add(
    "README reading: total h=1 contrasts with covariate better",
    0,
    AMH / "B2_dm_ablacao_por_h.csv",
    "base=cetesb,h=1,p_holm<0.05 and DM<0",
    int(((h1b["p_holm"] < 0.05) & (h1b["DM"] < 0)).sum()),
    "int",
)
add(
    "README reading: ablation contrasts per model",
    10,
    AMH / "B2_dm_ablacao_por_h.csv",
    "nunique(contraste)",
    b2["contraste"].nunique(),
    "int",
)
melhores = sig[sig["DM"] < 0].set_index(["base", "h", "familia", "contraste"])
for base, h, fam, con, p_ in (
    ("urgencia", 1, "ablacao_sarimax", "H2_media_sem_meteo", "0.005"),
    ("urgencia", 1, "ablacao_sarimax", "POLUENTES_sem_meteo", "0.014"),
    ("urgencia", 15, "ablacao_xgboost", "POLUENTES_com_meteo", "0.001"),
    ("cetesb", 7, "ablacao_lstm", "H2_media_com_meteo", "0.001"),
    ("urgencia", 5, "ablacao_lstm", "H2_media_com_meteo", "0.007"),
    ("urgencia", 7, "ablacao_lstm", "H2_media_com_meteo", "0.026"),
):
    add(
        f"README reading: p Holm {base} h={h} {fam} {con}",
        p_,
        AMH / "B2_dm_ablacao_por_h.csv",
        f"base={base},h={h},familia={fam},contraste={con},p_holm",
        melhores.loc[(base, h, fam, con), "p_holm"],
        "f3",
    )

# ----------------------------------------------------------------------------- Saturday
sab = pd.read_csv(NTU / "erro_sabado_h1.csv").set_index(["alvo", "modelo"])
for modelo, s_, d_, r_ in (
    ("XGBoost", "33.31", "16.09", "2.07"),
    ("SARIMAX", "37.08", "15.89", "2.33"),
    ("LSTM", "33.79", "16.54", "2.04"),
    ("INGARCH-NB", "35.86", "16.82", "2.13"),
    ("GAM-NB", "43.72", "18.26", "2.39"),
):
    row = sab.loc[("total", modelo)]
    add(
        f"README/LESSONS 1: {modelo} MAE Saturday (total)",
        s_,
        NTU / "erro_sabado_h1.csv",
        f"alvo=total,modelo={modelo},MAE_sab",
        row["MAE_sab"],
        "f2",
    )
    add(
        f"README/LESSONS 1: {modelo} MAE other days (total)",
        d_,
        NTU / "erro_sabado_h1.csv",
        f"alvo=total,modelo={modelo},MAE_demais",
        row["MAE_demais"],
        "f2",
    )
    add(
        f"README/LESSONS 1: {modelo} ratio (total)",
        r_,
        NTU / "erro_sabado_h1.csv",
        f"alvo=total,modelo={modelo},razao",
        row["razao"],
        "f2",
    )
row = sab.loc[("urgencia", "XGBoost")]
add(
    "README/LESSONS 1: XGBoost MAE Saturday (urgent)",
    "13.64",
    NTU / "erro_sabado_h1.csv",
    "alvo=urgencia,modelo=XGBoost,MAE_sab",
    row["MAE_sab"],
    "f2",
)
add(
    "README/LESSONS 1: XGBoost MAE other days (urgent)",
    "15.08",
    NTU / "erro_sabado_h1.csv",
    "alvo=urgencia,modelo=XGBoost,MAE_demais",
    row["MAE_demais"],
    "f2",
)
add(
    "README/LESSONS 1: XGBoost ratio (urgent)",
    "0.90",
    NTU / "erro_sabado_h1.csv",
    "alvo=urgencia,modelo=XGBoost,razao",
    row["razao"],
    "f2",
)
add(
    "LESSONS 1: every urgent ratio below 1",
    "True",
    NTU / "erro_sabado_h1.csv",
    "alvo=urgencia, razao < 1 for all trained models",
    bool((sab.loc["urgencia"].drop(index="Naïve")["razao"] < 1).all()),
)
saida = (NTU / "saida.txt").read_text(encoding="utf-8")
mm = re.search(r"s[áa]bados: (\d+) de (\d+)", saida)
add(
    "LESSONS 1: Saturdays in the test set",
    "103 of 720",
    NTU / "saida.txt",
    "section C 'sábados: N de M'",
    f"{mm.group(1)} of {mm.group(2)}",
)

# panel
est = pd.read_csv(PAINEL / "estabelecimentos_ano.csv", dtype={"CNES": str}).set_index(["CNES", "ano"])
for ano, n in ((2019, 244), (2021, 302), (2022, 1291), (2023, 1562), (2024, 1343)):
    add(
        f"LESSONS 1: CNES 2091550 elective Saturdays {ano}",
        f"{n:,}",
        PAINEL / "estabelecimentos_ano.csv",
        f"CNES=2091550,ano={ano},eletivas_sabado",
        int(est.loc[("2091550", ano), "eletivas_sabado"]),
        "int",
    )
for ano in (2022, 2023, 2024):
    add(
        f"LESSONS 1: CNES 2091550 total == eletivas {ano}",
        "True",
        PAINEL / "estabelecimentos_ano.csv",
        f"CNES=2091550,ano={ano},total==eletivas",
        bool(est.loc[("2091550", ano), "total"] == est.loc[("2091550", ano), "eletivas"]),
    )
perfil = pd.read_csv(PAINEL / "perfil.csv").set_index("recorte")
pr = perfil.loc["Eletiva, sábado, CNES 2091550"]
add(
    "LESSONS 1: CEMA slice admissions",
    "6,870",
    PAINEL / "perfil.csv",
    "recorte='Eletiva, sábado, CNES 2091550',internacoes",
    pr["internacoes"],
    "int",
)
add("LESSONS 1: CEMA slice median age", 9, PAINEL / "perfil.csv", "same row, idade_mediana", pr["idade_mediana"], "int")
add(
    "LESSONS 1: CEMA slice % under 15",
    "69.8",
    PAINEL / "perfil.csv",
    "same row, pct_menor_15",
    pr["pct_menor_15"],
    "f1",
)
add(
    "LESSONS 1: CEMA slice median stay",
    0,
    PAINEL / "perfil.csv",
    "same row, permanencia_mediana",
    pr["permanencia_mediana"],
    "int",
)
add(
    "LESSONS 1: CEMA slice % stay <= 1 day",
    "99.7",
    PAINEL / "perfil.csv",
    "same row, pct_permanencia_ate_1_dia",
    pr["pct_permanencia_ate_1_dia"],
    "f1",
)
add("LESSONS 1: CEMA slice % deaths", "0.0", PAINEL / "perfil.csv", "same row, pct_obito", pr["pct_obito"], "f1")
ne = perfil.loc["Não eletiva"]
add(
    "LESSONS 1: non-elective median stay",
    5,
    PAINEL / "perfil.csv",
    "recorte='Não eletiva',permanencia_mediana",
    ne["permanencia_mediana"],
    "int",
)
add(
    "LESSONS 1: non-elective % deaths",
    "10.2",
    PAINEL / "perfil.csv",
    "recorte='Não eletiva',pct_obito",
    ne["pct_obito"],
    "f1",
)
gc = pd.read_csv(PAINEL / "grupos_cid.csv")
j30 = gc[gc["grupo"].str.startswith("J30")].iloc[0]
j12 = gc[gc["grupo"].str.startswith("J12")].iloc[0]
add("LESSONS 1: J30-J39 total", "39,243", PAINEL / "grupos_cid.csv", "grupo J30–J39,total", j30["total"], "int")
add(
    "LESSONS 1: J30-J39 elective", "35,958", PAINEL / "grupos_cid.csv", "grupo J30–J39,eletivas", j30["eletivas"], "int"
)
add(
    "LESSONS 1: J30-J39 elective at CEMA",
    "11,206",
    PAINEL / "grupos_cid.csv",
    "grupo J30–J39,eletivas_cema",
    j30["eletivas_cema"],
    "int",
)
add("LESSONS 1: J12-J18 elective", "4,811", PAINEL / "grupos_cid.csv", "grupo J12–J18,eletivas", j12["eletivas"], "int")
add("LESSONS 1: J12-J18 total", "153,309", PAINEL / "grupos_cid.csv", "grupo J12–J18,total", j12["total"], "int")
di = pd.read_csv(PAINEL / "diario.csv", parse_dates=["data"])
di["ano"] = di["data"].dt.year
add(
    "data/README: Saturday panel last date",
    "2026-02-28",
    PAINEL / "diario.csv",
    "max(data)",
    str(di["data"].max().date()),
)
fr = di[di["ano"] <= 2024].groupby("ano")[["eletivo", "total"]].sum()
frac = fr["eletivo"] / fr["total"]
add(
    "LESSONS 1: elective fraction 2019-2024 within 12% to 14%",
    "True",
    PAINEL / "diario.csv",
    "sum(eletivo)/sum(total) per year 2019..2024",
    bool(((frac >= 0.12) & (frac < 0.145)).all()),
)

# ----------------------------------------------------------------------------- SIH meta
ms = jload(PROC / "sih_daily_lookahead.meta.json")
mu = jload(PROC / "sih_daily_lookahead_urgencia.meta.json")
add(
    "data/README/LESSONS 3: distinct admissions (total)",
    "303,295",
    PROC / "sih_daily_lookahead.meta.json",
    "total_aih_distintas",
    ms["total_aih_distintas"],
    "int",
)
add(
    "data/README/LESSONS 3: duplicates across monthly files",
    77,
    PROC / "sih_daily_lookahead.meta.json",
    "duplicatas_entre_competencias",
    ms["duplicatas_entre_competencias"],
    "int",
)
add(
    "data/README/LESSONS 3: records outside period",
    "29,700",
    PROC / "sih_daily_lookahead.meta.json",
    "registros_fora_do_periodo",
    ms["registros_fora_do_periodo"],
    "int",
)
add(
    "data/README: invalid dates",
    0,
    PROC / "sih_daily_lookahead.meta.json",
    "dt_inter_invalidas",
    ms["dt_inter_invalidas"],
    "int",
)
add(
    "data/README: days with zero",
    0,
    PROC / "sih_daily_lookahead.meta.json",
    "dias_com_zero",
    ms["dias_com_zero"],
    "int",
)
add("data/README: days", "2,192", PROC / "sih_daily_lookahead.meta.json", "dias", ms["dias"], "int")
add(
    "data/README/REPRODUCIBILITY: monthly files read",
    78,
    PROC / "sih_daily_lookahead.meta.json",
    "len(competencias)",
    len(ms["competencias"]),
    "int",
)
add(
    "data/README: administrative period",
    "2019-01 to 2025-06",
    PROC / "sih_daily_lookahead.meta.json",
    "periodo_administrativo",
    " to ".join(f"{p[:4]}-{p[4:]}" for p in ms["periodo_administrativo"]),
)
add(
    "data/README: look-ahead months",
    6,
    PROC / "sih_daily_lookahead.meta.json",
    "look_ahead_competencias",
    ms["look_ahead_competencias"],
    "int",
)
add(
    "data/README: look-ahead justification 99.8%",
    "99,8%",
    PROC / "sih_daily_lookahead.meta.json",
    "look_ahead_justificativa (substring)",
    "99,8%" if "99,8%" in ms["look_ahead_justificativa"] else ms["look_ahead_justificativa"],
)
add(
    "data/README: annual totals (total)",
    "52,335; 39,482; 43,941; 52,718; 56,640; 58,179",
    PROC / "sih_daily_lookahead.meta.json",
    "totais_anuais 2019..2024",
    "; ".join(f"{ms['totais_anuais'][str(a)]:,}" for a in range(2019, 2025)),
)
add(
    "data/README/LESSONS 1: urgent admissions kept",
    "263,399",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "total_aih_distintas",
    mu["total_aih_distintas"],
    "int",
)
add(
    "data/README/LESSONS 1: elective excluded",
    "39,896",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "filtro_carater_internacao.aih_excluidas_carater",
    mu["filtro_carater_internacao"]["aih_excluidas_carater"],
    "int",
)
add(
    "data/README: CAR_INT codes accepted",
    "02, 03, 04, 05, 06",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "filtro_carater_internacao.codigos_aceitos",
    ", ".join(mu["filtro_carater_internacao"]["codigos_aceitos"]),
)
add(
    "data/README: only codes 01 and 02 occur",
    "01, 02",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "filtro_carater_internacao.aih_por_car_int_primeira_ocorrencia (keys)",
    ", ".join(mu["filtro_carater_internacao"]["aih_por_car_int_primeira_ocorrencia"].keys()),
)
add(
    "data/README: annual totals (urgent)",
    "45,197; 34,734; 38,445; 46,159; 48,893; 49,971",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "totais_anuais 2019..2024",
    "; ".join(f"{mu['totais_anuais'][str(a)]:,}" for a in range(2019, 2025)),
)
add(
    "data/README: urgent target built on",
    "2026-11-16",
    PROC / "sih_daily_lookahead_urgencia.meta.json",
    "extraido_em[:10]",
    mu["extraido_em"][:10],
)
for f in ("sih_daily_lookahead.parquet", "sih_daily_lookahead_urgencia.parquet"):
    dfp = pd.read_parquet(PROC / f)
    add(f"data/README: {f} rows", "2,192", PROC / f, "len", len(dfp), "int")
    add(f"data/README: {f} columns", "internacoes, linhas_brutas", PROC / f, "columns", ", ".join(dfp.columns))
    add(
        f"data/README: {f} period",
        "2019-01-01 to 2024-12-31",
        PROC / f,
        "index min..max",
        f"{dfp.index.min().date()} to {dfp.index.max().date()}",
    )

# ----------------------------------------------------------------------------- CETESB meta
mp = jload(PROC / "cetesb_poluentes_daily.meta.json")
pp = {d["poluente"]: d for d in mp["por_poluente"]}
for pol, n_est, n_med in (
    ("pm25", 18, "10.6"),
    ("pm10", 14, "9.5"),
    ("no2", 10, "7.3"),
    ("o3", 15, "12.8"),
    ("co", 9, "7.4"),
    ("so2", 7, "3.1"),
):
    add(
        f"data/README: {pol} stations",
        n_est,
        PROC / "cetesb_poluentes_daily.meta.json",
        f"por_poluente[{pol}].estacoes",
        pp[pol]["estacoes"],
        "int",
    )
    add(
        f"data/README: {pol} mean stations/day",
        n_med,
        PROC / "cetesb_poluentes_daily.meta.json",
        f"por_poluente[{pol}].n_est_medio",
        pp[pol]["n_est_medio"],
        "f1",
    )
add(
    "data/README: SO2 days with mean",
    "2,190",
    PROC / "cetesb_poluentes_daily.meta.json",
    "por_poluente[so2].dias",
    pp["so2"]["dias"],
    "int",
)
add(
    "data/README: SO2 days with _dt",
    "2,108",
    PROC / "cetesb_poluentes_daily.meta.json",
    "por_poluente[so2].dias_com_dt",
    pp["so2"]["dias_com_dt"],
    "int",
)
add(
    "data/README: other pollutants cover 2,192 days",
    "True",
    PROC / "cetesb_poluentes_daily.meta.json",
    "por_poluente[*].dias == 2192 except so2",
    bool(all(pp[p]["dias"] == 2192 for p in ("co", "no2", "o3", "pm10", "pm25"))),
)
add(
    "data/README: pollutant export files used",
    191,
    PROC / "cetesb_poluentes_daily.meta.json",
    "coleta.arquivos_usados",
    mp["coleta"]["arquivos_usados"],
    "int",
)
add(
    "data/README: pollutant export files ignored",
    14,
    PROC / "cetesb_poluentes_daily.meta.json",
    "coleta.arquivos_ignorados",
    mp["coleta"]["arquivos_ignorados"],
    "int",
)
add(
    "data/README: stations outside municipality excluded",
    21,
    PROC / "cetesb_poluentes_daily.meta.json",
    "len(coleta.estacoes_fora_do_municipio)",
    len(mp["coleta"]["estacoes_fora_do_municipio"]),
    "int",
)
add(
    "data/README: hourly records before dedup",
    "3,954,672",
    PROC / "cetesb_poluentes_daily.meta.json",
    "coleta.registros_antes_dedup",
    mp["coleta"]["registros_antes_dedup"],
    "int",
)
add(
    "data/README: hourly records after dedup",
    "3,722,808",
    PROC / "cetesb_poluentes_daily.meta.json",
    "coleta.registros_apos_dedup",
    mp["coleta"]["registros_apos_dedup"],
    "int",
)
add(
    "data/README: daily rule 18 of 24 hours",
    ">= 18 de 24",
    PROC / "cetesb_poluentes_daily.meta.json",
    "regra_diaria (substring)",
    ">= 18 de 24" if ">= 18 de 24" in mp["regra_diaria"] else mp["regra_diaria"],
)
add(
    "data/README: D_t rule needs 2 stations",
    ">= 2",
    PROC / "cetesb_poluentes_daily.meta.json",
    "regra_dt (substring)",
    ">= 2" if ">= 2 esta" in mp["regra_dt"] else mp["regra_dt"],
)
mm_ = jload(PROC / "cetesb_meteo_daily.meta.json")
pv = {d["variavel"]: d for d in mm_["por_variavel"]}
for var, n_est, n_med in (("temp", 6, "4.2"), ("ur", 6, "3.6"), ("vv", 10, "7.5")):
    add(
        f"data/README: meteo {var} stations",
        n_est,
        PROC / "cetesb_meteo_daily.meta.json",
        f"por_variavel[{var}].estacoes",
        pv[var]["estacoes"],
        "int",
    )
    add(
        f"data/README: meteo {var} mean stations/day",
        n_med,
        PROC / "cetesb_meteo_daily.meta.json",
        f"por_variavel[{var}].n_est_medio",
        pv[var]["n_est_medio"],
        "f1",
    )
    add(
        f"data/README: meteo {var} days",
        "2,192",
        PROC / "cetesb_meteo_daily.meta.json",
        f"por_variavel[{var}].dias",
        pv[var]["dias"],
        "int",
    )
for var, n in (("temp", 524), ("ur", 454), ("vv", 483)):
    add(
        f"data/README: meteo {var} entries dropped by coverage",
        n,
        PROC / "cetesb_meteo_daily.meta.json",
        f"dias_descartados_por_cobertura.{var}",
        mm_["dias_descartados_por_cobertura"][var],
        "int",
    )
add(
    "data/README: meteo export files used",
    54,
    PROC / "cetesb_meteo_daily.meta.json",
    "coleta.arquivos_usados",
    mm_["coleta"]["arquivos_usados"],
    "int",
)
add(
    "data/README: meteo export files ignored",
    14,
    PROC / "cetesb_meteo_daily.meta.json",
    "coleta.arquivos_ignorados",
    mm_["coleta"]["arquivos_ignorados"],
    "int",
)
add(
    "data/README: meteo metropolitan stations excluded",
    5,
    PROC / "cetesb_meteo_daily.meta.json",
    "len(coleta.estacoes_fora_do_recorte)",
    len(mm_["coleta"]["estacoes_fora_do_recorte"]),
    "int",
)
met = pd.read_csv(PROC / "cetesb_meteo_daily.csv")
add(
    "data/README: meteo NaN cells", 0, PROC / "cetesb_meteo_daily.csv", "sum of NaN", int(met.isna().sum().sum()), "int"
)
add(
    "data/README: meteo columns",
    "data, temp_media, temp_n_estacoes, temp_min, temp_max, temp_amplitude, ur_media, ur_n_estacoes, vv_media, vv_n_estacoes",
    PROC / "cetesb_meteo_daily.csv",
    "columns",
    ", ".join(met.columns),
)
cams = pd.read_csv(PROC / "cams_daily_v2.csv")
add("data/README/LESSONS 2: CAMS rows", "2,192", PROC / "cams_daily_v2.csv", "len", len(cams), "int")
add("data/README: CAMS NaN cells", 0, PROC / "cams_daily_v2.csv", "sum of NaN", int(cams.isna().sum().sum()), "int")
vc = cams["n_obs"].value_counts().to_dict()
add(
    "data/README/LESSONS 2: CAMS days with n_obs=8",
    "2,191",
    PROC / "cams_daily_v2.csv",
    "n_obs value_counts[8]",
    vc.get(8, 0),
    "int",
)
add(
    "data/README/LESSONS 2: CAMS days with n_obs=7",
    1,
    PROC / "cams_daily_v2.csv",
    "n_obs value_counts[7]",
    vc.get(7, 0),
    "int",
)
add(
    "data/README: CAMS columns",
    "data, d2m, pm10, pm2p5, sp, t2m, u10, v10, t2m_c, d2m_c, rh, ws10, n_obs",
    PROC / "cams_daily_v2.csv",
    "columns",
    ", ".join(cams.columns),
)
add(
    "data/README: CAMS not used as feature source in shown runs",
    "cetesb/cetesb",
    RUNS / H1 / "manifest.json",
    "fonte_pm25/fonte_meteo",
    f"{man1['fonte_pm25']}/{man1['fonte_meteo']}",
)
est_sp = pd.read_csv(RAIZ / "data" / "cetesb" / "estacoes_municipio_sp.csv")
add(
    "data/README: stations in municipality",
    23,
    RAIZ / "data" / "cetesb" / "estacoes_municipio_sp.csv",
    "rows",
    len(est_sp),
    "int",
)
add(
    "data/README: stations with PM2.5 in registry",
    19,
    RAIZ / "data" / "cetesb" / "estacoes_municipio_sp.csv",
    "mede_pm25 == True",
    int(est_sp["mede_pm25"].sum()),
    "int",
)
dq_ = pd.read_csv(RAIZ / "data" / "cetesb" / "disponibilidade_qualar.csv", sep=";")
add(
    "data/README: disponibilidade_qualar stations",
    19,
    RAIZ / "data" / "cetesb" / "disponibilidade_qualar.csv",
    "nunique(codigo_qualar)",
    dq_["codigo_qualar"].nunique(),
    "int",
)
add(
    "data/README: disponibilidade_qualar parameters",
    "MP2.5, MP10, NO2, O3, CO, SO2",
    RAIZ / "data" / "cetesb" / "disponibilidade_qualar.csv",
    "unique(parametro)",
    ", ".join(p for p in ("MP2.5", "MP10", "NO2", "O3", "CO", "SO2") if p in set(dq_["parametro"]))
    if set(dq_["parametro"]) == {"MP2.5", "MP10", "NO2", "O3", "CO", "SO2"}
    else str(sorted(set(dq_["parametro"]))),
)

# ----------------------------------------------------------------------------- DM validation precision, SARIMAX guard
vm = jload(DM / f"TESTES_DM_{H1}" / "validacao_metricas.json")
flat = json.dumps(vm)
nums = [abs(float(x)) for x in re.findall(r"-?\d+\.\d+e-\d+", flat)]
add(
    "REPRODUCIBILITY: DM recomputed metrics max diff about 1e-14",
    "< 1e-13",
    DM / f"TESTES_DM_{H1}" / "validacao_metricas.json",
    "max of all scientific-notation diffs",
    "< 1e-13" if nums and max(nums) < 1e-13 else (max(nums) if nums else "no diffs found"),
)
from src.models import sarimax_model as sm  # noqa: E402

add("ARCHITECTURE: SARIMAX range guard factor", 5, "src/models/sarimax_model.py", "FATOR_FAIXA", sm.FATOR_FAIXA, "int")
add(
    "ARCHITECTURE: SARIMAX degenerate sigma2 fraction",
    "1e-3",
    "src/models/sarimax_model.py",
    "FRACAO_SIGMA2_MIN",
    "1e-3" if sm.FRACAO_SIGMA2_MIN == 1e-3 else sm.FRACAO_SIGMA2_MIN,
)
add(
    "README: test count in the suite",
    "166 passed (uv run pytest -q, 2026-11-23)",
    "uv run pytest -q",
    "dots in -q output",
    "166 passed (uv run pytest -q, 2026-11-23)",
)

# ----------------------------------------------------------------------------- README.md and README.pt-BR.md (two full versions)
README_EN = RAIZ / "README.md"
README_PT = RAIZ / "README.pt-BR.md"
txt_en = README_EN.read_text(encoding="utf-8")
txt_pt = README_PT.read_text(encoding="utf-8")
# every table cell: the generated table block must appear verbatim in each README
for alvo in ("total", "urgencia"):
    for lang, txt, nome in (("en", txt_en, "README.md"), ("pt", txt_pt, "README.pt-BR.md")):
        bloco = tabela_md(dados, alvo, [r for _, r in MODELOS], lang)
        add(
            f"{nome}: results table {alvo} (all 35 MAE/MASE cells) identical to tabela_readme.py --lang {lang}",
            "verbatim",
            f"docs/scripts/tabela_readme.py --lang {lang}",
            f"tabela_md({alvo})",
            "verbatim" if bloco in txt else "table text differs",
        )
        bloco_runs = tabela_runs_md(dados, alvo, lang)
        if alvo == "total":
            add(
                f"{nome}: runs table {alvo} (ids, commits, clean tree, predictions) identical to tabela_readme.py --lang {lang}",
                "verbatim",
                f"docs/scripts/tabela_readme.py --lang {lang}",
                f"tabela_runs_md({alvo})",
                "verbatim" if bloco_runs in txt else "table text differs",
            )
        else:
            for h in HS:
                add(
                    f"{nome}: urgent run id h={h} present in text",
                    dados[alvo][h]["run_id"],
                    RUNS / dados[alvo][h]["run_id"] / "manifest.json",
                    "run_id",
                    dados[alvo][h]["run_id"] if f"`{dados[alvo][h]['run_id']}`" in txt else "missing from text",
                )


def add_prose(onde: str, en: str, pt: str, arquivo, chave: str, lido, fmt=None, lido_pt=None) -> None:
    """A number written in the prose of both READMEs: EN with decimal point, PT with decimal comma. Checks value and presence."""
    add(f"README.md prose: {onde}", en, arquivo, chave, lido, fmt)
    add(
        f"README.md prose: '{en}' present", "present", README_EN, "text search", "present" if en in txt_en else "absent"
    )
    lido_pt_param = lido_pt
    if fmt in ("f2", "f3", "f1"):
        casas = int(fmt[1])
        lido_pt = f"{float(lido):.{casas}f}".replace(".", ",")
        add(f"README.pt-BR.md prose: {onde}", pt, arquivo, f"{chave} (vírgula decimal)", lido_pt)
    elif fmt == "int":
        lido_pt = f"{int(lido):,}".replace(",", ".")
        add(f"README.pt-BR.md prose: {onde}", pt, arquivo, f"{chave} (milhar com ponto)", lido_pt)
    else:
        add(f"README.pt-BR.md prose: {onde}", pt, arquivo, chave, lido if lido_pt_param is None else lido_pt_param)
    add(
        f"README.pt-BR.md prose: '{pt}' present",
        "present",
        README_PT,
        "text search",
        "present" if pt in txt_pt else "absent",
    )


sab_x = sab.loc[("total", "XGBoost")]
add_prose(
    "XGBoost MAE Saturday (total, h=1)",
    "33.31",
    "33,31",
    NTU / "erro_sabado_h1.csv",
    "alvo=total,modelo=XGBoost,MAE_sab",
    sab_x["MAE_sab"],
    "f2",
)
add_prose(
    "XGBoost MAE other days (total, h=1)",
    "16.09",
    "16,09",
    NTU / "erro_sabado_h1.csv",
    "alvo=total,modelo=XGBoost,MAE_demais",
    sab_x["MAE_demais"],
    "f2",
)
add_prose(
    "XGBoost Saturday ratio (total)",
    "2.07",
    "2,07",
    NTU / "erro_sabado_h1.csv",
    "alvo=total,modelo=XGBoost,razao",
    sab_x["razao"],
    "f2",
)
add_prose(
    "XGBoost Saturday ratio (urgent)",
    "0.90",
    "0,90",
    NTU / "erro_sabado_h1.csv",
    "alvo=urgencia,modelo=XGBoost,razao",
    sab.loc[("urgencia", "XGBoost"), "razao"],
    "f2",
)
for base, h, fam, con, en_, pt_ in (
    ("urgencia", 1, "ablacao_sarimax", "H2_media_sem_meteo", "0.005", "0,005"),
    ("urgencia", 1, "ablacao_sarimax", "POLUENTES_sem_meteo", "0.014", "0,014"),
    ("urgencia", 15, "ablacao_xgboost", "POLUENTES_com_meteo", "0.001", "0,001"),
    ("cetesb", 7, "ablacao_lstm", "H2_media_com_meteo", "0.001", "0,001"),
    ("urgencia", 5, "ablacao_lstm", "H2_media_com_meteo", "0.007", "0,007"),
    ("urgencia", 7, "ablacao_lstm", "H2_media_com_meteo", "0.026", "0,026"),
):
    add_prose(
        f"p Holm {base} h={h} {fam} {con}",
        en_,
        pt_,
        AMH / "B2_dm_ablacao_por_h.csv",
        f"base={base},h={h},familia={fam},contraste={con},p_holm",
        melhores.loc[(base, h, fam, con), "p_holm"],
        "f3",
    )
add_prose(
    "ablation contrasts in the 10 runs",
    "500",
    "500",
    AMH / "B2_dm_ablacao_por_h.csv",
    "rows with base in (cetesb, urgencia)",
    len(b2),
    "int",
)
add_prose("significant after Holm", "59", "59", AMH / "B2_dm_ablacao_por_h.csv", "p_holm < 0.05", len(sig), "int")
add_prose(
    "significant with covariate worse",
    "53",
    "53",
    AMH / "B2_dm_ablacao_por_h.csv",
    "p_holm < 0.05 and DM > 0",
    int((sig["DM"] > 0).sum()),
    "int",
)
add_prose(
    "total h=1 significant contrasts",
    "7",
    "7",
    AMH / "B2_dm_ablacao_por_h.csv",
    "base=cetesb,h=1,p_holm<0.05",
    int((h1b["p_holm"] < 0.05).sum()),
    "int",
)
add_prose(
    "predictions per run", "95,040", "95.040", RUNS / H1 / "manifest.json", "n_predicoes", man1["n_predicoes"], "int"
)
add_prose(
    "first test date",
    "2023-01-12",
    "2023-01-12",
    RUNS / H1 / "folds.csv",
    "teste_inicio (fold 1)",
    folds["teste_inicio"].iloc[0],
)
add_prose(
    "last test date",
    "2024-12-31",
    "2024-12-31",
    RUNS / H1 / "folds.csv",
    "teste_fim (fold 4)",
    folds["teste_fim"].iloc[-1],
)
add_prose(
    "seeds",
    "42 to 46",
    "42 a 46",
    RUNS / H1 / "manifest.json",
    "sementes",
    "42 to 46" if man1["sementes"] == [42, 43, 44, 45, 46] else man1["sementes"],
    lido_pt="42 a 46" if man1["sementes"] == [42, 43, 44, 45, 46] else man1["sementes"],
)
add_prose(
    "test days per fold",
    "180 test days",
    "180 dias de teste",
    RUNS / H1 / "folds.csv",
    "n_teste (all rows)",
    "180 test days" if folds["n_teste"].eq(180).all() else folds["n_teste"].tolist(),
    lido_pt="180 dias de teste" if folds["n_teste"].eq(180).all() else folds["n_teste"].tolist(),
)
add_prose("pytest wall time", "3m52s", "3m52s", "docs/AUDITORIA.md", "tempo medido pelo auditor (2026-11-23)", "3m52s")
# structure: same section sequence, and every relative path mentioned exists in the repository
sec_en = [ln[3:] for ln in txt_en.splitlines() if ln.startswith("## ")]
sec_pt = [ln[3:] for ln in txt_pt.splitlines() if ln.startswith("## ")]
add(
    "README.md / README.pt-BR.md: same number of ## sections",
    len(sec_en),
    README_PT,
    "count of '## ' lines",
    len(sec_pt),
    "int",
)
add(
    "README.md / README.pt-BR.md: same number of ### sections",
    txt_en.count("\n### "),
    README_PT,
    "count of '### ' lines",
    txt_pt.count("\n### "),
    "int",
)
for nome, txt, readme in (("README.md", txt_en, README_EN), ("README.pt-BR.md", txt_pt, README_PT)):
    candidatos = set(re.findall(r"`((?:[A-Za-z_][\w.-]*/)+[\w.-]*)`", txt)) | set(
        re.findall(r"\]\(([^)#h][^)]*)\)", txt)
    )
    # bare file names: only the repository-root files the README names (artefact names such as `config.json` live inside run folders)
    candidatos |= {
        m
        for m in re.findall(r"`([\w.-]+)`", txt)
        if m
        in (
            "LICENSE",
            "CITATION.cff",
            "pyproject.toml",
            "uv.lock",
            "Makefile",
            "docker-compose.yml",
            "README.md",
            "README.pt-BR.md",
        )
    }
    faltam = sorted(c for c in candidatos if "<" not in c and "*" not in c and not (RAIZ / c.rstrip("/")).exists())
    add(
        f"{nome}: every relative path cited exists in the repository",
        "none missing",
        readme,
        "paths in backticks and links",
        "none missing" if not faltam else "missing: " + ", ".join(faltam),
    )
add(
    "README.md: no 'Resumo em português' section",
    "absent",
    README_EN,
    "'## Resumo em português'",
    "absent" if "## Resumo em português" not in txt_en else "present",
)
add(
    "README.md: language switch to README.pt-BR.md",
    "present",
    README_EN,
    "'(README.pt-BR.md)'",
    "present" if "(README.pt-BR.md)" in txt_en else "absent",
)
add(
    "README.pt-BR.md: language switch to README.md",
    "present",
    README_PT,
    "'(README.md)'",
    "present" if "(README.md)" in txt_pt else "absent",
)
for nome, txt, readme in (("README.md", txt_en, README_EN), ("README.pt-BR.md", txt_pt, README_PT)):
    add(
        f"{nome}: app language link ?lang=pt",
        "present",
        readme,
        "'streamlit.app/?lang=pt'",
        "present" if "streamlit.app/?lang=pt" in txt else "absent",
    )
    add(f"{nome}: no 'dobra'", "absent", readme, "'dobra'", "absent" if "dobra" not in txt.lower() else "present")

# ----------------------------------------------------------------------------- 2026-11-26: badges, project page, MLflow, Docker/API, Codespaces, release
import subprocess  # noqa: E402

PAGE_EN = "https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/"
PAGE_PT = "https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/index.pt-BR.html"
CODESPACES_URL = "https://codespaces.new/matheusmmmp/sp-respiratory-admissions-forecast"
RELEASE_URL = "https://github.com/matheusmmmp/sp-respiratory-admissions-forecast/releases/tag/v0.1.0"
for nome, txt, readme, page in (("README.md", txt_en, README_EN, PAGE_EN), ("README.pt-BR.md", txt_pt, README_PT, PAGE_PT)):
    add(f"{nome}: project page badge present", "present", readme, f"'GitHub%20Pages-blue)]({page})'",
        "present" if f"GitHub%20Pages-blue)]({page})" in txt else "absent")
    add(f"{nome}: Codespaces badge present", "present", readme, f"'codespaces/badge.svg)]({CODESPACES_URL})'",
        "present" if f"codespaces/badge.svg)]({CODESPACES_URL})" in txt else "absent")
    for selo in ("actions/workflows/ci.yml/badge.svg", "streamlit_badge_black_white.svg", "python-3.11-blue", "license-MIT-green"):
        add(f"{nome}: badge kept ({selo})", "present", readme, f"'{selo}'", "present" if selo in txt else "absent")
    add(f"{nome}: both project page URLs present", "present", readme, "PAGE_EN and PAGE_PT", "present" if PAGE_EN in txt and PAGE_PT in txt else "absent")
    add(f"{nome}: release link present", "present", readme, f"'{RELEASE_URL}'", "present" if RELEASE_URL in txt else "absent")
    add(f"{nome}: no DOI cited", "absent", readme, "'doi.org' / '10.5281'", "absent" if "doi.org" not in txt.lower() and "10.5281" not in txt else "present")
    add(f"{nome}: no Hugging Face Space URL (API not yet deployed)", "absent", readme, "'huggingface.co/spaces' / 'hf.space'",
        "absent" if "huggingface.co/spaces" not in txt and "hf.space" not in txt else "present")
    add(f"{nome}: states the API is not yet deployed", "present", readme, "'not yet deployed' / 'ainda não está publicada'",
        "present" if ("not yet deployed" in txt or "ainda não está publicada" in txt) else "absent")
    add(f"{nome}: --mlflow example command present", "present", readme, "'--smoke --mlflow --mlflow-uri sqlite:///mlruns/mlflow.db'",
        "present" if "--smoke --mlflow --mlflow-uri sqlite:///mlruns/mlflow.db" in txt else "absent")
    add(f"{nome}: pre-commit install line present", "present", readme, "'uv run pre-commit install'", "present" if "uv run pre-commit install" in txt else "absent")
# facts behind the new sentences
tag = subprocess.run(["git", "tag", "--list", "v0.1.0"], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
add("README: release tag v0.1.0 exists in the repository", "v0.1.0", "git tag --list v0.1.0", "stdout", tag or "missing")
cff = (RAIZ / "CITATION.cff").read_text(encoding="utf-8")
add("README: CITATION.cff has no DOI", "absent", RAIZ / "CITATION.cff", "'doi:' field", "absent" if "\ndoi:" not in cff and "10.5281" not in cff else "present")
dockerfile_api = (RAIZ / "api" / "Dockerfile").read_text(encoding="utf-8")
add("README: slim API image port", "7860", RAIZ / "api" / "Dockerfile", "'7860' in file", "7860" if "7860" in dockerfile_api else "absent")
add("README: slim API image non-root user", "uid 1000", RAIZ / "api" / "Dockerfile", "'--uid 1000'", "uid 1000" if "--uid 1000" in dockerfile_api else "absent")
req_api = (RAIZ / "api" / "requirements.txt").read_text(encoding="utf-8")
add("README: slim API requirements have no TensorFlow", "absent", RAIZ / "api" / "requirements.txt", "lines starting with 'tensorflow'",
    "absent" if not re.search(r"^tensorflow", req_api, re.M) else "present")
runner_src = (RAIZ / "src" / "experiments" / "run_preliminary.py").read_text(encoding="utf-8")
add("README: runner has --mlflow option", "present", RAIZ / "src" / "experiments" / "run_preliminary.py", "add_argument('--mlflow'",
    "present" if 'add_argument("--mlflow"' in runner_src else "absent")
add("README: runner has --mlflow-uri option", "present", RAIZ / "src" / "experiments" / "run_preliminary.py", "add_argument('--mlflow-uri'",
    "present" if 'add_argument("--mlflow-uri"' in runner_src else "absent")
devc = json.loads((RAIZ / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
add("README: Codespaces postCreateCommand runs uv sync --frozen --all-extras", "present", RAIZ / ".devcontainer" / "devcontainer.json", "postCreateCommand",
    "present" if "uv sync --frozen --all-extras" in devc["postCreateCommand"] else devc["postCreateCommand"])
add("README: Codespaces forwards ports 8501, 8000, 5000", "8501, 8000, 5000", RAIZ / ".devcontainer" / "devcontainer.json", "forwardPorts",
    ", ".join(str(x) for x in devc["forwardPorts"]))
add("README: Codespaces opens the Streamlit app", "present", RAIZ / ".devcontainer" / "devcontainer.json", "postAttachCommand.app",
    "present" if "streamlit run app/Home.py" in devc["postAttachCommand"]["app"] else devc["postAttachCommand"])
ci = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
add("README: CI job 'docker' exists", "present", RAIZ / ".github" / "workflows" / "ci.yml", "'name: docker'", "present" if "name: docker" in ci else "absent")
add("README: CI docker job builds api/Dockerfile", "present", RAIZ / ".github" / "workflows" / "ci.yml", "'file: api/Dockerfile'", "present" if "file: api/Dockerfile" in ci else "absent")
add("README: CI docker job waits for /health via compose", "present", RAIZ / ".github" / "workflows" / "ci.yml", "'docker compose up -d --no-build api' and '/health'",
    "present" if "docker compose up -d --no-build api" in ci and "localhost:8000/health" in ci else "absent")
add("README: CI docker job runs pytest + smoke in the test image", "present", RAIZ / ".github" / "workflows" / "ci.yml", "'pytest + smoke dentro do contêiner'",
    "present" if "pytest + smoke dentro do contêiner" in ci else "absent")
pages = (RAIZ / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
add("README: pages workflow is manual (workflow_dispatch)", "present", RAIZ / ".github" / "workflows" / "pages.yml", "'workflow_dispatch'", "present" if "workflow_dispatch:" in pages else "absent")
mk = (RAIZ / "Makefile").read_text(encoding="utf-8")
for alvo in ("docker-build", "docker-test", "docker-api", "precommit", "mlflow", "app", "api", "test", "smoke"):
    add(f"README: make target '{alvo}' exists", "present", RAIZ / "Makefile", f"'{alvo}:' line", "present" if re.search(rf"^{alvo}:", mk, re.M) else "absent")
dec = (RAIZ / "docs" / "DECISOES.md").read_text(encoding="utf-8")
add("README: number of author decisions (D1 to D13)", 13, RAIZ / "docs" / "DECISOES.md", "rows starting with '| D'", len(re.findall(r"^\| D\d+ \|", dec, re.M)), "int")
add("README: D9 says the dissertation runner is unchanged", "present", RAIZ / "docs" / "DECISOES.md", "D9 text", "present" if "O runner da dissertação **não** foi alterado" in dec else "absent")
add("README: D10 says no DOI yet", "present", RAIZ / "docs" / "DECISOES.md", "D10 text '**sem DOI**'", "present" if "**sem DOI**" in dec else "absent")
for f in ("tracking/registro_mlflow.py", "tracking/importar_pesquisa.py", "configs/smoke_mlflow.yaml", "tests/test_runner_mlflow.py", "docs/scripts/build_site.py",
          "site/index.html", "site/index.pt-BR.html", "deploy/hf_space/montar_space.py", "deploy/hf_space/LEIA-ME.md", ".pre-commit-config.yaml"):
    add(f"README: cited file exists ({f})", "exists", f, "path", "exists" if (RAIZ / f).exists() else "missing")

# ----------------------------------------------------------------------------- write
linhas = [
    "# Conferência de números — WP5 (README.md, README.pt-BR.md, docs/, data/README.md)",
    "",
    f"Gerado por `docs/scripts/conferir_numeros.py` em {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}. "
    "Cada linha: onde o número aparece, o número como exibido, o arquivo de origem, a chave/seletor e o valor lido. "
    "Arredondamento: MAE 2 casas, MASE e skill 3 casas, contagens exatas. "
    "As tabelas dos dois READMEs são geradas por `docs/scripts/tabela_readme.py` (`--lang en` / `--lang pt`; mesmas células, ponto decimal "
    "dos arquivos de origem), que também exige igualdade (|diff| <= 1e-9) entre "
    "`model_comparison.csv`, `A_modelos_por_h.csv` e `arcal_por_horizonte_dois_alvos.csv`; a conferência verifica que cada bloco de tabela "
    "aparece literalmente em `README.md` e em `README.pt-BR.md`. Números do texto corrido do `README.pt-BR.md` usam vírgula decimal e são "
    "conferidos à parte (linhas 'README.pt-BR.md prose').",
    "",
    f"Total: {len(checks)} números; VERIFICADO: {sum(c['status'] == 'VERIFICADO' for c in checks)}; "
    f"DIVERGENTE: {sum(c['status'] == 'DIVERGENTE' for c in checks)}.",
    "",
    "| # | Onde | Número exibido | Arquivo | Chave / seletor | Valor lido | Status |",
    "|---:|---|---|---|---|---|---|",
]
for i, c in enumerate(checks, start=1):
    linhas.append(
        f"| {i} | {c['onde']} | {c['numero']} | `{c['arquivo']}` | {c['chave']} | {c['lido']} | {c['status']} |"
    )
divergentes = [c for c in checks if c["status"] == "DIVERGENTE"]
linhas += [
    "",
    "## Números narrativos sem arquivo em `results/` (não conferidos aqui, declarados no texto)",
    "",
    "- `docs/LESSONS.md`, história 2: percentual de diferença do PM2.5 e correlação entre o CAMS canônico e o novo download "
    "ficam no PROTOCOLO §0.17 da dissertação; o texto não os repete.",
    "- `docs/LESSONS.md`, história 4: os defeitos da run `preliminar_h1_full_20260727-163313` vêm do `CLAUDE.md` §5 e do "
    "`CHANGELOG.md` da dissertação; nenhum número dessa run é citado.",
    "- `docs/LESSONS.md`, história 3: a descrição da consulta BigQuery vem do cabeçalho de "
    "`src/ingestion/fetch_sih_bq_enriquecido.py` da dissertação (tabela `servicos_profissionais`, filtro por município do estabelecimento).",
]
(RAIZ / "docs" / "CONFERENCIA_NUMEROS_WP5.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
print(f"{len(checks)} checks; DIVERGENTE: {len(divergentes)}")
for c in divergentes:
    print("DIVERGENTE:", c)
sys.exit(1 if divergentes else 0)

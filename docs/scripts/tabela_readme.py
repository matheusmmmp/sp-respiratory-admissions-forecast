"""Builds the README result tables from the copied run artifacts. No number is typed by hand.

    uv run python docs/scripts/tabela_readme.py            # prints Markdown tables
    uv run python docs/scripts/tabela_readme.py --json     # prints the numbers as JSON (for the audit list)

Sources (all inside this repository):
- results/runs/<RUN_ID>/model_comparison.csv  (feature_set == AR_CAL; baselines under feature_set == baseline)
  -> MAE_medio, MASE_medio, skill_MAE_medio
- results/runs/<RUN_ID>/manifest.json                                  -> git_commit, git_sujo, n_predicoes
- results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A_modelos_por_h.csv (base == cetesb)
- results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/arcal_por_horizonte_dois_alvos.csv

Cross-check: every MAE/MASE printed must agree (|diff| <= 1e-9) with the two analysis CSVs above; otherwise
the script raises. Rounding: MAE to 2 decimals, MASE to 3 decimals, skill to 3 decimals.
MASE only compares models within the same horizon (it uses the Naive of that horizon); across horizons use
MAE and skill = 1 - MAE / min(Naive, Seasonal Naive).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RUNS = RAIZ / "results" / "runs"
A_MODELOS = RAIZ / "results" / "analise_multihorizonte" / "ANALISE_MULTIHORIZONTE_V02_20261118" / "A_modelos_por_h.csv"
ARCAL_DOIS = (
    RAIZ
    / "results"
    / "numeros_texto_urgencia"
    / "NUMEROS_TEXTO_URGENCIA_V02_20261118"
    / "arcal_por_horizonte_dois_alvos.csv"
)

HS = [1, 5, 7, 15, 30]
RUNS_POR_ALVO = {
    "total": {
        1: "h1_v02_cetesb_cetesb_classicos_full_20261022-211834",
        5: "mh_h5_cetesb_cetesb_full_20261110-211453",
        7: "mh_h7_cetesb_cetesb_full_20261111-030322",
        15: "mh_h15_cetesb_cetesb_full_20261111-070926",
        30: "mh_h30_cetesb_cetesb_full_20261113-104814",
    },
    "urgencia": {
        1: "ur_h1_cetesb_cetesb_full_20261116-191534",
        5: "ur_h5_cetesb_cetesb_full_20261116-222823",
        7: "ur_h7_cetesb_cetesb_full_20261117-073926",
        15: "ur_h15_cetesb_cetesb_full_20261117-190532",
        30: "ur_h30_cetesb_cetesb_full_20261117-221426",
    },
}
MODELOS = [
    ("xgboost", "XGBoost"),
    ("sarimax", "SARIMAX"),
    ("lstm", "LSTM"),
    ("ingarch_nb", "INGARCH-NB"),
    ("gam_nb", "GAM-NB"),
    ("naive", "Naive"),
    ("seasonal_naive", "Seasonal Naive"),
]
ROTULO_DOIS = {
    "XGBoost": "XGBoost",
    "SARIMAX": "SARIMAX",
    "LSTM": "LSTM",
    "INGARCH-NB": "INGARCH-NB",
    "GAM-NB": "GAM-NB",
    "Naive": "Naïve",
    "Seasonal Naive": "Seasonal Naïve",
}
TOL = 1e-9


def ler_arcal(run_id: str) -> pd.DataFrame:
    """AR_CAL rows for the trained models; the two baselines are stored under feature_set == 'baseline'
    (they use no features and are evaluated on the same test dates)."""
    df = pd.read_csv(RUNS / run_id / "model_comparison.csv")
    df = df[(df["feature_set"] == "AR_CAL") | (df["feature_set"] == "baseline")].set_index("model")
    if df.index.duplicated().any():
        raise RuntimeError(f"{run_id}: duplicated model rows after filtering AR_CAL/baseline")
    faltam = [m for m, _ in MODELOS if m not in df.index]
    if faltam:
        raise RuntimeError(f"{run_id}: models missing in AR_CAL: {faltam}")
    return df


def ler_manifesto(run_id: str) -> dict:
    m = json.loads((RUNS / run_id / "manifest.json").read_text(encoding="utf-8"))
    if m["modo"] != "full":
        raise RuntimeError(f"{run_id}: modo {m['modo']!r}, expected 'full'")
    return m


def coletar() -> dict:
    a_mod = pd.read_csv(A_MODELOS)
    a_mod = a_mod[a_mod["base"] == "cetesb"].set_index(["h", "modelo"])
    dois = pd.read_csv(ARCAL_DOIS).set_index(["alvo", "h", "modelo"])
    saida: dict = {}
    for alvo, runs in RUNS_POR_ALVO.items():
        saida[alvo] = {}
        for h in HS:
            run_id = runs[h]
            mc = ler_arcal(run_id)
            man = ler_manifesto(run_id)
            linhas = {}
            for chave, rotulo in MODELOS:
                mae = float(mc.loc[chave, "MAE_medio"])
                mase = float(mc.loc[chave, "MASE_medio"])
                skill = float(mc.loc[chave, "skill_MAE_medio"])
                # cross-check 1: arcal_por_horizonte_dois_alvos.csv
                ref = dois.loc[(alvo, h, ROTULO_DOIS[rotulo])]
                if abs(float(ref["MAE"]) - mae) > TOL or abs(float(ref["MASE"]) - mase) > TOL:
                    raise RuntimeError(f"{run_id} {chave}: model_comparison.csv != arcal_por_horizonte_dois_alvos.csv")
                # cross-check 2: A_modelos_por_h.csv (total target only, trained models only)
                if alvo == "total" and chave not in ("naive", "seasonal_naive"):
                    ref2 = a_mod.loc[(h, chave)]
                    if ref2["run"] != run_id:
                        raise RuntimeError(f"A_modelos_por_h.csv points to {ref2['run']}, expected {run_id}")
                    if abs(float(ref2["MAE_ARCAL"]) - mae) > TOL or abs(float(ref2["MASE_ARCAL"]) - mase) > TOL:
                        raise RuntimeError(f"{run_id} {chave}: model_comparison.csv != A_modelos_por_h.csv")
                linhas[rotulo] = {
                    "MAE": mae,
                    "MASE": mase,
                    "skill_MAE": skill,
                    "n_folds": int(mc.loc[chave, "n_folds"]),
                    "n_sementes": int(mc.loc[chave, "n_sementes"]),
                }
            ref_naive = min(linhas["Naive"]["MAE"], linhas["Seasonal Naive"]["MAE"])
            for rotulo in linhas:
                linhas[rotulo]["skill_vs_ref"] = 1.0 - linhas[rotulo]["MAE"] / ref_naive
            if alvo == "total":
                for chave, rotulo in MODELOS[:5]:
                    ref2 = a_mod.loc[(h, chave)]
                    if abs(float(ref2["skill_vs_ref"]) - linhas[rotulo]["skill_vs_ref"]) > TOL:
                        raise RuntimeError(f"{run_id} {chave}: skill_vs_ref differs from A_modelos_por_h.csv")
            saida[alvo][h] = {
                "run_id": run_id,
                "git_commit": man["git_commit"],
                "git_sujo": bool(man["git_sujo"]),
                "n_predicoes": int(man["n_predicoes"]),
                "status": man["status"],
                "modelos": linhas,
            }
    return saida


def tabela_md(dados: dict, alvo: str, modelos: list[str]) -> str:
    out = []
    out.append("| Model | " + " | ".join(f"h = {h}" for h in HS) + " |")
    out.append("|---|" + "|".join("---:" for _ in HS) + "|")
    for rotulo in modelos:
        celulas = []
        for h in HS:
            d = dados[alvo][h]["modelos"][rotulo]
            celulas.append(f"{d['MAE']:.2f} / {d['MASE']:.3f}")
        out.append(f"| {rotulo} | " + " | ".join(celulas) + " |")
    return "\n".join(out)


def tabela_runs_md(dados: dict, alvo: str) -> str:
    out = ["| h | Run id | Commit | Clean tree at start | Predictions |", "|---:|---|---|---|---:|"]
    for h in HS:
        d = dados[alvo][h]
        limpo = "yes" if not d["git_sujo"] else "NO"
        out.append(f"| {h} | `{d['run_id']}` | `{d['git_commit'][:7]}` | {limpo} | {d['n_predicoes']:,} |")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    dados = coletar()
    if args.json:
        print(json.dumps(dados, indent=2))
        return
    print(
        "Cells are MAE (admissions/day, 2 decimals) / MASE (3 decimals), feature set AR_CAL, mean over 4 folds "
        "(and 5 seeds for XGBoost and LSTM). MASE uses the Naive of the same h: compare across rows, "
        "not across columns.\n"
    )
    print("## Total target (all respiratory admissions)\n")
    print(tabela_md(dados, "total", [r for _, r in MODELOS]))
    print()
    print(tabela_runs_md(dados, "total"))
    print("\n## Urgent target (non-elective admissions)\n")
    print(tabela_md(dados, "urgencia", [r for _, r in MODELOS]))
    print()
    print(tabela_runs_md(dados, "urgencia"))
    print("\n## Skill vs best naive of the same h (1 - MAE / min(Naive, Seasonal Naive)), 3 decimals\n")
    for alvo in ("total", "urgencia"):
        print(f"### {alvo}")
        print("| Model | " + " | ".join(f"h = {h}" for h in HS) + " |")
        print("|---|" + "|".join("---:" for _ in HS) + "|")
        for _, rotulo in MODELOS[:5]:
            print(
                f"| {rotulo} | "
                + " | ".join(f"{dados[alvo][h]['modelos'][rotulo]['skill_vs_ref']:.3f}" for h in HS)
                + " |"
            )
        print()


if __name__ == "__main__":
    main()

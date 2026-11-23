"""Validação de métricas e teste pareado de perdas (Diebold–Mariano) sobre UMA run do runner.

    python -m src.experiments.teste_dm_v02 --run <RUN_ID> [--saida reports/experiments/TESTES_DM_<RUN_ID>]

O que faz (tudo a partir de `predictions.csv`, `metrics_by_fold.csv`, `model_comparison.csv` e `manifest.json` da run):

1. **Recalcula** MAE, RMSE, R², MASE por (modelo, conjunto, semente, fold) e os agregados do runner (sementes dentro da
   fold, depois folds) e compara com os CSV da run — diferença máxima reportada; falha alto se > 1e-6.
2. **Perda por data**: erro absoluto |y − ŷ| por data-alvo. Para modelos estocásticos (várias sementes) a perda da data é a
   **média das sementes** — é a mesma agregação do protocolo (MAE por semente, depois média), apenas reordenada por data.
3. **Teste de Diebold–Mariano** (Diebold & Mariano, 1995) para cada contraste pareado: d_t = L_A(t) − L_B(t) nas MESMAS
   datas-alvo; estatística DM = d̄ / sqrt(V̂_HAC/T), com variância de longo prazo de Newey–West (kernel de Bartlett,
   largura ⌊T^{1/3}⌋, nunca menor que h − 1), correção de amostra pequena de Harvey, Leybourne & Newbold (1997) e p-valor
   bicaudal na t de Student com T − 1 graus de liberdade. Calculado **por fold** (T = 180) e **agrupado** (T = 720: as
   quatro janelas de teste são contíguas no tempo, 2023-01-12 a 2024-12-31, logo a série de d_t é uma só).
4. **Famílias de contrastes** e correção de Holm dentro de cada família (p ajustado):
   - `modelos_AR_CAL`: todos os pares de modelos no conjunto comum AR_CAL (baselines incluídos);
   - `ablacao_<modelo>`: para cada modelo treinável, os contrastes de bloco previstos no PROTOCOLO (H2 sobre a média
     isolada, especificação rica do PM2,5, poluentes, completo), pareados por fold e semente.
5. Reporta também o **critério descritivo do PROTOCOLO §0.7** (Δ pareado acima do desvio entre sementes em ≥ 3 de 4
   folds, mesmo sinal) ao lado do DM, para leitura conjunta.

Limitações (declaradas no relatório): o DM assume estacionariedade fraca de d_t dentro da janela; a média das sementes
por data reduz, mas não elimina, a variância de treino; o p agrupado não é independente dos p por fold; não há
Model Confidence Set (Hansen et al., 2011) — só pares com Holm. Nenhum valor é digitado à mão.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ = Path(__file__).resolve().parents[2]
EXP = RAIZ / "reports" / "experiments"

ORDEM_MODELOS = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb", "naive", "seasonal_naive"]
CONJ_COMUM = "AR_CAL"
PERDAS_IDENTICAS = "perdas idênticas em todas as datas"
# contrastes de ablação (A = com bloco, B = sem): Δ = L_A − L_B; negativo favorece o bloco acrescentado
CONTRASTES_ABLACAO = [
    ("H2_media_sem_meteo", "AR_CAL_PM25MEDIA", "AR_CAL"),
    ("H2_media_com_meteo", "AR_CAL_METEO_PM25MEDIA", "AR_CAL_METEO"),
    ("PM25_rico_sem_meteo", "AR_CAL_PM25", "AR_CAL"),
    ("PM25_rico_com_meteo", "AR_CAL_METEO_PM25", "AR_CAL_METEO"),
    ("rico_vs_media_com_meteo", "AR_CAL_METEO_PM25", "AR_CAL_METEO_PM25MEDIA"),
    ("POLUENTES_sem_meteo", "AR_CAL_POLUENTES", "AR_CAL"),
    ("POLUENTES_com_meteo", "AR_CAL_METEO_POLUENTES", "AR_CAL_METEO"),
    ("METEO", "AR_CAL_METEO", "AR_CAL"),
    ("COMPLETO_vs_meteo", "COMPLETO", "AR_CAL_METEO"),
    ("COMPLETO_vs_meteo_poluentes", "COMPLETO", "AR_CAL_METEO_POLUENTES"),
]


# ------------------------------------------------------------------ leitura
def carregar(run: str) -> dict:
    r = EXP / run
    if not r.is_dir():
        raise SystemExit(f"run não encontrada: {r}")
    man = json.loads((r / "manifest.json").read_text(encoding="utf-8"))
    if man.get("modo") != "full":
        raise SystemExit(f"{run}: modo {man.get('modo')!r}; o teste só vale para runs --full")
    pred = pd.read_csv(r / "predictions.csv", parse_dates=["target_date", "forecast_origin"])
    if pred.horizon.nunique() != 1:
        raise SystemExit("mais de um horizonte em predictions.csv")
    mbf = pd.read_csv(r / "metrics_by_fold.csv")
    mc = pd.read_csv(r / "model_comparison.csv")
    return {"run": run, "dir": r, "manifesto": man, "pred": pred, "mbf": mbf, "mc": mc, "h": int(pred.horizon.iloc[0])}


# ------------------------------------------------------- 1. recálculo
def recalcular(d: dict) -> dict:
    pred, mbf, mc = d["pred"], d["mbf"], d["mc"]
    naive = pred[pred.model == "naive"][["fold", "target_date", "abs_error"]].rename(columns={"abs_error": "ae_naive"})
    naive = naive.drop_duplicates(["fold", "target_date"])
    q = pred.merge(naive, on=["fold", "target_date"], how="left", validate="many_to_one")
    if q.ae_naive.isna().any():
        raise RuntimeError("datas de teste sem previsão do Naïve — MASE não recalculável")

    def _m(g):
        e = g.y_true - g.y_pred
        sst = ((g.y_true - g.y_true.mean()) ** 2).sum()
        return pd.Series({"MAE": e.abs().mean(), "RMSE": math.sqrt((e ** 2).mean()),
                          "R2": 1 - (e ** 2).sum() / sst if sst > 0 else np.nan,
                          "MASE": e.abs().mean() / g.ae_naive.mean()})
    rec = q.groupby(["model", "feature_set", "seed", "fold"]).apply(_m, include_groups=False).reset_index()
    cmp_ = rec.merge(mbf, on=["model", "feature_set", "seed", "fold"], suffixes=("_rec", "_run"), validate="one_to_one")
    if len(cmp_) != len(mbf):
        raise RuntimeError(f"linhas de metrics_by_fold sem par no recálculo: {len(mbf) - len(cmp_)}")
    dif_fold = {k: float((cmp_[f"{k}_rec"] - cmp_[f"{k}_run"]).abs().max()) for k in ("MAE", "RMSE", "R2", "MASE")}
    # agregação do runner: sementes dentro da fold, depois folds
    por_fold = rec.groupby(["model", "feature_set", "fold"]).agg(MAE=("MAE", "mean"), RMSE=("RMSE", "mean"),
                                                                  R2=("R2", "mean"), MASE=("MASE", "mean")).reset_index()
    agg = por_fold.groupby(["model", "feature_set"]).agg(MAE_medio=("MAE", "mean"), MAE_std_fold=("MAE", "std"),
                                                          RMSE_medio=("RMSE", "mean"), R2_medio=("R2", "mean"),
                                                          MASE_medio=("MASE", "mean")).reset_index()
    cmp2 = agg.merge(mc, on=["model", "feature_set"], suffixes=("_rec", "_run"), validate="one_to_one")
    dif_agg = {k: float((cmp2[f"{k}_rec"] - cmp2[f"{k}_run"]).abs().max())
               for k in ("MAE_medio", "MAE_std_fold", "RMSE_medio", "R2_medio", "MASE_medio")}
    pior = max(list(dif_fold.values()) + list(dif_agg.values()))
    if pior > 1e-6:
        raise RuntimeError(f"métricas recalculadas divergem dos CSV da run: {dif_fold} {dif_agg}")
    return {"n_linhas_metrics_by_fold": int(len(mbf)), "n_linhas_model_comparison": int(len(mc)),
            "n_previsoes": int(len(pred)), "dif_max_por_fold_semente": dif_fold, "dif_max_agregado": dif_agg,
            "n_datas_teste": int(pred.target_date.nunique()), "n_folds": int(pred.fold.nunique())}


# ------------------------------------------------------- 2. perda por data
def perdas_por_data(pred: pd.DataFrame) -> pd.DataFrame:
    """Perda absoluta por (modelo, conjunto, fold, data): média das sementes quando há várias."""
    g = pred.groupby(["model", "feature_set", "fold", "target_date"]).agg(
        perda=("abs_error", "mean"), n_sementes=("seed", "nunique")).reset_index()
    return g


def serie(perdas: pd.DataFrame, modelo: str, conjunto: str) -> pd.DataFrame | None:
    q = perdas[(perdas.model == modelo) & (perdas.feature_set == conjunto)]
    return None if q.empty else q.set_index(["fold", "target_date"]).sort_index()


# ------------------------------------------------------- 3. Diebold–Mariano
def dm(d: np.ndarray, h: int) -> dict:
    """DM com HAC de Newey–West (Bartlett), largura max(⌊T^{1/3}⌋, h−1), correção HLN e t de Student(T−1)."""
    d = np.asarray(d, dtype=float)
    T = len(d)
    if T < 10:
        raise ValueError(f"T={T} pequeno demais para o DM")
    dbar = d.mean()
    u = d - dbar
    L = max(int(math.floor(T ** (1 / 3))), h - 1)
    if np.all(d == 0):  # perdas idênticas em todas as datas (ex.: Naïve ≡ Seasonal Naïve em h = 7): não há teste
        return {"T": T, "d_medio": 0.0, "DM": np.nan, "p": np.nan, "largura_HAC": L, "nota": PERDAS_IDENTICAS}
    gamma0 = float((u @ u) / T)
    lrv = gamma0
    for k in range(1, L + 1):
        gk = float((u[k:] @ u[:-k]) / T)
        lrv += 2.0 * (1.0 - k / (L + 1.0)) * gk
    if lrv <= 0:  # pode acontecer com d quase constante; cai para a variância amostral
        lrv = gamma0
    if lrv <= 0:
        return {"T": T, "d_medio": float(dbar), "DM": np.nan, "p": np.nan, "largura_HAC": L, "nota": "d_t constante"}
    dm_stat = dbar / math.sqrt(lrv / T)
    hln = math.sqrt((T + 1 - 2 * h + h * (h - 1) / T) / T)
    dm_hln = dm_stat * hln
    p = 2 * stats.t.sf(abs(dm_hln), df=T - 1)
    return {"T": T, "d_medio": float(dbar), "DM": float(dm_hln), "p": float(p), "largura_HAC": L}


def contraste(perdas: pd.DataFrame, a: tuple[str, str], b: tuple[str, str], h: int, mbf: pd.DataFrame) -> dict | None:
    sa, sb = serie(perdas, *a), serie(perdas, *b)
    if sa is None or sb is None:
        return None
    j = sa[["perda"]].join(sb[["perda"]], lsuffix="_a", rsuffix="_b", how="inner")
    if len(j) != len(sa) or len(j) != len(sb):
        raise RuntimeError(f"datas não pareadas entre {a} e {b}: {len(sa)} / {len(sb)} / {len(j)}")
    dif = (j.perda_a - j.perda_b)
    out = {"A": f"{a[0]}:{a[1]}", "B": f"{b[0]}:{b[1]}", "n_sementes_A": int(sa.n_sementes.iloc[0]),
           "n_sementes_B": int(sb.n_sementes.iloc[0])}
    por_fold = {}
    for f, dv in dif.groupby(level="fold"):
        por_fold[int(f)] = dm(dv.to_numpy(), h)
    out["por_fold"] = por_fold
    out["agrupado"] = dm(dif.sort_index(level="target_date").to_numpy(), h)
    # critério descritivo §0.7: Δ pareado por fold e semente acima do ruído de semente em ≥ 3 de 4 folds, mesmo sinal
    ma = mbf[(mbf.model == a[0]) & (mbf.feature_set == a[1])].set_index(["fold", "seed"]).MAE
    mb = mbf[(mbf.model == b[0]) & (mbf.feature_set == b[1])].set_index(["fold", "seed"]).MAE
    if a[0] == b[0]:  # mesmo modelo: pareia por semente
        delta = (ma - mb).groupby(level="fold").agg(["mean", "std"])
    else:  # modelos diferentes: diferença das médias por fold; ruído = raiz da soma das variâncias entre sementes
        ga, gb = ma.groupby(level="fold").agg(["mean", "std"]), mb.groupby(level="fold").agg(["mean", "std"])
        delta = pd.DataFrame({"mean": ga["mean"] - gb["mean"],
                              "std": np.sqrt(ga["std"].fillna(0) ** 2 + gb["std"].fillna(0) ** 2)})
    ruido = delta["std"].fillna(0.0)
    acima = (delta["mean"].abs() > ruido) & (np.sign(delta["mean"]) == np.sign(delta["mean"].iloc[0]))
    out["criterio_0_7"] = {"delta_MAE_por_fold": [float(v) for v in delta["mean"]],
                           "ruido_semente_por_fold": [float(v) for v in ruido],
                           "folds_acima_mesmo_sinal": int(acima.sum()), "veredito": bool(acima.sum() >= 3)}
    return out


def holm(ps: list[float]) -> list[float]:
    idx = np.argsort(ps)
    m = len(ps)
    adj = np.empty(m)
    atual = 0.0
    for rank, i in enumerate(idx):
        val = min(1.0, (m - rank) * ps[i])
        atual = max(atual, val)
        adj[i] = atual
    return [float(v) for v in adj]


def aplicar_holm(familias: dict[str, list[dict]]) -> list[str]:
    """Grava `p_holm` no escopo agrupado de cada contraste, família a família.

    Contraste com perdas idênticas em todas as datas (d_t ≡ 0) não é um teste: sai da família antes do ajuste e é
    devolvido na lista, para o relatório. Qualquer outro p agrupado indefinido falha alto (antes, a família inteira
    ficava sem p Holm em silêncio).
    """
    fora = []
    for nome, fam in familias.items():
        validos = []
        for c in fam:
            g = c["agrupado"]
            if np.isfinite(g["p"]):
                validos.append(c)
            elif g.get("nota") == PERDAS_IDENTICAS:
                fora.append(f"{nome}: {c['contraste']} ({c['A']} vs {c['B']})")
            else:
                raise RuntimeError(f"{nome}: {c['contraste']} sem p agrupado ({g.get('nota')}); Holm da família indefinido")
        for c, pa in zip(validos, holm([c["agrupado"]["p"] for c in validos])):
            c["agrupado"]["p_holm"] = pa
    return fora


# ------------------------------------------------------- relatório
def executar(run: str, saida: Path) -> None:
    d = carregar(run)
    h = d["h"]
    val = recalcular(d)
    perdas = perdas_por_data(d["pred"])
    modelos = [m for m in ORDEM_MODELOS if m in set(d["pred"].model)]
    conj = lambda m: "baseline" if m in ("naive", "seasonal_naive") else CONJ_COMUM  # noqa: E731

    familias: dict[str, list[dict]] = {}
    fam = []
    for ma, mb in itertools.combinations(modelos, 2):
        c = contraste(perdas, (ma, conj(ma)), (mb, conj(mb)), h, d["mbf"])
        if c:
            c["contraste"] = f"{ma} − {mb}"
            fam.append(c)
    familias["modelos_AR_CAL"] = fam
    ausentes = []
    for m in [x for x in modelos if x not in ("naive", "seasonal_naive")]:
        fam = []
        for nome, ca, cb in CONTRASTES_ABLACAO:
            c = contraste(perdas, (m, ca), (m, cb), h, d["mbf"])
            if c is None:
                ausentes.append(f"{m}:{nome} ({ca} vs {cb})")
                continue
            c["contraste"] = nome
            fam.append(c)
        if fam:
            familias[f"ablacao_{m}"] = fam
    fora_holm = aplicar_holm(familias)

    saida.mkdir(parents=True, exist_ok=True)
    linhas = []
    for nome, fam in familias.items():
        for c in fam:
            base = {"familia": nome, "contraste": c["contraste"], "A": c["A"], "B": c["B"],
                    "n_sementes_A": c["n_sementes_A"], "n_sementes_B": c["n_sementes_B"]}
            for f, r in c["por_fold"].items():
                linhas.append({**base, "escopo": f"fold{f}", **r})
            linhas.append({**base, "escopo": "agrupado", **c["agrupado"],
                           "criterio_0_7_folds": c["criterio_0_7"]["folds_acima_mesmo_sinal"],
                           "criterio_0_7": c["criterio_0_7"]["veredito"]})
    tab = pd.DataFrame(linhas)
    tab.to_csv(saida / "dm_contrastes.csv", index=False)
    (saida / "validacao_metricas.json").write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf-8")
    (saida / "dm_detalhe.json").write_text(json.dumps(familias, ensure_ascii=False, indent=2, default=float), encoding="utf-8")

    def fmt(x, c=3):
        return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{c}f}".replace(".", ",")

    md = [f"# Validação e teste pareado de perdas — run `{run}`", "",
          f"Gerado por `src/experiments/teste_dm_v02.py`. h = {h}; {val['n_previsoes']} previsões; "
          f"{val['n_datas_teste']} datas-alvo em {val['n_folds']} folds.", "",
          "## 1. Métricas recalculadas de `predictions.csv`", "",
          f"- Por (modelo, conjunto, semente, fold): {val['n_linhas_metrics_by_fold']} linhas; diferença máxima contra "
          f"`metrics_by_fold.csv`: " + ", ".join(f"{k} {v:.1e}" for k, v in val["dif_max_por_fold_semente"].items()),
          f"- Agregados (sementes dentro da fold, depois folds): {val['n_linhas_model_comparison']} linhas; diferença máxima "
          f"contra `model_comparison.csv`: " + ", ".join(f"{k} {v:.1e}" for k, v in val["dif_max_agregado"].items()),
          "", "## 2. Diebold–Mariano — método", "",
          "Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). "
          "d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção "
          "de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). "
          "p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.", ""]
    for nome, fam in familias.items():
        md += [f"## Família `{nome}`", "",
               "| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |", "|---|---|---|---|---|---|---|"]
        for c in fam:
            pf = c["por_fold"]
            sig = [f"{f}{'−' if r['DM'] < 0 else '+'}" for f, r in pf.items() if np.isfinite(r["p"]) and r["p"] < 0.05]
            g = c["agrupado"]
            md.append(f"| {c['contraste']} | {fmt(g['d_medio'])} | {fmt(g['DM'], 2)} | {fmt(g['p'])} | "
                      f"{fmt(g.get('p_holm'))} | {', '.join(sig) if sig else 'nenhum'} | "
                      f"{'sim' if c['criterio_0_7']['veredito'] else 'não'} ({c['criterio_0_7']['folds_acima_mesmo_sinal']}/4) |")
        md.append("")
    if ausentes:
        md += ["## Contrastes não calculáveis nesta run (conjunto ausente)", ""] + [f"- {a}" for a in ausentes] + [""]
    if fora_holm:
        md += ["## Contrastes fora do Holm (perdas idênticas em todas as datas)", "",
               "As duas previsões coincidem em todas as datas-alvo; d_t ≡ 0, o DM não é definido e o contraste sai da "
               "família antes do ajuste de Holm (o p Holm das demais usa só os contrastes testáveis). Quando o par é "
               "Naïve × Seasonal Naïve (h = 7, defasagem igual à sazonal), os contrastes de cada modelo contra os dois "
               "baselines são duplicados e ambos permanecem na família, o que torna o Holm conservador.", ""] + \
              [f"- {a}" for a in fora_holm] + [""]
    md += ["## Limitações", "",
           "- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.",
           "- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes "
           "explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.",
           "- O p agrupado e os p por fold usam as mesmas datas; não são independentes.",
           "- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.",
           "- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.", ""]
    (saida / "RELATORIO_DM.md").write_text("\n".join(md), encoding="utf-8")
    print(f"validação OK (dif. máx. {max(val['dif_max_agregado'].values()):.1e}); {len(tab)} linhas de DM em {saida}")
    if ausentes:
        print(f"  contrastes ausentes: {len(ausentes)}")
    if fora_holm:
        print(f"  contrastes fora do Holm (perdas idênticas): {len(fora_holm)}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args(argv)
    saida = Path(a.saida) if a.saida else EXP / f"TESTES_DM_{a.run}"
    executar(a.run, saida)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

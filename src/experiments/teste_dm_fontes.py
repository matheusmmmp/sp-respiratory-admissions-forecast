"""Diebold–Mariano pareado ENTRE BASES (mesmo modelo, mesmo conjunto de covariáveis, mesmas datas-alvo, runs diferentes).

    python -m src.experiments.teste_dm_fontes --referencia <RUN>=<rótulo> --run <RUN>=<rótulo> [--run ...] --saida <pasta>

Complementa `compara_fontes_v02.py` (critério descritivo §0.7 por fold e semente) com o teste das perdas por data:

- Pré-condições verificadas (falha alto): modo `full`, mesmas datas de teste por fold, mesmo horizonte, mesmo alvo (sha256),
  mesmas sementes; o MAE do Naïve tem de ser IDÊNTICO por fold (mesmo alvo e mesmas datas).
- Conjuntos comparados: a interseção dos conjuntos das runs (os de fora são listados); modelos: a interseção.
- Perda por data = |y − ŷ|, média das sementes por data (XGBoost/LSTM); d_t = L_base − L_referência; DM com HAC de
  Newey–West, correção HLN e t(T−1) — mesma função de `teste_dm_v02.dm`. Por fold (T = 180) e agrupado (T = 720).
- Holm dentro de cada família (base × modelo), sobre os conjuntos que CONTÊM bloco ambiental; os conjuntos sem bloco
  ambiental (`AR`, `AR_CAL`) e os baselines são controles: d_t ≡ 0 é verificado e reportado, não testado.
- Conjunto com bloco ambiental cujas previsões são IDÊNTICAS nas duas runs (d_t ≡ 0; ex.: `AR_CAL_PM25MEDIA` na híbrida, que
  só usa `pm25_media` da CETESB) é classificado como `identico` — controle de fato, DM indefinido — e NÃO entra na família.
- Holm usa só os p finitos da família (m = nº de testes definidos). Correção de 2026-10-24: a versão anterior só aplicava Holm
  se TODOS os p fossem finitos, e um p indefinido deixava a família inteira sem correção (`TESTES_DM_FONTES_V03_20261023`,
  famílias HÍBRIDA × CETESB rica).
- DM < 0 favorece a base comparada; > 0 favorece a referência.
- `--testar-sem-ambiente` (2026-11-18): `AR` e `AR_CAL` deixam de ser controles e entram no teste e na família de Holm; só os
  baselines seguem como controle. Uso: runs com a MESMA fonte e PERÍODOS DE TREINO diferentes (braços COVID A × B, §0.22), em
  que as previsões sem bloco ambiental também diferem. Sem a opção, nesses pares os dois conjuntos sairiam como "controle"
  com d_t ≠ 0 e sem teste.
Nenhum valor é digitado; tudo vem de `predictions.csv` e `manifest.json` das runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from src.experiments.teste_dm_v02 import EXP, dm, holm, perdas_por_data

CONTROLES = {"AR", "AR_CAL", "baseline"}


def holm_finitos(ps: list[float]) -> list[float]:
    """Holm sobre os p finitos (m = quantos são finitos); p indefinido fica NaN e não conta em m."""
    ps = np.asarray(ps, dtype=float)
    out = np.full(len(ps), np.nan)
    ok = np.flatnonzero(np.isfinite(ps))
    if len(ok):
        out[ok] = holm(list(ps[ok]))
    return list(out)


def _ler(run: str) -> dict:
    r = EXP / run
    man = json.loads((r / "manifest.json").read_text(encoding="utf-8"))
    if man.get("modo") != "full":
        raise SystemExit(f"{run}: modo {man.get('modo')!r}; só runs --full")
    pred = pd.read_csv(r / "predictions.csv", parse_dates=["target_date"])
    folds = pd.read_csv(r / "folds.csv")
    return {"run": run, "man": man, "pred": pred, "folds": folds, "perdas": perdas_por_data(pred)}


def _verificar(ref: dict, outro: dict) -> None:
    erros = []
    c = ["fold", "teste_inicio", "teste_fim"]
    if not ref["folds"][c].astype(str).equals(outro["folds"][c].astype(str)):
        erros.append("datas de teste por fold diferem")
    for k in ("dataset_sih_sha256", "sementes"):
        if ref["man"].get(k) != outro["man"].get(k):
            erros.append(f"{k} difere")
    if ref["pred"].horizon.unique().tolist() != outro["pred"].horizon.unique().tolist():
        erros.append("horizonte difere")
    na = ref["pred"][ref["pred"].model == "naive"].groupby("fold").abs_error.mean()
    nb = outro["pred"][outro["pred"].model == "naive"].groupby("fold").abs_error.mean()
    if not np.allclose(na.values, nb.values, atol=1e-12):
        erros.append("MAE do Naïve difere por fold — alvo ou datas não são os mesmos")
    if erros:
        raise RuntimeError(f"{outro['run']} × {ref['run']}: " + "; ".join(erros))


def executar(ref_id: str, ref_rot: str, outros: list[tuple[str, str]], saida: Path,
             controles: set[str] | frozenset[str] = frozenset(CONTROLES)) -> None:
    ref = _ler(ref_id)
    h = int(ref["pred"].horizon.iloc[0])
    linhas, fora = [], []
    for rid, rot in outros:
        o = _ler(rid)
        _verificar(ref, o)
        conj = sorted((set(ref["perdas"].feature_set) & set(o["perdas"].feature_set)))
        fora += [f"{rot}: {c}" for c in sorted(set(ref["perdas"].feature_set) ^ set(o["perdas"].feature_set))]
        modelos = sorted(set(ref["perdas"].model) & set(o["perdas"].model))
        for m in modelos:
            fam = []
            for c in conj:
                a = o["perdas"][(o["perdas"].model == m) & (o["perdas"].feature_set == c)].set_index(["fold", "target_date"])
                b = ref["perdas"][(ref["perdas"].model == m) & (ref["perdas"].feature_set == c)].set_index(["fold", "target_date"])
                if a.empty or b.empty:
                    continue
                j = a[["perda"]].join(b[["perda"]], lsuffix="_base", rsuffix="_ref", how="inner")
                if len(j) != len(a) or len(j) != len(b):
                    raise RuntimeError(f"{rot}/{m}/{c}: datas não pareadas ({len(a)}/{len(b)}/{len(j)})")
                d = (j.perda_base - j.perda_ref)
                base = {"base": rot, "run_base": rid, "referencia": ref_rot, "run_referencia": ref_id, "modelo": m, "conjunto": c,
                        "MAE_base": float(j.perda_base.mean()), "MAE_ref": float(j.perda_ref.mean())}
                if c in controles:
                    linhas.append({**base, "escopo": "agrupado", "T": len(d), "d_medio": float(d.mean()),
                                   "max_abs_d": float(d.abs().max()), "tipo": "controle"})
                    continue
                if float(d.abs().max()) == 0.0:
                    linhas.append({**base, "escopo": "agrupado", "T": len(d), "d_medio": 0.0, "max_abs_d": 0.0, "tipo": "identico",
                                   "nota": "previsões idênticas nas duas runs (o conjunto não usa coluna da fonte que difere): "
                                           "controle de fato, DM indefinido, fora da família de Holm"})
                    continue
                for f, dv in d.groupby(level="fold"):
                    linhas.append({**base, "escopo": f"fold{int(f)}", "tipo": "teste", **dm(dv.to_numpy(), h)})
                g = {**base, "escopo": "agrupado", "tipo": "teste", **dm(d.sort_index(level="target_date").to_numpy(), h)}
                linhas.append(g)
                fam.append(g)
            ps = [x["p"] for x in fam]
            for x, pa in zip(fam, holm_finitos(ps)):
                x["p_holm"] = pa
            for x in fam:
                x["m_familia_holm"] = int(np.isfinite(ps).sum())
    tab = pd.DataFrame(linhas)
    saida.mkdir(parents=True, exist_ok=True)
    tab.to_csv(saida / "dm_entre_bases.csv", index=False)

    def f(x, c=3):
        return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{c}f}".replace(".", ",")

    md = [f"# Diebold–Mariano entre bases — referência {ref_rot} (`{ref_id}`)", "",
          "Gerado por `src/experiments/teste_dm_fontes.py`. Perda = erro absoluto por data (média das sementes); d = L_base − L_ref; "
          "HAC Newey–West, correção HLN, t(T−1); agrupado em 720 datas contíguas; Holm por família (base × modelo) nos conjuntos com "
          "bloco ambiental. **DM < 0 favorece a base comparada.** Pré-condições verificadas: mesmas datas por fold, alvo (sha256), "
          "horizonte, sementes e MAE do Naïve idêntico por fold.", "",
          "Runs comparadas: " + ", ".join(f"{rot} (`{rid}`)" for rid, rot in outros) + ".", ""]
    if set(controles) != CONTROLES:
        md += [f"**`--testar-sem-ambiente`**: controles = {sorted(controles)}; `AR` e `AR_CAL` são testados e entram em Holm "
               "(runs com períodos de treino diferentes).", ""]
    ctrl = tab[tab.tipo == "controle"]
    if len(ctrl):
        md += [f"Controles ({', '.join(sorted(controles))}): {len(ctrl)} pares; máx |d_t| = "
               f"{ctrl.max_abs_d.max():.1e} (zero exato = mesmas previsões).", ""]
    ident = tab[tab.tipo == "identico"]
    if len(ident):
        md += [f"Conjuntos com previsões idênticas nas duas runs (controles de fato, fora de Holm): "
               + ", ".join(f"{r.base}/{r.modelo}/`{r.conjunto}`" for r in ident.itertuples()) + ".", ""]
    ag = tab[(tab.tipo == "teste") & (tab.escopo == "agrupado")]
    md += ["## Resumo por base (testes agrupados, Holm por modelo)", "",
           "| Base − referência | Testes definidos | p bruto < 0,05 | p Holm < 0,05 | a favor da base (DM < 0) | a favor da referência (DM > 0) |",
           "|---|---|---|---|---|---|"]
    for b, g in ag.groupby("base", sort=False):
        gd = g[np.isfinite(g.p)]
        sig = gd[gd.p_holm < 0.05]
        md.append(f"| {b} − {ref_rot} | {len(gd)} | {int((gd.p < 0.05).sum())} | {len(sig)} | {int((sig.DM < 0).sum())} | {int((sig.DM > 0).sum())} |")
    md.append("")
    for (b, m), g in ag.groupby(["base", "modelo"], sort=False):
        md += [f"## {b} − {ref_rot}: `{m}`", "",
               "| Conjunto | MAE base | MAE ref | d̄ | DM | p | p Holm | folds com p<0,05 (sinal) |", "|---|---|---|---|---|---|---|---|"]
        for _, x in g.iterrows():
            pf = tab[(tab.base == b) & (tab.modelo == m) & (tab.conjunto == x.conjunto) & (tab.escopo.str.startswith("fold"))]
            sig = [f"{e[-1]}{'−' if r.DM < 0 else '+'}" for e, r in zip(pf.escopo, pf.itertuples()) if np.isfinite(r.p) and r.p < 0.05]
            md.append(f"| `{x.conjunto}` | {f(x.MAE_base, 2)} | {f(x.MAE_ref, 2)} | {f(x.d_medio)} | {f(x.DM, 2)} | {f(x.p)} | "
                      f"{f(x.get('p_holm'))} | {', '.join(sig) or 'nenhum'} |")
        md.append("")
    if fora:
        md += ["## Conjuntos fora da interseção (não comparados)", ""] + [f"- {x}" for x in fora] + [""]
    md += ["## Limitações", "",
           "- O DM compara previsões de duas runs nas mesmas datas; não separa fonte de representação quando o número de colunas difere.",
           "- Sementes agregadas por data; a variância entre sementes não entra no teste (o critério §0.7 de `compara_fontes_v02.py` a cobre).",
           "- Sem Model Confidence Set; Holm por família é conservador.", ""]
    (saida / "RELATORIO_DM_ENTRE_BASES.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{len(ag)} testes agrupados, {len(ctrl)} controles → {saida}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--referencia", required=True, help="RUN=rótulo")
    ap.add_argument("--run", action="append", required=True, help="RUN=rótulo; repetível")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--testar-sem-ambiente", action="store_true",
                    help="testa AR e AR_CAL (runs com períodos de treino diferentes, ex. braços COVID)")
    a = ap.parse_args(argv)
    sp = lambda x: tuple(x.split("=", 1)) if "=" in x else (x, x)  # noqa: E731
    rid, rot = sp(a.referencia)
    executar(rid, rot, [sp(x) for x in a.run], Path(a.saida),
             controles={"baseline"} if a.testar_sem_ambiente else set(CONTROLES))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

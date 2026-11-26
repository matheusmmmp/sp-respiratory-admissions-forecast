"""Builds the project page (GitHub Pages) in site/ from the files in results/. No number is typed by hand.

    uv run python docs/scripts/build_site.py              # (re)writes site/ (idempotent)
    uv run python docs/scripts/build_site.py --check      # builds into a temporary folder, compares with site/, exit 1 if stale
    uv run python docs/scripts/build_site.py --saida DIR  # writes the generated files into DIR instead of site/

What it reads (all inside this repository):
- results/runs/<RUN_ID>/model_comparison.csv, manifest.json, folds.csv (10 runs: 5 horizons x 2 targets),
  results/runs/<h = 1 runs>/metrics_by_fold.csv, config.json
- results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A_modelos_por_h.csv, A2_dm_modelos_por_h.csv
- results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/arcal_por_horizonte_dois_alvos.csv,
  erro_sabado_h1.csv
- README.md, README.pt-BR.md (protocol paragraph, Mermaid pipeline, "What is in the box", "What this repository is
  not"), data/README.md (sources, licences, attribution lines), CITATION.cff (title, authors, BibTeX),
  app/graficos.py (model colours, read with ast; nothing is imported from the app)

What it checks before writing anything (raises RuntimeError on any divergence):
- every results/ file it reads has the sha256 recorded in docs/INVENTARIO_FASE0.tsv;
- the AR_CAL table: model_comparison.csv == arcal_por_horizonte_dois_alvos.csv == A_modelos_por_h.csv (both targets),
  via docs/scripts/tabela_readme.py::coletar() plus the urgent-target check added here (|diff| <= 1e-9);
- per-fold means of metrics_by_fold.csv == MAE_medio; MAE_std_semente == dp_sem; the best feature set per model ==
  melhor_conj of A_modelos_por_h.csv; the MAE leader per horizon == lider of A2_dm_modelos_por_h.csv;
  razao == MAE_sab / MAE_demais in erro_sabado_h1.csv; all runs are 'full', clean tree, same test windows.

What it writes (site/ by default): index.html, index.pt-BR.html, data/*.json + copies of the source CSVs (sha256
checked after copying), static/images/*.png (+ .prov.json each), static/images/pipeline_{en,pt}.svg,
build_provenance.json. JSON files carry a 'gerado_em' timestamp that is kept when nothing else changed, so a second
run rewrites nothing. MASE compares models within one horizon only; across horizons the page uses MAE and
skill = 1 - MAE / min(Naive, Seasonal Naive) of the same horizon.
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import html
import json
import platform
import re
import shutil
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402
from jinja2 import Environment, StrictUndefined  # noqa: E402
from markupsafe import Markup  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "docs" / "scripts"))

from tabela_readme import (  # noqa: E402
    A_MODELOS,
    ARCAL_DOIS,
    HS,
    MODELOS,
    ROTULO_DOIS,
    RUNS,
    RUNS_POR_ALVO,
    TOL,
    coletar,
)

SITE = RAIZ / "site"
AMH = RAIZ / "results" / "analise_multihorizonte" / "ANALISE_MULTIHORIZONTE_V02_20261118"
A2_DM = AMH / "A2_dm_modelos_por_h.csv"
NTU = RAIZ / "results" / "numeros_texto_urgencia" / "NUMEROS_TEXTO_URGENCIA_V02_20261118"
ERRO_SAB = NTU / "erro_sabado_h1.csv"
INVENTARIO = RAIZ / "docs" / "INVENTARIO_FASE0.tsv"
README_EN = RAIZ / "README.md"
README_PT = RAIZ / "README.pt-BR.md"
DATA_CARD = RAIZ / "data" / "README.md"
CITATION = RAIZ / "CITATION.cff"
GRAFICOS_APP = RAIZ / "app" / "graficos.py"
SCREENSHOT = "static/images/app_screenshot.png"
PAGES_URL = "https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/"
LIMITE_PNG = 300 * 1024
CONJUNTO = "AR_CAL"
TREINADOS = [k for k, _ in MODELOS[:5]]  # xgboost, sarimax, lstm, ingarch_nb, gam_nb
ALVOS = ("total", "urgencia")
BASE_A_MODELOS = {"total": "cetesb", "urgencia": "urgencia"}  # 'base' column of A_modelos_por_h / A2_dm_modelos_por_h
IGNORAR_NA_COMPARACAO = {"gerado_em", "ambiente"}
STATUS_EN = "Provisional (pre-defence)"
STATUS_PT = "Provisório (pré-defesa)"


# ----------------------------------------------------------------------------- helpers
def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return p.resolve().relative_to(RAIZ).as_posix()


def rotulo(chave: str) -> str:
    """Display label of a model key (the labels of the app and of arcal_por_horizonte_dois_alvos.csv)."""
    return ROTULO_DOIS[dict(MODELOS)[chave]]


def fmt(x: float, casas: int, lang: str) -> str:
    s = f"{x:.{casas}f}"
    return s.replace(".", ",") if lang == "pt" else s


def fmt_int(n: int, lang: str) -> str:
    s = f"{n:,}"
    return s.replace(",", ".") if lang == "pt" else s


class Entradas:
    """Every input file read by the build, with its sha256; results/ files are checked against the inventory."""

    def __init__(self) -> None:
        inv = pd.read_csv(INVENTARIO, sep="\t")
        self.inventario = dict(zip(inv["destino"], inv["sha256"], strict=True))
        self.vistos: dict[str, str] = {}

    def registrar(self, p: Path) -> Path:
        r = rel(p)
        h = sha256(p)
        if r.startswith("results/"):
            if r not in self.inventario:
                raise RuntimeError(f"{r} is not listed in docs/INVENTARIO_FASE0.tsv")
            if self.inventario[r] != h:
                raise RuntimeError(f"{r}: sha256 {h} differs from docs/INVENTARIO_FASE0.tsv ({self.inventario[r]})")
        self.vistos[r] = h
        return p

    def lista(self, paths: list[Path]) -> list[dict]:
        return [{"caminho": rel(p), "sha256": self.vistos[rel(p)]} for p in paths]


# ----------------------------------------------------------------------------- data collection and cross-checks
def linha_mc(mc: pd.DataFrame, chave: str, conjunto: str = CONJUNTO) -> pd.Series:
    sel = mc[(mc["model"] == chave) & (mc["feature_set"] == conjunto)]
    if len(sel) != 1:
        raise RuntimeError(f"model_comparison.csv: {len(sel)} rows for {chave} / {conjunto}")
    return sel.iloc[0]


def coletar_tudo(ent: Entradas) -> dict:
    for alvo in ALVOS:
        for h in HS:
            for nome in ("model_comparison.csv", "manifest.json", "folds.csv"):
                ent.registrar(RUNS / RUNS_POR_ALVO[alvo][h] / nome)
    for p in (A_MODELOS, ARCAL_DOIS, A2_DM, ERRO_SAB):
        ent.registrar(p)

    tab = (
        coletar()
    )  # raises if model_comparison.csv, A_modelos_por_h.csv and arcal_por_horizonte_dois_alvos.csv disagree
    a_mod = pd.read_csv(A_MODELOS)
    a2 = pd.read_csv(A2_DM)
    mcs: dict[str, dict[int, pd.DataFrame]] = {a: {} for a in ALVOS}
    janelas = None
    for alvo in ALVOS:
        am = a_mod[a_mod["base"] == BASE_A_MODELOS[alvo]].set_index(["h", "modelo"])
        for h in HS:
            run_id = RUNS_POR_ALVO[alvo][h]
            d = tab[alvo][h]
            if d["git_sujo"]:
                raise RuntimeError(f"{run_id}: git_sujo is true; a run with a dirty tree cannot be shown")
            mc = pd.read_csv(RUNS / run_id / "model_comparison.csv")
            mcs[alvo][h] = mc
            folds = pd.read_csv(RUNS / run_id / "folds.csv")
            jan = folds[["teste_inicio", "teste_fim", "n_teste"]].to_dict("records")
            if janelas is None:
                janelas = jan
            elif jan != janelas:
                raise RuntimeError(f"{run_id}: test windows differ from the other runs")
            # urgent target vs A_modelos_por_h.csv (tabela_readme cross-checks the total target only)
            for chave in TREINADOS:
                ref = am.loc[(h, chave)]
                if ref["run"] != run_id:
                    raise RuntimeError(f"A_modelos_por_h.csv ({alvo}, h={h}) points to {ref['run']}, expected {run_id}")
                vals = d["modelos"][dict(MODELOS)[chave]]
                for col, val in (("MAE_ARCAL", vals["MAE"]), ("MASE_ARCAL", vals["MASE"])):
                    if abs(float(ref[col]) - val) > TOL:
                        raise RuntimeError(f"{run_id} {chave}: {col} differs from model_comparison.csv")
                if abs(float(ref["skill_vs_ref"]) - vals["skill_vs_ref"]) > TOL:
                    raise RuntimeError(f"{run_id} {chave}: skill_vs_ref differs from A_modelos_por_h.csv")
                linha = linha_mc(mc, chave)
                if chave in ("xgboost", "lstm"):
                    if abs(float(linha["MAE_std_semente"]) - float(ref["dp_sem"])) > TOL:
                        raise RuntimeError(f"{run_id} {chave}: MAE_std_semente differs from dp_sem")
            # leader by MAE == lider of A2_dm_modelos_por_h.csv
            lider = min(TREINADOS, key=lambda k: d["modelos"][dict(MODELOS)[k]]["MAE"])
            linha_a2 = a2[(a2["base"] == BASE_A_MODELOS[alvo]) & (a2["h"] == h)]
            if len(linha_a2) != 1 or linha_a2.iloc[0]["run"] != run_id:
                raise RuntimeError(f"A2_dm_modelos_por_h.csv: no single row for {alvo} h={h} / {run_id}")
            if linha_a2.iloc[0]["lider"] != lider:
                raise RuntimeError(f"{run_id}: MAE leader {lider} != lider {linha_a2.iloc[0]['lider']} in A2")
            d["lider"] = lider
            d["dm_n_sig"] = int(linha_a2.iloc[0]["n_sig_entre_modelos"])
            sig = linha_a2.iloc[0]["sig_entre_modelos"]
            pares = []
            if isinstance(sig, str) and sig.strip():
                for par in sig.split(";"):
                    a, b = (x.strip() for x in par.split("−"))
                    pares.append((a, b))
            if len(pares) != d["dm_n_sig"]:
                raise RuntimeError(f"A2 {alvo} h={h}: n_sig_entre_modelos != number of listed pairs")
            d["dm_pares"] = pares

    preds = {tab[a][h]["n_predicoes"] for a in ALVOS for h in HS}
    if len(preds) != 1:
        raise RuntimeError(f"n_predicoes differs across runs: {preds}")
    man1 = json.loads((RUNS / RUNS_POR_ALVO["total"][1] / "manifest.json").read_text(encoding="utf-8"))
    sementes = list(man1["sementes"])
    modelos_mc = set(mcs["total"][1]["model"])
    if modelos_mc != {k for k, _ in MODELOS}:
        raise RuntimeError(f"models in model_comparison.csv {sorted(modelos_mc)} != MODELOS of tabela_readme")

    # per-fold MAE at h = 1 (mean over seeds), both targets
    por_fold: dict[str, pd.DataFrame] = {}
    for alvo in ALVOS:
        run_id = RUNS_POR_ALVO[alvo][1]
        mbf = pd.read_csv(ent.registrar(RUNS / run_id / "metrics_by_fold.csv"))
        mbf = mbf[mbf["feature_set"].isin([CONJUNTO, "baseline"])]
        pf = mbf.groupby(["model", "fold"])["MAE"].mean().unstack("fold")
        for chave, _ in MODELOS:
            if abs(float(pf.loc[chave].mean()) - tab[alvo][1]["modelos"][dict(MODELOS)[chave]]["MAE"]) > TOL:
                raise RuntimeError(f"{run_id} {chave}: mean of per-fold MAE != MAE_medio")
        por_fold[alvo] = pf

    # ablation at h = 1: MAE per feature set and trained model, both targets
    ablacao: dict[str, pd.DataFrame] = {}
    for alvo in ALVOS:
        run_id = RUNS_POR_ALVO[alvo][1]
        cfg = json.loads((ent.registrar(RUNS / run_id / "config.json")).read_text(encoding="utf-8"))
        ordem = list(cfg["feature_sets"])
        mc = mcs[alvo][1]
        mc = mc[mc["model"].isin(TREINADOS)]
        if set(mc["feature_set"]) != set(ordem):
            raise RuntimeError(f"{run_id}: feature sets in model_comparison.csv != config.json")
        ab = mc.pivot(index="feature_set", columns="model", values="MAE_medio").loc[ordem, TREINADOS]
        am = a_mod[(a_mod["base"] == BASE_A_MODELOS[alvo]) & (a_mod["h"] == 1)].set_index("modelo")
        for chave in TREINADOS:
            melhor = ab[chave].idxmin()
            if melhor != am.loc[chave, "melhor_conj"] or abs(ab[chave].min() - am.loc[chave, "MAE_melhor"]) > TOL:
                raise RuntimeError(f"{run_id} {chave}: best feature set differs from A_modelos_por_h.csv")
            if abs(ab.loc["AR", chave] - am.loc[chave, "MAE_AR"]) > TOL:
                raise RuntimeError(f"{run_id} {chave}: MAE of AR differs from A_modelos_por_h.csv")
        ablacao[alvo] = ab

    # Saturday / other days, h = 1
    sab = pd.read_csv(ERRO_SAB)
    if ((sab["MAE_sab"] / sab["MAE_demais"] - sab["razao"]).abs() > 1e-12).any():
        raise RuntimeError("erro_sabado_h1.csv: razao != MAE_sab / MAE_demais")

    # seed dispersion (MAE_std_semente) per h, XGBoost and LSTM, both targets
    sementes_dp = {
        alvo: {
            chave: [float(linha_mc(mcs[alvo][h], chave)["MAE_std_semente"]) for h in HS]
            for chave in ("xgboost", "lstm")
        }
        for alvo in ALVOS
    }
    dp_fold_xgb_h1 = float(linha_mc(mcs["total"][1], "xgboost")["MAE_std_fold"])

    return {
        "tab": tab,
        "janelas": janelas,
        "n_predicoes": preds.pop(),
        "sementes": sementes,
        "por_fold": por_fold,
        "ablacao": ablacao,
        "sabado": sab,
        "sementes_dp": sementes_dp,
        "dp_fold_xgb_h1": dp_fold_xgb_h1,
    }


# ----------------------------------------------------------------------------- texts read from the repository
def ler_citation(ent: Entradas) -> dict:
    return yaml.safe_load(ent.registrar(CITATION).read_text(encoding="utf-8"))


def bibtex(cff: dict) -> str:
    """@software entry from CITATION.cff (field by field; tests/test_build_site.py checks the mapping)."""
    autores = " and ".join(f"{a['family-names']}, {a['given-names']}" for a in cff["authors"])
    data = dt.date.fromisoformat(str(cff["date-released"]))
    nome = cff["title"].split(":", 1)[0]
    chave = f"{cff['authors'][0]['family-names'].lower()}_{data.year}_{re.sub(r'[^a-z0-9]+', '_', nome.lower())}"
    nota = cff["message"].split(". ", 1)[1].rstrip(".") if ". " in cff["message"] else cff["message"]
    campos = [
        ("author", autores),
        ("title", "{" + cff["title"] + "}"),
        ("year", str(data.year)),
        ("month", str(data.month)),
        ("version", str(cff["version"])),
        ("url", cff["repository-code"]),
        ("license", cff["license"]),
        ("note", nota),
    ]
    corpo = ",\n".join(f"  {k} = {{{v}}}" for k, v in campos)
    return f"@software{{{chave},\n{corpo}\n}}"


def secao(md: str, titulo: str) -> str:
    m = re.search(rf"^## {re.escape(titulo)}\n(.*?)(?=^## |\Z)", md, re.M | re.S)
    if not m:
        raise RuntimeError(f"section '## {titulo}' not found")
    return m.group(1).strip()


def md_inline(s: str, github: str) -> Markup:
    """Minimal inline Markdown -> HTML: `code` (linked to GitHub when it is an existing path), **bold**, [t](http...)."""
    out = []
    for parte in re.split(r"(`[^`]+`)", s):
        if parte.startswith("`") and parte.endswith("`") and len(parte) > 1:
            code = parte[1:-1]
            caminho = RAIZ / code.rstrip("/")
            if re.fullmatch(r"[\w.-]+(/[\w.-]*)+|[\w-]+\.(md|cff|toml)", code) and caminho.exists():
                tipo = "tree" if caminho.is_dir() else "blob"
                out.append(f'<a href="{github}/{tipo}/main/{code.rstrip("/")}"><code>{html.escape(code)}</code></a>')
            else:
                out.append(f"<code>{html.escape(code)}</code>")
            continue
        t = html.escape(parte, quote=False)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)

        def link(m: re.Match) -> str:
            if not m.group(2).startswith("https://"):
                raise RuntimeError(f"relative Markdown link not supported on the page: {m.group(0)}")
            return f'<a href="{m.group(2)}">{m.group(1)}</a>'

        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, t)
        out.append(t)
    return Markup("".join(out))


def ler_readme(p: Path, lang: str, github: str, ent: Entradas) -> dict:
    md = ent.registrar(p).read_text(encoding="utf-8")
    paragrafos = [x.strip() for x in re.split(r"\n\s*\n", md)]
    i_lema = next(i for i, x in enumerate(paragrafos) if x.startswith("**") and x.endswith("**"))
    lema = paragrafos[i_lema].strip("*")
    resumo = paragrafos[i_lema + 1]
    aviso = next(x for x in paragrafos if x.startswith("> **")).lstrip("> ").strip()
    prefixo = "Protocol in one paragraph. " if lang == "en" else "O protocolo em um parágrafo. "
    protocolo = next((x for x in paragrafos if x.startswith(prefixo)), None)
    if protocolo is None:
        raise RuntimeError(f"{p.name}: protocol paragraph starting with {prefixo!r} not found")
    protocolo = protocolo[len(prefixo) :]
    titulo_caixa = "What is in the box" if lang == "en" else "O que há aqui"
    linhas = [ln for ln in secao(md, titulo_caixa).splitlines() if ln.startswith("|")]
    cab = [c.strip() for c in linhas[0].strip("|").split("|")]
    corpo = [[c.strip() for c in ln.strip("|").split("|")] for ln in linhas[2:]]
    if len(corpo) != 10 or any(len(r) != 3 for r in corpo):
        raise RuntimeError(f"{p.name}: 'What is in the box' table changed shape (expected 10 rows x 3 columns)")
    # six of the ten rows: target, environmental series, seven models, ten runs, analyses, app/API/tracking
    escolha = [0, 1, 3, 6, 7, 9]
    caixa = {
        "cabecalho": cab,
        "linhas": [[md_inline(c, github) for c in corpo[i]] for i in escolha],
    }
    titulo_nao = "What this repository is not" if lang == "en" else "O que este repositório não é"
    nao = [md_inline(ln[2:], github) for ln in secao(md, titulo_nao).splitlines() if ln.startswith("- ")]
    if len(nao) < 5:
        raise RuntimeError(f"{p.name}: '{titulo_nao}' has fewer than 5 items")
    m = re.search(r"```mermaid\n(.*?)```", md, re.S)
    if not m:
        raise RuntimeError(f"{p.name}: Mermaid block not found")
    return {
        "lema": lema,
        "resumo": md_inline(resumo, github),
        "aviso": md_inline(aviso, github),
        "protocolo": md_inline(protocolo, github),
        "caixa": caixa,
        "nao": nao,
        "mermaid": m.group(1),
    }


def ler_data_card(ent: Entradas) -> dict:
    md = ent.registrar(DATA_CARD).read_text(encoding="utf-8")
    linhas = {}
    for ln in md.splitlines():
        m = re.match(r"\| `processed/([\w.]+)` \|", ln)
        if m:
            cel = [c.strip() for c in ln.strip("|").split("|")]
            linhas[m.group(1)] = {"fonte": cel[3], "licenca": cel[4]}
    escolhidos = {
        "sih": "sih_daily_lookahead.parquet",
        "cetesb": "cetesb_poluentes_daily.csv",
        "cams": "cams_daily_v2.csv",
    }
    faltam = [f for f in escolhidos.values() if f not in linhas]
    if faltam:
        raise RuntimeError(f"data/README.md: rows not found: {faltam}")
    bloco = md.split("Attribution lines to keep when reusing:", 1)
    if len(bloco) != 2:
        raise RuntimeError("data/README.md: attribution block not found")
    atrib = []
    for ln in bloco[1].strip().splitlines():
        if not ln.startswith("- "):
            break
        atrib.append(ln[2:].strip().strip('"').strip("“”"))
    if len(atrib) != 3:
        raise RuntimeError("data/README.md: expected 3 attribution lines")
    return {k: linhas[v] for k, v in escolhidos.items()} | {"atribuicao": atrib}


def cores_modelos(ent: Entradas) -> dict[str, str]:
    """Same colour per model as the Streamlit app (app/graficos.py, light palette), read with ast."""
    arvore = ast.parse(ent.registrar(GRAFICOS_APP).read_text(encoding="utf-8"))
    vals = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            if no.targets[0].id in ("SLOTS", "ORDEM_MODELOS"):
                vals[no.targets[0].id] = ast.literal_eval(no.value)
    if set(vals) != {"SLOTS", "ORDEM_MODELOS"}:
        raise RuntimeError("app/graficos.py: SLOTS or ORDEM_MODELOS not found")
    por_rotulo = {nome: vals["SLOTS"]["light"][i] for i, nome in enumerate(vals["ORDEM_MODELOS"])}
    cores = {}
    for chave, _ in MODELOS:
        if rotulo(chave) not in por_rotulo:
            raise RuntimeError(f"app/graficos.py has no colour for {rotulo(chave)}")
        cores[chave] = por_rotulo[rotulo(chave)]
    return cores


# ----------------------------------------------------------------------------- pipeline SVG (from the README Mermaid block)
LAYOUT = {
    # (row, column, position in the column stack); row 0 = sources -> features, row 1 = models -> consumers
    "SIH": (0, 0, 0),
    "CETESB": (0, 0, 1),
    "CAMS": (0, 0, 2),
    "ALVO": (0, 1, 0),
    "ENV": (0, 1, 1),
    "GATE": (0, 2, 0),
    "FEAT": (0, 3, 0),
    "MOD": (1, 0, 0),
    "EVAL": (1, 1, 0),
    "ART": (1, 2, 0),
    "MLF": (1, 3, 0),
    "APP": (1, 3, 1),
    "API": (1, 3, 2),
}
ESTILO = {
    "SIH": "src",
    "CETESB": "src",
    "CAMS": "alt",
    "ALVO": "data",
    "ENV": "data",
    "GATE": "gate",
    "FEAT": "proc",
    "MOD": "model",
    "EVAL": "proc",
    "ART": "out",
    "MLF": "layer",
    "APP": "layer",
    "API": "layer",
}


def parse_mermaid(bloco: str) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    linhas = [ln.strip() for ln in bloco.strip().splitlines()]
    if linhas[0] != "flowchart LR":
        raise RuntimeError(f"Mermaid: expected 'flowchart LR', got {linhas[0]!r}")
    rot: dict[str, list[str]] = {}
    arestas = []
    for ln in linhas[1:]:
        for nid, lab in re.findall(r'(\w+)\["([^"]*)"\]', ln):
            partes = lab.split("<br/>")
            if nid in rot and rot[nid] != partes:
                raise RuntimeError(f"Mermaid: node {nid} defined twice with different labels")
            rot[nid] = partes
        nu = re.sub(r'\["[^"]*"\]', "", ln)
        partes = [x.strip() for x in nu.split("-->")]
        if len(partes) != 2 or not all(partes):
            raise RuntimeError(f"Mermaid: unsupported line {ln!r}")
        arestas.append((partes[0], partes[1]))
    nos = set(rot) | {a for e in arestas for a in e}
    if nos != set(LAYOUT):
        raise RuntimeError(f"Mermaid nodes {sorted(nos)} != layout nodes {sorted(LAYOUT)}; update LAYOUT")
    return rot, arestas


def svg_pipeline(bloco: str, titulo: str) -> str:
    rot, arestas = parse_mermaid(bloco)
    CH, PADX, PADY, LH, GAPX, GAPY, MARG, GAPROW = 6.9, 14, 10, 16, 56, 14, 16, 70
    larg = {n: max(len(x) for x in rot[n]) * CH + 2 * PADX for n in rot}
    alt = {n: len(rot[n]) * LH + 2 * PADY for n in rot}
    pos: dict[str, tuple[float, float, float, float]] = {}
    y0 = MARG
    largura_total = 0.0
    for linha in (0, 1):
        cols = sorted({c for (r, c, _) in LAYOUT.values() if r == linha})
        pilhas = {
            c: sorted((n for n, v in LAYOUT.items() if v[0] == linha and v[1] == c), key=lambda n: LAYOUT[n][2])
            for c in cols
        }
        alt_pilha = {c: sum(alt[n] for n in pilhas[c]) + GAPY * (len(pilhas[c]) - 1) for c in cols}
        alt_linha = max(alt_pilha.values())
        x = MARG
        for c in cols:
            w = max(larg[n] for n in pilhas[c])
            y = y0 + (alt_linha - alt_pilha[c]) / 2
            for n in pilhas[c]:
                pos[n] = (x, y, w, alt[n])
                y += alt[n] + GAPY
            x += w + GAPX
        largura_total = max(largura_total, x - GAPX + MARG)
        y0 += alt_linha + GAPROW
    altura_total = y0 - GAPROW + MARG
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura_total:.0f} {altura_total:.0f}" '
        f'width="{largura_total:.0f}" height="{altura_total:.0f}" role="img" aria-labelledby="pipeline-title">',
        f'<title id="pipeline-title">{html.escape(titulo)}</title>',
        '<defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#52514e"/></marker></defs>',
        "<style>"
        "text{font-family:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;font-size:12px;fill:#0b0b0b}"
        ".t{font-weight:600}.e{fill:none;stroke:#52514e;stroke-width:1.4}"
        ".src{fill:#f3f2ee;stroke:#898781}.alt{fill:#f3f2ee;stroke:#898781;stroke-dasharray:5 3}"
        ".data{fill:#e8f1fc;stroke:#2a78d6}.gate{fill:#fdecec;stroke:#e34948}.proc{fill:#fcfcfb;stroke:#52514e}"
        ".model{fill:#e8f1fc;stroke:#184f95;stroke-width:2}.out{fill:#e6f6ef;stroke:#1baf7a}"
        ".layer{fill:#fcfcfb;stroke:#898781}"
        "</style>",
    ]
    for a, b in arestas:
        xa, ya, wa, ha = pos[a]
        xb, yb, wb, hb = pos[b]
        if LAYOUT[a][0] == LAYOUT[b][0]:
            x1, y1, x2, y2 = xa + wa, ya + ha / 2, xb - 2, yb + hb / 2
            dx = (x2 - x1) / 2
            d = f"M{x1:.1f},{y1:.1f} C{x1 + dx:.1f},{y1:.1f} {x2 - dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"
        else:  # row change: down from the bottom of a, across, down into the top of b
            x1, y1 = xa + wa / 2, ya + ha
            x2, y2 = xb + wb / 2, yb - 2
            ym = (y1 + yb) / 2
            d = f"M{x1:.1f},{y1:.1f} L{x1:.1f},{ym:.1f} L{x2:.1f},{ym:.1f} L{x2:.1f},{y2:.1f}"
        partes.append(f'<path class="e" d="{d}" marker-end="url(#seta)"/>')
    for n, (x, y, w, h) in pos.items():
        partes.append(f'<rect class="{ESTILO[n]}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6"/>')
        cx = x + w / 2
        linhas_txt = []
        for i, t in enumerate(rot[n]):
            ty = y + PADY + LH * i + 12
            cls = ' class="t"' if i == 0 else ""
            linhas_txt.append(f'<text x="{cx:.1f}" y="{ty:.1f}" text-anchor="middle"{cls}>{html.escape(t)}</text>')
        partes.extend(linhas_txt)
    partes.append("</svg>")
    return "\n".join(partes) + "\n"


# ----------------------------------------------------------------------------- figures
TXT_FIG = {
    "en": {
        "mae": "MAE (admissions per day)",
        "skill": "Skill vs best naive of the same h",
        "h": "Forecast horizon h (days)",
        "fold": "Fold",
        "por_fold": "MAE per fold",
        "sab": "MAE on Saturdays / MAE on other days",
        "dp_sem": "Std. dev. of MAE across {ns} seeds",
        "alvo": {"total": "total target", "urgencia": "urgent target"},
        "alvo_leg": {"total": "total", "urgencia": "urgent"},
        "conj": "Feature set",
        "prov": "provisional (pre-defence)",
    },
    "pt": {
        "mae": "MAE (internações por dia)",
        "skill": "Skill contra o melhor ingênuo do mesmo h",
        "h": "Horizonte de previsão h (dias)",
        "fold": "Fold",
        "por_fold": "MAE por fold",
        "sab": "MAE aos sábados / MAE nos demais dias",
        "dp_sem": "Desvio-padrão do MAE entre {ns} sementes",
        "alvo": {"total": "alvo total", "urgencia": "alvo de urgência"},
        "alvo_leg": {"total": "total", "urgencia": "urgência"},
        "conj": "Conjunto de features",
        "prov": "provisório (pré-defesa)",
    },
}


def _estilo() -> None:
    plt.rcParams.update(
        {
            "font.size": 10,
            "font.family": "DejaVu Sans",
            "axes.edgecolor": "#c3c2b7",
            "axes.labelcolor": "#0b0b0b",
            "xtick.color": "#52514e",
            "ytick.color": "#52514e",
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlelocation": "left",
            "legend.frameon": False,
            "legend.fontsize": 9,
            "svg.hashsalt": "build_site",
        }
    )


def _eixo(lang: str, figsize=(7.6, 4.2)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e1e0d9", linewidth=0.8)
    ax.set_axisbelow(True)
    if lang == "pt":
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
    return fig, ax


def _salvar(fig, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=110, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    if destino.stat().st_size >= LIMITE_PNG:
        raise RuntimeError(f"{destino.name}: {destino.stat().st_size} bytes, limit is {LIMITE_PNG}")


def figuras(d: dict, cores: dict[str, str], ent: Entradas, saida: Path) -> dict[str, dict]:
    """Writes every PNG in both languages; returns {figure id: {lang: {arquivo, legenda}, fontes, runs}}."""
    _estilo()
    tab = d["tab"]
    xs = np.arange(len(HS))
    out: dict[str, dict] = {}
    runs_todos = {a: [RUNS_POR_ALVO[a][h] for h in HS] for a in ALVOS}
    fontes_tab = [ARCAL_DOIS, A_MODELOS] + [
        RUNS / RUNS_POR_ALVO[a][h] / "model_comparison.csv" for a in ALVOS for h in HS
    ]

    def reg(fid: str, lang: str, legenda: str, fontes: list[Path], runs: list[str], titulo: str) -> None:
        item = out.setdefault(fid, {"fontes": ent.lista(fontes), "runs": runs})
        item[lang] = {"arquivo": f"static/images/{fid}_{lang}.png", "legenda": legenda, "titulo": titulo}

    nf, ns, nt = len(d["janelas"]), len(d["sementes"]), d["janelas"][0]["n_teste"]
    s0, s1 = d["sementes"][0], d["sementes"][-1]
    for lang in ("en", "pt"):
        T = dict(TXT_FIG[lang])
        T["dp_sem"] = T["dp_sem"].format(ns=ns)
        for alvo in ALVOS:
            # (a) MAE by horizon
            fid = f"fig_mae_por_h_{alvo}"
            fig, ax = _eixo(lang)
            for chave, _ in MODELOS:
                ys = [tab[alvo][h]["modelos"][dict(MODELOS)[chave]]["MAE"] for h in HS]
                base = chave in ("naive", "seasonal_naive")
                ax.plot(
                    xs,
                    ys,
                    marker="o",
                    ms=5,
                    lw=1.4 if base else 2,
                    ls="--" if base else "-",
                    color=cores[chave],
                    label=rotulo(chave),
                )
            ax.set_xticks(xs, [f"h = {h}" for h in HS])
            ax.set_ylabel(T["mae"])
            ax.set_xlabel(T["h"])
            titulo = f"MAE, AR_CAL, {T['alvo'][alvo]} · {T['prov']}"
            ax.set_title(titulo)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
            _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
            lideres = []
            for h in HS:
                m = min((k for k, _ in MODELOS), key=lambda k: tab[alvo][h]["modelos"][dict(MODELOS)[k]]["MAE"])
                lideres.append(f"h = {h}: {rotulo(m)} {fmt(tab[alvo][h]['modelos'][dict(MODELOS)[m]]['MAE'], 2, lang)}")
            if lang == "en":
                leg = (
                    f"MAE (admissions per day) by horizon, feature set AR_CAL, {T['alvo'][alvo]}; mean over {nf} folds "
                    f"(and {ns} seeds for XGBoost and LSTM). Lowest MAE per horizon: {'; '.join(lideres)}. "
                    "Dashed lines: the two naive baselines."
                )
            else:
                leg = (
                    f"MAE (internações por dia) por horizonte, conjunto AR_CAL, {T['alvo'][alvo]}; média dos {nf} folds "
                    f"(e das {ns} sementes para XGBoost e LSTM). Menor MAE por horizonte: {'; '.join(lideres)}. "
                    "Linhas tracejadas: os dois modelos ingênuos."
                )
            reg(fid, lang, leg, fontes_tab, runs_todos[alvo], titulo)

            # (b) skill vs the best naive of the same h
            fid = f"fig_skill_por_h_{alvo}"
            fig, ax = _eixo(lang)
            vals = {}
            for chave in TREINADOS:
                ys = [tab[alvo][h]["modelos"][dict(MODELOS)[chave]]["skill_vs_ref"] for h in HS]
                vals[chave] = ys
                ax.plot(xs, ys, marker="o", ms=5, lw=2, color=cores[chave], label=rotulo(chave))
            ax.axhline(0, color="#898781", lw=1)
            ax.set_xticks(xs, [f"h = {h}" for h in HS])
            ax.set_ylabel(T["skill"])
            ax.set_xlabel(T["h"])
            titulo = f"Skill, AR_CAL, {T['alvo'][alvo]} · {T['prov']}"
            ax.set_title(titulo)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
            _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
            pares = [(v, k, HS[i]) for k, ys in vals.items() for i, v in enumerate(ys)]
            mx, mn = max(pares), min(pares)
            if lang == "en":
                leg = (
                    f"Skill = 1 − MAE / min(Naïve, Seasonal Naïve) of the same horizon, AR_CAL, {T['alvo'][alvo]}; "
                    f"comparable across horizons, unlike MASE. Highest: {rotulo(mx[1])} at h = {mx[2]} "
                    f"({fmt(mx[0], 3, lang)}); lowest: {rotulo(mn[1])} at h = {mn[2]} ({fmt(mn[0], 3, lang)})."
                )
            else:
                leg = (
                    f"Skill = 1 − MAE / min(Naïve, Seasonal Naïve) do mesmo horizonte, AR_CAL, {T['alvo'][alvo]}; "
                    f"comparável entre horizontes, ao contrário do MASE. Maior: {rotulo(mx[1])} em h = {mx[2]} "
                    f"({fmt(mx[0], 3, lang)}); menor: {rotulo(mn[1])} em h = {mn[2]} ({fmt(mn[0], 3, lang)})."
                )
            reg(fid, lang, leg, fontes_tab, runs_todos[alvo], titulo)

            # (c) MAE per fold at h = 1
            fid = f"fig_mae_por_fold_h1_{alvo}"
            run1 = RUNS_POR_ALVO[alvo][1]
            pf = d["por_fold"][alvo]
            folds = list(pf.columns)
            fig, ax = _eixo(lang)
            xf = np.arange(len(folds))
            for chave, _ in MODELOS:
                base = chave in ("naive", "seasonal_naive")
                ax.plot(
                    xf,
                    pf.loc[chave].values,
                    marker="o",
                    ms=5,
                    lw=1.4 if base else 2,
                    ls="--" if base else "-",
                    color=cores[chave],
                    label=rotulo(chave),
                )
            jan = d["janelas"]
            ax.set_xticks(
                xf, [f"{T['fold']} {f}\n{jan[i]['teste_inicio']}\n{jan[i]['teste_fim']}" for i, f in enumerate(folds)]
            )
            ax.set_ylabel(T["mae"])
            titulo = f"{T['por_fold']}, h = 1, AR_CAL, {T['alvo'][alvo]} · {T['prov']}"
            ax.set_title(titulo)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
            _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
            lider = tab[alvo][1]["lider"]
            serie = pf.loc[lider]
            if lang == "en":
                leg = (
                    f"MAE per fold at h = 1, AR_CAL, {T['alvo'][alvo]} ({nt} test days per fold; mean over {ns} seeds for "
                    f"XGBoost and LSTM). The MAE leader at h = 1, {rotulo(lider)}, goes from "
                    f"{fmt(serie.min(), 2, lang)} (fold {serie.idxmin()}) to {fmt(serie.max(), 2, lang)} (fold {serie.idxmax()}). "
                    f"Run {run1}."
                )
            else:
                leg = (
                    f"MAE por fold em h = 1, AR_CAL, {T['alvo'][alvo]} ({nt} dias de teste por fold; média das {ns} sementes "
                    f"para XGBoost e LSTM). O líder em MAE em h = 1, {rotulo(lider)}, vai de "
                    f"{fmt(serie.min(), 2, lang)} (fold {serie.idxmin()}) a {fmt(serie.max(), 2, lang)} (fold {serie.idxmax()}). "
                    f"Run {run1}."
                )
            reg(
                fid,
                lang,
                leg,
                [RUNS / run1 / "metrics_by_fold.csv", RUNS / run1 / "folds.csv", RUNS / run1 / "model_comparison.csv"],
                [run1],
                titulo,
            )

            # (d) ablation at h = 1
            fid = f"fig_ablacao_h1_{alvo}"
            ab = d["ablacao"][alvo]
            fig, ax = _eixo(lang, figsize=(7.6, 5.0))
            ax.grid(axis="y", visible=False)
            ax.grid(axis="x", color="#e1e0d9", linewidth=0.8)
            if lang == "pt":
                ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
            yy = np.arange(len(ab.index))[::-1]
            desloc = np.linspace(-0.28, 0.28, len(TREINADOS))
            for j, chave in enumerate(TREINADOS):
                ax.scatter(ab[chave].values, yy + desloc[j], s=30, color=cores[chave], label=rotulo(chave), zorder=3)
            ax.set_yticks(yy, list(ab.index))
            ax.set_xlabel(T["mae"])
            titulo = f"{T['conj']} × MAE, h = 1, {T['alvo'][alvo]} · {T['prov']}"
            ax.set_title(titulo)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
            _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
            melhores = "; ".join(f"{rotulo(k)} {ab[k].idxmin()} {fmt(ab[k].min(), 2, lang)}" for k in TREINADOS)
            if lang == "en":
                leg = (
                    f"Ablation at h = 1, {T['alvo'][alvo]}: MAE of each trained model on each feature set "
                    f"(blocks AR, CAL, METEO, PM25, POLUENTES; PM25MEDIA = PM2.5 mean only). Best set per model: {melhores}. "
                    f"Whether a difference is significant is decided by the paired tests in results/testes_dm/, not by this figure. Run {run1}."
                )
            else:
                leg = (
                    f"Ablação em h = 1, {T['alvo'][alvo]}: MAE de cada modelo treinado em cada conjunto de features "
                    f"(blocos AR, CAL, METEO, PM25, POLUENTES; PM25MEDIA = só a média de PM2,5). Melhor conjunto por modelo: "
                    f"{melhores}. A significância de cada diferença é decidida pelos testes pareados em results/testes_dm/, "
                    f"não por esta figura. Run {run1}."
                )
            reg(
                fid,
                lang,
                leg,
                [RUNS / run1 / "model_comparison.csv", RUNS / run1 / "config.json", A_MODELOS],
                [run1],
                titulo,
            )

        # (e) Saturday ratio, both targets
        fid = "fig_sabado_razao_h1"
        sab = d["sabado"].copy()
        ordem = [rotulo(k) for k, _ in MODELOS if rotulo(k) in set(sab["modelo"])]
        fig, ax = _eixo(lang, figsize=(7.6, 3.8))
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", color="#e1e0d9", linewidth=0.8)
        if lang == "pt":
            ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
        yy = np.arange(len(ordem))[::-1]
        cor_por_rotulo = {rotulo(k): cores[k] for k, _ in MODELOS}
        for i, m in enumerate(ordem):
            t = float(sab[(sab["alvo"] == "total") & (sab["modelo"] == m)]["razao"].iloc[0])
            u = float(sab[(sab["alvo"] == "urgencia") & (sab["modelo"] == m)]["razao"].iloc[0])
            ax.plot([u, t], [yy[i], yy[i]], color="#c3c2b7", lw=1.5, zorder=2)
            ax.scatter([t], [yy[i]], s=60, color=cor_por_rotulo[m], zorder=3)
            ax.scatter([u], [yy[i]], s=60, facecolors="white", edgecolors=cor_por_rotulo[m], linewidths=2, zorder=3)
        ax.axvline(1, color="#898781", lw=1, ls=":")
        ax.set_yticks(yy, ordem)
        ax.set_xlabel(T["sab"])
        ax.scatter([], [], s=60, color="#52514e", label=T["alvo_leg"]["total"])
        ax.scatter(
            [], [], s=60, facecolors="white", edgecolors="#52514e", linewidths=2, label=T["alvo_leg"]["urgencia"]
        )
        titulo = f"{T['sab']}, h = 1, AR_CAL · {T['prov']}"
        ax.set_title(titulo)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
        xg = {a: sab[(sab["alvo"] == a) & (sab["modelo"] == "XGBoost")].iloc[0] for a in ALVOS}
        if lang == "en":
            leg = (
                "Ratio of the MAE on Saturdays to the MAE on the other days, h = 1, AR_CAL, all seeds (filled: total target; "
                f"hollow: urgent target). XGBoost: {fmt(xg['total']['MAE_sab'], 2, lang)} against "
                f"{fmt(xg['total']['MAE_demais'], 2, lang)} on the total target (ratio {fmt(xg['total']['razao'], 2, lang)}), "
                f"ratio {fmt(xg['urgencia']['razao'], 2, lang)} on the urgent target. The Saturday excess comes from elective "
                "day-surgery batches (docs/LESSONS.md, story 1)."
            )
        else:
            leg = (
                "Razão entre o MAE aos sábados e o MAE nos demais dias, h = 1, AR_CAL, todas as sementes (cheio: alvo total; "
                f"vazado: alvo de urgência). XGBoost: {fmt(xg['total']['MAE_sab'], 2, lang)} contra "
                f"{fmt(xg['total']['MAE_demais'], 2, lang)} no alvo total (razão {fmt(xg['total']['razao'], 2, lang)}), "
                f"razão {fmt(xg['urgencia']['razao'], 2, lang)} no alvo de urgência. O excesso do sábado vem de lotes de "
                "cirurgias eletivas de curta permanência (docs/LESSONS.md, história 1)."
            )
        reg(fid, lang, leg, [ERRO_SAB], [RUNS_POR_ALVO["total"][1], RUNS_POR_ALVO["urgencia"][1]], titulo)

        # (f) seed dispersion
        fid = "fig_dispersao_sementes"
        fig, ax = _eixo(lang)
        for chave in ("xgboost", "lstm"):
            for alvo, ls in (("total", "-"), ("urgencia", "--")):
                ax.plot(
                    xs,
                    d["sementes_dp"][alvo][chave],
                    marker="o",
                    ms=5,
                    lw=2,
                    ls=ls,
                    color=cores[chave],
                    label=f"{rotulo(chave)}, {T['alvo_leg'][alvo]}",
                )
        ax.set_xticks(xs, [f"h = {h}" for h in HS])
        ax.set_ylabel(T["dp_sem"])
        ax.set_xlabel(T["h"])
        titulo = f"{T['dp_sem']}, AR_CAL · {T['prov']}"
        ax.set_title(titulo)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        _salvar(fig, saida / f"static/images/{fid}_{lang}.png")
        todos = [
            (v, k, a, HS[i]) for a in ALVOS for k in ("xgboost", "lstm") for i, v in enumerate(d["sementes_dp"][a][k])
        ]
        mx = max(todos)
        if lang == "en":
            leg = (
                f"Mean, over the {nf} folds, of the standard deviation of the MAE across the {ns} seeds, {s0} to {s1} (MAE_std_semente), "
                f"AR_CAL; solid: total target, dashed: urgent "
                f"target. Largest: {rotulo(mx[1])}, {T['alvo'][mx[2]]}, h = {mx[3]} ({fmt(mx[0], 2, lang)}). For scale, the "
                f"standard deviation of the XGBoost MAE across the {nf} folds at h = 1 (total) is {fmt(d['dp_fold_xgb_h1'], 2, lang)}: "
                "results are reported as the mean over seeds, never the best seed."
            )
        else:
            leg = (
                f"Média, sobre os {nf} folds, do desvio-padrão do MAE entre as {ns} sementes, {s0} a {s1} (MAE_std_semente), "
                f"AR_CAL; contínua: alvo total, tracejada: alvo de urgência. "
                f"Maior: {rotulo(mx[1])}, {T['alvo'][mx[2]]}, h = {mx[3]} ({fmt(mx[0], 2, lang)}). Para comparação, o "
                f"desvio-padrão do MAE do XGBoost entre os {nf} folds em h = 1 (total) é {fmt(d['dp_fold_xgb_h1'], 2, lang)}: "
                "os resultados são a média das sementes, nunca a melhor semente."
            )
        reg(fid, lang, leg, fontes_tab, runs_todos["total"] + runs_todos["urgencia"], titulo)
    return out


# ----------------------------------------------------------------------------- page texts
T = {
    "en": {
        "lang": "en",
        "outra": "index.pt-BR.html",
        "outra_rotulo": "Português",
        "status": STATUS_EN,
        "faixa": "The dissertation has not been defended. Every number on this page is read from a file in results/ "
        "and shown with the full id of the run that produced it; numbers can change before the final text.",
        "titulo": None,
        "afil": "Graduate Program in Computer Science (PPGCC), Federal University of Santa Catarina (UFSC)",
        "papeis": ["", "advisor", "co-advisor"],
        "code": "Code",
        "demo": "Demo",
        "data": "Data",
        "data_nota": "Zenodo DOI: pending author decision",
        "diss": "Dissertation (in preparation)",
        "diss_tip": "Not defended yet: no paper, preprint or DOI exists.",
        "api": "API docs",
        "pipeline": "Pipeline",
        "pipeline_leg": "Pipeline, drawn from the Mermaid block of the README (README.md, section Pipeline).",
        "protocolo": "Protocol in one paragraph",
        "glance": "At a glance",
        "caixa": "What is in the box",
        "caixa_nota": "Six of the ten rows of the README table.",
        "results": "Results",
        "tab_titulo": {
            "total": "Total target (all respiratory admissions)",
            "urgencia": "Urgent target (non-elective admissions)",
        },
        "tab_leg": "Cells: MAE (admissions per day, 2 decimals) / MASE (3 decimals), feature set AR_CAL, mean over {nf} folds "
        "(and {ns} seeds for XGBoost and LSTM). Lowest MAE of each horizon highlighted. MASE uses the Naïve of the same h: "
        "compare rows within a column, not columns.",
        "model": "Model",
        "runs_nota": "Runs (full id, commit, clean tree at start, predictions)",
        "limpa": "clean tree",
        "status_urg": "the urgent target has not been validated against TabNet yet (status {s} in each manifest.json)",
        "dm_titulo": "Paired tests (Diebold–Mariano, Holm), AR_CAL, trained models",
        "dm_leg": "Pairs of trained models whose MAE difference is significant after Holm correction "
        "(results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv). Leader = lowest MAE.",
        "dm_h": "h",
        "dm_lider": "Leader",
        "dm_pares": "Significant pairs",
        "nenhum": "none",
        "figs": "Figures",
        "explorer": "Results explorer",
        "explorer_intro": "Pick a target, a horizon and a metric. Everything is read from data/a_modelos_por_h.json, "
        "generated from results/ by docs/scripts/build_site.py; no server, no key.",
        "demo_titulo": "Interactive demo",
        "demo_texto": "The Streamlit app shows the target series, the results by horizon and the Saturday case, every "
        "number read from results/. It is an engineering demonstration, not a clinical or operational tool.",
        "demo_botao": "Open the app",
        "demo_alt": "Home page of the Streamlit app",
        "fontes": "Data sources",
        "fontes_intro": "Only daily aggregates are redistributed (no microdata). Source and licence text copied from data/README.md.",
        "fonte_cols": ["Source", "Used for", "Licence"],
        "uso": {
            "sih": "Target series (daily admissions)",
            "cetesb": "Main environmental source (PM2.5, PM10, NO2, O3, CO, meteorology)",
            "cams": "Alternative environmental source; none of its columns enters a feature in the runs shown here",
        },
        "atrib": "Attribution lines to keep when reusing",
        "cnes": "The Saturday case names one establishment, CNES 2091550 (Instituto CEMA), by its public CNES code and "
        "name: elective day-surgery batches concentrated on Saturdays explain the Saturday excess of the total target "
        "(docs/LESSONS.md, story 1).",
        "nao": "What this repository is not",
        "citar": "Citation",
        "citar_intro": "Software citation generated from CITATION.cff. The dissertation entry will be added after the defence.",
        "contato": "Contact",
        "contato_texto": "Questions, corrections and issues: GitHub issues of the repository.",
        "rodape_build": "Generated by docs/scripts/build_site.py from results/ (build provenance: build_provenance.json).",
        "rodape_tpl": "Page template adapted from Nerfies (CC BY-SA 4.0), following the layout of deeppersona-ai.github.io "
        "(adapted from AgentFlow). site/static/css/site.css: CC BY-SA 4.0. Code of this repository: MIT.",
        "decimal": "",
    },
    "pt": {
        "lang": "pt-BR",
        "outra": "index.html",
        "outra_rotulo": "English",
        "status": STATUS_PT,
        "faixa": "A dissertação ainda não foi defendida. Todo número desta página é lido de um arquivo em results/ e "
        "aparece com o id completo da run que o gerou; os números podem mudar antes do texto final.",
        "titulo": None,
        "afil": "Programa de Pós-Graduação em Ciência da Computação (PPGCC), Universidade Federal de Santa Catarina (UFSC)",
        "papeis": ["", "orientador", "coorientadora"],
        "code": "Código",
        "demo": "Demo",
        "data": "Dados",
        "data_nota": "DOI no Zenodo: pendente de decisão do autor",
        "diss": "Dissertação (em preparação)",
        "diss_tip": "Ainda não defendida: não há artigo, preprint nem DOI.",
        "api": "Docs da API",
        "pipeline": "Pipeline",
        "pipeline_leg": "Pipeline, desenhado a partir do bloco Mermaid do README (README.pt-BR.md, seção Pipeline).",
        "protocolo": "O protocolo em um parágrafo",
        "glance": "Em números",
        "caixa": "O que há aqui",
        "caixa_nota": "Seis das dez linhas da tabela do README.",
        "results": "Resultados",
        "tab_titulo": {
            "total": "Alvo total (todas as internações respiratórias)",
            "urgencia": "Alvo de urgência (internações não eletivas)",
        },
        "tab_leg": "Células: MAE (internações por dia, 2 casas) / MASE (3 casas), conjunto AR_CAL, média dos {nf} folds "
        "(e das {ns} sementes para XGBoost e LSTM). Menor MAE de cada horizonte em destaque. O MASE usa o Naïve do mesmo h: "
        "compare linhas dentro de uma coluna, não colunas. Ponto decimal mantido como nos arquivos de origem.",
        "model": "Modelo",
        "runs_nota": "Runs (id completo, commit, árvore limpa no início, previsões)",
        "limpa": "árvore limpa",
        "status_urg": "o alvo de urgência ainda não foi validado contra o TabNet (status {s} em cada manifest.json)",
        "dm_titulo": "Testes pareados (Diebold–Mariano, Holm), AR_CAL, modelos treinados",
        "dm_leg": "Pares de modelos treinados cuja diferença de MAE é significativa após a correção de Holm "
        "(results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv). Líder = menor MAE.",
        "dm_h": "h",
        "dm_lider": "Líder",
        "dm_pares": "Pares significativos",
        "nenhum": "nenhum",
        "figs": "Figuras",
        "explorer": "Explorador de resultados",
        "explorer_intro": "Escolha alvo, horizonte e métrica. Tudo é lido de data/a_modelos_por_h.json, gerado a partir de "
        "results/ por docs/scripts/build_site.py; sem servidor, sem chave.",
        "demo_titulo": "Demo interativa",
        "demo_texto": "O app Streamlit mostra a série-alvo, os resultados por horizonte e o caso do sábado, com todo número "
        "lido de results/. É uma demonstração de engenharia, não uma ferramenta clínica ou operacional.",
        "demo_botao": "Abrir o app",
        "demo_alt": "Página inicial do app Streamlit",
        "fontes": "Fontes de dados",
        "fontes_intro": "Só agregados diários são redistribuídos (nenhum microdado). Fonte e licença copiadas do "
        "data/README.md (em inglês).",
        "fonte_cols": ["Fonte", "Uso", "Licença"],
        "uso": {
            "sih": "Série-alvo (internações diárias)",
            "cetesb": "Fonte ambiental principal (PM2,5, PM10, NO2, O3, CO, meteorologia)",
            "cams": "Fonte ambiental alternativa; nenhuma coluna dela entra como feature nas runs mostradas aqui",
        },
        "atrib": "Linhas de atribuição a manter no reúso",
        "cnes": "O caso do sábado cita um estabelecimento, o CNES 2091550 (Instituto CEMA), pelo código e pelo nome "
        "públicos do CNES: lotes de cirurgias eletivas de curta permanência concentrados aos sábados explicam o excesso "
        "do sábado no alvo total (docs/LESSONS.md, história 1).",
        "nao": "O que este repositório não é",
        "citar": "Citação",
        "citar_intro": "Citação do software gerada a partir do CITATION.cff. A entrada da dissertação entra depois da defesa.",
        "contato": "Contato",
        "contato_texto": "Dúvidas, correções e problemas: issues do repositório no GitHub.",
        "rodape_build": "Gerada por docs/scripts/build_site.py a partir de results/ (proveniência: build_provenance.json).",
        "rodape_tpl": "Template adaptado do Nerfies (CC BY-SA 4.0), seguindo o layout de deeppersona-ai.github.io "
        "(adaptado do AgentFlow). site/static/css/site.css: CC BY-SA 4.0. Código deste repositório: MIT.",
        "decimal": "",
    },
}


def montar_contexto(lang: str, d: dict, readme: dict, card: dict, cff: dict, figs: dict, cores: dict, bib: str) -> dict:
    t = dict(T[lang])
    t["tab_leg"] = t["tab_leg"].format(nf=len(d["janelas"]), ns=len(d["sementes"]))
    github = cff["repository-code"]
    tab = d["tab"]
    nome, resto = cff["title"].split(": ", 1)
    if lang == "en":
        titulo = resto.split(", with ")[0]
        titulo = titulo[0].upper() + titulo[1:]
    else:
        titulo = (
            f"Previsão diária de internações hospitalares respiratórias no município de São Paulo, "
            f"de {min(HS)} a {max(HS)} dias à frente"
        )
    # results tables
    tabelas = []
    for alvo in ALVOS:
        linhas = []
        for chave, rot in MODELOS:
            celulas = []
            for h in HS:
                v = tab[alvo][h]["modelos"][rot]
                celulas.append(
                    {
                        "h": h,
                        "texto": f"{v['MAE']:.2f} / {v['MASE']:.3f}",
                        "lider": tab[alvo][h]["lider"] == chave,
                    }
                )
            linhas.append({"chave": chave, "rotulo": rotulo(chave), "cor": cores[chave], "celulas": celulas})
        runs = [
            {
                "h": h,
                "run_id": tab[alvo][h]["run_id"],
                "commit": tab[alvo][h]["git_commit"][:7],
                "limpa": not tab[alvo][h]["git_sujo"],
                "n": fmt_int(tab[alvo][h]["n_predicoes"], lang),
                "status": tab[alvo][h]["status"],
            }
            for h in HS
        ]
        status_urg = sorted({r["status"] for r in runs})
        dm = [
            {
                "h": h,
                "lider": rotulo(tab[alvo][h]["lider"]),
                "pares": [f"{rotulo(a)} – {rotulo(b)}" for a, b in tab[alvo][h]["dm_pares"]],
            }
            for h in HS
        ]
        tabelas.append(
            {
                "alvo": alvo,
                "titulo": t["tab_titulo"][alvo],
                "linhas": linhas,
                "runs": runs,
                "nota_status": t["status_urg"].format(s=", ".join(status_urg)) if alvo == "urgencia" else "",
                "dm": dm,
            }
        )
    # headline numbers
    jan = d["janelas"]
    h1 = tab["total"][1]
    lider1 = h1["lider"]
    v1 = h1["modelos"][dict(MODELOS)[lider1]]
    sem = d["sementes"]
    if lang == "en":
        glance = [
            (str(len(MODELOS)), "models under one protocol"),
            (str(len(ALVOS)), "targets: total and urgent admissions"),
            (", ".join(str(h) for h in HS), "forecast horizons h (days)"),
            (str(len(ALVOS) * len(HS)), "identified runs, clean tree at start"),
            (fmt_int(d["n_predicoes"], lang), "predictions per run"),
            (
                f"{len(jan)} × {jan[0]['n_teste']}",
                f"rolling-origin folds × test days ({jan[0]['teste_inicio']} to {jan[-1]['teste_fim']})",
            ),
            (f"{len(sem)}", f"seeds ({sem[0]} to {sem[-1]}) for XGBoost and LSTM, reported as the mean"),
            (
                fmt(v1["MAE"], 2, lang),
                f"lowest MAE at h = 1, total target ({rotulo(lider1)}, MASE {fmt(v1['MASE'], 3, lang)})",
            ),
        ]
    else:
        glance = [
            (str(len(MODELOS)), "modelos sob um protocolo"),
            (str(len(ALVOS)), "alvos: internações totais e de urgência"),
            (", ".join(str(h) for h in HS), "horizontes de previsão h (dias)"),
            (str(len(ALVOS) * len(HS)), "runs identificadas, árvore limpa no início"),
            (fmt_int(d["n_predicoes"], lang), "previsões por run"),
            (
                f"{len(jan)} × {jan[0]['n_teste']}",
                f"folds rolling-origin × dias de teste ({jan[0]['teste_inicio']} a {jan[-1]['teste_fim']})",
            ),
            (f"{len(sem)}", f"sementes ({sem[0]} a {sem[-1]}) para XGBoost e LSTM, reportadas pela média"),
            (
                fmt(v1["MAE"], 2, lang),
                f"menor MAE em h = 1, alvo total ({rotulo(lider1)}, MASE {fmt(v1['MASE'], 3, lang)})",
            ),
        ]
    ordem_figs = [
        "fig_mae_por_h_total",
        "fig_mae_por_h_urgencia",
        "fig_skill_por_h_total",
        "fig_skill_por_h_urgencia",
        "fig_mae_por_fold_h1_total",
        "fig_mae_por_fold_h1_urgencia",
        "fig_ablacao_h1_total",
        "fig_ablacao_h1_urgencia",
        "fig_sabado_razao_h1",
        "fig_dispersao_sementes",
    ]
    if set(ordem_figs) != set(figs):
        raise RuntimeError("figure list out of sync")
    lista_figs = [
        {
            "id": f,
            "arquivo": figs[f][lang]["arquivo"],
            "legenda": figs[f][lang]["legenda"],
            "titulo": figs[f][lang]["titulo"],
            "runs": figs[f]["runs"],
        }
        for f in ordem_figs
    ]
    autores = [
        {"nome": "Matheus de Medeiros Pereira", "papel": t["papeis"][0]},
        {"nome": "Renato Fileto", "papel": t["papeis"][1]},
        {"nome": "Simone S. Werner", "papel": t["papeis"][2]},
    ]
    # the first author must be the CITATION.cff author
    a0 = cff["authors"][0]
    if f"{a0['given-names']} {a0['family-names']}" != autores[0]["nome"]:
        raise RuntimeError("first author differs from CITATION.cff")
    fontes = [
        {"nome": "SIH/SUS (DATASUS)", "chave": "sih", "fonte": card["sih"]["fonte"], "licenca": card["sih"]["licenca"]},
        {
            "nome": "CETESB / QUALAR",
            "chave": "cetesb",
            "fonte": card["cetesb"]["fonte"],
            "licenca": card["cetesb"]["licenca"],
        },
        {
            "nome": "CAMS (Copernicus)",
            "chave": "cams",
            "fonte": card["cams"]["fonte"],
            "licenca": card["cams"]["licenca"],
        },
    ]
    for f in fontes:
        f["uso"] = t["uso"][f["chave"]]
    novos = {
        "nome": nome,
        "titulo": titulo,
        "readme": readme,
        "github": github,
        "app_url": cff["url"],
        "pages_url": PAGES_URL,
        "tabelas": tabelas,
        "hs": HS,
        "numeros": glance,
        "figuras_lista": lista_figs,
        "autores": autores,
        "fontes_lista": fontes,
        "atribuicao": card["atribuicao"],
        "bibtex": bib,
        "screenshot": SCREENSHOT,
        "svg": f"static/images/pipeline_{'en' if lang == 'en' else 'pt'}.svg",
    }
    colisao = (set(novos) & set(t)) - {"titulo"}
    if colisao:
        raise RuntimeError(f"template context keys collide with page texts: {sorted(colisao)}")
    t.update(novos)
    return t


# ----------------------------------------------------------------------------- HTML template
TEMPLATE = r"""<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{{ readme.lema }}">
  <title>{{ nome }}</title>
  <link rel="alternate" hreflang="{{ 'pt-BR' if lang == 'en' else 'en' }}" href="{{ outra }}">
  <link rel="stylesheet" href="static/css/bulma.min.css">
  <link rel="stylesheet" href="static/css/fontawesome.all.min.css">
  <link rel="stylesheet" href="static/css/site.css">
</head>
<body>
<!-- Generated by docs/scripts/build_site.py from results/. Do not edit by hand: edit the script and rebuild. -->
<div class="provisional-banner" id="provisional-banner" role="note">
  <strong>{{ status }}</strong>{% if lang != 'en' %} · <span lang="en">Provisional (pre-defence)</span>{% endif %} — {{ faixa }}
</div>
<nav class="lang-switch"><a href="{{ outra }}" hreflang="{{ 'pt-BR' if lang == 'en' else 'en' }}"><span class="icon"><i class="fas fa-language"></i></span>{{ outra_rotulo }}</a></nav>

<section class="hero">
  <div class="hero-body">
    <div class="container is-max-desktop has-text-centered">
      <p class="publication-repo"><code>{{ nome }}</code></p>
      <h1 class="title is-2 publication-title">{{ titulo }}</h1>
      <p class="subtitle is-5 publication-subtitle">{{ readme.lema }}</p>
      <div class="is-size-5 publication-authors">
        {% for a in autores %}<span class="author-block">{{ a.nome }}{% if a.papel %} <span class="author-role">({{ a.papel }})</span>{% endif %}{% if not loop.last %},{% endif %}</span>
        {% endfor %}
      </div>
      <div class="is-size-6 publication-authors"><span class="author-block">{{ afil }}</span></div>
      <div class="publication-links">
        <span class="link-block"><a href="{{ github }}" class="button is-normal is-rounded is-dark"><span class="icon"><i class="fab fa-github"></i></span><span>{{ code }}</span></a></span>
        <span class="link-block"><a href="{{ app_url }}" class="button is-normal is-rounded is-dark"><span class="icon"><i class="fas fa-desktop"></i></span><span>{{ demo }}</span></a></span>
        <span class="link-block"><a href="{{ github }}/blob/main/data/README.md" class="button is-normal is-rounded is-dark"><span class="icon"><i class="fas fa-database"></i></span><span>{{ data }}</span></a></span>
        <span class="link-block"><span class="button is-normal is-rounded is-dark is-disabled" id="btn-dissertation" aria-disabled="true" title="{{ diss_tip }}"><span class="icon"><i class="fas fa-book"></i></span><span>{{ diss }}</span></span></span>
        <span class="link-block"><a href="{{ github }}/blob/main/api/README.md" class="button is-normal is-rounded is-dark"><span class="icon"><i class="fas fa-code"></i></span><span>{{ api }}</span></a></span>
      </div>
      <p class="is-size-7 link-note">{{ data }}: {{ data_nota }}. {{ diss }}: {{ diss_tip }}</p>
    </div>
  </div>
</section>

<section class="section pt-0">
  <div class="container is-max-desktop">
    <div class="content">
      <p>{{ readme.resumo }}</p>
      <div class="notification is-warning is-light">{{ readme.aviso }}</div>
    </div>
  </div>
</section>

<section class="section pt-0" id="pipeline">
  <div class="container is-max-widescreen">
    <h2 class="title is-3">{{ pipeline }}</h2>
    <figure class="teaser"><img src="{{ svg }}" alt="{{ pipeline_leg }}" width="100%"><figcaption class="caption">{{ pipeline_leg }}</figcaption></figure>
    <div class="box protocol">
      <h3 class="title is-5">{{ protocolo }}</h3>
      <p>{{ readme.protocolo }}</p>
    </div>
  </div>
</section>

<section class="section pt-0" id="glance">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ glance }}</h2>
  </div>
  <div class="container is-max-desktop">
    <div class="columns is-multiline is-mobile glance">
      {% for v, txt in numeros %}<div class="column is-half-mobile is-one-quarter-tablet"><p class="glance-num">{{ v }}</p><p class="glance-txt">{{ txt }}</p></div>
      {% endfor %}
    </div>
    <p class="is-size-7 caption">{{ status }}. {{ rodape_build }}</p>
  </div>
</section>

<section class="section pt-0" id="box">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ caixa }}</h2>
    <div class="table-container">
      <table class="table is-fullwidth is-narrow is-striped">
        <thead><tr>{% for c in readme.caixa.cabecalho %}<th>{{ c }}</th>{% endfor %}</tr></thead>
        <tbody>{% for r in readme.caixa.linhas %}<tr>{% for c in r %}<td>{{ c }}</td>{% endfor %}</tr>{% endfor %}</tbody>
      </table>
    </div>
    <p class="is-size-7 caption">{{ caixa_nota }}</p>
  </div>
</section>

<section class="section pt-0" id="results">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ results }} <span class="tag is-warning is-medium provisional-tag">{{ status }}</span></h2>
    {% for tb in tabelas %}
    <h3 class="title is-5">{{ tb.titulo }} <span class="tag is-warning provisional-tag">{{ status }}</span></h3>
    <div class="table-container">
      <table class="table is-fullwidth is-narrow results-table" id="tabela-{{ tb.alvo }}">
        <thead><tr><th>{{ model }}</th>{% for h in hs %}<th class="has-text-right">h = {{ h }}</th>{% endfor %}</tr></thead>
        <tbody>
        {% for ln in tb.linhas %}<tr><th><span class="dot" style="background:{{ ln.cor }}"></span>{{ ln.rotulo }}</th>{% for c in ln.celulas %}<td class="num{% if c.lider %} is-leader{% endif %}" data-alvo="{{ tb.alvo }}" data-h="{{ c.h }}" data-modelo="{{ ln.chave }}">{{ c.texto }}</td>{% endfor %}</tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <p class="is-size-7 caption">{{ tab_leg }}</p>
    <details class="runs-note"><summary class="is-size-7">{{ runs_nota }}</summary>
      <ul class="is-size-7">{% for r in tb.runs %}<li>h = {{ r.h }}: <code>{{ r.run_id }}</code> · <code>{{ r.commit }}</code> · {% if r.limpa %}{{ limpa }}{% else %}DIRTY{% endif %} · {{ r.n }}</li>{% endfor %}</ul>
    </details>
    <p class="is-size-7 footnote">{{ status }} · runs: {% for r in tb.runs %}<code>{{ r.run_id }}</code>{% if not loop.last %}, {% endif %}{% endfor %}{% if tb.nota_status %}; {{ tb.nota_status }}{% endif %}.</p>
    {% endfor %}

    <h3 class="title is-5 mt-5">{{ dm_titulo }} <span class="tag is-warning provisional-tag">{{ status }}</span></h3>
    <div class="table-container">
      <table class="table is-fullwidth is-narrow dm-table">
        <thead><tr><th></th><th>{{ dm_h }}</th><th>{{ dm_lider }}</th><th>{{ dm_pares }}</th></tr></thead>
        <tbody>
        {% for tb in tabelas %}{% for r in tb.dm %}<tr>{% if loop.first %}<th rowspan="{{ tb.dm|length }}">{{ tb.titulo }}</th>{% endif %}<td>{{ r.h }}</td><td>{{ r.lider }}</td><td>{% if r.pares %}{{ r.pares|join('; ') }}{% else %}{{ nenhum }}{% endif %}</td></tr>
        {% endfor %}{% endfor %}
        </tbody>
      </table>
    </div>
    <p class="is-size-7 caption">{{ dm_leg }}</p>
  </div>
</section>

<section class="section pt-0" id="figures">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ figs }} <span class="tag is-warning is-medium provisional-tag">{{ status }}</span></h2>
    <div class="columns is-multiline">
    {% for f in figuras_lista %}
      <div class="column is-half-desktop is-full-tablet">
        <figure class="result-fig" id="{{ f.id }}">
          <a href="{{ f.arquivo }}"><img src="{{ f.arquivo }}" alt="{{ f.titulo }}" loading="lazy"></a>
          <figcaption class="caption">{{ f.legenda }} <a href="{{ f.arquivo|replace('.png', '.prov.json') }}">prov.json</a></figcaption>
        </figure>
      </div>
    {% endfor %}
    </div>
  </div>
</section>

<section class="section pt-0" id="explorer">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ explorer }} <span class="tag is-warning is-medium provisional-tag">{{ status }}</span></h2>
    <p class="mb-3">{{ explorer_intro }}</p>
    <div id="results-explorer" data-lang="{{ 'en' if lang == 'en' else 'pt' }}" data-src="data/a_modelos_por_h.json">
      <noscript>JavaScript is needed for the explorer; the same numbers are in the tables above.</noscript>
    </div>
  </div>
</section>

<section class="section pt-0" id="demo">
  <div class="container is-max-desktop">
    <div class="box demo-box">
      <div class="columns is-vcentered">
        <div class="column is-5">
          <h2 class="title is-3">{{ demo_titulo }}</h2>
          <p class="mb-4">{{ demo_texto }}</p>
          <a class="button is-medium is-rounded is-dark" href="{{ app_url }}"><span class="icon"><i class="fas fa-play"></i></span><span>{{ demo_botao }}</span></a>
        </div>
        <div class="column is-7"><a href="{{ app_url }}"><img class="screenshot" src="{{ screenshot }}" alt="{{ demo_alt }}" loading="lazy"></a></div>
      </div>
    </div>
  </div>
</section>

<section class="section pt-0" id="data">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ fontes }}</h2>
    <p class="mb-3">{{ fontes_intro }}</p>
    <div class="table-container">
      <table class="table is-fullwidth is-narrow">
        <thead><tr>{% for c in fonte_cols %}<th>{{ c }}</th>{% endfor %}</tr></thead>
        <tbody>{% for f in fontes_lista %}<tr><td><strong>{{ f.nome }}</strong><br><span class="is-size-7">{{ f.fonte }}</span></td><td>{{ f.uso }}</td><td class="is-size-7">{{ f.licenca }}</td></tr>{% endfor %}</tbody>
      </table>
    </div>
    <p><strong>{{ atrib }}:</strong></p>
    <ul class="attribution">{% for a in atribuicao %}<li>“{{ a }}”</li>{% endfor %}</ul>
    <p class="mt-3">{{ cnes }}</p>
  </div>
</section>

<section class="section pt-0" id="not">
  <div class="container is-max-desktop content">
    <h2 class="title is-3">{{ nao }}</h2>
    <ul>{% for item in readme.nao %}<li>{{ item }}</li>{% endfor %}</ul>
  </div>
</section>

<section class="section pt-0" id="citation">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ citar }}</h2>
    <p class="mb-3">{{ citar_intro }}</p>
    <pre id="bibtex"><code>{{ bibtex }}</code></pre>
  </div>
</section>

<section class="section pt-0" id="contact">
  <div class="container is-max-desktop">
    <h2 class="title is-3">{{ contato }}</h2>
    <p><a href="{{ github }}/issues"><span class="icon"><i class="fab fa-github"></i></span>{{ contato_texto }}</a></p>
  </div>
</section>

<footer class="footer">
  <div class="container is-max-desktop content has-text-centered is-size-7">
    <p>{{ status }}. {{ rodape_build }}</p>
    <p>{{ rodape_tpl }}</p>
  </div>
</footer>
<script src="static/js/results_explorer.js"></script>
</body>
</html>
"""


# ----------------------------------------------------------------------------- outputs
def json_estavel(destino: Path, obj: dict) -> None:
    """Writes JSON; keeps the previous 'gerado_em' when nothing else changed, so rebuilding is a no-op."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and "gerado_em" in obj:
        try:
            antigo = json.loads(destino.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            antigo = None
        if isinstance(antigo, dict) and {k: v for k, v in antigo.items() if k != "gerado_em"} == {
            k: v for k, v in obj.items() if k != "gerado_em"
        }:
            obj = dict(obj, gerado_em=antigo["gerado_em"])
    escrever(destino, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def escrever(destino: Path, texto: str) -> None:
    """Writes generated text already in the repository's format (no trailing spaces, LF, one final newline).

    The pre-commit fixers (trailing-whitespace, end-of-file-fixer, mixed-line-ending) would otherwise rewrite the
    generated files and make `--check` fail. Copies of source CSVs do not go through here (see copiar_dados).
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    texto = "\n".join(linha.rstrip() for linha in texto.splitlines()).rstrip("\n") + "\n"
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def ambiente() -> dict:
    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
    }


def copiar_dados(ent: Entradas, saida: Path) -> dict[str, str]:
    """Copies the source CSVs next to the page (site/data/...), checking the sha256 of each copy."""
    copias = {
        A_MODELOS: "data/A_modelos_por_h.csv",
        A2_DM: "data/A2_dm_modelos_por_h.csv",
        ARCAL_DOIS: "data/arcal_por_horizonte_dois_alvos.csv",
        ERRO_SAB: "data/erro_sabado_h1.csv",
    }
    for alvo in ALVOS:
        for h in HS:
            r = RUNS_POR_ALVO[alvo][h]
            copias[RUNS / r / "model_comparison.csv"] = f"data/runs/{r}/model_comparison.csv"
        r1 = RUNS_POR_ALVO[alvo][1]
        copias[RUNS / r1 / "metrics_by_fold.csv"] = f"data/runs/{r1}/metrics_by_fold.csv"
    feitas = {}
    for origem, destino in copias.items():
        alvo_p = saida / destino
        alvo_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origem, alvo_p)
        if sha256(alvo_p) != ent.vistos[rel(origem)]:
            raise RuntimeError(f"copy of {rel(origem)} has a different sha256")
        feitas[destino] = rel(origem)
    return feitas


def json_explorer(d: dict, cores: dict, ent: Entradas) -> dict:
    tab = d["tab"]
    nf, ns = len(d["janelas"]), len(d["sementes"])
    return {
        "gerado_por": "docs/scripts/build_site.py",
        "status": STATUS_EN,
        "conjunto_de_features": CONJUNTO,
        "nota": {
            "en": f"{STATUS_EN}. Feature set {CONJUNTO}; mean over {nf} folds (and {ns} seeds for XGBoost and LSTM).",
            "pt": f"{STATUS_PT}. Conjunto {CONJUNTO}; média dos {nf} folds (e das {ns} sementes para XGBoost e LSTM).",
        },
        "horizontes": HS,
        "modelos": [{"chave": k, "rotulo": rotulo(k), "cor": cores[k]} for k, _ in MODELOS],
        "alvos": {
            alvo: {
                "rotulo": {"en": T["en"]["tab_titulo"][alvo], "pt": T["pt"]["tab_titulo"][alvo]},
                "por_h": {
                    str(h): {
                        "run_id": tab[alvo][h]["run_id"],
                        "git_commit": tab[alvo][h]["git_commit"],
                        "n_predicoes": tab[alvo][h]["n_predicoes"],
                        "status_manifesto": tab[alvo][h]["status"],
                        "valores": {
                            k: {
                                "MAE": tab[alvo][h]["modelos"][r]["MAE"],
                                "MASE": tab[alvo][h]["modelos"][r]["MASE"],
                                "skill": tab[alvo][h]["modelos"][r]["skill_vs_ref"],
                            }
                            for k, r in MODELOS
                        },
                    }
                    for h in HS
                },
            }
            for alvo in ALVOS
        },
        "fontes": ent.lista(
            [ARCAL_DOIS, A_MODELOS] + [RUNS / RUNS_POR_ALVO[a][h] / "model_comparison.csv" for a in ALVOS for h in HS]
        ),
    }


def construir(saida: Path) -> dict:
    ent = Entradas()
    d = coletar_tudo(ent)
    cores = cores_modelos(ent)
    cff = ler_citation(ent)
    github = cff["repository-code"]
    readmes = {"en": ler_readme(README_EN, "en", github, ent), "pt": ler_readme(README_PT, "pt", github, ent)}
    card = ler_data_card(ent)
    bib = bibtex(cff)

    saida.mkdir(parents=True, exist_ok=True)
    shot = saida / SCREENSHOT if (saida / SCREENSHOT).exists() else SITE / SCREENSHOT
    prov_shot = json.loads(shot.with_suffix(".prov.json").read_text(encoding="utf-8"))
    if sha256(shot) != prov_shot["sha256"] or shot.stat().st_size >= LIMITE_PNG:
        raise RuntimeError(f"{SCREENSHOT}: sha256 differs from its .prov.json or file is >= 300 KB")

    figs = figuras(d, cores, ent, saida)
    gerado_em = dt.datetime.now().isoformat(timespec="seconds")
    for fid, item in figs.items():
        for lang in ("en", "pt"):
            png = saida / item[lang]["arquivo"]
            json_estavel(
                png.with_suffix(".prov.json"),
                {
                    "figura": f"{fid}_{lang}",
                    "descricao": item[lang]["legenda"],
                    "artefatos_de_origem": item["fontes"],
                    "runs": item["runs"],
                    "conjunto_de_features": CONJUNTO if "ablacao" not in fid else "all (ablation)",
                    "status": STATUS_EN,
                    "script": "docs/scripts/build_site.py",
                    "gerado_em": gerado_em,
                    "ambiente": ambiente(),
                },
            )
    for lang, sufixo in (("en", "en"), ("pt", "pt")):
        titulo_svg = T[lang]["pipeline_leg"]
        escrever(saida / f"static/images/pipeline_{sufixo}.svg", svg_pipeline(readmes[lang]["mermaid"], titulo_svg))

    copias = copiar_dados(ent, saida)
    json_estavel(saida / "data/a_modelos_por_h.json", json_explorer(d, cores, ent))

    env = Environment(autoescape=True, undefined=StrictUndefined, keep_trailing_newline=True)
    tpl = env.from_string(TEMPLATE)
    for lang, nome in (("en", "index.html"), ("pt", "index.pt-BR.html")):
        ctx = montar_contexto(lang, d, readmes[lang], card, cff, figs, cores, bib)
        escrever(saida / nome, tpl.render(**ctx))

    saidas = {}
    for p in sorted(saida.rglob("*")):
        if p.is_file() and p.suffix in (".html", ".svg", ".png", ".csv") and "static/css" not in p.as_posix():
            saidas[p.relative_to(saida).as_posix()] = sha256(p)
    json_estavel(
        saida / "build_provenance.json",
        {
            "script": "docs/scripts/build_site.py",
            "gerado_em": gerado_em,
            "status": STATUS_EN,
            "ambiente": ambiente(),
            "runs": {a: {str(h): RUNS_POR_ALVO[a][h] for h in HS} for a in ALVOS},
            "entradas": dict(sorted(ent.vistos.items())),
            "copias_de_results": copias,
            "saidas": saidas,
            "verificacoes": [
                "results/ files == docs/INVENTARIO_FASE0.tsv (sha256)",
                "model_comparison.csv == arcal_por_horizonte_dois_alvos.csv == A_modelos_por_h.csv (AR_CAL, both targets, |diff| <= 1e-9)",
                "mean of per-fold MAE (metrics_by_fold.csv) == MAE_medio",
                "MAE_std_semente == dp_sem (A_modelos_por_h.csv)",
                "best feature set and MAE of AR == melhor_conj, MAE_melhor, MAE_AR (A_modelos_por_h.csv)",
                "MAE leader == lider (A2_dm_modelos_por_h.csv)",
                "razao == MAE_sab / MAE_demais (erro_sabado_h1.csv)",
                "all runs: modo full, clean tree, same n_predicoes, same test windows",
            ],
        },
    )
    return {"figs": figs, "saidas": saidas}


# ----------------------------------------------------------------------------- --check
GERADOS_SUFIXOS = (".html", ".svg", ".json", ".csv", ".png")


def _normalizar_json(obj):
    if isinstance(obj, dict):
        return {
            k: _normalizar_json(v)
            for k, v in obj.items()
            if k not in IGNORAR_NA_COMPARACAO and not (isinstance(k, str) and k.endswith(".png"))
        }
    if isinstance(obj, list):
        return [_normalizar_json(v) for v in obj]
    return obj


def comparar(novo: Path, atual: Path) -> list[str]:
    """Differences between a fresh build (novo) and site/ (atual). PNG bytes and the 'gerado_em'/'ambiente' keys are
    not compared (they depend on the platform and on the clock); everything else must be identical."""
    problemas = []
    gerados = {p.relative_to(novo).as_posix() for p in novo.rglob("*") if p.is_file() and p.suffix in GERADOS_SUFIXOS}
    for r in sorted(gerados):
        a, b = novo / r, atual / r
        if not b.exists():
            problemas.append(f"missing in site/: {r}")
            continue
        if r.endswith(".png"):
            if b.stat().st_size >= LIMITE_PNG:
                problemas.append(f"{r}: >= 300 KB")
            continue
        if r.endswith(".json"):
            if _normalizar_json(json.loads(a.read_text(encoding="utf-8"))) != _normalizar_json(
                json.loads(b.read_text(encoding="utf-8"))
            ):
                problemas.append(f"differs: {r}")
            continue
        if a.read_bytes() != b.read_bytes():
            problemas.append(f"differs: {r}")
    extras = (
        {
            p.relative_to(atual).as_posix()
            for p in atual.rglob("*")
            if p.is_file() and p.suffix in GERADOS_SUFIXOS and "static/css" not in p.as_posix()
        }
        - gerados
        - {SCREENSHOT, SCREENSHOT.replace(".png", ".prov.json")}
    )
    problemas += [f"stale file in site/ (not generated): {r}" for r in sorted(extras)]
    return problemas


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=SITE, help="output folder (default: site/)")
    ap.add_argument("--check", action="store_true", help="build into a temporary folder and compare with site/")
    args = ap.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            construir(Path(tmp))
            problemas = comparar(Path(tmp), SITE)
        if problemas:
            print("site/ is stale; run: uv run python docs/scripts/build_site.py")
            for p in problemas:
                print(" -", p)
            sys.exit(1)
        print("site/ is up to date")
        return
    r = construir(args.saida)
    print(f"site written to {args.saida} ({len(r['saidas'])} generated files, {2 * len(r['figs'])} figures)")


if __name__ == "__main__":
    main()

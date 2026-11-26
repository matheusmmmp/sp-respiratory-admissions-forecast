"""Project page (site/): generated from results/ by docs/scripts/build_site.py, never written by hand."""

from __future__ import annotations

import datetime as dt
import html
import importlib.util
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
SITE = RAIZ / "site"
HTMLS = {"en": SITE / "index.html", "pt": SITE / "index.pt-BR.html"}
TEXTO_SUFIXOS = {".html", ".js", ".json", ".md", ".svg", ".css", ".csv"}


def _carregar_build():
    sys.path.insert(0, str(RAIZ / "docs" / "scripts"))
    spec = importlib.util.spec_from_file_location("build_site", RAIZ / "docs" / "scripts" / "build_site.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build():
    return _carregar_build()


@pytest.fixture(scope="module")
def build_tmp(build, tmp_path_factory):
    saida = tmp_path_factory.mktemp("site")
    build.construir(saida)
    return saida


def _arquivos_texto(raiz: Path):
    return [p for p in raiz.rglob("*") if p.is_file() and p.suffix in TEXTO_SUFIXOS]


def test_gerador_roda_limpo_e_site_esta_atualizado(build, build_tmp):
    """A fresh build in a temporary folder equals the committed site/ (PNG bytes and timestamps excepted)."""
    assert (build_tmp / "index.html").exists() and (build_tmp / "index.pt-BR.html").exists()
    problemas = build.comparar(build_tmp, SITE)
    assert problemas == [], "site/ is stale; run: uv run python docs/scripts/build_site.py\n" + "\n".join(problemas)


def test_segunda_execucao_nao_muda_nada(build, build_tmp):
    """Idempotence: building again into the same folder leaves every text file byte-identical."""
    antes = {p: p.read_bytes() for p in _arquivos_texto(build_tmp)}
    build.construir(build_tmp)
    depois = {p: p.read_bytes() for p in _arquivos_texto(build_tmp)}
    assert antes.keys() == depois.keys()
    mudaram = [p.name for p in antes if antes[p] != depois[p]]
    assert mudaram == []


def test_numeros_da_tabela_html_vem_do_csv():
    ref = pd.read_csv(
        RAIZ
        / "results"
        / "numeros_texto_urgencia"
        / "NUMEROS_TEXTO_URGENCIA_V02_20261118"
        / "arcal_por_horizonte_dois_alvos.csv"
    )
    rotulos = {
        "xgboost": "XGBoost",
        "sarimax": "SARIMAX",
        "lstm": "LSTM",
        "ingarch_nb": "INGARCH-NB",
        "gam_nb": "GAM-NB",
        "naive": "Naïve",
        "seasonal_naive": "Seasonal Naïve",
    }
    padrao = re.compile(r'<td class="num[^"]*" data-alvo="(\w+)" data-h="(\d+)" data-modelo="(\w+)">([^<]+)</td>')
    for lang, p in HTMLS.items():
        celulas = padrao.findall(p.read_text(encoding="utf-8"))
        assert len(celulas) == 2 * 5 * 7, f"{lang}: expected 70 result cells, found {len(celulas)}"
        for alvo, h, modelo, texto in celulas:
            linha = ref[(ref["alvo"] == alvo) & (ref["h"] == int(h)) & (ref["modelo"] == rotulos[modelo])]
            assert len(linha) == 1
            esperado = f"{linha['MAE'].iloc[0]:.2f} / {linha['MASE'].iloc[0]:.3f}"
            assert texto == esperado, f"{lang} {alvo} h={h} {modelo}: {texto!r} != {esperado!r}"


def test_json_do_explorador_vem_dos_csv():
    db = json.loads((SITE / "data" / "a_modelos_por_h.json").read_text(encoding="utf-8"))
    runs = RAIZ / "results" / "runs"
    for alvo, dados in db["alvos"].items():
        for h, item in dados["por_h"].items():
            mc = pd.read_csv(runs / item["run_id"] / "model_comparison.csv")
            mc = mc[mc["feature_set"].isin(["AR_CAL", "baseline"])].set_index("model")
            for chave, v in item["valores"].items():
                assert v["MAE"] == pytest.approx(float(mc.loc[chave, "MAE_medio"]), abs=1e-12)
                assert v["MASE"] == pytest.approx(float(mc.loc[chave, "MASE_medio"]), abs=1e-12)
            ref = min(item["valores"]["naive"]["MAE"], item["valores"]["seasonal_naive"]["MAE"])
            for v in item["valores"].values():
                assert v["skill"] == pytest.approx(1 - v["MAE"] / ref, abs=1e-12)


def test_png_abaixo_de_300kb_e_sem_pdf():
    pngs = list(SITE.rglob("*.png"))
    assert pngs, "no PNG in site/"
    grandes = [f"{p.name}: {p.stat().st_size}" for p in pngs if p.stat().st_size >= 300 * 1024]
    assert grandes == []
    assert list(SITE.rglob("*.pdf")) == []


def test_toda_figura_tem_proveniencia_com_sha256_atual():
    from hashlib import sha256

    for png in SITE.rglob("*.png"):
        prov = png.with_suffix(".prov.json")
        assert prov.exists(), f"{png.name} has no .prov.json"
        meta = json.loads(prov.read_text(encoding="utf-8"))
        if meta.get("gerado_por_build_site") is False:  # app screenshot: captured outside the build
            assert sha256(png.read_bytes()).hexdigest() == meta["sha256"]
            continue
        assert meta["script"] == "docs/scripts/build_site.py"
        assert meta["runs"], f"{prov.name}: no run id"
        for r in meta["runs"]:
            assert (RAIZ / "results" / "runs" / r).is_dir(), f"{prov.name}: run {r} not in results/runs/"
        for a in meta["artefatos_de_origem"]:
            assert sha256((RAIZ / a["caminho"]).read_bytes()).hexdigest() == a["sha256"], a["caminho"]


def test_figuras_so_de_runs_da_base_principal():
    """No figure of the mirror/CAMS/hybrid bases (those runs are not in results/ of the portfolio)."""
    for prov in SITE.rglob("*.prov.json"):
        texto = prov.read_text(encoding="utf-8")
        for proibido in ("cetesbmin", "cams_cams", "hibrida"):
            assert proibido not in texto, f"{prov.name} mentions {proibido}"


def test_sem_dobra():
    for p in _arquivos_texto(SITE):
        assert "dobra" not in p.read_text(encoding="utf-8", errors="ignore").lower(), p.name


def test_faixa_provisoria_nos_dois_html():
    for lang, p in HTMLS.items():
        txt = p.read_text(encoding="utf-8")
        assert 'id="provisional-banner"' in txt, lang
        assert "Provisional (pre-defence)" in txt, lang
        # next to every results table
        for alvo in ("total", "urgencia"):
            i = txt.index(f'id="tabela-{alvo}"')
            assert "provisional-tag" in txt[max(0, i - 600) : i], f"{lang}: no provisional tag before table {alvo}"
    assert "Provisório (pré-defesa)" in HTMLS["pt"].read_text(encoding="utf-8")


def test_dissertacao_desabilitada_sem_venue_inventado():
    for p in HTMLS.values():
        txt = p.read_text(encoding="utf-8")
        assert re.search(r'id="btn-dissertation" aria-disabled="true"', txt)
        assert "arxiv.org" not in txt.lower()
        assert "doi.org" not in txt.lower()


def test_secao_o_que_nao_e_preservada():
    for lang, p in HTMLS.items():
        readme = (RAIZ / ("README.md" if lang == "en" else "README.pt-BR.md")).read_text(encoding="utf-8")
        titulo = "What this repository is not" if lang == "en" else "O que este repositório não é"
        sec = readme.split(f"## {titulo}\n", 1)[1].split("\n## ", 1)[0]
        pagina = html.unescape(re.sub(r"<[^>]+>", "", p.read_text(encoding="utf-8")))
        assert titulo in pagina
        for item in (ln[2:] for ln in sec.splitlines() if ln.startswith("- ")):
            limpo = item.replace("**", "").replace("`", "")
            assert limpo in pagina, f"{lang}: missing item {limpo[:60]!r}"


def test_sem_localhost_nem_caminho_local():
    for p in _arquivos_texto(SITE):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        assert "localhost" not in txt, p.name
        assert "127.0.0.1" not in txt, p.name
        assert not re.search(r"[A-Za-z]:\\\\|[A-Za-z]:\\[A-Za-z]|\b[CD]:/", txt), p.name


def test_bibtex_consistente_com_citation_cff(build):
    cff = yaml.safe_load((RAIZ / "CITATION.cff").read_text(encoding="utf-8"))
    bib = build.bibtex(cff)
    assert bib.startswith("@software{")
    campos = dict(re.findall(r"^  (\w+) = \{(.*)\},?$", bib, re.M))
    autores = " and ".join(f"{a['family-names']}, {a['given-names']}" for a in cff["authors"])
    data = dt.date.fromisoformat(str(cff["date-released"]))
    assert campos["author"] == autores
    assert campos["title"] == "{" + cff["title"] + "}"
    assert campos["year"] == str(data.year)
    assert campos["month"] == str(data.month)
    assert campos["version"] == str(cff["version"])
    assert campos["url"] == cff["repository-code"]
    assert campos["license"] == cff["license"]
    assert campos["note"] in cff["message"]
    # the page shows exactly this entry, in both languages; no dissertation entry before the defence
    for p in HTMLS.values():
        txt = html.unescape(p.read_text(encoding="utf-8"))
        assert bib in txt
        assert "@phdthesis" not in txt and "@mastersthesis" not in txt


def test_svg_do_pipeline_fiel_ao_mermaid(build):
    for lang, readme in (("en", "README.md"), ("pt", "README.pt-BR.md")):
        md = (RAIZ / readme).read_text(encoding="utf-8")
        bloco = re.search(r"```mermaid\n(.*?)```", md, re.S).group(1)
        rot, arestas = build.parse_mermaid(bloco)
        svg = html.unescape((SITE / "static" / "images" / f"pipeline_{lang}.svg").read_text(encoding="utf-8"))
        for linhas in rot.values():
            for t in linhas:
                assert f">{t}</text>" in svg, f"{lang}: label {t!r} missing in the SVG"
        assert svg.count('class="e"') == len(arestas)

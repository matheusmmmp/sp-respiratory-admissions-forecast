"""Teste de fumaça do app Streamlit: Home e cada página rodam sem exceção (streamlit.testing.v1.AppTest),
nos dois idiomas (en, pt).

Também exercita as trocas de alvo/horizonte das páginas, para cobrir os dois alvos e todas as runs, e confere que
toda chave usada em `t("...")` existe nos dois idiomas.
"""

import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from streamlit.testing.v1 import AppTest  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
APP = RAIZ / "app"
PAGINAS = sorted((APP / "pages").glob("*.py"))
TODAS = [APP / "Home.py"] + PAGINAS
TIMEOUT = 120
IDIOMAS = ["en", "pt"]
BANNER = {"en": "provisional (pre-defense)", "pt": "provisórios (pré-defesa)"}
FONTE = {"en": "Source:", "pt": "Fonte:"}

sys.path.insert(0, str(APP))


def _rodar(caminho: Path, lang: str = "en") -> AppTest:
    at = AppTest.from_file(str(caminho), default_timeout=TIMEOUT)
    at.session_state["lang"] = lang
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _mudar_radio(at: AppTest, key: str, valor) -> None:
    at.radio(key=key).set_value(valor).run()
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("lang", IDIOMAS)
def test_home_abre_sem_excecao(lang: str):
    at = _rodar(APP / "Home.py", lang)
    assert any(BANNER[lang] in w.value.lower() for w in at.warning)
    assert at.metric, "Home must show at least one metric read from a file"


@pytest.mark.parametrize("lang", IDIOMAS)
@pytest.mark.parametrize("pagina", PAGINAS, ids=[p.stem for p in PAGINAS])
def test_cada_pagina_abre_sem_excecao(pagina: Path, lang: str):
    at = _rodar(pagina, lang)
    assert any(BANNER[lang] in w.value.lower() for w in at.warning), "every page carries the provisional label"
    assert any(FONTE[lang] in c.value for c in at.caption), "every page shows the source file of its numbers"
    outro = "pt" if lang == "en" else "en"
    assert not any(BANNER[outro] in w.value.lower() for w in at.warning), "banner must be in the chosen language"


def test_seletor_de_idioma_troca_e_persiste():
    at = _rodar(APP / "Home.py")
    assert at.sidebar.radio(key="lang_sel").value == "en"
    at.sidebar.radio(key="lang_sel").set_value("pt").run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["lang"] == "pt"
    assert at.query_params.get("lang") == "pt"
    assert any(BANNER["pt"] in w.value.lower() for w in at.warning)


def test_query_param_define_idioma():
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=TIMEOUT)
    at.query_params["lang"] = "pt"
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["lang"] == "pt"


def test_overview_alvo_urgencia():
    at = _rodar(APP / "pages" / "1_Overview.py")
    _mudar_radio(at, "ov_alvo", "urgencia")
    assert any("sih_daily_lookahead_urgencia" in c.value for c in at.caption)


@pytest.mark.parametrize("alvo", ["total", "urgencia"])
def test_modelos_por_horizonte_todos_os_h(alvo: str):
    at = _rodar(APP / "pages" / "2_Models_by_horizon.py")
    _mudar_radio(at, "mh_alvo", alvo)
    for h in [1, 5, 7, 15, 30]:
        _mudar_radio(at, "mh_h", h)
        _mudar_radio(at, "ab_h", h)
        _mudar_radio(at, "dm_h", h)
    _mudar_radio(at, "ab_metrica", "MASE_medio")


def test_sabado_controles():
    at = _rodar(APP / "pages" / "3_The_Saturday_case.py", "pt")
    _mudar_radio(at, "sab_periodo", "per_2019")
    _mudar_radio(at, "sab_estab", "met_total")
    _mudar_radio(at, "sab_metr", "met_vies")
    for h in [5, 7, 15, 30]:
        _mudar_radio(at, "sab_h", h)


def test_leitura_falha_alto_se_faltar_arquivo():
    import dados

    with pytest.raises(FileNotFoundError):
        dados.caminho("results/runs/run_que_nao_existe/metrics.json")


def test_skill_total_bate_com_arquivo():
    """O skill calculado a partir dos MAEs (fórmula do app) reproduz o skill_vs_ref do arquivo (alvo total)."""
    import dados

    tab = dados.tabela_arcal("total")
    base = dados.carregar_arcal_dois_alvos()
    base = base[base["alvo"] == "total"]
    ref = base[base["modelo"].isin(["Naïve", "Seasonal Naïve"])].groupby("h")["MAE"].min()
    for _, r in tab[~tab["modelo"].isin(["Naïve", "Seasonal Naïve"])].iterrows():
        assert abs((1 - r["MAE"] / ref[r["h"]]) - r["skill_vs_ref"]) < 1e-9


def test_todas_as_chaves_de_t_existem_nos_dois_idiomas():
    """Varre app/*.py e app/pages/*.py por t("...") e t(f"prefixo.{x}") e confere contra o dicionário."""
    from i18n import IDIOMAS as IDS
    from i18n import TEXTOS

    for chave, por_idioma in TEXTOS.items():
        assert set(por_idioma) == set(IDS), f"key {chave!r} must have exactly {sorted(IDS)}"
        for lang, texto in por_idioma.items():
            assert texto not in (None, ""), f"key {chave!r} is empty in {lang!r}"

    arquivos = list(APP.glob("*.py")) + list((APP / "pages").glob("*.py"))
    literais: set[str] = set()
    prefixos: set[str] = set()
    for arq in arquivos:
        codigo = arq.read_text(encoding="utf-8")
        literais |= set(re.findall(r"""\bt\(\s*"([^"]+)"\s*[,)]""", codigo))
        literais |= set(re.findall(r"""\bt\(\s*'([^']+)'\s*[,)]""", codigo))
        prefixos |= set(re.findall(r"""\bt\(\s*f"([a-z_.]+)\{""", codigo))
    assert literais, "no t(...) call found"
    faltam = sorted(k for k in literais if k not in TEXTOS)
    assert not faltam, f"keys used in t() but missing from i18n.TEXTOS: {faltam}"
    for pref in prefixos:
        assert any(k.startswith(pref) for k in TEXTOS), f"no key starts with dynamic prefix {pref!r}"


def test_fmt_num_por_idioma():
    import streamlit as st
    from i18n import fmt_num

    st.session_state["lang"] = "en"
    assert fmt_num(303295, 0) == "303,295" and fmt_num(18.5566, 2) == "18.56"
    st.session_state["lang"] = "pt"
    assert fmt_num(303295, 0) == "303.295" and fmt_num(18.5566, 2) == "18,56"
    st.session_state["lang"] = "en"

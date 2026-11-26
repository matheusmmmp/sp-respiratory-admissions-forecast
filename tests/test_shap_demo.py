"""Checks of the SHAP outputs of the demonstration models (models_demo/shap/).

Demonstration, not a dissertation result. What is checked, per horizon:

* additivity: ``base + sum(SHAP)`` stored in ``shap_valores_h{h}.parquet`` equals
  the model margin (``output_margin=True``) on features rebuilt by
  ``models_demo.comum`` (|delta| < 1e-4), and ``exp(margem)`` equals the API path
  ``comum.prever_direto`` (relative tolerance < 1e-5);
* the SHAP columns are exactly ``metadata.json -> modelos[h].features``, in order;
* no feature has lag < h;
* ``resumo_importancia.csv`` matches the mean |SHAP| recomputed from the parquet;
* every expected output exists and each ``.prov.json`` carries the right model sha256.

No network, no training. If the outputs are missing the tests FAIL (not skip):
generate them with ``uv run python -m models_demo.interpretabilidade``.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from models_demo import comum

PASTA = comum.PASTA_MODELOS / "shap"
HORIZONTES = (1, 7, 30)
EXTRAS = ["base", "margem", "previsao"]
FIGURAS = [f"fig_importancia_h{h}" for h in HORIZONTES] + [
    "fig_beeswarm_h1",
    "fig_dependencia_dow_h1",
    "fig_dependencia_lag_h1",
    "fig_waterfall_sabado_h1",
    "fig_waterfall_quarta_h1",
]
ARQUIVOS = (
    [f"shap_valores_h{h}.parquet" for h in HORIZONTES]
    + [f"features_h{h}.parquet" for h in HORIZONTES]
    + ["resumo_importancia.csv", "manifest.json", "LEIA-ME.md"]
    + [f"{f}_{lang}.{ext}" for f in FIGURAS for lang in ("en", "pt") for ext in ("png", "prov.json")]
)
N_AMOSTRA_API = 25  # dates per horizon checked one by one through comum.prever_direto


def _exigir(nome: str):
    p = PASTA / nome
    if not p.exists():
        pytest.fail(
            f"{comum.caminho_relativo(p)} missing. Generate the SHAP outputs with "
            "`uv run python -m models_demo.interpretabilidade`. This is a failure, not a skip."
        )
    return p


@pytest.fixture(scope="module")
def meta() -> dict:
    return json.loads(comum.CAMINHO_METADATA.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def shaps() -> dict[int, pd.DataFrame]:
    return {h: pd.read_parquet(_exigir(f"shap_valores_h{h}.parquet")) for h in HORIZONTES}


@pytest.fixture(scope="module")
def construidos() -> dict:
    out = {}
    for h in HORIZONTES:
        ds, colunas, _ = comum.construir_para(h)
        out[h] = (ds, colunas, comum.carregar_modelo(h))
    return out


def test_arquivos_existem():
    faltando = [n for n in ARQUIVOS if not (PASTA / n).exists()]
    if faltando:
        pytest.fail(
            "SHAP outputs missing: " + ", ".join(faltando) + ". Run `uv run python -m models_demo.interpretabilidade`."
        )
    for f in FIGURAS:
        for lang in ("en", "pt"):
            assert (PASTA / f"{f}_{lang}.png").stat().st_size <= 300_000, f"{f}_{lang}.png is larger than 300 KB"


@pytest.mark.parametrize("h", HORIZONTES)
def test_features_iguais_ao_metadata(h, meta, shaps):
    feats = meta["modelos"][str(h)]["features"]
    assert list(shaps[h].columns) == feats + EXTRAS


@pytest.mark.parametrize("h", HORIZONTES)
def test_nenhuma_feature_com_lag_menor_que_h(h, meta, shaps):
    feats = [c for c in shaps[h].columns if c not in EXTRAS]
    for c, lag in comum.lags_das_colunas(feats).items():
        if lag is None:
            assert c in comum.COLUNAS_CALENDARIO, f"unlagged feature {c} is not a calendar column"
        else:
            assert lag >= h, f"h={h}: {c} has lag {lag} < h"
    assert (
        min(v for v in comum.lags_das_colunas(feats).values() if v is not None)
        == (meta["modelos"][str(h)]["lag_minimo_das_features"])
    )


@pytest.mark.parametrize("h", HORIZONTES)
def test_aditividade_e_previsao_da_api(h, meta, shaps, construidos):
    df = shaps[h]
    ds, colunas, modelo = construidos[h]
    assert list(colunas) == meta["modelos"][str(h)]["features"]
    assert df.index.equals(pd.DatetimeIndex(ds.X.index, name="data_alvo")), "target dates differ from the builder"
    margem_modelo = modelo.predict(comum.matriz(ds, colunas), output_margin=True).astype(np.float64)
    soma = df["base"].to_numpy() + df[colunas].to_numpy().sum(axis=1)
    assert np.max(np.abs(soma - margem_modelo)) < 1e-4
    assert np.max(np.abs(df["margem"].to_numpy() - margem_modelo)) < 1e-6
    assert np.ptp(df["base"].to_numpy()) == 0.0, "base must be the same for every row"
    # exp(margin) is the API point forecast (same function the API tests compare against)
    idx = np.linspace(0, len(df) - 1, N_AMOSTRA_API).round().astype(int)
    for data in df.index[idx]:
        api = comum.prever_direto(modelo, ds, colunas, data)
        assert abs(np.exp(df.at[data, "margem"]) - api) / api < 1e-5, f"h={h} {data.date()}"
    prev_todas = modelo.predict(comum.matriz(ds, colunas)).astype(np.float64)
    assert np.max(np.abs(np.exp(df["margem"].to_numpy()) - prev_todas) / prev_todas) < 1e-5
    assert np.max(np.abs(df["previsao"].to_numpy() - prev_todas) / prev_todas) < 1e-6


def test_resumo_importancia_bate_com_parquet(meta, shaps):
    resumo = pd.read_csv(_exigir("resumo_importancia.csv"))
    for h in HORIZONTES:
        feats = meta["modelos"][str(h)]["features"]
        r = resumo[resumo.h == h].set_index("feature")
        assert sorted(r.index) == sorted(feats)
        recalculado = shaps[h][feats].abs().mean(axis=0)
        np.testing.assert_allclose(r.loc[feats, "media_abs_shap"].to_numpy(), recalculado.to_numpy(), rtol=1e-8)
        ordem = r.sort_values("posicao").index.tolist()
        assert ordem == recalculado.sort_values(ascending=False, kind="mergesort").index.tolist()


def test_prov_json_com_sha256_do_modelo(meta):
    shas_modelo = {h: comum.sha256_arquivo(comum.caminho_modelo(h)) for h in HORIZONTES}
    for h in HORIZONTES:
        assert shas_modelo[h] == meta["modelos"][str(h)]["arquivo_sha256"]
    for f in FIGURAS:
        for lang in ("en", "pt"):
            prov = json.loads(_exigir(f"{f}_{lang}.prov.json").read_text(encoding="utf-8"))
            h = prov["modelo"]["horizonte"]
            assert prov["modelo"]["sha256"] == shas_modelo[h], f"{f}_{lang}: model sha256"
            assert prov["modelo"]["arquivo"] == comum.caminho_relativo(comum.caminho_modelo(h))
            assert prov["modelo"]["versao"] == meta["versao"]
            assert prov["png_sha256"] == comum.sha256_arquivo(PASTA / f"{f}_{lang}.png"), f"{f}_{lang}: png sha256"
            for art in prov["artefatos_de_origem"] + prov["entradas"]:
                assert comum.sha256_arquivo(comum.RAIZ / art["caminho"]) == art["sha256"], art["caminho"]
            assert "not a dissertation result" in prov["status"]
            assert "dobra" not in json.dumps(prov, ensure_ascii=False).lower()


def test_regra_das_datas_explicadas(shaps):
    sel = json.loads(_exigir("manifest.json").read_text(encoding="utf-8"))["selecao_waterfall"]
    df = shaps[1]
    sab = df[(df.index.year == 2024) & (df.index.dayofweek == 5)]
    esperado = sab.index[np.argmax(sab["previsao"].to_numpy())]  # argmax returns the first (earliest) on ties
    assert sel["sabado"]["data"] == esperado.date().isoformat()
    assert sel["quarta"]["data"] == (esperado - pd.Timedelta(days=3)).date().isoformat()
    assert pd.Timestamp(sel["quarta"]["data"]).dayofweek == 2

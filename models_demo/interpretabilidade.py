"""SHAP values of the demonstration XGBoost ``AR_CAL`` models (h = 1, 7, 30).

Demonstration, not a dissertation result; provisional. The models explained here
are the ones in ``models_demo/`` (whole 2019-2024 history, one seed, see
``models_demo/MODEL_CARD.md``). SHAP explains what *the model* does with its
inputs; it says nothing causal about admissions.

Method
------
XGBoost's native TreeSHAP: ``Booster.predict(DMatrix(X), pred_contribs=True)``.
No extra dependency. The features are built through exactly the same path as
training and serving (``models_demo.comum.construir_para`` and ``matriz``).

Scale. The objective is ``count:poisson``, so the trees add up on the
**log-margin** scale: ``margem = base + sum(phi_j)`` and the forecast is
``exp(margem)`` admissions/day. ``base`` is ``log(base_score)``, the same for
every row. In count terms each contribution is a multiplicative factor:
``forecast = exp(base) * prod(exp(phi_j))``; a contribution of +0.10 multiplies
the forecast by about 1.105. Every figure states this.

Outputs (``models_demo/shap/``, deterministic for the same inputs except the
``gerado_em`` timestamp in the JSON files):

* ``shap_valores_h{h}.parquet``: one row per target date (index ``data_alvo``),
  one column per feature with its SHAP value (log-margin), plus ``base``,
  ``margem`` (model output with ``output_margin=True``) and ``previsao``
  (model prediction, admissions/day);
* ``features_h{h}.parquet``: the feature values fed to the model (float32, as
  served) and the observed target ``alvo_observado``, same index; used to colour
  the figures;
* ``resumo_importancia.csv``: mean |SHAP| per feature and horizon;
* ``fig_*_{en,pt}.png`` + ``.prov.json`` each; ``manifest.json``.

Run: ``uv run python -m models_demo.interpretabilidade``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xgboost as xgb  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from models_demo import comum  # noqa: E402

PASTA_SHAP = comum.PASTA_MODELOS / "shap"
SCRIPT = "models_demo/interpretabilidade.py"
COMANDO = "uv run python -m models_demo.interpretabilidade"
METODO = (
    "XGBoost native TreeSHAP: Booster.predict(DMatrix(X), pred_contribs=True); contributions on the "
    "log-margin scale of count:poisson (forecast = exp(base + sum of contributions))"
)
STATUS = "demonstration, not a dissertation result; provisional"
LIMITE_PNG = 300_000  # bytes
TOL_ADITIVIDADE = 1e-4
H_DETALHE = 1  # horizon of the beeswarm, dependence and waterfall figures

COR_AR = "#184f95"
COR_CAL = "#898781"
COR_POS = "#d55e00"
COR_NEG = "#2a78d6"
COR_PONTO = "#52514e"
COR_GRADE = "#e1e0d9"
CMAP_VALOR = LinearSegmentedColormap.from_list("baixo_alto", ["#2a78d6", "#d9d8d0", "#d55e00"])

DIAS = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "pt": ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
}
T = {
    "en": {
        "aviso": "Demonstration, not a dissertation result · provisional · model {versao}",
        "escala": "SHAP on the log-margin scale of count:poisson: forecast = exp(base + Σ SHAP); "
        "a contribution φ multiplies the forecast by exp(φ).",
        "imp_titulo": "h = {h}: global importance, demo XGBoost AR_CAL",
        "imp_x": "mean |SHAP| over {n} target dates (log-margin units)",
        "bloco_AR": "AR (lags of the target)",
        "bloco_CAL": "CAL (calendar of the target date)",
        "bee_titulo": "h = 1: SHAP value of each feature on each target date",
        "bee_x": "SHAP value (log-margin; > 0 raises the forecast)",
        "bee_cor": "feature value (low → high, 5th–95th percentile)",
        "dow_titulo": "h = 1: contribution of the day of the week (dow)",
        "dow_y": "SHAP of dow (log-margin)",
        "dow_x": "day of the week of the target date",
        "mediana": "median",
        "lag_titulo": "h = 1: dependence on {f}, the most important lag",
        "lag_x": "{f} (admissions on day u − {L})",
        "lag_y": "SHAP of {f} (log-margin)",
        "lag_sab": "target date is a Saturday",
        "lag_outros": "other days",
        "wf_titulo": "h = 1, {dia} {data}: forecast {prev} admissions/day",
        "wf_x": "log-margin (base + cumulative SHAP)",
        "wf_base": "base {b} → exp = {eb}/day",
        "wf_final": "margin {m} → forecast {p}/day",
        "sabado": "Saturday",
        "quarta": "Wednesday",
        "wf_regra": "Rule: the 2024 Saturday with the highest h = 1 forecast and the Wednesday of the same week "
        "(Saturday − 3 days). In-sample: the model was trained on this date.",
    },
    "pt": {
        "aviso": "Demonstração, não é resultado da dissertação · provisório · modelo {versao}",
        "escala": "SHAP na escala da margem (log) do count:poisson: previsão = exp(base + Σ SHAP); "
        "uma contribuição φ multiplica a previsão por exp(φ).",
        "imp_titulo": "h = {h}: importância global, XGBoost AR_CAL de demonstração",
        "imp_x": "média do |SHAP| em {n} datas-alvo (unidades da margem log)",
        "bloco_AR": "AR (defasagens do alvo)",
        "bloco_CAL": "CAL (calendário da data-alvo)",
        "bee_titulo": "h = 1: valor SHAP de cada feature em cada data-alvo",
        "bee_x": "valor SHAP (margem log; > 0 aumenta a previsão)",
        "bee_cor": "valor da feature (baixo → alto, percentis 5–95)",
        "dow_titulo": "h = 1: contribuição do dia da semana (dow)",
        "dow_y": "SHAP de dow (margem log)",
        "dow_x": "dia da semana da data-alvo",
        "mediana": "mediana",
        "lag_titulo": "h = 1: dependência de {f}, a defasagem mais importante",
        "lag_x": "{f} (internações no dia u − {L})",
        "lag_y": "SHAP de {f} (margem log)",
        "lag_sab": "data-alvo é sábado",
        "lag_outros": "demais dias",
        "wf_titulo": "h = 1, {dia} {data}: previsão de {prev} internações/dia",
        "wf_x": "margem log (base + SHAP acumulado)",
        "wf_base": "base {b} → exp = {eb}/dia",
        "wf_final": "margem {m} → previsão {p}/dia",
        "sabado": "sábado",
        "quarta": "quarta-feira",
        "wf_regra": "Regra: o sábado de 2024 com maior previsão para h = 1 e a quarta-feira da mesma semana "
        "(sábado − 3 dias). Dentro da amostra: o modelo foi treinado com esta data.",
    },
}


# ----------------------------------------------------------------- utilities
def _fmt(v: float, casas: int, lang: str) -> str:
    s = f"{v:.{casas}f}"
    return s.replace(".", ",") if lang == "pt" else s


def _fmt_sinal(v: float, casas: int, lang: str) -> str:
    s = f"{v:+.{casas}f}".replace("-", "−")
    return s.replace(".", ",") if lang == "pt" else s


def _formatador(lang: str) -> FuncFormatter:
    return FuncFormatter(lambda v, _: (f"{v:g}".replace(".", ",") if lang == "pt" else f"{v:g}").replace("-", "−"))


def _escrever_texto(p: Path, texto: str) -> None:
    p.write_text(texto, encoding="utf-8", newline="\n")


def _escrever_json(p: Path, obj: dict) -> None:
    _escrever_texto(p, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def _agora() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _ambiente() -> dict:
    return {
        "python": platform.python_version(),
        "xgboost": xgb.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "matplotlib": matplotlib.__version__,
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
        }
    )


def _eixo(figsize=(7.6, 4.4)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_axisbelow(True)
    return fig, ax


def _rodape(fig, lang: str, versao: str, extra: str | None = None) -> None:
    linhas = [T[lang]["escala"], T[lang]["aviso"].format(versao=versao)]
    if extra:
        linhas.insert(0, extra)
    fig.text(0.01, -0.01, "\n".join(linhas), ha="left", va="top", fontsize=7.5, color="#52514e", wrap=True)


def _salvar(fig, destino: Path) -> None:
    fig.savefig(destino, dpi=110, bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
    if destino.stat().st_size > LIMITE_PNG:
        raise RuntimeError(f"{destino.name}: {destino.stat().st_size} bytes, limit is {LIMITE_PNG}")


def _bloco(feature: str) -> str:
    return "CAL" if feature in comum.COLUNAS_CALENDARIO else "AR"


def _espalhar(valores: np.ndarray, largura: float = 0.38, nbins: int = 60) -> np.ndarray:
    """Deterministic beeswarm offsets: points in the same value bin are stacked 0, +1, −1, +2, …"""
    v = np.asarray(valores, dtype=float)
    if v.size == 0:
        return v
    lo, hi = float(v.min()), float(v.max())
    span = hi - lo if hi > lo else 1.0
    b = np.clip(np.floor((v - lo) / span * nbins), 0, nbins - 1).astype(int)
    off = np.zeros(v.size)
    contagem: dict[int, int] = {}
    for i in np.lexsort((np.arange(v.size), v)):
        k = contagem.get(b[i], 0)
        contagem[b[i]] = k + 1
        off[i] = ((k + 1) // 2) * (1 if k % 2 else -1)
    m = np.abs(off).max()
    return off / m * largura if m > 0 else off


def _valor_legivel(feature: str, valor: float, lang: str) -> str:
    if feature == "dow":
        return DIAS[lang][int(valor)]
    if feature in ("sin1", "cos1", "sin2", "cos2"):
        return _fmt(valor, 3, lang).replace("-", "−")
    return f"{int(round(valor))}"


# ------------------------------------------------------------------ compute
def carregar_metadata() -> dict:
    return json.loads(comum.CAMINHO_METADATA.read_text(encoding="utf-8"))


def calcular_shap(h: int, meta: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """SHAP values (log-margin) and feature values for every target date of horizon ``h``."""
    info = meta["modelos"][str(h)]
    ds, colunas, _ = comum.construir_para(h)
    if list(colunas) != list(info["features"]):
        raise RuntimeError(f"h={h}: features {colunas} differ from metadata.json {info['features']}")
    for c, lag in comum.lags_das_colunas(colunas).items():
        if lag is None and c not in comum.COLUNAS_CALENDARIO:
            raise RuntimeError(f"h={h}: unlagged feature {c} is not a calendar column")
        if lag is not None and lag < h:
            raise RuntimeError(f"h={h}: feature {c} has lag {lag} < h")
    caminho = comum.caminho_modelo(h)
    sha = comum.sha256_arquivo(caminho)
    if sha != info["arquivo_sha256"]:
        raise RuntimeError(f"{comum.caminho_relativo(caminho)}: sha256 {sha} differs from metadata.json")
    modelo = comum.carregar_modelo(h)
    X = comum.matriz(ds, colunas)
    contrib = modelo.get_booster().predict(xgb.DMatrix(X), pred_contribs=True)
    if contrib.shape != (X.shape[0], len(colunas) + 1):
        raise RuntimeError(f"h={h}: unexpected pred_contribs shape {contrib.shape}")
    margem = modelo.predict(X, output_margin=True).astype(np.float64)
    previsao = modelo.predict(X).astype(np.float64)
    soma = contrib.astype(np.float64).sum(axis=1)
    delta = float(np.max(np.abs(soma - margem)))
    if delta >= TOL_ADITIVIDADE:
        raise RuntimeError(f"h={h}: base + sum(SHAP) differs from the margin by {delta:.2e}")
    base = contrib[:, -1].astype(np.float64)
    if np.ptp(base) > 0:
        raise RuntimeError(f"h={h}: the bias column of pred_contribs is not constant")
    indice = pd.DatetimeIndex(ds.X.index, name="data_alvo")
    shap = pd.DataFrame(contrib[:, :-1].astype(np.float64), index=indice, columns=list(colunas))
    shap["base"] = base
    shap["margem"] = margem
    shap["previsao"] = previsao
    feats = pd.DataFrame(X, index=indice, columns=list(colunas))
    feats["alvo_observado"] = ds.y.reindex(ds.X.index).to_numpy(dtype=np.float64)
    if feats["alvo_observado"].isna().any():
        raise RuntimeError(f"h={h}: target missing on some feature dates")
    return shap, feats


def resumo_importancia(shaps: dict[int, pd.DataFrame], meta: dict) -> pd.DataFrame:
    linhas = []
    for h, df in shaps.items():
        feats = meta["modelos"][str(h)]["features"]
        media = df[feats].abs().mean(axis=0).sort_values(ascending=False, kind="mergesort")
        lags = comum.lags_das_colunas(feats)
        for pos, (f, v) in enumerate(media.items(), start=1):
            linhas.append(
                {
                    "h": h,
                    "posicao": pos,
                    "feature": f,
                    "bloco": _bloco(f),
                    "lag": lags[f] if lags[f] is not None else "",
                    "media_abs_shap": float(v),
                    "n_datas": int(len(df)),
                }
            )
    return pd.DataFrame(linhas)


def escolher_datas(shap_h1: pd.DataFrame, feats_h1: pd.DataFrame) -> dict:
    """Rule: the 2024 Saturday with the highest h=1 forecast (ties: earliest) and the Wednesday 3 days before."""
    idx = shap_h1.index
    sab = shap_h1[(idx.year == 2024) & (idx.dayofweek == 5)]
    if sab.empty:
        raise RuntimeError("no Saturday of 2024 among the h=1 target dates")
    ordem = sab.assign(_d=sab.index).sort_values(["previsao", "_d"], ascending=[False, True], kind="mergesort")
    sabado = ordem.index[0]
    quarta = sabado - pd.Timedelta(days=3)
    if quarta not in idx or quarta.dayofweek != 2:
        raise RuntimeError(f"Wednesday {quarta.date()} of the selected week is not an h=1 target date")
    return {
        "regra": (
            "sabado = the Saturday of 2024 (target date) with the highest h=1 forecast, ties broken by the earliest "
            "date; quarta = sabado - 3 days (the Wednesday of the same Monday-Sunday week)"
        ),
        "sabado": {
            "data": sabado.date().isoformat(),
            "previsao": float(shap_h1.at[sabado, "previsao"]),
            "feriado": int(feats_h1.at[sabado, "feriado"]),
        },
        "quarta": {
            "data": quarta.date().isoformat(),
            "previsao": float(shap_h1.at[quarta, "previsao"]),
            "feriado": int(feats_h1.at[quarta, "feriado"]),
        },
    }


# ------------------------------------------------------------------ figures
def fig_importancia(resumo: pd.DataFrame, h: int, lang: str, versao: str, destino: Path) -> None:
    r = resumo[resumo.h == h].sort_values("posicao", ascending=False)
    fig, ax = _eixo((7.6, 4.6))
    ax.grid(axis="x", color=COR_GRADE, linewidth=0.8)
    cores = [COR_AR if b == "AR" else COR_CAL for b in r.bloco]
    y = np.arange(len(r))
    ax.barh(y, r.media_abs_shap, color=cores, height=0.7)
    for yy, v in zip(y, r.media_abs_shap, strict=True):
        ax.text(v, yy, " " + _fmt(v, 3, lang), va="center", ha="left", fontsize=8, color="#0b0b0b")
    ax.set_yticks(y, list(r.feature))
    ax.set_xlim(0, float(r.media_abs_shap.max()) * 1.18)
    ax.xaxis.set_major_formatter(_formatador(lang))
    ax.set_xlabel(T[lang]["imp_x"].format(n=int(r.n_datas.iloc[0])))
    ax.set_title(T[lang]["imp_titulo"].format(h=h))
    ax.legend(
        handles=[Patch(color=COR_AR, label=T[lang]["bloco_AR"]), Patch(color=COR_CAL, label=T[lang]["bloco_CAL"])],
        loc="lower right",
    )
    _rodape(fig, lang, versao)
    _salvar(fig, destino)


def fig_beeswarm(shap: pd.DataFrame, feats: pd.DataFrame, ordem: list[str], lang: str, versao: str, destino: Path):
    fig, ax = _eixo((7.6, 5.6))
    ax.grid(axis="x", color=COR_GRADE, linewidth=0.8)
    ax.axvline(0, color="#898781", lw=1)
    n = len(ordem)
    sc = None
    for i, f in enumerate(ordem):
        yy = n - 1 - i
        s = shap[f].to_numpy()
        v = feats[f].to_numpy(dtype=float)
        lo, hi = np.percentile(v, [5, 95])
        if hi <= lo:  # binary or nearly constant feature (feriado): fall back to min-max
            lo, hi = float(v.min()), float(v.max())
        cor = np.clip((v - lo) / (hi - lo), 0, 1) if hi > lo else np.full(v.size, 0.5)
        sc = ax.scatter(
            s, yy + _espalhar(s), c=cor, cmap=CMAP_VALOR, vmin=0, vmax=1, s=3, linewidths=0, rasterized=True
        )
    ax.set_yticks(np.arange(n), list(reversed(ordem)))
    ax.set_ylim(-0.6, n - 0.4)
    ax.xaxis.set_major_formatter(_formatador(lang))
    ax.set_xlabel(T[lang]["bee_x"])
    ax.set_title(T[lang]["bee_titulo"])
    cb = fig.colorbar(sc, ax=ax, pad=0.01, aspect=40, ticks=[0, 1])
    cb.ax.set_yticklabels(["low" if lang == "en" else "baixo", "high" if lang == "en" else "alto"])
    cb.set_label(T[lang]["bee_cor"], fontsize=8)
    cb.outline.set_visible(False)
    _rodape(fig, lang, versao)
    _salvar(fig, destino)


def fig_dependencia_dow(shap: pd.DataFrame, feats: pd.DataFrame, lang: str, versao: str, destino: Path) -> None:
    fig, ax = _eixo()
    ax.grid(axis="y", color=COR_GRADE, linewidth=0.8)
    ax.axhline(0, color="#898781", lw=1)
    dow = feats["dow"].to_numpy(dtype=int)
    s = shap["dow"].to_numpy()
    for d in range(7):
        m = dow == d
        ax.scatter(d + _espalhar(s[m], largura=0.32, nbins=40), s[m], s=4, color=COR_PONTO, alpha=0.45, linewidths=0)
        med = float(np.median(s[m]))
        ax.plot([d - 0.38, d + 0.38], [med, med], color=COR_POS, lw=2, label=T[lang]["mediana"] if d == 0 else None)
    ax.set_xticks(range(7), DIAS[lang])
    ax.yaxis.set_major_formatter(_formatador(lang))
    ax.set_xlabel(T[lang]["dow_x"])
    ax.set_ylabel(T[lang]["dow_y"])
    ax.set_title(T[lang]["dow_titulo"])
    ax.legend(loc="upper left")
    _rodape(fig, lang, versao)
    _salvar(fig, destino)


def fig_dependencia_lag(shap: pd.DataFrame, feats: pd.DataFrame, f: str, lang: str, versao: str, destino: Path) -> None:
    L = comum.lags_das_colunas([f])[f]
    fig, ax = _eixo()
    ax.grid(color=COR_GRADE, linewidth=0.8)
    ax.axhline(0, color="#898781", lw=1)
    sab = feats["dow"].to_numpy(dtype=int) == 5
    x = feats[f].to_numpy(dtype=float)
    s = shap[f].to_numpy()
    ax.scatter(x[~sab], s[~sab], s=5, color=COR_NEG, alpha=0.4, linewidths=0, label=T[lang]["lag_outros"])
    ax.scatter(x[sab], s[sab], s=7, color=COR_POS, alpha=0.7, linewidths=0, label=T[lang]["lag_sab"])
    ax.yaxis.set_major_formatter(_formatador(lang))
    ax.set_xlabel(T[lang]["lag_x"].format(f=f, L=L))
    ax.set_ylabel(T[lang]["lag_y"].format(f=f))
    ax.set_title(T[lang]["lag_titulo"].format(f=f))
    ax.legend(loc="upper left", markerscale=2)
    _rodape(fig, lang, versao)
    _salvar(fig, destino)


def fig_waterfall(
    shap: pd.DataFrame, feats: pd.DataFrame, data: str, chave_dia: str, lang: str, versao: str, destino: Path
) -> None:
    d = pd.Timestamp(data)
    colunas = [c for c in shap.columns if c not in ("base", "margem", "previsao")]
    phi = shap.loc[d, colunas].astype(float)
    ordem = list(phi.abs().sort_values(ascending=False, kind="mergesort").index)
    base = float(shap.at[d, "base"])
    margem = float(shap.at[d, "margem"])
    prev = float(shap.at[d, "previsao"])
    fig, ax = _eixo((7.6, 5.4))
    ax.grid(axis="x", color=COR_GRADE, linewidth=0.8)
    n = len(ordem)
    acum = base
    for i, f in enumerate(ordem):
        yy = n - 1 - i
        v = float(phi[f])
        ax.barh(yy, v, left=acum, color=COR_POS if v >= 0 else COR_NEG, height=0.7)
        txt = f" {_fmt_sinal(v, 3, lang)} (×{_fmt(np.exp(v), 3, lang)}) "
        x_txt = max(acum, acum + v)
        ax.text(
            x_txt,
            yy,
            txt,
            va="center",
            ha="left",
            fontsize=7.5,
            color="#0b0b0b",
            zorder=4,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.1, "alpha": 0.8},
        )
        acum += v
    ax.axvline(base, color="#898781", lw=1, ls=":")
    ax.axvline(margem, color="#0b0b0b", lw=1, ls="--", zorder=1)
    rotulos = [f"{f} = {_valor_legivel(f, float(feats.at[d, f]), lang)}" for f in ordem]
    ax.set_yticks(np.arange(n), list(reversed(rotulos)))
    ax.set_ylim(-1.6, n - 0.4)
    ax.text(
        base,
        -1.1,
        T[lang]["wf_base"].format(b=_fmt(base, 3, lang), eb=_fmt(np.exp(base), 1, lang)),
        ha="right" if margem >= base else "left",
        va="center",
        fontsize=8,
        color="#52514e",
    )
    ax.text(
        margem,
        -1.1,
        T[lang]["wf_final"].format(m=_fmt(margem, 3, lang), p=_fmt(prev, 1, lang)),
        ha="left" if margem >= base else "right",
        va="center",
        fontsize=8,
        color="#0b0b0b",
    )
    lo = min(base, margem, *(base + np.cumsum([phi[f] for f in ordem])))
    hi = max(base, margem, *(base + np.cumsum([phi[f] for f in ordem])))
    pad = (hi - lo) * 0.35
    ax.set_xlim(lo - pad, hi + pad)
    ax.xaxis.set_major_formatter(_formatador(lang))
    ax.set_xlabel(T[lang]["wf_x"])
    ax.set_title(T[lang]["wf_titulo"].format(dia=T[lang][chave_dia], data=data, prev=_fmt(prev, 1, lang)))
    _rodape(fig, lang, versao, extra=T[lang]["wf_regra"])
    _salvar(fig, destino)


# ------------------------------------------------------------------ main
def _escrever_parquet(df: pd.DataFrame, destino: Path) -> None:
    df.to_parquet(destino, engine="pyarrow", index=True, compression="snappy")


def gerar(saida: Path = PASTA_SHAP) -> dict:
    meta = carregar_metadata()
    versao = meta["versao"]
    saida.mkdir(parents=True, exist_ok=True)
    gerado_em = _agora()
    ambiente = _ambiente()
    entrada_alvo = {
        "caminho": meta["entradas"]["sih"]["arquivo"],
        "sha256": comum.sha256_arquivo(comum.RAIZ / meta["entradas"]["sih"]["arquivo"]),
    }
    if entrada_alvo["sha256"] != meta["entradas"]["sih"]["sha256"]:
        raise RuntimeError(f"{entrada_alvo['caminho']}: sha256 differs from models_demo/metadata.json")

    shaps: dict[int, pd.DataFrame] = {}
    feats: dict[int, pd.DataFrame] = {}
    arquivos: dict[str, str] = {}
    for h in comum.HORIZONTES:
        shaps[h], feats[h] = calcular_shap(h, meta)
        for nome, df in ((f"shap_valores_h{h}.parquet", shaps[h]), (f"features_h{h}.parquet", feats[h])):
            _escrever_parquet(df, saida / nome)
            arquivos[nome] = comum.sha256_arquivo(saida / nome)
        print(f"h={h}: {len(shaps[h])} target dates, SHAP additivity checked")

    resumo = resumo_importancia(shaps, meta)
    resumo.to_csv(saida / "resumo_importancia.csv", index=False, lineterminator="\n", float_format="%.10g")
    arquivos["resumo_importancia.csv"] = comum.sha256_arquivo(saida / "resumo_importancia.csv")

    selecao = escolher_datas(shaps[H_DETALHE], feats[H_DETALHE])
    ordem_h1 = list(resumo[resumo.h == H_DETALHE].sort_values("posicao").feature)
    lag_top = next(f for f in ordem_h1 if _bloco(f) == "AR")

    def origem(h: int) -> list[dict]:
        return [
            {"caminho": comum.caminho_relativo(saida / n), "sha256": arquivos[n]}
            for n in (f"shap_valores_h{h}.parquet", f"features_h{h}.parquet")
        ]

    def modelo(h: int) -> dict:
        info = meta["modelos"][str(h)]
        return {"arquivo": info["arquivo"], "sha256": info["arquivo_sha256"], "versao": versao, "horizonte": h}

    _estilo()
    figuras: list[tuple[str, int, str, dict, object]] = []
    for h in comum.HORIZONTES:
        figuras.append(
            (
                f"fig_importancia_h{h}",
                h,
                f"Global importance (mean |SHAP|, log-margin) of the demo XGBoost AR_CAL model, h = {h}.",
                {"estatistica": "mean of |SHAP| over all target dates", "n_datas": len(shaps[h])},
                lambda lang, p, h=h: fig_importancia(resumo, h, lang, versao, p),
            )
        )
    figuras += [
        (
            "fig_beeswarm_h1",
            1,
            "SHAP value of each feature on each h = 1 target date; colour = feature value (5th-95th percentile).",
            {"ordem_features": ordem_h1, "cor": "feature value scaled to its 5th-95th percentile", "jitter": "binned"},
            lambda lang, p: fig_beeswarm(shaps[1], feats[1], ordem_h1, lang, versao, p),
        ),
        (
            "fig_dependencia_dow_h1",
            1,
            "SHAP of dow (day of the week of the target date, 0 = Monday) against dow, h = 1, with the median per day.",
            {"feature": "dow", "codificacao": "0 = Monday ... 6 = Sunday (pandas dayofweek)"},
            lambda lang, p: fig_dependencia_dow(shaps[1], feats[1], lang, versao, p),
        ),
        (
            "fig_dependencia_lag_h1",
            1,
            f"SHAP of {lag_top} (the AR feature with the highest mean |SHAP| at h = 1) against its value; "
            "orange = target date is a Saturday.",
            {"feature": lag_top, "regra": "AR feature with the highest mean |SHAP| at h = 1 (resumo_importancia.csv)"},
            lambda lang, p: fig_dependencia_lag(shaps[1], feats[1], lag_top, lang, versao, p),
        ),
        (
            "fig_waterfall_sabado_h1",
            1,
            f"Waterfall (log-margin) of the h = 1 forecast for Saturday {selecao['sabado']['data']}.",
            {"data_alvo": selecao["sabado"]["data"], "selecao": selecao},
            lambda lang, p: fig_waterfall(shaps[1], feats[1], selecao["sabado"]["data"], "sabado", lang, versao, p),
        ),
        (
            "fig_waterfall_quarta_h1",
            1,
            f"Waterfall (log-margin) of the h = 1 forecast for Wednesday {selecao['quarta']['data']}.",
            {"data_alvo": selecao["quarta"]["data"], "selecao": selecao},
            lambda lang, p: fig_waterfall(shaps[1], feats[1], selecao["quarta"]["data"], "quarta", lang, versao, p),
        ),
    ]

    lista_figuras = []
    for nome, h, descricao, params, desenhar in figuras:
        for lang in ("en", "pt"):
            png = saida / f"{nome}_{lang}.png"
            desenhar(lang, png)
            prov = {
                "figura": f"{nome}_{lang}",
                "descricao": descricao,
                "script": SCRIPT,
                "comando": COMANDO,
                "metodo": METODO,
                "escala": "log-margin of count:poisson; forecast (admissions/day) = exp(base + sum of SHAP); "
                "a contribution phi multiplies the forecast by exp(phi)",
                "modelo": modelo(h),
                "entradas": [entrada_alvo],
                "artefatos_de_origem": origem(h),
                "conjunto_de_features": comum.FEATURE_SET,
                "parametros": {"horizonte": h, "idioma": lang, **params},
                "png_sha256": comum.sha256_arquivo(png),
                "png_bytes": png.stat().st_size,
                "status": STATUS,
                "gerado_em": gerado_em,
                "ambiente": ambiente,
            }
            _escrever_json(png.with_suffix(".prov.json"), prov)
            lista_figuras.append({"arquivo": png.name, "bytes": png.stat().st_size, "sha256": prov["png_sha256"]})

    manifest = {
        "script": SCRIPT,
        "comando": COMANDO,
        "metodo": METODO,
        "status": STATUS,
        "versao_modelos": versao,
        "modelos": {str(h): modelo(h) for h in comum.HORIZONTES},
        "entradas": [entrada_alvo],
        "tolerancia_aditividade": TOL_ADITIVIDADE,
        "selecao_waterfall": selecao,
        "arquivos": arquivos,
        "figuras": lista_figuras,
        "gerado_em": gerado_em,
        "ambiente": ambiente,
    }
    _escrever_json(saida / "manifest.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", type=Path, default=PASTA_SHAP, help="output folder (default: models_demo/shap)")
    args = ap.parse_args(argv)
    man = gerar(args.saida)
    print(
        f"selected dates: {man['selecao_waterfall']['sabado']['data']} / {man['selecao_waterfall']['quarta']['data']}"
    )
    for f in man["figuras"]:
        print(f"{f['arquivo']}: {f['bytes']} bytes")


if __name__ == "__main__":
    main()

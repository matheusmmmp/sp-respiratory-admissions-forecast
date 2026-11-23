"""Figuras do capítulo de resultados — geradas DIRETAMENTE dos artefatos das runs.

    python -m src.viz.figuras_resultados_v02                 # todas as figuras
    python -m src.viz.figuras_resultados_v02 --figura 4 7    # só algumas
    python -m src.viz.figuras_resultados_v02 --figura 11 12 13 14   # bloco 2026-10-22: AR_CAL comum,
                                                   # folds em AR_CAL, ablação do PM2,5, painel exploratório

Regras (CLAUDE.md §4.4, skill figuras-tabelas): nenhum número vem de digitação; toda figura sai de
`predictions.csv` / `metrics_by_fold.csv` / `model_comparison.csv` de uma run identificada pelo id
completo, ou dos CSV de `compara_fontes_v02.py`. Cada figura gera `.pdf` (vetorial), `.png` (300 dpi) e
`.prov.json` (artefatos de origem com sha256, script, commit, versões, data, frase do que mostra).
Nada é re-treinado. Saída em `reports/figs/resultados_v02/` (pasta nova; não sobrescreve figuras antigas).

Desvio declarado da convenção "um script por figura": as catorze figuras partilham leitores e paleta, então
vivem num módulo só, com uma função por figura e seleção pela linha de comando.

Agregação (a mesma do runner): métricas por (modelo, conjunto, semente, fold); sementes agregadas DENTRO
da fold, depois folds. Nas séries de observado × previsto, XGBoost e LSTM (5 sementes) aparecem pela
MÉDIA das sementes por data — é uma leitura derivada, declarada na legenda; os demais são determinísticos.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
EXP = RAIZ / "reports" / "experiments"
SAIDA = RAIZ / "reports" / "figs" / "resultados_v02"

RUN = "h1_v02_cetesbmin_cetesbmin_classicos_full_20261022-092503"      # sete modelos, base CETESB espelho
RUN_CAMS = "h1_v02_cams_cams_full_20261019-084446"                     # base CAMS (só para a figura 10)
RUN_CETESB_ESP = "h1_v02_cetesbmin_cetesbmin_full_20261019-100229"     # base CETESB espelho, 4 modelos (figura 10)
ALVO = RAIZ / "data" / "processed" / "sih_daily_lookahead.parquet"
CSV_PAREADO = EXP / "COMPARACAO_FONTES_V02_pareado.csv"

# ---------------------------------------------------------------- paleta e estilos
# Cinco modelos treináveis em ordem fixa (Okabe–Ito, validada com o validador da skill dataviz);
# baselines em cinza/preto com traço distinto: são referências, não séries categóricas.
MODELOS = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb", "naive", "seasonal_naive"]
NOME = {"xgboost": "XGBoost", "sarimax": "SARIMAX", "lstm": "LSTM", "ingarch_nb": "INGARCH-NB",
        "gam_nb": "GAM-NB", "naive": "Naïve", "seasonal_naive": "Seasonal Naïve"}
COR = {"xgboost": "#0072B2", "sarimax": "#009E73", "lstm": "#D55E00", "ingarch_nb": "#CC79A7",
       "gam_nb": "#E69F00", "naive": "#000000", "seasonal_naive": "#7F7F7F"}
TRACO = {"xgboost": "-", "sarimax": "-", "lstm": "-", "ingarch_nb": "-", "gam_nb": "-",
         "naive": "--", "seasonal_naive": ":"}
MARCA = {"xgboost": "o", "sarimax": "s", "lstm": "^", "ingarch_nb": "D", "gam_nb": "v",
         "naive": "x", "seasonal_naive": "+"}
ORDEM_CONJUNTOS = ["AR", "AR_CAL", "AR_CAL_PM25MEDIA", "AR_CAL_PM25", "AR_CAL_POLUENTES", "AR_CAL_METEO",
                   "AR_CAL_METEO_PM25MEDIA", "AR_CAL_METEO_PM25", "AR_CAL_METEO_POLUENTES", "COMPLETO"]
# Os conjuntos *PM25MEDIA (bloco customizado só com pm25_media) existem a partir da run
# h1_v02_cetesb_cetesb_classicos (2026-10-22); nas runs anteriores são ignorados por `_presentes`.
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.5, "lines.linewidth": 1.1,
    "pdf.fonttype": 42, "savefig.bbox": "tight",
})


def _mes_pt(x, _pos=None):
    d = mdates.num2date(x)
    return f"{MESES[d.month - 1]}/{d.year}"


# ----------------------------------------------------------------------- dados
def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "indisponível"


class Dados:
    """Leitura única dos artefatos; registra tudo que foi lido para a proveniência."""

    def __init__(self):
        self.lidos: dict[str, str] = {}
        r = EXP / RUN
        self.pred = self._csv(r / "predictions.csv", parse_dates=["target_date", "forecast_origin"])
        self.mbf = self._csv(r / "metrics_by_fold.csv")
        self.mc = self._csv(r / "model_comparison.csv")
        self.folds = self._csv(r / "folds.csv")
        self.manifesto = json.loads(self._reg(r / "manifest.json").read_text(encoding="utf-8"))
        self.alvo = pd.read_parquet(self._reg(ALVO))
        self.alvo.index = pd.to_datetime(self.alvo.index)
        self._pareado = None

    def _reg(self, p: Path) -> Path:
        self.lidos[p.relative_to(RAIZ).as_posix()] = _sha(p)
        return p

    def _csv(self, p: Path, **kw) -> pd.DataFrame:
        return pd.read_csv(self._reg(p), **kw)

    @property
    def pareado(self) -> pd.DataFrame:
        if self._pareado is None:
            self._pareado = self._csv(CSV_PAREADO)
            for rid in (RUN_CAMS, RUN_CETESB_ESP):
                self._reg(EXP / rid / "metrics_by_fold.csv")
        return self._pareado

    def melhor_conjunto(self) -> dict[str, str]:
        """Conjunto de menor MAE médio por modelo (mesmo critério da tabela do capítulo)."""
        mc = self.mc.sort_values("MAE_medio")
        return {m: g.iloc[0]["feature_set"] for m, g in mc.groupby("model")}

    def serie_media_sementes(self, modelo: str, conjunto: str) -> pd.DataFrame:
        """Previsões por data: média das sementes (XGBoost/LSTM) ou a única execução."""
        q = self.pred[(self.pred.model == modelo) & (self.pred.feature_set == conjunto)]
        g = q.groupby(["fold", "target_date"]).agg(y_true=("y_true", "first"), y_pred=("y_pred", "mean"),
                                                   y_min=("y_pred", "min"), y_max=("y_pred", "max"),
                                                   n_sementes=("seed", "nunique")).reset_index()
        return g.sort_values("target_date")


# ------------------------------------------------------------------ utilidades
def _salvar(fig, nome: str, dados: Dados, frase: str, extra: dict | None = None) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA / f"{nome}.pdf")
    fig.savefig(SAIDA / f"{nome}.png", dpi=300)
    plt.close(fig)
    prov = {
        "figura": nome, "rotulo_latex": "fig:" + nome.replace("_", "-"),
        "descricao": frase,
        "artefatos_de_origem": [{"caminho": k, "sha256": v} for k, v in dados.lidos.items()],
        "run_principal": RUN,
        "script": "src/viz/figuras_resultados_v02.py",
        "commit": _git(), "gerado_em": _dt.datetime.now().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "pacotes": {"matplotlib": matplotlib.__version__, "pandas": pd.__version__, "numpy": np.__version__},
        **(extra or {}),
    }
    (SAIDA / f"{nome}.prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {nome}.pdf / .png / .prov.json")


def _rotulo_conj(c: str) -> str:
    return c.replace("_", "+").replace("PM25MEDIA", "PM25méd")


def _presentes(d: Dados, conjuntos) -> list[str]:
    """Só os conjuntos que a run de fato executou (ordem fixa de ORDEM_CONJUNTOS)."""
    tem = set(d.mc.feature_set)
    return [c for c in conjuntos if c in tem]


# ------------------------------------------------------------------- figuras
def fig1_serie_alvo(d: Dados) -> None:
    s = d.alvo["internacoes"]
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.plot(s.index, s.values, color="#222222", lw=0.6)
    for _, f in d.folds.iterrows():
        ax.axvspan(pd.Timestamp(f.teste_inicio), pd.Timestamp(f.teste_fim), color="#BBBBBB", alpha=0.45, lw=0)
        ax.text(pd.Timestamp(f.teste_inicio) + pd.Timedelta(days=90), s.max() * 0.98, f"teste {int(f.fold)}",
                ha="center", va="top", fontsize=7.5)
    ax.set_ylim(0, s.max() * 1.05)
    ax.set_ylabel("Internações por dia (J00–J99)")
    ax.set_xlabel("Data")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_mes_pt))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    _salvar(fig, "fig_res_serie_alvo", d,
            "Série diária de internações respiratórias no município de São Paulo, 2019-01-01 a 2024-12-31, com as quatro "
            "janelas de teste de 180 dias sombreadas (2023-01-12 a 2024-12-31).")


def fig2_metricas_agregadas(d: Dados) -> None:
    melhor = d.melhor_conjunto()
    mc = d.mc.copy()
    linhas = [mc[(mc.model == m) & (mc.feature_set == melhor[m])].iloc[0] for m in MODELOS]
    tab = pd.DataFrame(linhas)
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.9))
    x = np.arange(len(MODELOS))
    for ax, (col, sd, rot, melhor_e) in zip(axes, [("MAE_medio", "MAE_std_fold", "MAE (internações/dia)", "menor é melhor"),
                                                 ("RMSE_medio", "RMSE_std_fold", "RMSE (internações/dia)", "menor é melhor"),
                                                 ("MASE_medio", None, "MASE (adimensional)", "menor é melhor"),
                                                 ("R2_medio", None, "R² (adimensional)", "maior é melhor")]):
        vals = tab[col].values
        ax.bar(x, vals, color=[COR[m] for m in MODELOS], width=0.7, edgecolor="white", linewidth=0.5)
        if sd:
            ax.errorbar(x, vals, yerr=tab[sd].values, fmt="none", ecolor="#333333", elinewidth=0.8, capsize=2)
        if col == "MASE_medio":
            ax.axhline(1.0, color="#333333", lw=0.7, ls="--")
        topo = vals + (tab[sd].values if sd else 0.0)
        for xi, v, t in zip(x, vals, topo):
            ax.text(xi, max(t, 0) + (abs(vals).max() * 0.02), f"{v:.2f}".replace(".", ","), ha="center",
                    va="bottom", fontsize=6, rotation=90)
        ax.margins(y=0.18)
        ax.set_xticks(x)
        ax.set_xticklabels([NOME[m] for m in MODELOS], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel(rot)
        ax.set_title(melhor_e, fontsize=7.5, color="#444444")
        ax.grid(axis="x", visible=False)
        if col != "R2_medio":
            ax.set_ylim(0, None)
    fig.tight_layout(w_pad=1.0)
    _salvar(fig, "fig_res_metricas_por_modelo", d,
            "MAE, RMSE, MASE e R² médios por modelo no melhor conjunto de covariáveis de cada um; barras de erro = "
            "desvio-padrão entre as quatro folds (MAE e RMSE).",
            {"conjunto_por_modelo": melhor})


def fig3_por_fold(d: Dados) -> None:
    melhor = d.melhor_conjunto()
    pf = d.mbf.groupby(["model", "feature_set", "fold"]).agg(MAE=("MAE", "mean"), MASE=("MASE", "mean")).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharex=True)
    for ax, col in zip(axes, ["MAE", "MASE"]):
        for m in MODELOS:
            q = pf[(pf.model == m) & (pf.feature_set == melhor[m])].sort_values("fold")
            ax.plot(q.fold, q[col], marker=MARCA[m], ls=TRACO[m], color=COR[m], ms=5, label=NOME[m], lw=1.0)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xlabel("Fold (teste de 180 dias)")
        ax.set_ylabel("MAE (internações/dia)" if col == "MAE" else "MASE (adimensional)")
        if col == "MASE":
            ax.axhline(1.0, color="#333333", lw=0.7, ls="--")
            ax.text(1.02, 1.0, "Naïve = 1", fontsize=7, va="bottom", ha="left")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=7, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02), fontsize=7)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _salvar(fig, "fig_res_por_fold", d,
            "MAE e MASE em cada fold temporal, por modelo (melhor conjunto de cada um; média das sementes dentro da fold). "
            "Fold 1 = jan–jul/2023; 2 = jul/2023–jan/2024; 3 = jan–jul/2024; 4 = jul–dez/2024.")


def fig4_obs_vs_prev_tempo(d: Dados) -> None:
    principais = ["xgboost", "sarimax", "lstm"]
    melhor = d.melhor_conjunto()
    series = {m: d.serie_media_sementes(m, melhor[m]) for m in principais + ["naive"]}
    obs = series["naive"][["fold", "target_date", "y_true"]]
    fig, axes = plt.subplots(4, 1, figsize=(7.2, 8.0))
    for k, ax in enumerate(axes, start=1):
        o = obs[obs.fold == k]
        ax.plot(o.target_date, o.y_true, color="#222222", lw=1.0, label="Observado")
        nv = series["naive"][series["naive"].fold == k]
        ax.plot(nv.target_date, nv.y_pred, color=COR["naive"], lw=0.8, ls="--", label="Naïve", alpha=0.8)
        for m in principais:
            q = series[m][series[m].fold == k]
            ax.plot(q.target_date, q.y_pred, color=COR[m], lw=1.0, label=f"{NOME[m]} ({_rotulo_conj(melhor[m])})")
        ax.set_ylim(0, 290)
        ax.set_ylabel("Internações/dia")
        ax.text(0.01, 0.95, f"Fold {k}", transform=ax.transAxes, va="top", fontsize=8, fontweight="bold")
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_mes_pt))
    axes[0].legend(ncol=5, frameon=False, loc="lower left", fontsize=7)
    axes[-1].set_xlabel("Data-alvo")
    fig.tight_layout(h_pad=0.6)
    _salvar(fig, "fig_res_observado_previsto_tempo", d,
            "Internações observadas e previstas a um dia (h = 1) nas quatro janelas de teste: Naïve e os três modelos de "
            "menor erro, cada um no seu melhor conjunto; XGBoost e LSTM pela média das cinco sementes por data.",
            {"conjunto_por_modelo": {m: melhor[m] for m in principais}, "xgboost_lstm": "média das 5 sementes por data"})


def fig5_dispersao(d: Dados) -> None:
    melhor = d.melhor_conjunto()
    fig, axes = plt.subplots(2, 4, figsize=(7.4, 4.2), sharex=True, sharey=True)
    axes = axes.ravel()
    for ax, m in zip(axes, MODELOS):
        s = d.serie_media_sementes(m, melhor[m])
        ax.plot([40, 280], [40, 280], color="#999999", lw=0.8, ls="--")
        ax.scatter(s.y_true, s.y_pred, s=5, color=COR[m], alpha=0.55, linewidths=0)
        mae = float(np.abs(s.y_true - s.y_pred).mean())
        ax.text(0.03, 0.95, f"{NOME[m]}\n{_rotulo_conj(melhor[m])}\nMAE {mae:.1f}".replace(".", ","),
                transform=ax.transAxes, va="top", fontsize=7)
        ax.set_xlim(40, 280); ax.set_ylim(40, 280)
        ax.set_aspect("equal")
    axes[-1].axis("off")
    for ax in (axes[0], axes[4]):
        ax.set_ylabel("Previsto (internações/dia)")
    fig.supxlabel("Observado (internações/dia)", fontsize=9)
    fig.tight_layout(h_pad=0.5, w_pad=0.5)
    _salvar(fig, "fig_res_dispersao_observado_previsto", d,
            "Previsto contra observado por data-alvo nas 720 datas de teste, um painel por modelo (melhor conjunto), com a "
            "linha de identidade y = ŷ; XGBoost e LSTM pela média das sementes por data. O MAE anotado é o das médias por "
            "data e por isso difere ligeiramente do MAE do protocolo, que é calculado por semente.",
            {"conjunto_por_modelo": melhor})


def fig6_erro_tempo(d: Dados) -> None:
    principais = ["xgboost", "sarimax", "lstm"]
    melhor = d.melhor_conjunto()
    picos = d.pred[d.pred.model == "naive"][["target_date", "y_true"]].drop_duplicates()
    picos = picos[picos.y_true >= 250]
    fig, axes = plt.subplots(len(principais), 1, figsize=(7.2, 6.0), sharex=True)
    for ax, m in zip(axes, principais):
        s = d.serie_media_sementes(m, melhor[m])
        erro = s.y_true - s.y_pred
        ax.plot(s.target_date, erro, color=COR[m], lw=0.7)
        ax.axhline(0, color="#333333", lw=0.7)
        for _, f in d.folds.iterrows():
            if int(f.fold) > 1:
                ax.axvline(pd.Timestamp(f.teste_inicio), color="#BBBBBB", lw=0.7, ls=":")
        xs = [p.target_date for _, p in picos.iterrows() if (s.target_date == p.target_date).any()]
        ys = [float(erro[s.target_date == x].iloc[0]) for x in xs]
        ax.scatter(xs, ys, s=22, facecolors="none", edgecolors="#222222", linewidths=0.8, zorder=5,
                   label="dias com ≥ 250 internações observadas")
        ax.set_ylabel("Observado − previsto")
        ax.text(0.01, 0.95, f"{NOME[m]} ({_rotulo_conj(melhor[m])})", transform=ax.transAxes, va="top", fontsize=8)
        ax.set_ylim(-110, 130)
    axes[0].legend(frameon=False, fontsize=7, loc="upper right")
    axes[-1].set_xlabel("Data-alvo")
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[-1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(_mes_pt))
    plt.setp(axes[-1].get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout(h_pad=0.5)
    _salvar(fig, "fig_res_erro_tempo", d,
            "Erro fora da amostra (observado − previsto) ao longo das quatro janelas de teste para os três modelos de menor "
            "erro; linhas pontilhadas separam as folds e os círculos marcam os dias com 250 ou mais internações observadas "
            "(20/05/2023, 03/04/2024, 06/04/2024, 02/05/2024 e 08/08/2024).",
            {"picos_anotados": [str(x.date()) for x in picos.target_date], "xgboost_lstm": "média das 5 sementes por data"})


def fig7_erro_contexto(d: Dados) -> None:
    principais = ["xgboost", "sarimax", "lstm", "naive"]
    melhor = d.melhor_conjunto()
    q = d.pred[[(m, c) in {(k, melhor[k]) for k in principais} for m, c in zip(d.pred.model, d.pred.feature_set)]].copy()
    q["dow"] = q.target_date.dt.dayofweek
    q["mes"] = q.target_date.dt.month
    # MAE por semente e grupo, depois média das sementes (mesma lógica do protocolo)
    def mae_grupo(chave):
        g = q.groupby(["model", "seed", chave]).abs_error.mean().reset_index()
        return g.groupby(["model", chave]).abs_error.mean().unstack(0)
    n_dow = q[q.model == "naive"].groupby("dow").size()
    n_mes = q[q.model == "naive"].groupby("mes").size()
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.0), gridspec_kw={"width_ratios": [7, 12]})
    for ax, chave, rot, n in [(axes[0], "dow", DOW, n_dow), (axes[1], "mes", MESES, n_mes)]:
        t = mae_grupo(chave)
        for m in principais:
            ax.plot(t.index, t[m], marker=MARCA[m], ls=TRACO[m], color=COR[m], ms=4, lw=1.0, label=NOME[m])
        ax.set_xticks(t.index)
        # dayofweek é 0..6 (segunda = 0); mês é 1..12 — o deslocamento só vale para o mês.
        desloc = 1 if chave == "mes" else 0
        ax.set_xticklabels([f"{rot[i - desloc]}\nn={n[i]}" for i in t.index], fontsize=6)
        ax.set_ylim(0, None)
        ax.set_ylabel("MAE (internações/dia)")
    axes[0].set_xlabel("Dia da semana da data-alvo")
    axes[1].set_xlabel("Mês da data-alvo (folds 1–4 reunidas)")
    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=4, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02), fontsize=7)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _salvar(fig, "fig_res_erro_por_contexto", d,
            "MAE fora da amostra por dia da semana e por mês da data-alvo, para Naïve e os três modelos de menor erro; n = "
            "número de datas de teste em cada grupo (720 no total; cada mês reúne datas de 2023 e 2024).",
            {"conjunto_por_modelo": {m: melhor[m] for m in principais}})


def fig8_ablacao(d: Dados) -> None:
    modelos = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb"]
    conjuntos = _presentes(d, [c for c in ORDEM_CONJUNTOS if c not in ("AR", "AR_CAL")])
    pf = d.mbf.groupby(["model", "feature_set", "fold"]).MAE.mean().reset_index()
    ref = pf[pf.feature_set == "AR_CAL"].set_index(["model", "fold"]).MAE
    fig, axes = plt.subplots(1, len(modelos), figsize=(7.4, 3.2 + 0.25 * max(0, len(conjuntos) - 6)), sharey=True)
    for ax, m in zip(axes, modelos):
        for j, c in enumerate(conjuntos):
            q = pf[(pf.model == m) & (pf.feature_set == c)].set_index("fold").MAE
            delta = (q - ref.loc[m]).reindex([1, 2, 3, 4])
            ax.scatter([j] * 4, delta.values, s=14, color=COR[m], alpha=0.6, linewidths=0)
            ax.plot([j - 0.25, j + 0.25], [delta.mean()] * 2, color=COR[m], lw=1.6)
        ax.axhline(0, color="#333333", lw=0.7)
        ax.set_xticks(range(len(conjuntos)))
        ax.set_xticklabels([_rotulo_conj(c).replace("AR+CAL+", "+") for c in conjuntos], rotation=70, ha="right", fontsize=6.5)
        ax.set_title(NOME[m], fontsize=8)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("ΔMAE em relação a AR+CAL\n(internações/dia)")
    fig.tight_layout(w_pad=0.4)
    _salvar(fig, "fig_res_ablacao_blocos", d,
            "Ablação por blocos de covariáveis: diferença de MAE de cada conjunto em relação a AR+CAL, pareada por fold "
            "(pontos = folds, média das sementes; traço = média das folds); valores negativos indicam que o bloco "
            "acrescentado reduziu o erro. '+PM25' isola o PM2,5 (H2).")


def fig9_sementes(d: Dados) -> None:
    conjuntos = ["AR_CAL", "AR_CAL_PM25"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, m in zip(axes, ["xgboost", "lstm"]):
        for j, c in enumerate(conjuntos):
            q = d.mbf[(d.mbf.model == m) & (d.mbf.feature_set == c)]
            for f in (1, 2, 3, 4):
                v = q[q.fold == f].MAE.values
                x = f + (j - 0.5) * 0.3
                ax.scatter([x] * len(v), v, s=16, color=COR[m], alpha=0.35 if j == 0 else 0.9,
                           marker="o" if j == 0 else "^", linewidths=0,
                           label=_rotulo_conj(c) if f == 1 else None)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xlabel("Fold")
        ax.set_title(f"{NOME[m]} — 5 sementes (42–46)", fontsize=8)
        ax.legend(frameon=False, fontsize=7, loc="upper right")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("MAE (internações/dia)")
    fig.tight_layout()
    _salvar(fig, "fig_res_sementes", d,
            "MAE de cada uma das cinco sementes, por fold, para XGBoost e LSTM nos conjuntos AR+CAL e AR+CAL+PM25: a "
            "dispersão entre sementes é mostrada como valores observados, não como intervalo de confiança.")


def fig15_sementes_todos(d: Dados) -> None:
    """Sete modelos × quatro folds em AR_CAL: um painel por fold, um ponto por semente (XGBoost e LSTM)
    e um marcador único para os determinísticos; traço largo = média das sementes. Mostra, na mesma
    escala, a variação entre folds (de painel a painel) e a entre sementes (dentro da coluna)."""
    conjunto = "AR_CAL"
    q = d.mbf[(d.mbf.feature_set == conjunto) | (d.mbf.feature_set == "baseline")]
    fig, axes = plt.subplots(1, 4, figsize=(7.4, 3.2), sharey=True)
    rot_fold = {1: "Fold 1\njan–jul/23", 2: "Fold 2\njul/23–jan/24", 3: "Fold 3\njan–jul/24", 4: "Fold 4\njul–dez/24"}
    for ax, f in zip(axes, (1, 2, 3, 4)):
        for j, m in enumerate(MODELOS):
            v = q[(q.model == m) & (q.fold == f)].MAE.values
            if len(v) == 0:
                continue
            if len(v) > 1:  # estocástico: um ponto por semente + média
                ax.scatter([j] * len(v), v, s=12, color=COR[m], alpha=0.45, linewidths=0, zorder=2)
                ax.plot([j - 0.3, j + 0.3], [v.mean()] * 2, color=COR[m], lw=1.8, zorder=3,
                        label=NOME[m] if f == 1 else None)
            else:          # determinístico: marcador único
                ax.scatter([j], v, s=28, color=COR[m], marker=MARCA[m], linewidths=1.2, zorder=3,
                           facecolors="none" if MARCA[m] not in ("x", "+") else COR[m],
                           label=NOME[m] if f == 1 else None)
        ax.set_xticks(range(len(MODELOS)))
        ax.set_xticklabels([NOME[m].replace("Seasonal ", "S. ").replace("-NB", "\n-NB") for m in MODELOS],
                           fontsize=6, rotation=90)
        ax.set_title(rot_fold[f], fontsize=8)
        ax.grid(axis="x", visible=False)
        ax.set_xlim(-0.7, len(MODELOS) - 0.3)
    axes[0].set_ylabel("MAE (internações/dia)")
    fig.tight_layout()
    _salvar(fig, "fig_res_sementes_todos", d,
            "MAE por fold dos sete modelos no conjunto AR_CAL: XGBoost e LSTM com um ponto por semente (42–46) e "
            "traço na média das sementes; demais modelos determinísticos com marcador único. A variação entre folds "
            "(de painel a painel) e a entre sementes (dentro de cada coluna) ficam na mesma escala.",
            {"conjunto": conjunto, "sementes": "pontos individuais; traço = média"})


def fig10_cams_cetesb(d: Dados) -> None:
    pr = d.pareado[d.pareado.base == "CETESB_espelho"]
    conjuntos = [c for c in ORDEM_CONJUNTOS if c not in ("AR", "AR_CAL")]
    pf = pr.groupby(["modelo", "conjunto", "fold"]).delta_MAE.mean().reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2), sharey=True)
    for ax, m in zip(axes, ["xgboost", "lstm"]):
        for j, c in enumerate(conjuntos):
            v = pf[(pf.modelo == m) & (pf.conjunto == c)].sort_values("fold").delta_MAE.values
            ax.scatter([j] * len(v), v, s=14, color=COR[m], alpha=0.6, linewidths=0)
            ax.plot([j - 0.25, j + 0.25], [v.mean()] * 2, color=COR[m], lw=1.6)
        ax.axhline(0, color="#333333", lw=0.7)
        ax.set_xticks(range(len(conjuntos)))
        ax.set_xticklabels([_rotulo_conj(c).replace("AR+CAL+", "+") for c in conjuntos], rotation=70, ha="right", fontsize=6.5)
        ax.set_title(NOME[m], fontsize=8)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("ΔMAE: CETESB espelho − CAMS\n(internações/dia)")
    fig.tight_layout()
    _salvar(fig, "fig_res_cams_vs_cetesb", d,
            "Diferença de MAE entre as bases CETESB espelho e CAMS, pareada por fold e semente (pontos = folds, média "
            "das sementes; traço = média das folds), nos conjuntos com bloco ambiental; valores negativos favorecem a "
            "CETESB. Runs h1_v02_cetesbmin_cetesbmin_full_20261019-100229 e h1_v02_cams_cams_full_20261019-084446.",
            {"runs": [RUN_CETESB_ESP, RUN_CAMS]})


CONJ_PRINCIPAL = "AR_CAL"   # conjunto comum da comparação principal entre modelos


BASELINES = ("naive", "seasonal_naive")   # no runner, os baselines têm feature_set == "baseline"


def _conj(modelo: str, conjunto: str) -> str:
    return "baseline" if modelo in BASELINES else conjunto


def _linha_mc(d: Dados, modelo: str, conjunto: str) -> pd.Series:
    q = d.mc[(d.mc.model == modelo) & (d.mc.feature_set == _conj(modelo, conjunto))]
    if len(q) != 1:
        raise RuntimeError(f"model_comparison.csv: esperava 1 linha para ({modelo}, {conjunto}), achei {len(q)}")
    return q.iloc[0]


def _fmt(v: float, casas: int = 2) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def fig11_metricas_ar_cal(d: Dados) -> None:
    """MAE, RMSE e MASE dos sete modelos no MESMO conjunto (AR_CAL): comparação principal."""
    tab = pd.DataFrame([_linha_mc(d, m, CONJ_PRINCIPAL) for m in MODELOS])
    fig, axes = plt.subplots(1, 3, figsize=(7.4, 3.0))
    x = np.arange(len(MODELOS))
    for ax, (col, sd, rot) in zip(axes, [("MAE_medio", "MAE_std_fold", "MAE (internações/dia)"),
                                         ("RMSE_medio", "RMSE_std_fold", "RMSE (internações/dia)"),
                                         ("MASE_medio", None, "MASE (adimensional)")]):
        vals = tab[col].values.astype(float)
        ax.bar(x, vals, color=[COR[m] for m in MODELOS], width=0.7, edgecolor="white", linewidth=0.5)
        if sd:
            ax.errorbar(x, vals, yerr=tab[sd].values.astype(float), fmt="none", ecolor="#333333",
                        elinewidth=0.8, capsize=2)
        else:
            ax.axhline(1.0, color="#333333", lw=0.7, ls="--")
            ax.text(-0.45, 1.0, "Naïve = 1", fontsize=6.5, va="bottom", ha="left")
        topo = vals + (tab[sd].values.astype(float) if sd else 0.0)
        for xi, v, t in zip(x, vals, topo):
            ax.text(xi, t + vals.max() * 0.02, _fmt(v), ha="center", va="bottom", fontsize=6, rotation=90)
        ax.margins(y=0.2)
        ax.set_ylim(0, None)
        ax.set_xticks(x)
        ax.set_xticklabels([NOME[m] for m in MODELOS], rotation=60, ha="right", fontsize=7)
        ax.set_ylabel(rot)
        ax.set_title("menor é melhor", fontsize=7.5, color="#444444")
        ax.grid(axis="x", visible=False)
    fig.suptitle(f"Conjunto comum {_rotulo_conj(CONJ_PRINCIPAL)} (memória do alvo + calendário)", fontsize=8, y=1.0)
    fig.tight_layout(w_pad=1.0)
    _salvar(fig, "fig_res_metricas_ar_cal", d,
            "MAE, RMSE e MASE médios dos sete modelos no mesmo conjunto de covariáveis AR+CAL (comparação principal, "
            "sem bloco ambiental); barras de erro = desvio-padrão entre as quatro folds (MAE e RMSE); sementes "
            "agregadas dentro de cada fold.",
            {"conjunto": CONJ_PRINCIPAL,
             "valores": {m: {k: float(_linha_mc(d, m, CONJ_PRINCIPAL)[k]) for k in ("MAE_medio", "RMSE_medio", "MASE_medio")}
                         for m in MODELOS}})


def fig12_por_fold_ar_cal(d: Dados) -> None:
    """MAE e MASE por fold, todos os modelos em AR_CAL (variação temporal do erro)."""
    sel = d.mbf[[fs == _conj(m, CONJ_PRINCIPAL) for m, fs in zip(d.mbf.model, d.mbf.feature_set)]]
    pf = sel.groupby(["model", "fold"]).agg(MAE=("MAE", "mean"), MASE=("MASE", "mean")).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.1), sharex=True)
    for ax, col in zip(axes, ["MAE", "MASE"]):
        for m in MODELOS:
            q = pf[pf.model == m].sort_values("fold")
            if len(q) != 4:
                raise RuntimeError(f"metrics_by_fold.csv: {m}/{CONJ_PRINCIPAL} tem {len(q)} folds, esperava 4")
            ax.plot(q.fold, q[col], marker=MARCA[m], ls=TRACO[m], color=COR[m], ms=5, label=NOME[m], lw=1.0)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xticklabels(["1\njan–jul/23", "2\njul/23–jan/24", "3\njan–jul/24", "4\njul–dez/24"], fontsize=7)
        ax.set_xlabel("Fold (teste de 180 dias)")
        ax.set_ylabel("MAE (internações/dia)" if col == "MAE" else "MASE (adimensional)")
        if col == "MASE":
            ax.axhline(1.0, color="#333333", lw=0.7, ls="--")
            ax.text(1.02, 1.0, "Naïve = 1", fontsize=7, va="bottom", ha="left")
        else:
            ax.set_ylim(0, None)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=7, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02), fontsize=7)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _salvar(fig, "fig_res_por_fold_ar_cal", d,
            "MAE e MASE em cada fold temporal para os sete modelos no conjunto comum AR+CAL (média das sementes dentro "
            "da fold). Fold 1 = jan–jul/2023; 2 = jul/2023–jan/2024; 3 = jan–jul/2024; 4 = jul–dez/2024.",
            {"conjunto": CONJ_PRINCIPAL})


def _delta_pareado(d: Dados, modelo: str, base: str, com: str) -> pd.DataFrame:
    """ΔMAE = MAE(com) − MAE(base), pareado por (fold, semente); por fold: média, dp e n entre sementes."""
    q = d.mbf[(d.mbf.model == modelo) & (d.mbf.feature_set.isin([base, com]))]
    piv = q.pivot_table(index=["fold", "seed"], columns="feature_set", values="MAE")
    if piv.isna().any().any() or set(piv.columns) != {base, com}:
        raise RuntimeError(f"pareamento incompleto para {modelo}: {base} × {com}")
    delta = (piv[com] - piv[base]).rename("delta").reset_index()
    return delta.groupby("fold").delta.agg(["mean", "std", "count"]).reindex([1, 2, 3, 4])


def fig13_ablacao_pm25(d: Dados) -> None:
    """Ablação pareada do PM2,5: AR_CAL ± PM25 e AR_CAL_METEO ± PM25, por modelo e fold (H2)."""
    modelos = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb"]
    tem = set(d.mc.feature_set)
    pares = [(b, c) for b, c in [("AR_CAL", "AR_CAL_PM25MEDIA"), ("AR_CAL_METEO", "AR_CAL_METEO_PM25MEDIA"),
                                 ("AR_CAL", "AR_CAL_PM25"), ("AR_CAL_METEO", "AR_CAL_METEO_PM25")] if c in tem]
    nlin = 2 if len(pares) > 2 else 1
    fig, axes = plt.subplots(nlin, 2, figsize=(7.4, 3.3 * nlin), sharey=True)
    axes = np.atleast_1d(axes).ravel()
    resumo: dict[str, dict] = {}
    desl = (np.arange(4) - 1.5) * 0.15
    for ax, (base, com) in zip(axes, pares):
        for j, m in enumerate(modelos):
            t = _delta_pareado(d, m, base, com)
            media = t["mean"].values.astype(float)
            dp = t["std"].fillna(0).values.astype(float)
            ax.errorbar(j + desl, media, yerr=dp, fmt="none", ecolor=COR[m], elinewidth=0.7, capsize=0, alpha=0.6)
            ax.scatter(j + desl, media, s=30, color=COR[m], linewidths=0, zorder=4)
            ax.plot([j - 0.35, j + 0.35], [media.mean()] * 2, color=COR[m], lw=1.8, zorder=3)
            for k, f in enumerate((1, 2, 3, 4)):
                ax.text(j + desl[k], media[k], str(f), fontsize=4.5, ha="center", va="center", color="white", zorder=5)
            resumo[f"{m}:{base}->{com}"] = {
                "delta_MAE_por_fold": [float(v) for v in media],
                "dp_sementes_por_fold": [None if np.isnan(v) else float(v) for v in t["std"].values],
                "n_sementes": int(t["count"].iloc[0]), "media_folds": float(media.mean())}
        ax.axhline(0, color="#333333", lw=0.7)
        ax.set_xticks(range(len(modelos)))
        ax.set_xticklabels([NOME[m] for m in modelos], rotation=30, ha="right", fontsize=7)
        ax.set_title(f"{_rotulo_conj(base)}  →  {_rotulo_conj(com)}", fontsize=8)
        ax.grid(axis="x", visible=False)
    for ax in axes[::2]:
        ax.set_ylabel("ΔMAE ao acrescentar PM2,5\n(internações/dia; < 0 favorece o PM2,5)")
    for ax in axes[len(pares):]:
        ax.axis("off")
    fig.text(0.5, -0.01, "Pontos = folds 1–4 (número no ponto), pareados por semente; barra fina = ±1 dp entre sementes "
             "(XGBoost e LSTM); traço largo = média das folds. PM25méd = só a média de PM2,5; PM25 = média + nº de "
             "estações + D_t.", ha="center", fontsize=6.5, color="#444444")
    fig.tight_layout(w_pad=1.0)
    _salvar(fig, "fig_res_ablacao_pm25", d,
            "Ablação pareada do bloco PM2,5 (H2): diferença de MAE ao acrescentar PM2,5 a AR+CAL e a AR+CAL+METEO, "
            "pareada por fold e semente (painéis: média isolada e, quando a run tem o bloco rico, média + nº de estações "
            "+ D_t); pontos = folds, barra fina = ±1 desvio-padrão entre sementes, traço = média das folds. Valores "
            "negativos indicam que o PM2,5 reduziu o erro.",
            {"pares": [f"{b}->{c}" for b, c in pares], "delta_MAE": resumo})


def fig14_painel_exploratorio(d: Dados) -> None:
    """Painel exploratório: MAE médio de cada modelo em cada um dos oito conjuntos (mapa de calor, um matiz)."""
    modelos = ["xgboost", "sarimax", "lstm", "ingarch_nb", "gam_nb"]
    conjuntos = _presentes(d, ORDEM_CONJUNTOS)
    mat = np.full((len(modelos), len(conjuntos)), np.nan)
    for i, m in enumerate(modelos):
        for j, c in enumerate(conjuntos):
            mat[i, j] = float(_linha_mc(d, m, c)["MAE_medio"])
    naive = float(_linha_mc(d, "naive", CONJ_PRINCIPAL)["MAE_medio"])
    vmin, vmax = float(np.nanmin(mat)), float(np.nanmax(mat))
    fig, ax = plt.subplots(figsize=(7.4, 3.4))
    im = ax.imshow(mat, cmap="Blues", aspect="auto", vmin=vmin, vmax=vmax)
    for i in range(mat.shape[0]):
        melhor_j = int(np.nanargmin(mat[i]))
        for j in range(mat.shape[1]):
            v = mat[i, j]
            cor = "white" if (v - vmin) / (vmax - vmin) > 0.6 else "#111111"
            ax.text(j, i, _fmt(v), ha="center", va="center", fontsize=7, color=cor,
                    fontweight="bold" if j == melhor_j else "normal")
            if j == melhor_j:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor="#111111", lw=1.2))
    ax.set_xticks(range(len(conjuntos)))
    ax.set_xticklabels([_rotulo_conj(c) for c in conjuntos], rotation=40, ha="right", fontsize=7)
    ax.set_yticks(range(len(modelos)))
    ax.set_yticklabels([NOME[m] for m in modelos], fontsize=8)
    ax.axvline(1.5, color="#111111", lw=1.6)   # separa AR_CAL (comparação principal) dos conjuntos com bloco ambiental
    ax.text(1.0, -0.62, "comparação" + chr(10) + "principal", ha="center", va="bottom", fontsize=6, color="#444444")
    ax.text(1.5 + (len(conjuntos) - 2) / 2, -0.62, "exploratório: conjuntos com blocos ambientais", ha="center",
            va="bottom", fontsize=6.5, color="#444444")
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cb.set_label("MAE médio (internações/dia)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_title(f"PAINEL EXPLORATÓRIO — todas as combinações de covariáveis por modelo (Naïve: MAE {_fmt(naive)})",
                 fontsize=7.5, loc="left", color="#444444", pad=20)
    fig.tight_layout()
    _salvar(fig, "fig_res_painel_exploratorio", d,
            "Painel exploratório, separado da comparação principal: MAE médio de cada modelo em cada um dos oito "
            "conjuntos de covariáveis (sementes agregadas dentro da fold, depois folds); contorno = menor MAE de cada "
            "modelo; a linha vertical separa AR+CAL (comparação principal) dos conjuntos com bloco ambiental.",
            {"MAE_medio": {m: {c: float(mat[i, j]) for j, c in enumerate(conjuntos)} for i, m in enumerate(modelos)},
             "naive_MAE_medio": naive})


FIGURAS = {1: fig1_serie_alvo, 2: fig2_metricas_agregadas, 3: fig3_por_fold, 4: fig4_obs_vs_prev_tempo,
           5: fig5_dispersao, 6: fig6_erro_tempo, 7: fig7_erro_contexto, 8: fig8_ablacao, 9: fig9_sementes,
           10: fig10_cams_cetesb, 11: fig11_metricas_ar_cal, 12: fig12_por_fold_ar_cal,
           13: fig13_ablacao_pm25, 14: fig14_painel_exploratorio, 15: fig15_sementes_todos}


def main(argv=None) -> None:
    global RUN, SAIDA
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--figura", type=int, nargs="*", default=sorted(FIGURAS), help="números das figuras (1–15)")
    ap.add_argument("--run", default=RUN, help="run principal (padrão: a da base CETESB espelho, sete modelos)")
    ap.add_argument("--saida", default=None, help="pasta de saída (padrão: reports/figs/resultados_v02; "
                    "com --run diferente do padrão, reports/figs/resultados_<run>)")
    args = ap.parse_args(argv)
    if args.run != RUN:
        RUN = args.run
        SAIDA = RAIZ / "reports" / "figs" / f"resultados_{RUN}"
    if args.saida:
        SAIDA = Path(args.saida)
    d = Dados()
    print(f"run principal: {RUN}  ·  saída: {SAIDA}")
    for k in args.figura:
        d.lidos = {p: h for p, h in d.lidos.items() if not p.startswith("reports/experiments/h1_v02_cams")
                   and not p.startswith("reports/experiments/COMPARACAO")}
        FIGURAS[k](d)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

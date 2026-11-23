"""Figuras do diagnóstico do sábado e do caráter da internação (PROTOCOLO §0.23).

    python -m src.viz.figuras_diagnostico_carater --microdados <dir com aih_alvo_enriquecido.parquet>
    python -m src.viz.figuras_diagnostico_carater --microdados <dir> --figura 1 3

Fonte única: `aih_alvo_enriquecido.parquet`, extraído por `src/ingestion/sih_extrair_aih_alvo.py` (mesma regra do
alvo; 0 dias divergentes de `data/processed/sih_daily_lookahead_2019_2026.parquet`). O arquivo é dado em nível de
registro e fica fora do repositório; a proveniência grava caminho e sha256. Nenhum número é digitado: tudo é
recalculado aqui. Saída em `reports/figs/diagnostico_carater/` (`.pdf` vetorial, `.png` 300 dpi, `.prov.json`).

Desvio declarado da convenção "um script por figura" (o mesmo de `figuras_resultados_v02.py`): as quatro figuras
partilham leitura, derivações e estilo, então ficam num módulo, uma função por figura.

Definições usadas (iguais às do diagnóstico registrado em §0.23):
- nível local = mediana móvel centrada de 29 dias da própria série diária; razão = y / nível local;
- dispersão de um dia da semana = intervalo interquartil da razão nesse dia;
- "não eletiva" = `CAR_INT` ≠ 01 (no alvo só ocorrem 01 e 02);
- grupos com mecanismo plausível de efeito da poluição = J00–J06, J09–J11, J12–J18, J20–J22, J40–J47.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "reports" / "figs" / "diagnostico_carater"
CNES_CEMA = "2091550"   # Instituto CEMA de Oftalmologia e Otorrinolaringologia
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
PRETO, CINZA, CINZA_CLARO = "#000000", "#7F7F7F", "#D9D9D9"

GRUPOS = [  # (rótulo, primeiro, último, mecanismo plausível de efeito da poluição)
    ("J00–J06 infecções agudas das vias aéreas superiores", 0, 6, True),
    ("J09–J11 influenza", 9, 11, True),
    ("J12–J18 pneumonias", 12, 18, True),
    ("J20–J22 bronquite e bronquiolite agudas", 20, 22, True),
    ("J30–J39 outras doenças das vias aéreas superiores", 30, 39, False),
    ("J40–J47 doenças crônicas das vias aéreas inferiores", 40, 47, True),
    ("J60–J70 doenças pulmonares por agentes externos", 60, 70, False),
    ("J80–J84 doenças intersticiais", 80, 84, False),
    ("J85–J86 afecções supurativas", 85, 86, False),
    ("J90–J94 doenças da pleura", 90, 94, False),
    ("J95–J99 outras (pós-procedimento, insuficiência respiratória)", 95, 99, False),
]

plt.rcParams.update({
    "font.size": 9, "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#DDDDDD",
    "grid.linewidth": 0.5, "lines.linewidth": 1.0, "pdf.fonttype": 42, "savefig.bbox": "tight",
    "hatch.linewidth": 0.6,
})


def _mes_pt(x, _pos=None):
    d = mdates.num2date(x)
    return f"{MESES[d.month - 1]}/{d.year}"


_VIRGULA = plt.FuncFormatter(lambda v, _p: f"{v:g}".replace(".", ","))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _git() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "indisponível"


class Dados:
    def __init__(self, pasta: Path):
        self.arq = pasta / "aih_alvo_enriquecido.parquet"
        if not self.arq.exists():
            raise SystemExit(f"{self.arq} não existe — rode src/ingestion/sih_extrair_aih_alvo.py")
        a = pd.read_parquet(self.arq, columns=["N_AIH", "DT_INTER", "DIAG_PRINC", "CAR_INT", "CNES"])
        if a.N_AIH.duplicated().any():
            raise SystemExit("N_AIH duplicado no arquivo de microdados")
        cod = set(a.CAR_INT.unique())
        if not cod <= {"01", "02", "03", "04", "05", "06"}:
            raise SystemExit(f"CAR_INT fora de 01–06: {sorted(cod)}")
        a["dt"] = pd.to_datetime(a.DT_INTER, format="%Y%m%d")
        a["n"] = a.DIAG_PRINC.str[1:3].astype(int)
        a["eletiva"] = a.CAR_INT == "01"
        self.a = a
        self.idx = pd.date_range(a.dt.min(), a.dt.max(), freq="D")
        self.lidos = {str(self.arq): _sha(self.arq)}

    def diaria(self, filtro=None) -> pd.Series:
        x = self.a if filtro is None else self.a[filtro]
        return x.groupby("dt").size().reindex(self.idx, fill_value=0)


def _razao(s: pd.Series) -> pd.Series:
    return s / s.rolling(29, center=True, min_periods=15).median()


def _salvar(fig, nome: str, d: Dados, frase: str, numeros: dict) -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    fig.savefig(SAIDA / f"{nome}.pdf")
    fig.savefig(SAIDA / f"{nome}.png", dpi=300)
    plt.close(fig)
    prov = {"figura": nome, "rotulo_latex": "fig:" + nome.removeprefix("fig_").replace("_", "-"), "descricao": frase,
            "artefatos_de_origem": [{"caminho": k, "sha256": v} for k, v in d.lidos.items()],
            "extrator": "src/ingestion/sih_extrair_aih_alvo.py", "script": "src/viz/figuras_diagnostico_carater.py",
            "commit": _git(), "gerado_em": _dt.datetime.now().isoformat(timespec="seconds"),
            "python": platform.python_version(),
            "pacotes": {"matplotlib": matplotlib.__version__, "pandas": pd.__version__, "numpy": np.__version__},
            "numeros_citaveis": numeros}
    (SAIDA / f"{nome}.prov.json").write_text(json.dumps(prov, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  {nome}.pdf / .png / .prov.json")


def fig1_sabados_cema(d: Dados) -> None:
    tot = d.diaria()
    sem = d.diaria(d.a.CNES != CNES_CEMA)
    sab = tot.index.dayofweek == 5
    st, ss = tot[sab], sem[sab]
    fig, ax = plt.subplots(figsize=(6.3, 2.6))
    ax.fill_between(st.index, ss.values, st.values, color=CINZA_CLARO, lw=0, label="Internações no CNES 2091550")
    ax.plot(st.index, st.values, color=PRETO, lw=0.8, label="Todos os estabelecimentos (alvo atual)")
    ax.plot(ss.index, ss.values, color=CINZA, lw=0.8, ls="--", label="Sem o CNES 2091550")
    ax.set_ylim(0, None)
    ax.set_ylabel("Internações por sábado")
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=1))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_mes_pt))
    ax.margins(x=0.01)
    ax.legend(frameon=False, loc="upper left", ncol=1)
    out = {}
    for k, s in (("com", tot), ("sem", sem)):
        r = _razao(s)
        x = r[(r.index.dayofweek == 5) & (r.index.year >= 2022)]
        out[f"sabados_2022_mais_razao_acima_1_3_{k}_cema"] = int((x > 1.3).sum())
    _salvar(fig, "fig_diag_sabados_cema", d,
            "Internações respiratórias em cada sábado, com e sem o estabelecimento CNES 2091550; a área cinza é "
            "o que esse estabelecimento internou, e concentra os picos de sábado a partir de 2022.", out)


def fig2_eletivas_por_grupo(d: Dados) -> None:
    linhas = []
    for rot, i, f, sens in GRUPOS:
        g = d.a[(d.a.n >= i) & (d.a.n <= f)]
        if len(g) == 0:
            continue
        linhas.append(dict(grupo=rot, sens=sens, total=len(g), elet=int(g.eletiva.sum()),
                           cema=int((g.eletiva & (g.CNES == CNES_CEMA)).sum())))
    t = pd.DataFrame(linhas)
    t["pct"] = 100 * t.elet / t.total
    t = t.sort_values("pct")
    fig, ax = plt.subplots(figsize=(6.3, 3.6))
    y = np.arange(len(t))
    ax.barh(y, t.pct, color=["#FFFFFF" if s else CINZA_CLARO for s in t.sens], edgecolor=PRETO, lw=0.6,
            hatch=["////" if s else "" for s in t.sens], height=0.65)
    for yi, (p, e, tot_) in enumerate(zip(t.pct, t.elet, t.total)):
        ax.text(p + 1.2, yi, f"{p:.1f}%".replace(".", ",") + f"  ({e:,} de {tot_:,})".replace(",", "."),
                va="center", fontsize=7)
    ax.set_yticks(y, t.grupo, fontsize=7.5)
    ax.set_xlim(0, 115)
    ax.set_xticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("Internações eletivas no grupo (% do grupo)")
    ax.grid(axis="y", visible=False)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor="#FFFFFF", edgecolor=PRETO, hatch="////",
                             label="Mecanismo plausível de efeito da poluição"),
                       Patch(facecolor=CINZA_CLARO, edgecolor=PRETO, label="Demais grupos")],
              frameon=False, loc="lower right")
    s = t[t.sens]
    _salvar(fig, "fig_diag_eletivas_por_grupo", d,
            "Percentual de internações eletivas em cada grupo de CID do capítulo X, isto é, o que sairia do alvo "
            "com o recorte de urgência; nos grupos com mecanismo plausível de efeito da poluição a parcela eletiva é "
            "pequena.",
            {"eletivas_total": int(d.a.eletiva.sum()), "pct_eletivas_do_alvo": round(100 * d.a.eletiva.mean(), 2),
             "eletivas_grupos_sensiveis": int(s.elet.sum()),
             "pct_eletivas_nos_grupos_sensiveis": round(100 * s.elet.sum() / s.total.sum(), 2),
             "eletivas_cema_grupos_sensiveis": int(s.cema.sum()),
             "por_grupo": t.drop(columns="sens").round(2).to_dict(orient="records")})


def fig3_sazonalidade(d: Dados) -> None:
    sens = np.zeros(len(d.a), dtype=bool)
    for _, i, f, s in GRUPOS:
        if s:
            sens |= ((d.a.n >= i) & (d.a.n <= f)).values
    def mensal(filtro):
        x = d.a[filtro].groupby(d.a.dt[filtro].dt.to_period("M")).size()
        x = x.reindex(pd.period_range(d.idx[0], d.idx[-1], freq="M"), fill_value=0)
        return x / x.index.days_in_month
    u, e = mensal(sens & ~d.a.eletiva.values), mensal(sens & d.a.eletiva.values)
    datas = u.index.to_timestamp()
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.3, 3.6), sharex=True, gridspec_kw={"hspace": 0.25})
    a1.plot(datas, u.values, color=PRETO, marker="o", ms=1.8)
    a1.set_ylim(0, None); a1.set_ylabel("Não eletivas\n(média/dia)")
    a2.plot(datas, e.values, color=CINZA, marker="s", ms=1.8, ls="--")
    a2.set_ylim(0, None); a2.set_ylabel("Eletivas\n(média/dia)")
    a2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=1))
    a2.xaxis.set_major_formatter(plt.FuncFormatter(_mes_pt))
    per = slice("2019-01", "2024-12")
    r = float(np.corrcoef(u[per].values, e[per].values)[0, 1])
    _salvar(fig, "fig_diag_sazonalidade_sensiveis", d,
            "Média diária mensal de internações não eletivas e eletivas nos grupos com mecanismo plausível de "
            "efeito da poluição; as não eletivas têm a sazonalidade respiratória e as eletivas não a acompanham.",
            {"correlacao_mensal_2019_2024": round(r, 3),
             "media_dia_nao_eletivas": round(float(u.mean()), 1), "media_dia_eletivas": round(float(e.mean()), 2)})


def fig4_dispersao_dow(d: Dados) -> None:
    res = {}
    for k, s in (("total", d.diaria()), ("nao_eletivo", d.diaria(~d.a.eletiva))):
        r = _razao(s)
        r = r[r.index.year >= 2022]
        res[k] = [float(r[r.index.dayofweek == i].quantile(.75) - r[r.index.dayofweek == i].quantile(.25))
                  for i in range(7)]
    fig, ax = plt.subplots(figsize=(6.3, 2.4))
    x = np.arange(7); w = 0.38
    ax.bar(x - w / 2, res["total"], w, color=CINZA_CLARO, edgecolor=PRETO, lw=0.6, label="Alvo total (atual)")
    ax.bar(x + w / 2, res["nao_eletivo"], w, color="#FFFFFF", edgecolor=PRETO, lw=0.6, hatch="////",
           label="Alvo não eletivo (urgência)")
    ax.set_xticks(x, DOW)
    ax.set_ylim(0, None)
    ax.set_ylabel("Intervalo interquartil de\ny / nível local")
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper left")
    _salvar(fig, "fig_diag_dispersao_dia_semana", d,
            "Dispersão de cada dia da semana em torno do nível local, de 2022 em diante, no alvo total e no alvo "
            "não eletivo; o excesso de dispersão do sábado desaparece no alvo não eletivo.",
            {k: dict(zip(DOW, [round(v, 3) for v in vs])) for k, vs in res.items()})


FIGURAS = {1: fig1_sabados_cema, 2: fig2_eletivas_por_grupo, 3: fig3_sazonalidade, 4: fig4_dispersao_dow}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--microdados", type=Path, required=True)
    ap.add_argument("--figura", type=int, nargs="*", default=sorted(FIGURAS))
    a = ap.parse_args(argv)
    d = Dados(a.microdados)
    for k in a.figura:
        FIGURAS[k](d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

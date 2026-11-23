"""Gera painel_carater_internacao.ipynb (roda no Google Colab e no Jupyter local). Só lê dados_painel/ (agregados)."""
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
celulas = []


def md(t):
    celulas.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n")})


def py(t):
    celulas.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n")})


md("""
# Painel — caráter da internação e o problema do sábado
**Internações respiratórias (CID-10 J00–J99), residentes do município de São Paulo, jan/2019 a fev/2026.**
Fonte: SIH/SUS, AIH-RD (microdados), agregados por dia, grupo de CID e estabelecimento. Diagnóstico do PROTOCOLO §0.23.

**Como usar no Google Colab:** *Ambiente de execução → Executar tudo*. A primeira célula conecta o Google Drive
e lê os arquivos da pasta `Meu Drive/Dashboard PM2.5` (só dados agregados, sem nenhum registro de paciente). Na
primeira vez o Colab pede permissão para acessar o Drive. Se a pasta não estiver lá, a célula pede o `dados_painel.zip`.
No Jupyter local, deixe a pasta `dados_painel/` ao lado do notebook.

> Leitura descritiva, sem teste formal. Em 2025–2026 o alvo ainda não foi conferido contra o TabNet.
""")

py("""
import io, os, zipfile, json
import numpy as np, pandas as pd
import plotly.express as px, plotly.graph_objects as go, plotly.io as pio
from plotly.subplots import make_subplots
import ipywidgets as w
from IPython.display import display, HTML

try:
    from google.colab import files  # noqa: F401
    NO_COLAB = True
except ImportError:
    NO_COLAB = False
pio.renderers.default = "colab" if NO_COLAB else "notebook"

PASTA_DRIVE = "/content/drive/MyDrive/Dashboard PM2.5"
BASE = "dados_painel"
if NO_COLAB:
    from google.colab import drive
    drive.mount("/content/drive")
    if os.path.exists(os.path.join(PASTA_DRIVE, "diario.csv")):
        BASE = PASTA_DRIVE
    elif os.path.exists(os.path.join(PASTA_DRIVE, "dados_painel.zip")):
        zipfile.ZipFile(os.path.join(PASTA_DRIVE, "dados_painel.zip")).extractall("dados_painel")
    else:
        print("Pasta do Drive sem os dados:", PASTA_DRIVE, "— vou pedir o zip.")
print("Lendo os dados de:", BASE)

if BASE == "dados_painel" and not os.path.isdir("dados_painel"):
    if os.path.exists("dados_painel.zip"):
        zipfile.ZipFile("dados_painel.zip").extractall("dados_painel")
    elif NO_COLAB:
        from google.colab import files
        enviado = files.upload()  # escolha dados_painel.zip
        zipfile.ZipFile(io.BytesIO(next(iter(enviado.values())))).extractall("dados_painel")
    else:
        raise FileNotFoundError("Coloque a pasta dados_painel/ ou dados_painel.zip ao lado do notebook")

D = pd.read_csv(f"{BASE}/diario.csv", parse_dates=["data"]).set_index("data")
G = pd.read_csv(f"{BASE}/grupos_cid.csv")
E = pd.read_csv(f"{BASE}/estabelecimentos_ano.csv", dtype={"CNES": str})
P = pd.read_csv(f"{BASE}/perfil.csv").set_index("recorte")
A = pd.read_csv(f"{BASE}/atraso_registro_2022_mais.csv").set_index("dow")
M = pd.read_csv(f"{BASE}/erros_modelos_ar_cal.csv", parse_dates=["target_date"])
MAN = json.load(open(f"{BASE}/manifest.json", encoding="utf-8"))

DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
COR = {"total": "#4D4D4D", "nao_eletivo": "#0072B2", "eletivo": "#D55E00", "cema": "#E69F00"}
NOME_MOD = {"xgboost": "XGBoost", "sarimax": "SARIMAX", "lstm": "LSTM", "ingarch_nb": "INGARCH-NB",
            "gam_nb": "GAM-NB", "naive": "Naïve", "seasonal_naive": "Seasonal Naïve"}
COR_MOD = {"XGBoost": "#0072B2", "SARIMAX": "#009E73", "LSTM": "#D55E00", "INGARCH-NB": "#CC79A7",
           "GAM-NB": "#E69F00", "Naïve": "#000000", "Seasonal Naïve": "#7F7F7F"}
LAYOUT = dict(template="plotly_white", font=dict(size=13), separators=",.", hovermode="x unified",
              margin=dict(l=60, r=20, t=100, b=40), legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0))
D["total_sem_cema"] = D.total - D.cema
D["dow"] = D.index.dayofweek
D["semana_mes"] = (D.index.day - 1) // 7 + 1

def razao(s):
    return s / s.rolling(29, center=True, min_periods=15).median()

def br(v, casas=1):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

print("Dados carregados:", MAN["gerado_em"], "| dias:", len(D), "| internações:", br(D.total.sum(), 0))
""")

md("## 1. Visão geral")
py("""
r_tot, r_ne = razao(D.total), razao(D.nao_eletivo)
sab22 = (D.dow == 5) & (D.index.year >= 2022)
kpis = [("Internações (2019–fev/2026)", br(D.total.sum(), 0)), ("Média por dia", br(D.total.mean())),
        ("Eletivas no alvo", br(100 * D.eletivo.sum() / D.total.sum()) + "%"),
        ("Sábados atípicos desde 2022", f"{int((r_tot[sab22] > 1.3).sum())} → {int((r_ne[sab22] > 1.3).sum())}")]
display(HTML("<div style='display:flex;gap:12px;flex-wrap:wrap'>" + "".join(
    f"<div style='background:#f4f4f2;border-radius:8px;padding:12px 16px;min-width:180px'>"
    f"<div style='font-size:12px;color:#555'>{k}</div><div style='font-size:24px'>{v}</div></div>" for k, v in kpis) +
    "</div><p style='font-size:12px;color:#666'>Sábados atípicos: 30% ou mais acima do nível local (mediana móvel de 29 dias); "
    "alvo total → alvo não eletivo.</p>"))
s = D[["total", "nao_eletivo", "eletivo"]].resample("W").mean()
fig = go.Figure()
for c, n in [("total", "Total (alvo atual)"), ("nao_eletivo", "Não eletivo (urgência)"), ("eletivo", "Eletivo")]:
    fig.add_scatter(x=s.index, y=s[c], name=n, line=dict(color=COR[c], width=1.6))
fig.update_layout(**LAYOUT, title="Média semanal de internações por dia", yaxis_title="Internações/dia",
                  xaxis=dict(rangeslider=dict(visible=True), tickformat="%m/%Y"))
fig.update_yaxes(rangemode="tozero")
fig.show()
""")

md("## 2. Dia da semana")
py("""
anual = D.groupby([D.index.year, "dow"]).total.mean().unstack()
fig = px.imshow(anual.values, x=DOW, y=[str(a) for a in anual.index], text_auto=".0f", aspect="auto",
                color_continuous_scale="Blues", labels=dict(color="Internações/dia"))
fig.update_layout(template="plotly_white", font=dict(size=13), title="Média de internações por dia da semana e ano",
                  margin=dict(l=60, r=20, t=50, b=40))
fig.show()

def dispersao(periodo):
    ini, fim = {"2019–2021": ("2019", "2021"), "2022–fev/2026": ("2022", "2026"), "Tudo": ("2019", "2026")}[periodo]
    linhas = []
    for col, nome in [("total", "Alvo total"), ("nao_eletivo", "Alvo não eletivo")]:
        r = razao(D[col])[ini:fim]
        for i, dn in enumerate(DOW):
            x = r[r.index.dayofweek == i]
            linhas.append(dict(dia=dn, alvo=nome, iqr=x.quantile(.75) - x.quantile(.25), atipicos=int((x > 1.3).sum())))
    t = pd.DataFrame(linhas)
    fig = px.bar(t, x="dia", y="iqr", color="alvo", barmode="group", hover_data=["atipicos"],
                 color_discrete_map={"Alvo total": COR["total"], "Alvo não eletivo": COR["nao_eletivo"]},
                 labels=dict(iqr="Intervalo interquartil de y / nível local", dia="", alvo="", atipicos="dias ≥ 30% acima"))
    fig.update_layout(**{**LAYOUT, "hovermode": "closest"}, title=f"Quanto cada dia oscila em torno do nível do mês ({periodo})")
    fig.show()

w.interact(dispersao, periodo=w.ToggleButtons(options=["2022–fev/2026", "2019–2021", "Tudo"], description="Período"));
""")

md("## 3. O sábado e o CNES 2091550 (Instituto CEMA)")
py("""
sab = D[D.dow == 5]
fig = go.Figure()
fig.add_scatter(x=sab.index, y=sab.total_sem_cema, name="Sem o CNES 2091550", line=dict(color=COR["nao_eletivo"], width=1.2))
fig.add_scatter(x=sab.index, y=sab.total, name="Todos os estabelecimentos", fill="tonexty",
                fillcolor="rgba(230,159,0,0.30)", line=dict(color=COR["total"], width=1.2))
fig.update_layout(**LAYOUT, title="Internações em cada sábado (área laranja = CNES 2091550)", yaxis_title="Internações por sábado",
                  xaxis=dict(rangeslider=dict(visible=True), tickformat="%m/%Y"))
fig.update_yaxes(rangemode="tozero")
fig.show()

rs = razao(D.total)[D.dow == 5].to_frame("r")
rs["semana"] = (rs.index.day - 1) // 7 + 1
rs["periodo"] = np.where(rs.index.year <= 2021, "2019–2021", "2022–fev/2026")
t = rs.groupby(["periodo", "semana"]).r.median().reset_index()
t["semana"] = t.semana.astype(str) + "º sábado"
fig = px.bar(t, x="semana", y="r", color="periodo", barmode="group",
             color_discrete_map={"2019–2021": "#B4B2A9", "2022–fev/2026": COR["eletivo"]},
             labels=dict(r="Razão mediana (1 = dia comum)", semana="", periodo=""))
fig.add_hline(y=1, line_dash="dot", line_color="#888")
fig.update_layout(**{**LAYOUT, "hovermode": "closest"}, title="O pico cai nos três primeiros sábados do mês (desde 2022)")
fig.show()

c = sab.cema.to_frame("n")
c["ano"] = c.index.year.astype(str); c["mes"] = c.index.month; c["sm"] = c.index.day.map(lambda d: (d - 1) // 7 + 1)
c["coluna"] = c.mes.map(lambda m: MESES[m - 1]) + "-" + c.sm.astype(str)
ordem = [f"{m}-{s}" for m in MESES for s in range(1, 6)]
piv = c.pivot_table(index="ano", columns="coluna", values="n", aggfunc="sum").reindex(columns=[o for o in ordem if o in c.coluna.unique()])
fig = px.imshow(piv, aspect="auto", color_continuous_scale="Oranges", labels=dict(color="Internações", x="mês-semana do mês", y=""))
fig.update_layout(template="plotly_white", font=dict(size=12), title="Calendário: internações do CNES 2091550 em cada sábado",
                  margin=dict(l=60, r=20, t=50, b=40))
fig.update_xaxes(tickangle=-90, tickfont=dict(size=9))
fig.show()

at = A.copy(); at.index = DOW
display(HTML("<b>Atraso de registro desde 2022</b> (% das AIH por meses entre a internação e a competência; 4 = 4 ou mais). "
             "O sábado não tem mais atraso que os outros dias:"))
display(at.round(1).rename(columns=lambda c: f"{c} mês(es)"))
""")

md("## 4. Caráter da internação e grupos de CID")
py("""
g = G.copy(); g["pct"] = 100 * g.eletivas / g.total
g["tipo"] = np.where(g.sensivel, "Mecanismo plausível de efeito da poluição", "Demais grupos")
g = g.sort_values("pct")
fig = px.bar(g, x="pct", y="grupo", color="tipo", orientation="h", hover_data=dict(eletivas=True, total=True, eletivas_cema=True),
             color_discrete_map={"Mecanismo plausível de efeito da poluição": COR["nao_eletivo"], "Demais grupos": "#B4B2A9"},
             labels=dict(pct="% eletivo no grupo (sairia do alvo de urgência)", grupo="", tipo="", eletivas_cema="eletivas no CEMA"))
fig.update_layout(**{**LAYOUT, "hovermode": "closest"}, height=480, title="O que o alvo de urgência exclui, por grupo de CID")
fig.update_xaxes(range=[0, 100], ticksuffix="%")
fig.show()
s = g[g.sensivel]
print(f"Grupos sensíveis à poluição: {br(s.eletivas.sum(), 0)} eletivas de {br(s.total.sum(), 0)} "
      f"({br(100 * s.eletivas.sum() / s.total.sum())}%); no CEMA: {int(s.eletivas_cema.sum())}.")

m = D[["sens_nao_eletivo", "sens_eletivo"]].resample("MS").mean()
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    subplot_titles=("Não eletivas (ficam no alvo)", "Eletivas (sairiam do alvo)"))
fig.add_scatter(x=m.index, y=m.sens_nao_eletivo, row=1, col=1, name="Não eletivas", line=dict(color=COR["nao_eletivo"]))
fig.add_scatter(x=m.index, y=m.sens_eletivo, row=2, col=1, name="Eletivas", line=dict(color=COR["eletivo"], dash="dash"))
r = m["2019":"2024"].corr().iloc[0, 1]
fig.update_layout(**LAYOUT, height=480, showlegend=False,
                  title=f"Grupos sensíveis à poluição: média diária por mês (correlação 2019–2024: {br(r, 2)})")
fig.update_yaxes(rangemode="tozero", title_text="Internações/dia"); fig.update_xaxes(tickformat="%m/%Y")
fig.show()

display(HTML("<b>Perfil dos recortes</b> (idade em anos, permanência em dias):"))
display(P.rename(columns={"internacoes": "internações", "idade_mediana": "idade mediana", "pct_menor_15": "% < 15 anos",
                          "permanencia_mediana": "permanência mediana", "pct_permanencia_ate_1_dia": "% permanência ≤ 1 dia",
                          "pct_obito": "% óbito"}))
""")

md("## 5. Estabelecimentos com mais internações eletivas aos sábados")
py("""
def estab(metrica):
    col = {"Eletivas aos sábados": "eletivas_sabado", "Eletivas (todos os dias)": "eletivas", "Total": "total"}[metrica]
    fig = px.line(E.sort_values("ano"), x="ano", y=col, color="nome", markers=True,
                  labels=dict(ano="", nome="", **{col: metrica + " por ano"}))
    fig.update_traces(line=dict(width=1.2), opacity=0.55)
    fig.for_each_trace(lambda t: t.update(line=dict(width=3, color=COR["cema"]), opacity=1) if "CEMA" in t.name else None)
    fig.update_layout(**{**LAYOUT, "hovermode": "closest", "legend": dict(orientation="v", x=1.02, y=1)}, height=480,
                      title=f"{metrica}: 15 estabelecimentos com mais eletivas aos sábados")
    fig.update_yaxes(rangemode="tozero")
    fig.show()

w.interact(estab, metrica=w.Dropdown(options=["Eletivas aos sábados", "Eletivas (todos os dias)", "Total"], description="Métrica"));
print("Células com menos de 5 internações foram suprimidas. Nomes além do CEMA: consultar o CNES/DATASUS.")
""")

md("## 6. Efeito nos modelos (conjunto comum AR_CAL, base CETESB rica)")
py("""
M["dow"] = M.target_date.dt.dayofweek
M["modelo"] = M.model.map(NOME_MOD)
M["erro"] = M.y - M.y_prev
M["mutirao"] = (M.dow == 5) & ((M.target_date.dt.day - 1) // 7 < 3) & (M.target_date.dt.year >= 2022)

def modelos(h, metrica):
    x = M[M.h == h]
    if metrica == "MAE":
        t = x.assign(v=x.erro.abs()).groupby(["modelo", "dow"]).v.mean().reset_index()
        rot = "MAE (internações/dia)"
    else:
        t = x.groupby(["modelo", "dow"]).erro.mean().reset_index().rename(columns={"erro": "v"})
        rot = "Viés (observado − previsto)"
    t["dia"] = t.dow.map(dict(enumerate(DOW)))
    fig = px.bar(t, x="dia", y="v", color="modelo", barmode="group", category_orders=dict(dia=DOW, modelo=list(COR_MOD)),
                 color_discrete_map=COR_MOD, labels=dict(v=rot, dia="", modelo=""))
    fig.update_layout(**{**LAYOUT, "hovermode": "closest"}, title=f"{metrica} por dia da semana — h = {h} (run {x.run.iloc[0]})")
    fig.show()
    part = (x.assign(a=x.erro.abs()).groupby("modelo")
            .apply(lambda g: pd.Series({"MAE": g.a.mean(), "MAE fora dos sábados de mutirão": g.a[~g.mutirao].mean(),
                                        "% do erro absoluto nos sábados de mutirão": 100 * g.a[g.mutirao].sum() / g.a.sum(),
                                        "% das datas": 100 * g.mutirao.mean()}), include_groups=False))
    display(HTML("<b>Quanto do erro vem do 1º–3º sábado do mês (2022+)</b>:"))
    display(part.reindex([m for m in COR_MOD if m in part.index]).round(1))

w.interact(modelos, h=w.ToggleButtons(options=[1, 5, 7, 15, 30], description="Horizonte"),
           metrica=w.ToggleButtons(options=["MAE", "Viés"], description="Métrica"));
""")

md("""
## 7. A decisão em discussão (PROTOCOLO §0.23, [PROPOSTO])
- **Alvo não eletivo (urgência)** para a pergunta do PM2,5: o critério é o caráter da internação registrado na AIH, igual
  para todos os dias, hospitais e CID, sem excluir estabelecimento.
- **Alvo total** continua para a previsão de demanda hospitalar (leito ocupado por eletiva também conta).
- O que sai: sobretudo cirurgias programadas das vias aéreas superiores (J30–J39). Nos grupos com mecanismo plausível de
  efeito da poluição, a parcela eletiva é pequena (seção 4) e não acompanha a sazonalidade.
- Ponto para o orientador: qual dos dois alvos é o desfecho principal da dissertação.
""")
py("""
print("Proveniência:"); print(json.dumps(MAN, ensure_ascii=False, indent=2))
""")

nb = {"cells": celulas, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                     "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "nbformat": 4, "nbformat_minor": 5}
(AQUI / "painel_carater_internacao.ipynb").write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok")

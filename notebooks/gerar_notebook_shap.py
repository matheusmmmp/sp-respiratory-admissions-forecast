"""Generates interpretabilidade_shap.ipynb.

The notebook only READS ``models_demo/shap/`` (written by
``uv run python -m models_demo.interpretabilidade``); it recomputes nothing.
Figures are referenced from markdown cells, so they render on GitHub without
running the notebook; code cells are saved with empty outputs.

Run: ``uv run python notebooks/gerar_notebook_shap.py``.
"""

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASTA = "../models_demo/shap"
celulas = []


def md(t):
    celulas.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n")})


def py(t):
    celulas.append(
        {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n")}
    )


def figura(nome, en, pt):
    md(
        f"""
![{nome}]({PASTA}/{nome}_en.png)

**EN.** {en}

**PT.** {pt} Versão em português: [`{nome}_pt.png`]({PASTA}/{nome}_pt.png).
"""
    )


md("""
# SHAP values of the demo XGBoost `AR_CAL` models / Valores SHAP dos modelos XGBoost `AR_CAL` de demonstração

> **Demonstration, not a dissertation result · provisional.** The three models in `models_demo/` (h = 1, 7, 30) are
> trained on the whole 2019–2024 history with one seed to serve the API (`models_demo/MODEL_CARD.md`).
> **Demonstração, não é resultado da dissertação · provisório.**

**EN.** SHAP explains what *the model* does with its inputs, not why admissions happen: nothing here is causal.
Method: XGBoost's native TreeSHAP (`Booster.predict(DMatrix(X), pred_contribs=True)`), on the features built by
`models_demo.comum`. The objective is `count:poisson`, so contributions add up on the **log-margin** scale:
forecast = exp(base + Σ SHAP), and a contribution φ multiplies the forecast by exp(φ) (φ = 0.10 → ×1.105).

**PT.** O SHAP explica o que *o modelo* faz com as entradas, não por que as internações acontecem: nada aqui é causal.
Método: TreeSHAP nativo do XGBoost, sobre as features construídas por `models_demo.comum`. Com objetivo
`count:poisson`, as contribuições somam na **escala da margem (log)**: previsão = exp(base + Σ SHAP), e uma
contribuição φ multiplica a previsão por exp(φ) (φ = 0,10 → ×1,105).

This notebook only reads `models_demo/shap/`. Regenerate with / Para regenerar:
`uv run python -m models_demo.interpretabilidade`.
""")

py("""
import json
from pathlib import Path

import pandas as pd

PASTA = next(p / "models_demo" / "shap" for p in [Path.cwd(), *Path.cwd().parents] if (p / "models_demo").is_dir())
if not (PASTA / "manifest.json").exists():
    raise FileNotFoundError(f"{PASTA} has no manifest.json: run `uv run python -m models_demo.interpretabilidade`")
MAN = json.loads((PASTA / "manifest.json").read_text(encoding="utf-8"))
RESUMO = pd.read_csv(PASTA / "resumo_importancia.csv")
print("status:", MAN["status"])
print("model version / versão dos modelos:", MAN["versao_modelos"], "| generated / gerado em:", MAN["gerado_em"])
""")

md("""
## 1. Global importance / Importância global

**EN.** Mean |SHAP| over every target date of each horizon (log-margin units). Blue = lags of the target (AR),
grey = calendar of the target date (CAL). **PT.** Média do |SHAP| em todas as datas-alvo de cada horizonte (unidades da
margem log). Azul = defasagens do alvo (AR), cinza = calendário da data-alvo (CAL).
""")
py("""
top3 = RESUMO[RESUMO.posicao <= 3].pivot(index="posicao", columns="h", values="feature")
top3.columns = [f"h = {h}" for h in top3.columns]
top3
""")
for h in (1, 7, 30):
    figura(
        f"fig_importancia_h{h}",
        f"Global importance at h = {h}.",
        f"Importância global em h = {h}.",
    )

md("""
## 2. Every date, every feature (h = 1) / Cada data, cada feature (h = 1)
""")
figura(
    "fig_beeswarm_h1",
    "One point per target date and feature; colour = feature value (5th–95th percentile). Points right of zero raise "
    "the forecast.",
    "Um ponto por data-alvo e feature; cor = valor da feature (percentis 5–95). Pontos à direita do zero aumentam a "
    "previsão.",
)

md("""
## 3. Dependence (h = 1) / Dependência (h = 1)
""")
figura(
    "fig_dependencia_dow_h1",
    "Contribution of the day of the week of the target date. Weekends pull the forecast down on average.",
    "Contribuição do dia da semana da data-alvo. Em média, o fim de semana puxa a previsão para baixo.",
)
figura(
    "fig_dependencia_lag_h1",
    "Contribution of the most important lag against its value; orange = target date is a Saturday.",
    "Contribuição da defasagem mais importante contra o seu valor; laranja = data-alvo é sábado.",
)

md("""
## 4. Two forecasts explained (h = 1) / Duas previsões explicadas (h = 1)

**EN.** Rule, fixed before looking at the result: the 2024 Saturday with the highest h = 1 forecast (ties: earliest
date) and the Wednesday of the same week (Saturday − 3 days). These dates are in-sample (the demo model was trained on
them). **PT.** Regra fixada antes de ver o resultado: o sábado de 2024 com maior previsão para h = 1 (empate: a data mais
antiga) e a quarta-feira da mesma semana (sábado − 3 dias). As datas estão dentro da amostra de treino.

The Saturday spikes of the total target come from elective day-surgery batches in one establishment
(`docs/LESSONS.md`, story 1; aggregated panel in `notebooks/dados_painel/`). SHAP shows how this model reacts to
recent high counts and to the weekday; it does not explain the spikes. / Os picos de sábado do alvo total vêm de
mutirões de cirurgias eletivas em um estabelecimento; o SHAP mostra como este modelo reage às contagens recentes e ao
dia da semana, não explica os picos.
""")
py("""
sel = MAN["selecao_waterfall"]
print(sel["regra"])
pd.DataFrame({k: sel[k] for k in ("sabado", "quarta")}).T
""")
figura(
    "fig_waterfall_sabado_h1",
    "Waterfall of the selected Saturday: from the base (log of the base score) to the model margin; labels give φ and "
    "the multiplicative factor exp(φ).",
    "Cascata do sábado selecionado: da base (log do base score) até a margem do modelo; os rótulos dão φ e o fator "
    "multiplicativo exp(φ).",
)
figura(
    "fig_waterfall_quarta_h1",
    "Waterfall of the Wednesday of the same week.",
    "Cascata da quarta-feira da mesma semana.",
)

md("""
## 5. Provenance / Proveniência

**EN.** Each figure has a `.prov.json` (script, model file and sha256, input parquet sha256, parameters, environment).
The cell below checks that the model sha256 recorded in each `.prov.json` matches the file on disk.
**PT.** Cada figura tem um `.prov.json`; a célula abaixo confere o sha256 do modelo registrado em cada um.
""")
py("""
import hashlib

def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

raiz = PASTA.parents[1]
linhas = []
for prov in sorted(PASTA.glob("*.prov.json")):
    d = json.loads(prov.read_text(encoding="utf-8"))
    linhas.append({"figura": d["figura"], "modelo": d["modelo"]["arquivo"],
                   "sha256_ok": sha256(raiz / d["modelo"]["arquivo"]) == d["modelo"]["sha256"]})
pd.DataFrame(linhas)
""")

for i, c in enumerate(celulas):
    c["id"] = f"celula-{i:02d}"  # stable ids (nbformat 4.5)

nb = {
    "cells": celulas,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
(AQUI / "interpretabilidade_shap.ipynb").write_text(
    json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
)
print("ok")

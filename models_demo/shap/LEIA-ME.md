# SHAP dos modelos de demonstração (`models_demo/shap/`)

> **Demonstration, not a dissertation result · provisional.** Demonstração, não é resultado da dissertação;
> provisório. Os modelos explicados são os XGBoost `AR_CAL` de `models_demo/` (h = 1, 7, 30), treinados em todo o
> histórico 2019–2024 com uma semente para servir a API (`models_demo/MODEL_CARD.md`, versão `ba6d6c40-20261123`).

## O que é

Valores SHAP de cada feature em cada data-alvo, calculados com o **TreeSHAP nativo do XGBoost**
(`Booster.predict(DMatrix(X), pred_contribs=True)`), sobre as features construídas pelo mesmo caminho do treino e da
API (`models_demo.comum.construir_para` e `matriz`). Sem dependência nova. A biblioteca `shap` (0.51.0) instala com
as versões travadas, mas traz `numba` e `llvmlite` e não acrescenta nada ao cálculo exato do TreeSHAP do próprio
XGBoost.

## Escala da margem (log)

O objetivo é `count:poisson`: as árvores somam na escala log. Para cada data-alvo,
`margem = base + Σ SHAP` e `previsao = exp(margem)` internações/dia; `base = log(base_score)` é igual em todas as
linhas. Em contagem, cada contribuição é um fator multiplicativo: uma contribuição φ multiplica a previsão por
`exp(φ)` (φ = 0,10 → ×1,105). As cascatas (*waterfall*) mostram φ e `exp(φ)`; nenhuma figura converte a soma de SHAP
para contagem de forma aditiva.

## Arquivos

| Arquivo | Conteúdo |
|---|---|
| `shap_valores_h{h}.parquet` | uma linha por data-alvo (`data_alvo`); colunas das features (SHAP, margem log) + `base`, `margem`, `previsao` |
| `features_h{h}.parquet` | valores das features dados ao modelo (float32) + `alvo_observado` |
| `resumo_importancia.csv` | média do \|SHAP\| por feature e h (`posicao` 1 = mais importante) |
| `fig_importancia_h{1,7,30}`, `fig_beeswarm_h1`, `fig_dependencia_{dow,lag}_h1`, `fig_waterfall_{sabado,quarta}_h1` | PNG em inglês (`_en`) e português (`_pt`), cada um com `.prov.json` |
| `manifest.json` | sha256 de todas as saídas, modelos, entrada e regra de escolha das datas |

Gerar: `uv run python -m models_demo.interpretabilidade` (alguns segundos). Notebook que só lê estas saídas:
`notebooks/interpretabilidade_shap.ipynb` (gerado por `notebooks/gerar_notebook_shap.py`). Testes:
`uv run pytest tests/test_shap_demo.py`. As saídas são determinísticas para as mesmas entradas, exceto o carimbo
`gerado_em` dos JSON.

## Duas previsões explicadas (h = 1)

Regra fixa: o sábado de 2024 com a maior previsão para h = 1 (empate: a data mais antiga) e a quarta-feira da mesma
semana (sábado − 3 dias). As datas escolhidas estão em `manifest.json → selecao_waterfall`. São datas **dentro da
amostra** (o modelo de demonstração foi treinado com elas).

## Ligação com o caso do sábado — sem causalidade

No alvo total, os picos de sábado vêm de mutirões de cirurgias eletivas em um estabelecimento (`docs/LESSONS.md`,
história 1; painel agregado em `notebooks/dados_painel/`). O SHAP mostra como **este modelo** usa as contagens recentes
e o dia da semana para prever esses dias; ele explica o modelo, não o fenômeno, e não diz nada sobre causas das
internações nem sobre o efeito de qualquer variável ambiental (o conjunto `AR_CAL` não tem nenhuma).

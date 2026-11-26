"""Textos da interface em inglês e português (BR) e formatação numérica por idioma.

- `TEXTOS[chave] = {"en": ..., "pt": ...}`; nenhuma string de interface fica nas páginas.
- `t(chave, **fmt)` lê o idioma corrente (`st.session_state["lang"]`, padrão "en") e aplica `str.format`.
- `fmt_num(x, casas)` usa vírgula decimal e ponto de milhar em português.
- Nomes de modelos, de colunas, de arquivos e ids de runs não se traduzem.
"""

from __future__ import annotations

import streamlit as st

IDIOMAS = {"en": "English", "pt": "Português (BR)"}
PADRAO = "en"

TEXTOS: dict[str, dict[str, object]] = {
    # --- comum ---------------------------------------------------------------------------------
    "app.curto": {"en": "SP respiratory admissions", "pt": "Internações respiratórias SP"},
    "ui.idioma": {"en": "Language / Idioma", "pt": "Language / Idioma"},
    "ui.provisorio": {"en": "provisional (pre-defense)", "pt": "provisório (pré-defesa)"},
    "ui.aviso": {
        "en": "**All results on this page are provisional (pre-defense).** Every number is read from an aggregated "
        "artifact in this repository and labelled with its file path and the full id of the run that produced it. "
        "Nothing here is a final result of the dissertation.",
        "pt": "**Todos os resultados desta página são provisórios (pré-defesa).** Cada número é lido de um artefato "
        "agregado deste repositório e acompanhado do caminho do arquivo e do id completo da run que o produziu. "
        "Nada aqui é resultado final da dissertação.",
    },
    "ui.fonte": {"en": "Source:", "pt": "Fonte:"},
    "ui.run": {"en": "run", "pt": "run"},
    "alvo.total": {"en": "Total (all admissions)", "pt": "Total (todas as internações)"},
    "alvo.urgencia": {"en": "Urgent (non-elective only)", "pt": "Urgência (só não eletivas)"},
    "alvo.rotulo": {"en": "Target", "pt": "Alvo"},
    "alvo.curto.total": {"en": "total", "pt": "total"},
    "alvo.curto.urgencia": {"en": "urgent", "pt": "urgência"},
    "serie.total": {"en": "Total (current target)", "pt": "Total (alvo atual)"},
    "serie.nao_eletivo": {"en": "Non-elective (urgent target)", "pt": "Não eletivo (alvo de urgência)"},
    "serie.eletivo": {"en": "Elective", "pt": "Eletivo"},
    "serie.cema": {"en": "CNES 2091550", "pt": "CNES 2091550"},
    "horizonte": {"en": "Horizon", "pt": "Horizonte"},
    "metrica": {"en": "Metric", "pt": "Métrica"},
    "dow": {
        "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "pt": ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
    },
    "meses": {
        "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
    },
    "unid.internacoes": {"en": "admissions", "pt": "internações"},
    "unid.internacoes_dia": {"en": "Admissions / day", "pt": "Internações / dia"},
    "unid.adm_dia_curto": {"en": "Adm./day", "pt": "Int./dia"},
    # --- Home ---------------------------------------------------------------------------------
    "home.titulo_aba": {"en": "Home", "pt": "Início"},
    "home.titulo": {
        "en": "Respiratory admissions in São Paulo — 1 to 30 days ahead",
        "pt": "Internações respiratórias em São Paulo — 1 a 30 dias à frente",
    },
    "home.intro": {
        "en": "Daily forecasting of respiratory hospital admissions (ICD-10 J00–J99) of residents of São Paulo city, "
        "2019–2024, with **seven models** (Naïve, Seasonal Naïve m = 7, XGBoost, LSTM, SARIMAX, GAM-NB, INGARCH-NB) "
        "evaluated under **one protocol**: 4 rolling-origin folds × 180 test days, 5 seeds for the stochastic models, "
        "Diebold–Mariano tests with Holm correction. Two targets: **total** admissions and **urgent** (non-elective) "
        "admissions. Environmental covariates come from CETESB/QUALAR (PM2.5, other pollutants, meteorology).",
        "pt": "Previsão diária de internações hospitalares respiratórias (CID-10 J00–J99) de residentes do município de "
        "São Paulo, 2019–2024, com **sete modelos** (Naïve, Seasonal Naïve m = 7, XGBoost, LSTM, SARIMAX, GAM-NB, "
        "INGARCH-NB) avaliados sob **um só protocolo**: 4 folds de origem rolante × 180 dias de teste, 5 sementes para "
        "os modelos estocásticos, teste pareado de Diebold–Mariano com correção de Holm. Dois alvos: o **alvo total** "
        "e o **alvo de urgência** (só internações não eletivas). As covariáveis ambientais vêm da CETESB/QUALAR "
        "(PM2,5, outros poluentes, meteorologia).",
    },
    "home.kpi_dias": {"en": "Days in the series", "pt": "Dias na série"},
    "home.kpi_aih_total": {"en": "Distinct AIH (total target)", "pt": "AIH distintas (alvo total)"},
    "home.kpi_aih_urg": {"en": "Distinct AIH (urgent target)", "pt": "AIH distintas (alvo de urgência)"},
    "home.kpi_melhor": {"en": "Best MAE, h = 1 ({modelo})", "pt": "Melhor MAE, h = 1 ({modelo})"},
    "home.paginas": {"en": "Pages", "pt": "Páginas"},
    "home.link_overview": {
        "en": "Overview — target series, fold test windows and PM2.5",
        "pt": "Visão geral — série do alvo, janelas de teste dos folds e PM2,5",
    },
    "home.link_modelos": {
        "en": "Models by horizon — MAE, MASE, skill, ablation and DM tests",
        "pt": "Modelos por horizonte — MAE, MASE, skill, ablação e testes DM",
    },
    "home.link_sabado": {
        "en": "The Saturday case — why the urgent target exists",
        "pt": "O caso do sábado — por que existe o alvo de urgência",
    },
    "home.link_dados": {
        "en": "Data and limitations — sources, rules, what is not here",
        "pt": "Dados e limitações — fontes, regras, o que não está aqui",
    },
    "home.runs": {"en": "Runs behind the numbers", "pt": "Runs por trás dos números"},
    "home.col_target": {"en": "target", "pt": "alvo"},
    "home.como_ler": {
        "en": "**How to read the metrics.** MASE divides a model's MAE by the Naïve MAE *of the same horizon*, so it "
        "compares models **within** one h only. Across horizons use MAE and *skill vs. reference* "
        "(1 − MAE / min(MAE Naïve, MAE Seasonal Naïve)).",
        "pt": "**Como ler as métricas.** O MASE divide o MAE do modelo pelo MAE do Naïve *do mesmo horizonte*; por isso "
        "compara modelos só **dentro** de um mesmo h. Entre horizontes use o MAE e o *skill contra a referência* "
        "(1 − MAE / min(MAE Naïve, MAE Seasonal Naïve)).",
    },
    # --- Overview -----------------------------------------------------------------------------
    "ov.titulo_aba": {"en": "Overview", "pt": "Visão geral"},
    "ov.titulo": {
        "en": "Overview — the target series and the test windows",
        "pt": "Visão geral — a série do alvo e as janelas de teste",
    },
    "ov.kpi_dias": {"en": "Days", "pt": "Dias"},
    "ov.kpi_aih": {"en": "Distinct AIH (2019–2024)", "pt": "AIH distintas (2019–2024)"},
    "ov.kpi_media": {"en": "Mean admissions / day", "pt": "Média de internações / dia"},
    "ov.kpi_zero": {"en": "Days with zero admissions", "pt": "Dias com zero internações"},
    "ov.nota_media": {"en": "mean computed from the parquet series", "pt": "média calculada da série do parquet"},
    "ov.sub_serie": {
        "en": "Daily admissions and the four fold test windows",
        "pt": "Internações diárias e as janelas de teste dos quatro folds",
    },
    "ov.hover_serie": {"en": "%{y} admissions", "pt": "%{y} internações"},
    "ov.nota_folds": {
        "en": "shaded = test window of each fold (same dates in every run)",
        "pt": "sombreado = janela de teste de cada fold (mesmas datas em toda run)",
    },
    "ov.exp_folds": {
        "en": "Fold table (training / validation / test dates)",
        "pt": "Tabela de folds (datas de treino / validação / teste)",
    },
    "ov.sub_anual": {"en": "Admissions per year", "pt": "Internações por ano"},
    "ov.eixo_anual": {"en": "Admissions / year", "pt": "Internações / ano"},
    "ov.hover_anual": {"en": "%{x}: %{y:,} admissions", "pt": "%{x}: %{y:,} internações"},
    "ov.nota_anual": {"en": "field `totais_anuais`", "pt": "campo `totais_anuais`"},
    "ov.sub_pm25": {
        "en": "PM2.5 — daily mean over CETESB stations in São Paulo city",
        "pt": "PM2,5 — média diária das estações da CETESB no município de São Paulo",
    },
    "ov.serie_pm25": {"en": "PM2.5 daily mean (µg/m³)", "pt": "Média diária de PM2,5 (µg/m³)"},
    "ov.hover_pm25": {"en": "%{y:.1f} µg/m³ · %{customdata} stations", "pt": "%{y:.1f} µg/m³ · %{customdata} estações"},
    "ov.eixo_pm25": {"en": "PM2.5 (µg/m³)", "pt": "PM2,5 (µg/m³)"},
    "ov.nota_regra": {"en": "daily rule: {regra}", "pt": "regra diária: {regra}"},
    "ov.kpi_pm25": {"en": "Mean PM2.5 (µg/m³)", "pt": "PM2,5 médio (µg/m³)"},
    "ov.kpi_estacoes": {"en": "Mean stations / day", "pt": "Estações / dia (média)"},
    "ov.kpi_sem_estacao": {"en": "Days without a valid station", "pt": "Dias sem estação válida"},
    "ov.nota_pm25": {
        "en": "computed from the csv columns pm25_media and pm25_n_estacoes",
        "pt": "calculado das colunas pm25_media e pm25_n_estacoes do csv",
    },
    "ov.exp_alvo": {
        "en": "How the target series is built (from the .meta.json next to the parquet)",
        "pt": "Como a série do alvo é construída (do .meta.json ao lado do parquet)",
    },
    "ov.exp_pm25": {
        "en": "How the PM2.5 series is built (from cetesb_poluentes_daily.meta.json)",
        "pt": "Como a série de PM2,5 é construída (de cetesb_poluentes_daily.meta.json)",
    },
    # --- Models by horizon --------------------------------------------------------------------
    "mh.titulo_aba": {"en": "Models by horizon", "pt": "Modelos por horizonte"},
    "mh.titulo": {"en": "Models by horizon", "pt": "Modelos por horizonte"},
    "mh.intro": {
        "en": "All models use the common feature set **AR_CAL** (autoregressive lags + calendar) unless stated "
        "otherwise. **MASE only compares models within the same horizon** (it uses the Naïve of that h); across "
        "horizons read **MAE** and **skill vs. reference** = 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve).",
        "pt": "Todos os modelos usam o conjunto de features comum **AR_CAL** (lags autorregressivos + calendário), "
        "salvo indicação. **O MASE só compara modelos dentro do mesmo horizonte** (usa o Naïve daquele h); entre "
        "horizontes leia o **MAE** e o **skill contra a referência** = 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve).",
    },
    "mh.nota_skill_total": {
        "en": "skill_vs_ref read from A_modelos_por_h.csv",
        "pt": "skill_vs_ref lido de A_modelos_por_h.csv",
    },
    "mh.nota_skill_urg": {
        "en": "skill computed as 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve) of the same h, from the csv",
        "pt": "skill calculado como 1 − MAE / min(MAE Naïve, MAE Seasonal Naïve) do mesmo h, a partir do csv",
    },
    "mh.sub_mae": {"en": "MAE by horizon (AR_CAL)", "pt": "MAE por horizonte (AR_CAL)"},
    "mh.eixo_mae": {"en": "MAE (admissions / day)", "pt": "MAE (internações / dia)"},
    "mh.nota_runs": {"en": "runs: {lista}", "pt": "runs: {lista}"},
    "mh.sub_skill": {"en": "Skill vs. reference by horizon", "pt": "Skill contra a referência por horizonte"},
    "mh.eixo_skill": {
        "en": "1 − MAE / MAE(best naïve of the same h)",
        "pt": "1 − MAE / MAE(melhor naïve do mesmo h)",
    },
    "mh.sub_mase": {"en": "MASE within one horizon", "pt": "MASE dentro de um horizonte"},
    "mh.hover_mase": {"en": "MASE %{x:.3f} · MAE %{customdata:.2f}", "pt": "MASE %{x:.3f} · MAE %{customdata:.2f}"},
    "mh.eixo_mase": {
        "en": "MASE at h = {h} (MAE / MAE Naïve of h = {h})",
        "pt": "MASE em h = {h} (MAE / MAE Naïve de h = {h})",
    },
    "mh.exp_tabela": {
        "en": "Table — MAE, MASE, skill and reference MAEs for every h and model",
        "pt": "Tabela — MAE, MASE, skill e MAEs de referência para cada h e modelo",
    },
    "mh.nota_dp": {
        "en": "dp_fold / dp_sem = std of MAE across folds / seeds (total target only)",
        "pt": "dp_fold / dp_sem = desvio-padrão do MAE entre folds / sementes (só alvo total)",
    },
    "mh.sub_ablacao": {
        "en": "Feature-set ablation (all feature sets of one run)",
        "pt": "Ablação por conjunto de features (todos os conjuntos de uma run)",
    },
    "mh.blocos": {
        "en": "Blocks: `AR` lags of the target · `CAL` calendar · `METEO` meteorology · `PM25` PM2.5 (mean, station "
        "count, spatial dispersion) · `PM25MEDIA` PM2.5 mean only · `POLUENTES` PM10, NO2, O3, CO · `COMPLETO` all "
        "blocks. `baseline` is the feature set of the naïve models.",
        "pt": "Blocos: `AR` lags do alvo · `CAL` calendário · `METEO` meteorologia · `PM25` PM2,5 (média, nº de "
        "estações, dispersão espacial) · `PM25MEDIA` só a média de PM2,5 · `POLUENTES` PM10, NO2, O3, CO · "
        "`COMPLETO` todos os blocos. `baseline` é o conjunto dos modelos naïve.",
    },
    "mh.horizonte_ablacao": {"en": "Horizon (ablation)", "pt": "Horizonte (ablação)"},
    "mh.nota_ablacao": {
        "en": "mean over 4 folds (and 5 seeds for XGBoost/LSTM); empty cell = model not run on that set; "
        "baselines (feature set `baseline`): {baselines}",
        "pt": "média de 4 folds (e 5 sementes para XGBoost/LSTM); célula vazia = modelo não executado naquele "
        "conjunto; baselines (conjunto `baseline`): {baselines}",
    },
    "mh.exp_mc": {
        "en": "Table — model_comparison.csv of this run",
        "pt": "Tabela — model_comparison.csv desta run",
    },
    "mh.sub_dm": {
        "en": "Which pairs of models are distinguishable? (Diebold–Mariano, Holm)",
        "pt": "Quais pares de modelos se distinguem? (Diebold–Mariano, Holm)",
    },
    "mh.dm_intro": {
        "en": "Loss = absolute error per target date (seed mean for XGBoost and LSTM), feature set AR_CAL, grouped "
        "over the four folds (T = 720), Newey–West long-run variance, Harvey–Leybourne–Newbold correction, Holm "
        "within the family of 21 contrasts. **DM < 0 favours A.** A pair is *distinguishable* when Holm-adjusted "
        "p < 0.05.",
        "pt": "Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM), conjunto de features "
        "AR_CAL, agrupado nos quatro folds (T = 720), variância de longo prazo de Newey–West, correção de "
        "Harvey–Leybourne–Newbold, Holm dentro da família de 21 contrastes. **DM < 0 favorece A.** Um par é "
        "*distinguível* quando o p ajustado por Holm é < 0,05.",
    },
    "mh.horizonte_dm": {"en": "Horizon (DM)", "pt": "Horizonte (DM)"},
    "mh.hover_dm": {"en": "%{y} vs %{x}: Holm p = %{z:.3f}", "pt": "%{y} vs %{x}: p de Holm = %{z:.3f}"},
    "mh.colorbar_dm": {"en": "Holm p", "pt": "p de Holm"},
    "mh.nota_dm": {
        "en": "family modelos_AR_CAL, grouped scope (T = 720)",
        "pt": "família modelos_AR_CAL, escopo agrupado (T = 720)",
    },
    "mh.dm_nenhum": {
        "en": "h = {h}: no pair among the five models is distinguishable after Holm.",
        "pt": "h = {h}: nenhum par entre os cinco modelos se distingue após Holm.",
    },
    "mh.dm_alguns": {
        "en": "h = {h}: {n} of {total} pairs among the five models are distinguishable after Holm — {lista}.",
        "pt": "h = {h}: {n} de {total} pares entre os cinco modelos se distinguem após Holm — {lista}.",
    },
    "mh.dm_par": {
        "en": "{a} vs {b} (favours {fav}, Holm p = {p})",
        "pt": "{a} vs {b} (favorece {fav}, p de Holm = {p})",
    },
    "mh.exp_contrastes": {
        "en": "Table — the 21 grouped contrasts of this run",
        "pt": "Tabela — os 21 contrastes agrupados desta run",
    },
    "mh.col_dmedio": {"en": "mean loss diff (A − B)", "pt": "dif. média de perda (A − B)"},
    "mh.col_distinguivel": {"en": "distinguishable (Holm)", "pt": "distinguível (Holm)"},
    "mh.col_favorece": {"en": "favours", "pt": "favorece"},
    "mh.exp_relatorio": {
        "en": "Full DM report of this run (RELATORIO_DM.md, in Portuguese)",
        "pt": "Relatório DM completo desta run (RELATORIO_DM.md)",
    },
    "mh.sub_resumo": {"en": "DM summary across horizons", "pt": "Resumo DM por horizonte"},
    "mh.col_lider": {"en": "nominal leader", "pt": "líder nominal"},
    "mh.col_contrastes": {"en": "contrasts", "pt": "contrastes"},
    "mh.col_sig_todos": {"en": "sig. after Holm (all)", "pt": "sig. após Holm (todos)"},
    "mh.col_sig_modelos": {"en": "sig. among the 5 models", "pt": "sig. entre os 5 modelos"},
    "mh.col_pares": {"en": "which pairs", "pt": "quais pares"},
    # --- Saturday case ------------------------------------------------------------------------
    "sab.titulo_aba": {"en": "The Saturday case", "pt": "O caso do sábado"},
    "sab.titulo": {"en": "The Saturday case", "pt": "O caso do sábado"},
    "sab.intro": {
        "en": "Since 2022 the daily count of respiratory admissions shows **Saturday spikes** that no environmental or "
        "epidemiological signal explains. They are **elective surgery campaigns** (almost all in ICD-10 group "
        "J30–J39, other diseases of the upper respiratory tract) concentrated in one establishment, "
        "**CNES 2091550 (Instituto CEMA)**. The admission "
        "character recorded in the AIH (`CAR_INT`) separates them cleanly, which is why a second target — "
        "**urgent = non-elective** — exists. Descriptive reading, no formal test. For 2025–2026 the target has not "
        "yet been checked against TabNet.",
        "pt": "Desde 2022 a contagem diária de internações respiratórias mostra **picos aos sábados** que nenhum sinal "
        "ambiental ou epidemiológico explica. São **mutirões de cirurgia eletiva** (quase todos no grupo J30–J39 da "
        "CID-10, outras doenças das vias aéreas superiores) concentrados em um estabelecimento, o "
        "**CNES 2091550 (Instituto CEMA)**. O caráter "
        "da internação registrado na AIH (`CAR_INT`) os separa com clareza, e por isso existe um segundo alvo — o "
        "**alvo de urgência = não eletivo**. Leitura descritiva, sem teste formal. Em 2025–2026 o alvo ainda não foi "
        "conferido contra o TabNet.",
    },
    "sab.h1": {"en": "1. Three series in one target", "pt": "1. Três séries em um alvo"},
    "sab.kpi_total": {"en": "Admissions (Jan 2019 – Feb 2026)", "pt": "Internações (jan/2019 – fev/2026)"},
    "sab.kpi_media": {"en": "Mean per day", "pt": "Média por dia"},
    "sab.kpi_eletivas": {"en": "Elective share of the total target", "pt": "Parcela eletiva do alvo total"},
    "sab.kpi_atipicos": {"en": "Atypical Saturdays since 2022", "pt": "Sábados atípicos desde 2022"},
    "sab.nota_atipicos": {
        "en": "atypical = 30% or more above the local level (centred 29-day rolling median); total target → urgent target",
        "pt": "atípico = 30% ou mais acima do nível local (mediana móvel centrada de 29 dias); alvo total → alvo de urgência",
    },
    "sab.fig_semanal": {"en": "Weekly mean of admissions per day", "pt": "Média semanal de internações por dia"},
    "sab.nota_painel": {"en": "panel generated {quando}", "pt": "painel gerado em {quando}"},
    "sab.h2": {"en": "2. Day of the week", "pt": "2. Dia da semana"},
    "sab.hover_dow": {"en": "%{y} · %{x}: %{z:.1f} admissions/day", "pt": "%{y} · %{x}: %{z:.1f} internações/dia"},
    "sab.fig_dow": {
        "en": "Mean admissions per day, by weekday and year (total target)",
        "pt": "Média de internações por dia, por dia da semana e ano (alvo total)",
    },
    "sab.periodo": {"en": "Period", "pt": "Período"},
    "sab.per_2022": {"en": "2022–Feb 2026", "pt": "2022–fev/2026"},
    "sab.per_2019": {"en": "2019–2021", "pt": "2019–2021"},
    "sab.per_tudo": {"en": "All", "pt": "Tudo"},
    "sab.hover_iqr": {
        "en": "IQR %{y:.3f} · %{customdata} days ≥ 30% above",
        "pt": "IIQ %{y:.3f} · %{customdata} dias ≥ 30% acima",
    },
    "sab.fig_iqr": {
        "en": "How much each weekday oscillates around the local level ({periodo})",
        "pt": "Quanto cada dia da semana oscila em torno do nível local ({periodo})",
    },
    "sab.eixo_iqr": {
        "en": "Interquartile range of y / local level",
        "pt": "Intervalo interquartil de y / nível local",
    },
    "sab.nota_iqr": {
        "en": "ratio = y / centred 29-day rolling median; computed from diario.csv",
        "pt": "razão = y / mediana móvel centrada de 29 dias; calculada de diario.csv",
    },
    "sab.h3": {"en": "3. Saturdays and CNES 2091550", "pt": "3. Os sábados e o CNES 2091550"},
    "sab.sem_cema": {"en": "Without CNES 2091550", "pt": "Sem o CNES 2091550"},
    "sab.todos_estab": {"en": "All establishments", "pt": "Todos os estabelecimentos"},
    "sab.fig_cema": {
        "en": "Admissions on each Saturday (shaded = CNES 2091550)",
        "pt": "Internações em cada sábado (área sombreada = CNES 2091550)",
    },
    "sab.eixo_sabado": {"en": "Admissions per Saturday", "pt": "Internações por sábado"},
    "sab.nota_cema": {
        "en": "highlighted establishment: CNES {cnes} (manifest.json)",
        "pt": "estabelecimento destacado: CNES {cnes} (manifest.json)",
    },
    "sab.ord1": {"en": "1st Saturday", "pt": "1º sábado"},
    "sab.ord2": {"en": "2nd Saturday", "pt": "2º sábado"},
    "sab.ord3": {"en": "3rd Saturday", "pt": "3º sábado"},
    "sab.ord4": {"en": "4th Saturday", "pt": "4º sábado"},
    "sab.ord5": {"en": "5th Saturday", "pt": "5º sábado"},
    "sab.hover_razao": {"en": "median ratio %{y:.2f}", "pt": "razão mediana %{y:.2f}"},
    "sab.fig_semana_mes": {
        "en": "The peak falls on the first three Saturdays of the month (since 2022)",
        "pt": "O pico cai nos três primeiros sábados do mês (desde 2022)",
    },
    "sab.eixo_razao": {"en": "Median ratio (1 = ordinary day)", "pt": "Razão mediana (1 = dia comum)"},
    "sab.nota_razao": {
        "en": "median of y / local level over the Saturdays of each rank within the month",
        "pt": "mediana de y / nível local nos sábados de cada posição dentro do mês",
    },
    "sab.colorbar_int": {"en": "Admissions", "pt": "Internações"},
    "sab.hover_cal": {"en": "%{y} · %{x}: %{z} admissions", "pt": "%{y} · %{x}: %{z} internações"},
    "sab.fig_cal": {
        "en": "Calendar: admissions of CNES 2091550 on each Saturday (month–rank of the Saturday)",
        "pt": "Calendário: internações do CNES 2091550 em cada sábado (mês–posição do sábado)",
    },
    "sab.nota_cal": {
        "en": "column `cema` = admissions of CNES 2091550",
        "pt": "coluna `cema` = internações do CNES 2091550",
    },
    "sab.atraso": {
        "en": "**Registration delay since 2022** — % of AIH by months between admission and the billing competence "
        "(4 = four or more). Saturday is not registered later than the other days:",
        "pt": "**Atraso de registro desde 2022** — % das AIH por meses entre a internação e a competência "
        "(4 = quatro ou mais). O sábado não é registrado mais tarde que os outros dias:",
    },
    "sab.col_meses": {"en": "{k} month(s)", "pt": "{k} mês(es)"},
    "sab.h4": {
        "en": "4. Admission character and ICD-10 groups",
        "pt": "4. Caráter da internação e grupos de CID-10",
    },
    "sab.mecanismo": {
        "en": "Plausible mechanism of pollution effect",
        "pt": "Mecanismo plausível de efeito da poluição",
    },
    "sab.outros_grupos": {"en": "Other groups", "pt": "Demais grupos"},
    "sab.hover_cid": {
        "en": "%{x:.1f}% elective · %{customdata[0]:,} of %{customdata[1]:,} · %{customdata[2]:,} elective at CNES 2091550",
        "pt": "%{x:.1f}% eletivo · %{customdata[0]:,} de %{customdata[1]:,} · %{customdata[2]:,} eletivas no CNES 2091550",
    },
    "sab.fig_cid": {
        "en": "What the urgent target excludes, by ICD-10 group (% elective in the group)",
        "pt": "O que o alvo de urgência exclui, por grupo de CID-10 (% eletivo no grupo)",
    },
    "sab.eixo_cid": {
        "en": "% elective in the group (leaves the urgent target)",
        "pt": "% eletivo no grupo (sai do alvo de urgência)",
    },
    "sab.texto_sensiveis": {
        "en": "Groups with a plausible pollution mechanism: **{eletivas}** elective admissions out of **{total}** "
        "({pct}%); **{cema}** of them at CNES 2091550.",
        "pt": "Grupos com mecanismo plausível de efeito da poluição: **{eletivas}** internações eletivas de "
        "**{total}** ({pct}%); **{cema}** delas no CNES 2091550.",
    },
    "sab.sub_nao_eletivas": {
        "en": "Non-elective (stay in the urgent target)",
        "pt": "Não eletivas (ficam no alvo de urgência)",
    },
    "sab.sub_eletivas": {"en": "Elective (leave the target)", "pt": "Eletivas (saem do alvo)"},
    "sab.nao_eletivas": {"en": "Non-elective", "pt": "Não eletivas"},
    "sab.eletivas": {"en": "Elective", "pt": "Eletivas"},
    "sab.fig_sens": {
        "en": "Pollution-sensitive groups: monthly mean per day (correlation 2019–2024: {corr})",
        "pt": "Grupos sensíveis à poluição: média diária por mês (correlação 2019–2024: {corr})",
    },
    "sab.nota_sens": {
        "en": "columns sens_nao_eletivo and sens_eletivo; correlation computed from the monthly means",
        "pt": "colunas sens_nao_eletivo e sens_eletivo; correlação calculada das médias mensais",
    },
    "sab.perfil": {
        "en": "**Profile of the two subsets** (age in years, length of stay in days):",
        "pt": "**Perfil dos dois recortes** (idade em anos, permanência em dias):",
    },
    "sab.col_internacoes": {"en": "admissions", "pt": "internações"},
    "sab.col_idade": {"en": "median age", "pt": "idade mediana"},
    "sab.col_menor15": {"en": "% under 15", "pt": "% < 15 anos"},
    "sab.col_permanencia": {"en": "median stay", "pt": "permanência mediana"},
    "sab.col_perm1": {"en": "% stay ≤ 1 day", "pt": "% permanência ≤ 1 dia"},
    "sab.col_obito": {"en": "% death", "pt": "% óbito"},
    "sab.h5": {
        "en": "5. Establishments with most elective admissions on Saturdays",
        "pt": "5. Estabelecimentos com mais internações eletivas aos sábados",
    },
    "sab.met_eletivas_sab": {"en": "Elective on Saturdays", "pt": "Eletivas aos sábados"},
    "sab.met_eletivas": {"en": "Elective (all days)", "pt": "Eletivas (todos os dias)"},
    "sab.met_total": {"en": "Total", "pt": "Total"},
    "sab.fig_estab": {
        "en": "{metrica} per year — 15 establishments with most elective Saturday admissions (highlight: CNES {cnes})",
        "pt": "{metrica} por ano — 15 estabelecimentos com mais eletivas aos sábados (destaque: CNES {cnes})",
    },
    "sab.eixo_estab": {"en": "{metrica} / year", "pt": "{metrica} / ano"},
    "sab.nota_estab": {
        "en": "cells with fewer than 5 admissions are suppressed at the source (gaps in the lines); the highlighted "
        "establishment is {nome}, name read from the column `nome` of this csv; the other establishments appear by "
        "code only, as in the csv; name and code are public information of the CNES registry",
        "pt": "células com menos de 5 internações são suprimidas na origem (lacunas nas linhas); o estabelecimento "
        "destacado é {nome}, nome lido da coluna `nome` deste csv; os demais aparecem só pelo código, como no csv; "
        "nome e código são informação pública do cadastro CNES",
    },
    "sab.h6": {
        "en": "6. Effect on the models (common set AR_CAL, CETESB base)",
        "pt": "6. Efeito nos modelos (conjunto comum AR_CAL, base CETESB)",
    },
    "sab.met_mae": {"en": "MAE", "pt": "MAE"},
    "sab.met_vies": {"en": "Bias", "pt": "Viés"},
    "sab.eixo_vies": {"en": "Bias (observed − predicted)", "pt": "Viés (observado − previsto)"},
    "sab.fig_modelos": {"en": "{metrica} by weekday — h = {h}", "pt": "{metrica} por dia da semana — h = {h}"},
    "sab.nota_modelos": {
        "en": "seed-mean predictions per target date, total target",
        "pt": "previsões médias das sementes por data-alvo, alvo total",
    },
    "sab.nota_mae_def": {
        "en": "Note on the MAE definition: in this section (chart and table below) MAE is computed on **seed-mean "
        "predictions** (one prediction per date, from erros_modelos_ar_cal.csv), so it is at most the **seed-mean "
        "MAE** reported in the README, in arcal_por_horizonte_dois_alvos.csv and in erro_sabado_h1.csv (mean of the "
        "MAE of each seed; {ref_geral} overall and {ref_sab} on Saturdays at h = 1 for XGBoost, against {aqui_geral} "
        "and {aqui_sab} here).",
        "pt": "Nota sobre a definição do MAE: nesta seção (gráfico e tabela abaixo) o MAE é calculado sobre as "
        "**previsões médias das sementes** (uma previsão por data, de erros_modelos_ar_cal.csv), e por isso é no "
        "máximo o **MAE médio das sementes** relatado no README, em arcal_por_horizonte_dois_alvos.csv e em "
        "erro_sabado_h1.csv (média do MAE de cada semente; {ref_geral} no geral e {ref_sab} aos sábados em h = 1 "
        "para o XGBoost, contra {aqui_geral} e {aqui_sab} aqui).",
    },
    "sab.col_mae_fora": {"en": "MAE outside campaign Saturdays", "pt": "MAE fora dos sábados de mutirão"},
    "sab.col_pct_erro": {
        "en": "% of absolute error on campaign Saturdays",
        "pt": "% do erro absoluto nos sábados de mutirão",
    },
    "sab.col_pct_datas": {"en": "% of dates", "pt": "% das datas"},
    "sab.quanto_erro": {
        "en": "**How much of the error comes from the 1st–3rd Saturday of the month (2022+)**, total target:",
        "pt": "**Quanto do erro vem do 1º–3º sábado do mês (2022+)**, alvo total:",
    },
    "sab.erro_h1": {
        "en": "**Saturday error at h = 1, both targets** — MAE on Saturdays vs. the other days, share of the absolute "
        "error on Saturdays and the ratio MAE_sat / MAE_other:",
        "pt": "**Erro de sábado em h = 1, nos dois alvos** — MAE aos sábados contra os demais dias, parcela do erro "
        "absoluto aos sábados e a razão MAE_sáb / MAE_demais:",
    },
    "sab.col_alvo": {"en": "target", "pt": "alvo"},
    "sab.col_modelo": {"en": "model", "pt": "modelo"},
    "sab.col_mae_sab": {"en": "MAE Saturdays", "pt": "MAE sábados"},
    "sab.col_mae_demais": {"en": "MAE other days", "pt": "MAE demais dias"},
    "sab.col_frac": {"en": "share of abs. error on Saturdays", "pt": "parcela do erro abs. aos sábados"},
    "sab.col_razao": {"en": "ratio", "pt": "razão"},
    "sab.nota_erro_h1": {
        "en": "runs: total `{total}`; urgent `{urgencia}`",
        "pt": "runs: alvo total `{total}`; alvo de urgência `{urgencia}`",
    },
    "sab.h7": {
        "en": "7. The decision under discussion (PROTOCOLO §0.23, proposed)",
        "pt": "7. A decisão em discussão (PROTOCOLO §0.23, [PROPOSTO])",
    },
    "sab.decisao": {
        "en": "- **Non-elective (urgent) target** for the PM2.5 question: the criterion is the admission character "
        "recorded in the AIH, applied equally to every day, hospital and ICD code, without excluding any "
        "establishment.\n"
        "- **Total target** stays for hospital-demand forecasting (a bed occupied by an elective admission still "
        "counts).\n"
        "- What leaves: mostly scheduled upper-airway surgery (J30–J39). In the groups with a plausible pollution "
        "mechanism the elective share is small (section 4) and does not follow the seasonality.\n"
        "- Open point for the advisor: which of the two targets is the main outcome of the dissertation.",
        "pt": "- **Alvo de urgência (não eletivo)** para a pergunta do PM2,5: o critério é o caráter da internação "
        "registrado na AIH, igual para todos os dias, hospitais e CID, sem excluir estabelecimento.\n"
        "- **Alvo total** continua para a previsão de demanda hospitalar (leito ocupado por eletiva também conta).\n"
        "- O que sai: sobretudo cirurgias programadas das vias aéreas superiores (J30–J39). Nos grupos com mecanismo "
        "plausível de efeito da poluição, a parcela eletiva é pequena (seção 4) e não acompanha a sazonalidade.\n"
        "- Ponto para o orientador: qual dos dois alvos é o desfecho principal da dissertação.",
    },
    "sab.exp_manifest": {
        "en": "Provenance of the panel data (manifest.json)",
        "pt": "Proveniência dos dados do painel (manifest.json)",
    },
    # --- Data and limitations -----------------------------------------------------------------
    "dl.titulo_aba": {"en": "Data and limitations", "pt": "Dados e limitações"},
    "dl.titulo": {"en": "Data and limitations", "pt": "Dados e limitações"},
    "dl.h_fontes": {"en": "Sources", "pt": "Fontes"},
    "dl.fontes": {
        "en": "- **Target — SIH/SUS, AIH-RD (DATASUS).** Hospital admission records of the Brazilian public health "
        "system, downloaded as public microdata (FTP of DATASUS) and aggregated to one count per day. Only the daily "
        "aggregates are in this repository.\n"
        "- **Environmental covariates — CETESB/QUALAR** (main source): PM2.5, PM10, NO2, O3, CO and meteorology from "
        "the monitoring stations inside São Paulo city, aggregated per day.\n"
        "- **CAMS (Copernicus)** — alternative source used only for sensitivity analysis in the dissertation; the "
        "daily file is in `data/processed/cams_daily_v2.csv` with the Copernicus licence.",
        "pt": "- **Alvo — SIH/SUS, AIH-RD (DATASUS).** Registros de internação hospitalar do SUS, baixados como "
        "microdados públicos (FTP do DATASUS) e agregados em uma contagem por dia. Só os agregados diários estão "
        "neste repositório.\n"
        "- **Covariáveis ambientais — CETESB/QUALAR** (fonte principal): PM2,5, PM10, NO2, O3, CO e meteorologia "
        "das estações de monitoramento dentro do município de São Paulo, agregadas por dia.\n"
        "- **CAMS (Copernicus)** — fonte alternativa usada só em análise de sensibilidade na dissertação; o arquivo "
        "diário está em `data/processed/cams_daily_v2.csv`, sob a licença Copernicus.",
    },
    "dl.h_alvo": {"en": "How the target is built", "pt": "Como o alvo é construído"},
    "dl.alvo": {
        "en": "- One count per day of **distinct AIH** (`N_AIH`), residents of São Paulo city (`{espacial}`), main "
        "diagnosis in chapter J (`{cid}`), dated by `{campo_data}`.\n"
        "- **Look-ahead of {lookahead} billing competences** after the epidemiological period ({ini} to {fim}; "
        "administrative files {adm_ini}–{adm_fim}), because an admission can be billed months later. "
        "{justificativa}.\n"
        "- **Urgent target**: same rule restricted to the non-elective admission character (`{regra_urg}`; filter "
        "`CAR_INT` 02–06).",
        "pt": "- Uma contagem por dia de **AIH distintas** (`N_AIH`), residentes do município de São Paulo "
        "(`{espacial}`), diagnóstico principal no capítulo J (`{cid}`), datada por `{campo_data}`.\n"
        "- **Look-ahead de {lookahead} competências** após o período epidemiológico ({ini} a {fim}; arquivos "
        "administrativos {adm_ini}–{adm_fim}), porque uma internação pode ser faturada meses depois. "
        "{justificativa}.\n"
        "- **Alvo de urgência**: a mesma regra restrita ao caráter não eletivo da internação (`{regra_urg}`; filtro "
        "`CAR_INT` 02–06).",
    },
    "dl.col_total": {"en": "total target", "pt": "alvo total"},
    "dl.col_urg": {"en": "urgent target", "pt": "alvo de urgência"},
    "dl.lin_linhas": {"en": "rows summed", "pt": "linhas somadas"},
    "dl.lin_aih": {"en": "distinct AIH", "pt": "AIH distintas"},
    "dl.lin_dup": {"en": "duplicates across competences", "pt": "duplicatas entre competências"},
    "dl.lin_invalidas": {"en": "invalid DT_INTER", "pt": "DT_INTER inválidas"},
    "dl.lin_dias": {"en": "days", "pt": "dias"},
    "dl.lin_zero": {"en": "days with zero", "pt": "dias com zero"},
    "dl.lin_extraido": {"en": "extracted", "pt": "extraído em"},
    "dl.h_cetesb": {"en": "How the CETESB series are built", "pt": "Como as séries da CETESB são construídas"},
    "dl.cetesb": {
        "en": "- Source: {fonte}; daily rule: **{regra}**; spatial dispersion D_t: {regra_dt}.\n"
        "- Pollutants present: {poluentes}. Known limitation: {limitacao}.\n"
        "- SO2 is excluded from the models by the coverage rule of the feature builder (days without a valid "
        "station); it is never imputed silently.",
        "pt": "- Fonte: {fonte}; regra diária: **{regra}**; dispersão espacial D_t: {regra_dt}.\n"
        "- Poluentes presentes: {poluentes}. Limitação conhecida: {limitacao}.\n"
        "- O SO2 fica fora dos modelos pela regra de cobertura do construtor de features (dias sem estação válida); "
        "nunca é imputado em silêncio.",
    },
    "dl.h_protocolo": {"en": "Evaluation protocol", "pt": "Protocolo de avaliação"},
    "dl.protocolo": {
        "en": "- Rolling-origin validation: **{n_folds} folds × {dias_teste} test days**, {dias_val} validation days, "
        "minimum training of {treino_min} days; same folds, same dates and same information for every model "
        "(`src/evaluation/splits.py`).\n"
        "- Target lags {lags_alvo}, exogenous lags {lags_exog}, seasonal period {m}; every lag L satisfies L ≥ h "
        "(checked with an exception).\n"
        "- Seeds {sementes} for XGBoost and LSTM; every seed is reported as a mean, never the best one.\n"
        "- Metrics: MAE, RMSE, MASE = MAE(model) / MAE(Naïve) on the same test dates; Diebold–Mariano with Holm.\n"
        "- A data-quality gate runs before every run; FAIL aborts the run.",
        "pt": "- Validação de origem rolante: **{n_folds} folds × {dias_teste} dias de teste**, {dias_val} dias de "
        "validação, treino mínimo de {treino_min} dias; mesmos folds, mesmas datas e mesma informação para todo "
        "modelo (`src/evaluation/splits.py`).\n"
        "- Lags do alvo {lags_alvo}, lags exógenos {lags_exog}, período sazonal {m}; todo lag L satisfaz L ≥ h "
        "(verificado com exceção).\n"
        "- Sementes {sementes} para XGBoost e LSTM; toda semente é reportada como média, nunca a melhor.\n"
        "- Métricas: MAE, RMSE, MASE = MAE(modelo) / MAE(Naïve) nas mesmas datas de teste; teste pareado de "
        "Diebold–Mariano com correção de Holm.\n"
        "- Um gate de qualidade dos dados roda antes de cada run; FAIL aborta a run.",
    },
    "dl.h_runs": {"en": "Runs in this repository", "pt": "Runs neste repositório"},
    "dl.status": {
        "en": "`status` is the runner's own label: the total target was validated monthly against TabNet/DATASUS "
        "(`PRELIMINARY_VALIDATED_TARGET`); the urgent target has not been validated against an official aggregate "
        "yet (`PRELIMINARY_UNVALIDATED_TARGET`). `dirty_tree` must be false for a run to count.",
        "pt": "`status` é o rótulo do próprio runner: o alvo total foi validado mês a mês contra o TabNet/DATASUS "
        "(`PRELIMINARY_VALIDATED_TARGET`); o alvo de urgência ainda não foi validado contra um agregado oficial "
        "(`PRELIMINARY_UNVALIDATED_TARGET`). `dirty_tree` precisa ser false para a run contar.",
    },
    "dl.h_limites": {
        "en": "What is not here, and other limitations",
        "pt": "O que não está aqui, e outras limitações",
    },
    "dl.limites": {
        "en": "- **Only aggregates.** No microdata, no `N_AIH`, no patient-level record. Establishment × year cells "
        "with fewer than 5 admissions are suppressed in the Saturday panel.\n"
        "- **Everything is provisional (pre-defense).** Numbers can change until the dissertation is defended; each "
        "one carries the full id of the run that produced it.\n"
        "- **The forecasting API in this repository is an engineering demonstration**, trained on the whole history "
        "for serving; its forecasts are **not** results of the dissertation and must not be read as such.\n"
        "- **CETESB coverage varies** (number of valid stations per day changes over the years); the rich PM2.5 "
        "representation (mean + station count + dispersion) hurts the LSTM for that reason.\n"
        "- **The canonical CAMS file is not reproducible** from the current ADS endpoint (different grid point); it "
        "is kept as the alternative source used in the dissertation, not as a reference product.\n"
        "- **Urgent target not yet checked against TabNet**; 2025–2026 data in the Saturday panel are also "
        "unchecked.\n"
        "- Not executed: TCN, TCN–LSTM, TFT, SHAP; no claims are made about them.",
        "pt": "- **Só agregados.** Nenhum microdado, nenhum `N_AIH`, nenhum registro por paciente. Células "
        "estabelecimento × ano com menos de 5 internações são suprimidas no painel do sábado.\n"
        "- **Tudo é provisório (pré-defesa).** Os números podem mudar até a defesa da dissertação; cada um carrega o "
        "id completo da run que o produziu.\n"
        "- **A API de previsão deste repositório é uma demonstração de engenharia**, treinada em todo o histórico "
        "para servir previsões; suas previsões **não** são resultados da dissertação e não devem ser lidas como tal.\n"
        "- **A cobertura da CETESB varia** (o número de estações válidas por dia muda ao longo dos anos); a "
        "representação rica do PM2,5 (média + nº de estações + dispersão) prejudica a LSTM por esse motivo.\n"
        "- **O arquivo CAMS canônico não é reproduzível** pelo endpoint atual do ADS (ponto de grade diferente); é "
        "mantido como a fonte alternativa usada na dissertação, não como produto de referência.\n"
        "- **Alvo de urgência ainda não conferido contra o TabNet**; os dados de 2025–2026 do painel do sábado "
        "também não foram conferidos.\n"
        "- Não executados: TCN, TCN–LSTM, TFT, SHAP; nada se afirma sobre eles.",
    },
}


def idioma() -> str:
    """Idioma corrente ('en' ou 'pt'); 'en' quando nada foi escolhido."""
    try:
        lang = st.session_state.get("lang", PADRAO)
    except Exception:  # noqa: BLE001 — fora de um ScriptRunContext
        lang = PADRAO
    return lang if lang in IDIOMAS else PADRAO


def t(chave: str, **fmt):
    """Texto da chave no idioma corrente; `KeyError` se a chave ou o idioma não existir (nunca silencioso)."""
    texto = TEXTOS[chave][idioma()]
    if fmt and isinstance(texto, str):
        return texto.format(**fmt)
    return texto


def fmt_num(x: float, casas: int = 1) -> str:
    """Número formatado no idioma corrente: en 18,566.56 · pt 18.566,56."""
    s = f"{x:,.{casas}f}"
    if idioma() == "pt":
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return s


def separadores_plotly() -> str:
    """`layout.separators` do Plotly: decimal seguido do milhar."""
    return ",." if idioma() == "pt" else ".,"

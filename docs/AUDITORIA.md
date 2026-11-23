# Auditoria WP-A — sp-respiratory-admissions-forecast

- **Data:** 2026-11-23
- **Commit auditado:** `44946b4` (`fix(wp0): preservar bytes originais de dados, artefatos e configs no Git`). A auditoria começou em `e87d574`; o gerente avisou do `44946b4` durante o trabalho e todas as conferências de hash, privacidade e números foram refeitas sobre ele. Durante a redação apareceu ainda o `0bd6c0a` (`chore(fase3): verificador do inventário copiado`, só acrescenta `docs/scripts/verificar_inventario.py`); ele foi executado e é citado onde relevante. Nenhum dos três commits muda conteúdo de dados ou de resultados (o `44946b4` só regrava o fim de linha no índice).
- **Árvore:** limpa (`git status --porcelain` vazio) em todos os pontos conferidos.
- **Método:** tudo conferido com `uv run python` (pandas/json/hashlib) e `git`, nunca de cabeça; os scripts de conferência ficaram no scratchpad da sessão e não entram no repositório. A conferência do WP5 (`docs/CONFERENCIA_NUMEROS_WP5.md`) **não** foi usada como fonte: a amostragem aqui é independente e cobre também app, model card, API README, docstrings, LESSONS e data card.

## Veredito por seção

| Seção | Veredito | Resumo |
|---|---|---|
| (a) Segredos | **OK** | `detect-secrets` (27 plugins) + hook `gitleaks` do pre-commit + varredura própria por padrões em `git ls-files` e em `git log -p --all` (472.982 linhas): nenhum segredo. 433 achados do detect-secrets em arquivos versionados são todos sha256/commits/ids de run (falso positivo). `.env`/`.cdsapirc` nunca entraram no histórico. |
| (b) Privacidade | **ACHADO** | Todos os arquivos são agregados; nenhum `N_AIH`, CPF ou nome de paciente; nenhuma célula estabelecimento × ano < 5; `predictions.csv` ausente. **Mas** `notebooks/dados_painel/estabelecimentos_ano.csv` (e o notebook) trazem o **nome** do estabelecimento ("Instituto CEMA"), quando a decisão D7 autoriza citar **o código**; e `diario.csv` tem 298 células estabelecimento × dia com 1–4 internações (a regra de supressão só cobre estabelecimento × ano). |
| (c) Números | **387 VERIFICADO / 1 DIVERGENTE / 2 SEM FONTE** (390) | As 140 células das duas tabelas do README, a tabela de runs, LESSONS inteiro, MODEL_CARD inteiro, data card, api README, ARCHITECTURE, REPRODUCIBILITY e as páginas do app batem com os artefatos. Divergente: a frase do README "covariáveis ambientais não melhoram `AR_CAL` de forma que sobreviva ao teste pareado" é contrariada por 6 contrastes de ablação significativos após Holm (ver c.1). Sem fonte: dois tempos de execução aproximados. |
| (d) Legado e escopo | **OK** | Nenhum arquivo da lista "fica fora" em `git ls-files` nem no histórico; `src/`, `tests/`, `configs/`, `data/` batem com o inventário (339/339; `gerar_notebook.py` editado de propósito, declarado em `verificar_inventario.py`); rótulo provisório no README (6×), em todas as páginas do app (`ui.aviso_provisorio` + caption `ui.fonte`), no model card e no CITATION.cff; CAMS nunca chamado de fonte principal; "dobra" só em comentários de código herdado; nada afirma desempenho de TCN/TFT/SHAP. |
| (e) Consistência | **ACHADO (menor)** | `docker-compose.yml`/`Makefile` apontam para `app/Home.py`, `api.main:app`, `./mlruns`; extras `app`/`api`/`tracking` cobrem os imports; README descreve a API corretamente (só origens com `origem + h ≤ 2024-12-31`). Menores: serviços `api` e `mlflow` do compose não têm `build:` (o `docker compose up api` do `api/README.md` falha sem imagem construída); `data/README.md` §6 diz que não há "outro período" mas o painel do sábado vai até 2026-02-28. |
| (f) Testes | **225 passed / 0 failed** | `uv run pytest -q`: 225 testes, 0 falhas, 3m52s nesta máquina (em `e87d574`); o gerente reporta 225 passed em 1m44s num clone limpo de `44946b4`. Smoke: PASS em 10,5 s (`STATUS: PRELIMINARY_VALIDATED_TARGET`, nunca é resultado). `verificar_inventario.py` (0bd6c0a): 0 erros. |

---

## (a) Segredos

### a.1 Ferramentas executadas

| Ferramenta | Comando | Resultado |
|---|---|---|
| detect-secrets 1.5 | `uv run --with detect-secrets detect-secrets scan --all-files` | 1.148 achados brutos em 305 arquivos, dos quais **1.148 − 433 = 715 estão em `.venv/`, `.pytest_cache/`, `.ruff_cache/`** (não versionados). Filtrando por `git ls-files`: 433 achados em 16 arquivos, todos "Hex High Entropy String" (423) ou "Base64 High Entropy String" (10). |
| gitleaks v8.24.3 (hook do `.pre-commit-config.yaml`) | `uv run --with pre-commit pre-commit run gitleaks --all-files` | `Detect hardcoded secrets.....Passed` |
| grep próprio (arquivos versionados) | `git ls-files -z \| xargs -0 grep -niE "cdsapirc\|CDSAPI_KEY\|ghp_\|AKIA[0-9A-Z]{12}\|BEGIN .*PRIVATE\|password\|passwd\|secret\|api[_-]?key\|token"` | 30 linhas, classificadas abaixo. |
| grep próprio (e-mails, arquivos versionados) | regex `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | **0** ocorrências em conteúdo versionado. |
| grep próprio (histórico) | `git log -p --all` + mesma regex (472.982 linhas de diff) | Só as mesmas linhas dos arquivos atuais (`+`), nenhuma linha removida com segredo; nenhum `.env`, `.cdsapirc`, `*.pem`, `*.key` jamais adicionado (`git log --all --diff-filter=A --name-only`). |

### a.2 Classificação das ocorrências

| Arquivo:linha | Trecho | Classificação |
|---|---|---|
| `.env.example:8` | `CDSAPI_KEY=<uid>:<api-key>` | placeholder (permitido) |
| `.env.example:5`, `.gitignore:3`, `.dockerignore:5`, `Dockerfile:54`, `docs/REPRODUCIBILITY.md:52` | menção a `.cdsapirc` como arquivo a nunca versionar | falso positivo (regra de exclusão) |
| `src/ingestion/cams_download_chunked.py:27-37, 180-219, 442` | lógica que lê `CDSAPI_URL`/`CDSAPI_KEY` do ambiente; exemplo `key: SEU_PERSONAL_ACCESS_TOKEN`; `CDSAPI_KEY=<token>` | placeholder / código de leitura de credencial, sem valor real |
| `src/experiments/preflight.py:44-79` | `CREDENCIAIS = ["CDSAPI_KEY", "CDSAPI_URL"]`, checagem de presença | nome de variável, sem valor |
| `docs/requirements-executado-20260727-163313.txt:24` | `asttokens==3.0.1` | nome de pacote |
| `results/runs/*/manifest.json` (10 arquivos, 6 linhas cada) | `git_commit`, `dataset_*_sha256`, `config_sha256` | falso positivo (hashes de proveniência) |
| `models_demo/metadata.json` (7), `notebooks/dados_painel/manifest.json` (7), `results/*/proveniencia.json` (2 arquivos), `data/processed/sih_daily_lookahead_urgencia.meta.json` (8) | sha256 de entradas/saídas, ids de run | falso positivo |
| `app/dados.py:24-25` | `DIR_MH = "results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118"` (base64 por entropia) | falso positivo (caminho) |
| metadados do Git (não é conteúdo de arquivo) | autor dos 8 commits: `Matheus de Medeiros Pereira <…@gmail.com>` | informativo: o e-mail pessoal do autor ficará público no `git log` ao publicar; não é segredo, mas é decisão do autor (noreply do GitHub ou manter). |

**Veredito (a): OK — nenhum SEGREDO.**

## (b) Privacidade

### b.1 Inventário dos arquivos de dados (todos lidos com pandas)

| Arquivo | Linhas | Granularidade | Colunas suspeitas (`n_aih`, `cpf`, `nome`, `paciente`…) | Veredito |
|---|---:|---|---|---|
| `data/processed/sih_daily_lookahead.parquet` | 2.192 | 1 linha por dia (`internacoes`, `linhas_brutas`) | nenhuma | agregado |
| `data/processed/sih_daily_lookahead_urgencia.parquet` | 2.192 | 1 linha por dia | nenhuma | agregado |
| `data/processed/cetesb_poluentes_daily.csv` | 2.192 | 1 linha por dia, 18 colunas `<pol>_{media,n_estacoes,dt}` | nenhuma | agregado |
| `data/processed/cetesb_meteo_daily.csv` | 2.192 | 1 linha por dia | nenhuma | agregado |
| `data/processed/cams_daily_v2.csv` | 2.192 | 1 linha por dia | nenhuma | agregado |
| `data/processed/*.meta.json` (4) | — | regras e contagens; `N_AIH` aparece só como **regra de contagem** (permitido) | — | ok |
| `data/cetesb/estacoes_municipio_sp.csv`, `disponibilidade_*.csv`, `stations_bbox.csv`, `stations_sp_pm25.csv` | 23 / 114 / 48 / 34 / 1 | cadastro de **estações** (nome da estação, código, lat/lon) | coluna `nome`/`Nome` = nome de estação CETESB (público) | ok |
| `notebooks/dados_painel/diario.csv` | 2.616 | 1 linha por dia (2019-01-01 a **2026-02-28**): `total`, `nao_eletivo`, `eletivo`, `cema`, `sens_*` | nenhuma; **mas** coluna `cema` = contagem diária de **um** estabelecimento (ver b.3) | agregado, com ressalva |
| `notebooks/dados_painel/estabelecimentos_ano.csv` | 112 | estabelecimento × ano (15 CNES, 2019–2026) | coluna `nome`: 14 linhas "CNES <código>", **8 linhas "Instituto CEMA (CNES 2091550)"** (ver b.3) | agregado, com ACHADO |
| `notebooks/dados_painel/grupos_cid.csv` | 11 | grupo CID × contagens | nenhuma | agregado |
| `notebooks/dados_painel/perfil.csv` | 4 | recorte × medianas/percentuais (menor recorte: 6.870 internações) | nenhuma | agregado |
| `notebooks/dados_painel/atraso_registro_2022_mais.csv` | 7 | dia da semana × % por atraso | nenhuma | agregado |
| `notebooks/dados_painel/erros_modelos_ar_cal.csv` | 25.200 | modelo × data-alvo × h (y, y_prev, run) = 7 modelos × 720 datas × 5 h | nenhuma | agregado (saída de modelo) |
| `notebooks/dados_painel/manifest.json` | — | proveniência (sha256 das entradas, runs, regras) | contém `N_AIH` só na regra "só agregados; nenhum N_AIH" | ok |
| `results/runs/*/` (10 runs × 15 arquivos) | `metrics_by_fold.csv` 528, `model_comparison.csv` 52, `feature_ablation.csv` 50, `folds.csv` 4 | modelo × conjunto × semente × fold | nenhuma; `N_AIH` só em `config.json`/`manifest.json`/`summary.md` como definição do alvo | agregado |
| `results/runs/*/predictions.csv` | — | **ausente nas 10 runs** (`glob results/**/predictions*.csv` = []) | — | conforme o combinado |
| `results/testes_dm/*/` (10) | `dm_contrastes.csv` 355 linhas | contraste × escopo | nenhuma | agregado |
| `results/analise_multihorizonte/…` (14 CSV) e `results/numeros_texto_urgencia/…` (3 CSV) | ≤ 1.260 | por h/base/modelo/conjunto | nenhuma | agregado |
| `models_demo/*.ubj` (3) + `metadata.json` | — | pesos XGBoost + sha256/hiperparâmetros | nenhuma | ok |

### b.2 Checagens específicas

| Checagem | Resultado |
|---|---|
| `estabelecimentos_ano.csv`: alguma célula numérica não vazia < 5? | **Não.** Mínimos: `total` 7, `eletivas` 6, `eletivas_sabado` 5; 50 células vazias (suprimidas); 0 células < 5. |
| `predictions.csv` em `results/`? | Não existe (excluído de propósito; `REPRODUCIBILITY.md` §5 diz isso). |
| `manifest.json` / `summary.md` das runs contêm registros individuais? | Não: contêm proveniência, hashes, folds, versões, parâmetros, `n_predicoes` e contagens agregadas. |
| Hashes de proveniência batem com os bytes do working copy (commit `44946b4`)? | **Sim.** `docs/INVENTARIO_FASE0.tsv`: 339 linhas, 338 sha256 exatos + `notebooks/gerar_notebook.py` editado de propósito (declarado em `docs/scripts/verificar_inventario.py`, `EDITADOS_DEPOIS`; o script dá `erros=0`). `dataset_{sih,cams,cetesb,meteo}_sha256` dos 10 `manifest.json`: 40/40 OK. `models_demo/metadata.json`: 4 entradas + 3 modelos (sha256 e bytes) OK. `proveniencia.json` (urgência): 26/26 artefatos copiados batem; (multihorizonte): 71/71 batem, 188 referem runs não copiadas (CAMS/espelho/híbrida/COVID), conforme `REPRODUCIBILITY.md` §5. |
| `.ipynb` com saídas embutidas? | Não: 16 células, 0 com `outputs`. |

### b.3 Caminhos absolutos e nomes em arquivos versionados

| Onde | Trecho | Classificação |
|---|---|---|
| `src/ingestion/cetesb_build_poluentes.py:16`, `cetesb_build_meteo.py:47`, `cetesb_build_daily.py:20` | exemplo de uso `--dir C:/Users/mathe/Downloads` | **deveria sair** (nome de usuário em docstring; trocar por `<pasta das exportações do QUALAR>`). Baixa gravidade; são os únicos `C:\Users\…` em conteúdo versionado. |
| `notebooks/dados_painel/manifest.json` (`script`, `entradas_sha256`) | `D:\Project\dados_extensao_2026-11\…`, `D:\Project\dataspell_workspace_template\reports\experiments\…` | aceitável (proveniência histórica, sem usuário) |
| `results/runs/*/environment.txt:1`, `docs/requirements-executado-20260727-163313.txt:14` | `# executável: D:\Project\dataspell_workspace_template\env\.venv311\Scripts\python.exe` | aceitável (proveniência) |
| `src/experiments/run_preliminary.py:84`, `src/ingestion/cams_rebuild_daily.py:26-29`, `src/ingestion/sih_build_lookahead.py:3`, `tests/test_caminhos_config.py:4` | `D:/Project/dados_rebaixa_2026-10/…` em exemplos | aceitável (exemplos de caminho fora do repo, sem usuário) |
| `notebooks/dados_painel/estabelecimentos_ano.csv` (col. `nome`, 8 linhas), `notebooks/gerar_notebook.py:146`, `notebooks/painel_carater_internacao.ipynb` (1×), colunas `cema` (`diario.csv`) e `eletivas_cema` (`grupos_cid.csv`), `notebooks/preparar_dados_painel.py:88` | "Instituto CEMA (CNES 2091550)" / "O sábado e o CNES 2091550 (Instituto CEMA)" | **ACHADO**: a decisão D7 (`docs/DECISOES.md`) autoriza citar **o código** CNES 2091550; o nome do estabelecimento está no CSV e no notebook. O app e o LESSONS citam só o código, mas o LESSONS (L19) remete ao CSV como onde o estabelecimento está "named", e a legenda do app (`3_The_Saturday_case.py:377`) diz "names: consult CNES/DATASUS" enquanto o CSV já traz o nome. É informação pública do CNES, não dado pessoal, mas extrapola a decisão registrada: o gerente decide entre ampliar D7 ou remover o nome (gerando o CSV com `nome = "CNES 2091550"` e atualizando o sha no inventário). |
| `notebooks/dados_painel/diario.csv`, coluna `cema` | contagem diária das internações do CNES 2091550: 298 dias com 1–4 internações (de 2.616; 1.840 zeros; máx. 96) | **ACHADO (menor)**: célula estabelecimento × **dia** < 5 para um estabelecimento identificado; a regra do painel ("estabelecimento × ano com < 5 internações suprimido") não cobre a série diária. Decidir se a regra se estende (suprimir < 5 ou agregar por semana) ou se fica registrado como aceito. As colunas `eletivo`/`sens_eletivo` também têm dias com 1–4, mas são agregados do município inteiro (sem identificação de estabelecimento). |

**Veredito (b): ACHADO** (nome do estabelecimento além do que D7 autoriza; células diárias < 5 de um estabelecimento). Nenhum microdado, nenhum `N_AIH` como coluna, nenhum CPF/nome de paciente.

## (c) Números

Regra de conferência: MAE com 2 casas, MASE com 3, contagens exatas; cada número foi lido do arquivo citado ao lado com pandas/json. Cobertura: **todas** as 140 células das duas tabelas de resultados do README (70 por alvo) + tabela de runs; todas as linhas do `docs/LESSONS.md`; todo o `models_demo/MODEL_CARD.md`; `api/README.md`; `data/README.md`; `docs/ARCHITECTURE.md`; `docs/REPRODUCIBILITY.md`; os números fixos e os calculados em tempo de execução de `app/Home.py` e `app/pages/*.py` (os calculados contam como rastreáveis porque cada bloco do app cita o arquivo de origem via `ui.fonte`; o que o app mostrará foi recalculado aqui com o mesmo código, p. ex. página do sábado: 368.758 internações Jan 2019–Fev 2026, 141,0/dia, 13,9 % eletivas, sábados atípicos 43 → 0, grupos sensíveis 8.315 de 277.006 (3,0 %) com 4 no CNES 2091550, correlação 0,04, 15 estabelecimentos, atraso por dia da semana somando 100 %). Também regenerei as tabelas do README com `docs/scripts/tabela_readme.py` e comparei linha a linha: todas as 14 linhas de MAE/MASE estão idênticas no README (o script imprime ainda tabelas de skill que o README não inclui).

Observação sobre a página do sábado (não é divergência, é rastreabilidade): a seção 6 calcula MAE por dia da semana a partir de `erros_modelos_ar_cal.csv` (previsão **média das sementes** por data), enquanto a tabela "Saturday error at h = 1" vem de `erro_sabado_h1.csv` (todas as sementes). Para XGBoost h = 1 isso dá 33,21/15,99 na seção 6 e 33,31/16,09 na tabela, na mesma página, e o MAE da seção 6 (18,45) difere do MAE do README (18,56). As duas origens estão citadas nas legendas, mas vale uma nota explicando a diferença (item 9 da lista final).


### c.3 Detalhe da divergência

**README L88 (bullet "How to read the tables") e L137 (Resumo em português):** "Environmental covariates (PM2.5, other pollutants, meteorology) do not improve `AR_CAL` in a way that survives the paired test". Nos `dm_contrastes.csv` das 10 runs (famílias `ablacao_*`, escopo agrupado, T = 720) há 59 contrastes com `p_holm < 0,05`; 53 têm DM > 0 (o conjunto mais rico é **pior**, quase todos LSTM com `PM25` rico — isso sustenta a frase), mas **6 têm DM < 0 com o conjunto mais rico melhor**:

| Run | Família | Contraste | A (mais rico) | B | d̄ | DM | p Holm |
|---|---|---|---|---|---:|---:|---:|
| `ur_h1_cetesb_cetesb_full_20261116-191534` | ablacao_sarimax | H2_media_sem_meteo | `AR_CAL_PM25MEDIA` | `AR_CAL` | −0,315 | −3,50 | 0,005 |
| `ur_h1_cetesb_cetesb_full_20261116-191534` | ablacao_sarimax | POLUENTES_sem_meteo | `AR_CAL_POLUENTES` | `AR_CAL` | −0,353 | −3,17 | 0,014 |
| `ur_h15_cetesb_cetesb_full_20261117-190532` | ablacao_xgboost | POLUENTES_com_meteo | `AR_CAL_METEO_POLUENTES` | `AR_CAL_METEO` | −0,836 | −3,93 | 0,001 |
| `mh_h7_cetesb_cetesb_full_20261111-030322` | ablacao_lstm | H2_media_com_meteo | `AR_CAL_METEO_PM25MEDIA` | `AR_CAL_METEO` | −0,915 | −3,79 | 0,001 |
| `ur_h5_cetesb_cetesb_full_20261116-222823` | ablacao_lstm | H2_media_com_meteo | `AR_CAL_METEO_PM25MEDIA` | `AR_CAL_METEO` | −0,658 | −3,27 | 0,007 |
| `ur_h7_cetesb_cetesb_full_20261117-073926` | ablacao_lstm | H2_media_com_meteo | `AR_CAL_METEO_PM25MEDIA` | `AR_CAL_METEO` | −0,720 | −2,86 | 0,026 |

Os dois primeiros são exatamente "covariável × `AR_CAL`" e sobrevivem a Holm (o `saida.txt` da análise de urgência, seção E, mostra o mesmo p = 0,005 para SARIMAX M0→M2). A frase é verdadeira para o alvo total em h = 1 (nenhum contraste de ablação significativo com DM < 0 na run `h1_v02_…`) e para XGBoost em quase todo h, mas como generalização sobre "todas as covariáveis, todos os modelos, todos os h e os dois alvos" é **DIVERGENTE**. Sugestão (WP5): restringir a frase ("On the total target at h = 1 no environmental block improves `AR_CAL` after Holm; on the urgent target a few contrasts are significant — SARIMAX at h = 1 with the PM2.5 mean or with pollutants, XGBoost at h = 15 with pollutants given meteorology — and are discussed in the dissertation") ou citar o arquivo `B2_dm_ablacao_por_h.csv` com a contagem.

### c.4 Tabelas de conferência

Total de números conferidos: **390** — VERIFICADO 387 · DIVERGENTE 1 · SEM FONTE 2.

Primeiro os itens que não bateram, depois a lista completa por bloco.

### c.1 DIVERGENTE e SEM FONTE

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 216 | README: covariáveis ambientais não melhoram AR_CAL de forma que sobreviva ao teste (contrastes de ablação sig. após Holm) | nenhum ganho sig. | `results/testes_dm/*/dm_contrastes.csv` | familia=ablacao_*, agrupado, p_holm<0.05 | [('h1_v02_cetes', 'ablacao_lstm', 'PM25_rico_sem_meteo', 6.46, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'PM25_rico_com_meteo', 4.35, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'rico_vs_media_com_meteo', 4.82, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'METEO', 4.35, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'COMPLETO_vs_meteo', 4.07, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'COMPLETO_vs_meteo_poluentes', 5.1, 0.0), ('h1_v02_cetes', 'ablacao_ingarch_nb', 'COMPLETO_vs_meteo_poluentes', 2.97, 0.031), ('mh_h5_cetesb', 'ablacao_lstm', 'PM25_rico_sem_meteo', 5.22, 0.0), ('mh_h5_cetesb', 'ablacao_lstm', 'PM25_rico_com_meteo', 4.2, 0.0), ('mh_h5_cetesb', 'ablacao_lstm', 'rico_vs_media_com_meteo', 4.8, 0.0), ('mh_h5_cetesb', 'ablacao_lstm', 'METEO', 2.96, 0.019), ('mh_h5_cetesb', 'ablacao_lstm', 'COMPLETO_vs_meteo', 3.82, 0.001), ('mh_h7_cetesb', 'ablacao_xgboost', 'METEO', 3.54, 0.004), ('mh_h7_cetesb', 'ablac … | **DIVERGENTE** |
| 389 | README L97 / Makefile: suíte de testes 'about 5 minutes' | ~5 min | `(nenhum artefato)` | medido nesta auditoria | 3m52s (e87d574, esta máquina); 1m44s (clone limpo do gerente, 44946b4) | **SEM FONTE** |
| 390 | REPRODUCIBILITY L82: `--smoke` 'takes about a minute' | ~1 min | `(nenhum artefato)` | medido nesta auditoria | 10,5 s (configs/smoke.yaml, esta máquina) | **SEM FONTE** |

### c.2 Lista completa (por bloco)


**README / runs / DM** — 246 números, 245 VERIFICADO

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 1 | README tabela total h=1 XGBoost MAE | 18.56 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 18.556640 | VERIFICADO |
| 2 | README tabela total h=1 XGBoost MASE | 0.645 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 0.645036 | VERIFICADO |
| 3 | README tabela total h=5 XGBoost MAE | 22.50 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 22.503195 | VERIFICADO |
| 4 | README tabela total h=5 XGBoost MASE | 0.656 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.656387 | VERIFICADO |
| 5 | README tabela total h=7 XGBoost MAE | 23.40 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 23.397313 | VERIFICADO |
| 6 | README tabela total h=7 XGBoost MASE | 0.810 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 0.809546 | VERIFICADO |
| 7 | README tabela total h=15 XGBoost MAE | 24.34 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 24.338431 | VERIFICADO |
| 8 | README tabela total h=15 XGBoost MASE | 0.654 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.654489 | VERIFICADO |
| 9 | README tabela total h=30 XGBoost MAE | 26.36 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 26.362735 | VERIFICADO |
| 10 | README tabela total h=30 XGBoost MASE | 0.698 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.697528 | VERIFICADO |
| 11 | README tabela total h=1 SARIMAX MAE | 18.92 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 18.922787 | VERIFICADO |
| 12 | README tabela total h=1 SARIMAX MASE | 0.660 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 0.659921 | VERIFICADO |
| 13 | README tabela total h=5 SARIMAX MAE | 23.04 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 23.040453 | VERIFICADO |
| 14 | README tabela total h=5 SARIMAX MASE | 0.674 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.673788 | VERIFICADO |
| 15 | README tabela total h=7 SARIMAX MAE | 24.37 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 24.370407 | VERIFICADO |
| 16 | README tabela total h=7 SARIMAX MASE | 0.845 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 0.845018 | VERIFICADO |
| 17 | README tabela total h=15 SARIMAX MAE | 25.84 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 25.840538 | VERIFICADO |
| 18 | README tabela total h=15 SARIMAX MASE | 0.698 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.697970 | VERIFICADO |
| 19 | README tabela total h=30 SARIMAX MAE | 25.32 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 25.315812 | VERIFICADO |
| 20 | README tabela total h=30 SARIMAX MASE | 0.668 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.668324 | VERIFICADO |
| 21 | README tabela total h=1 LSTM MAE | 19.01 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 19.011291 | VERIFICADO |
| 22 | README tabela total h=1 LSTM MASE | 0.662 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 0.662086 | VERIFICADO |
| 23 | README tabela total h=5 LSTM MAE | 22.56 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 22.563174 | VERIFICADO |
| 24 | README tabela total h=5 LSTM MASE | 0.660 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.660136 | VERIFICADO |
| 25 | README tabela total h=7 LSTM MAE | 23.64 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 23.641747 | VERIFICADO |
| 26 | README tabela total h=7 LSTM MASE | 0.821 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 0.820644 | VERIFICADO |
| 27 | README tabela total h=15 LSTM MAE | 25.32 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 25.318614 | VERIFICADO |
| 28 | README tabela total h=15 LSTM MASE | 0.683 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.682535 | VERIFICADO |
| 29 | README tabela total h=30 LSTM MAE | 26.76 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 26.757303 | VERIFICADO |
| 30 | README tabela total h=30 LSTM MASE | 0.710 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.709576 | VERIFICADO |
| 31 | README tabela total h=1 INGARCH-NB MAE | 19.55 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 19.545888 | VERIFICADO |
| 32 | README tabela total h=1 INGARCH-NB MASE | 0.681 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 0.680788 | VERIFICADO |
| 33 | README tabela total h=5 INGARCH-NB MAE | 23.59 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 23.590421 | VERIFICADO |
| 34 | README tabela total h=5 INGARCH-NB MASE | 0.690 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.690078 | VERIFICADO |
| 35 | README tabela total h=7 INGARCH-NB MAE | 24.71 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 24.709864 | VERIFICADO |
| 36 | README tabela total h=7 INGARCH-NB MASE | 0.857 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 0.856831 | VERIFICADO |
| 37 | README tabela total h=15 INGARCH-NB MAE | 26.39 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 26.389528 | VERIFICADO |
| 38 | README tabela total h=15 INGARCH-NB MASE | 0.713 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.712736 | VERIFICADO |
| 39 | README tabela total h=30 INGARCH-NB MAE | 25.47 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 25.469709 | VERIFICADO |
| 40 | README tabela total h=30 INGARCH-NB MASE | 0.674 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.673941 | VERIFICADO |
| 41 | README tabela total h=1 GAM-NB MAE | 21.91 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 21.905191 | VERIFICADO |
| 42 | README tabela total h=1 GAM-NB MASE | 0.763 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 0.762750 | VERIFICADO |
| 43 | README tabela total h=5 GAM-NB MAE | 25.35 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 25.352119 | VERIFICADO |
| 44 | README tabela total h=5 GAM-NB MASE | 0.741 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.741491 | VERIFICADO |
| 45 | README tabela total h=7 GAM-NB MAE | 26.28 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 26.281345 | VERIFICADO |
| 46 | README tabela total h=7 GAM-NB MASE | 0.909 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 0.909077 | VERIFICADO |
| 47 | README tabela total h=15 GAM-NB MAE | 27.24 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 27.237189 | VERIFICADO |
| 48 | README tabela total h=15 GAM-NB MASE | 0.734 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.733838 | VERIFICADO |
| 49 | README tabela total h=30 GAM-NB MAE | 27.52 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 27.522543 | VERIFICADO |
| 50 | README tabela total h=30 GAM-NB MASE | 0.726 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.726041 | VERIFICADO |
| 51 | README tabela total h=1 Naive MAE | 28.71 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 28.711111 | VERIFICADO |
| 52 | README tabela total h=1 Naive MASE | 1.000 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 53 | README tabela total h=5 Naive MAE | 34.13 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 34.127778 | VERIFICADO |
| 54 | README tabela total h=5 Naive MASE | 1.000 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 55 | README tabela total h=7 Naive MAE | 28.87 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 28.870833 | VERIFICADO |
| 56 | README tabela total h=7 Naive MASE | 1.000 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 57 | README tabela total h=15 Naive MAE | 37.05 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 37.052778 | VERIFICADO |
| 58 | README tabela total h=15 Naive MASE | 1.000 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 59 | README tabela total h=30 Naive MAE | 37.84 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 37.841667 | VERIFICADO |
| 60 | README tabela total h=30 Naive MASE | 1.000 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 61 | README tabela total h=1 Seasonal Naive MAE | 28.87 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 28.870833 | VERIFICADO |
| 62 | README tabela total h=1 Seasonal Naive MASE | 1.007 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | MASE_medio | 1.006760 | VERIFICADO |
| 63 | README tabela total h=5 Seasonal Naive MAE | 28.87 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 28.870833 | VERIFICADO |
| 64 | README tabela total h=5 Seasonal Naive MASE | 0.844 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | MASE_medio | 0.844175 | VERIFICADO |
| 65 | README tabela total h=7 Seasonal Naive MAE | 28.87 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 28.870833 | VERIFICADO |
| 66 | README tabela total h=7 Seasonal Naive MASE | 1.000 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 67 | README tabela total h=15 Seasonal Naive MAE | 33.25 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 33.254167 | VERIFICADO |
| 68 | README tabela total h=15 Seasonal Naive MASE | 0.897 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | MASE_medio | 0.896522 | VERIFICADO |
| 69 | README tabela total h=30 Seasonal Naive MAE | 34.85 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 34.852778 | VERIFICADO |
| 70 | README tabela total h=30 Seasonal Naive MASE | 0.917 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | MASE_medio | 0.916868 | VERIFICADO |
| 71 | README tabela urgencia h=1 XGBoost MAE | 14.88 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 14.877529 | VERIFICADO |
| 72 | README tabela urgencia h=1 XGBoost MASE | 0.749 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 0.749399 | VERIFICADO |
| 73 | README tabela urgencia h=5 XGBoost MAE | 17.61 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 17.614208 | VERIFICADO |
| 74 | README tabela urgencia h=5 XGBoost MASE | 0.665 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.665220 | VERIFICADO |
| 75 | README tabela urgencia h=7 XGBoost MAE | 18.51 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 18.510862 | VERIFICADO |
| 76 | README tabela urgencia h=7 XGBoost MASE | 0.865 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 0.865300 | VERIFICADO |
| 77 | README tabela urgencia h=15 XGBoost MAE | 20.99 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 20.991515 | VERIFICADO |
| 78 | README tabela urgencia h=15 XGBoost MASE | 0.738 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.737989 | VERIFICADO |
| 79 | README tabela urgencia h=30 XGBoost MAE | 22.45 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=xgboost,feature_set=AR_CAL,MAE_medio | 22.447150 | VERIFICADO |
| 80 | README tabela urgencia h=30 XGBoost MASE | 0.683 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.682782 | VERIFICADO |
| 81 | README tabela urgencia h=1 SARIMAX MAE | 14.26 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 14.262206 | VERIFICADO |
| 82 | README tabela urgencia h=1 SARIMAX MASE | 0.719 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 0.718844 | VERIFICADO |
| 83 | README tabela urgencia h=5 SARIMAX MAE | 17.66 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 17.659149 | VERIFICADO |
| 84 | README tabela urgencia h=5 SARIMAX MASE | 0.668 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.668283 | VERIFICADO |
| 85 | README tabela urgencia h=7 SARIMAX MAE | 18.72 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 18.723257 | VERIFICADO |
| 86 | README tabela urgencia h=7 SARIMAX MASE | 0.876 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 0.876425 | VERIFICADO |
| 87 | README tabela urgencia h=15 SARIMAX MAE | 21.17 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 21.173598 | VERIFICADO |
| 88 | README tabela urgencia h=15 SARIMAX MASE | 0.746 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.746205 | VERIFICADO |
| 89 | README tabela urgencia h=30 SARIMAX MAE | 21.46 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=sarimax,feature_set=AR_CAL,MAE_medio | 21.455908 | VERIFICADO |
| 90 | README tabela urgencia h=30 SARIMAX MASE | 0.652 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.652384 | VERIFICADO |
| 91 | README tabela urgencia h=1 LSTM MAE | 14.76 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 14.758035 | VERIFICADO |
| 92 | README tabela urgencia h=1 LSTM MASE | 0.744 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 0.743985 | VERIFICADO |
| 93 | README tabela urgencia h=5 LSTM MAE | 17.99 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 17.990163 | VERIFICADO |
| 94 | README tabela urgencia h=5 LSTM MASE | 0.681 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.680898 | VERIFICADO |
| 95 | README tabela urgencia h=7 LSTM MAE | 18.78 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 18.775988 | VERIFICADO |
| 96 | README tabela urgencia h=7 LSTM MASE | 0.879 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 0.878889 | VERIFICADO |
| 97 | README tabela urgencia h=15 LSTM MAE | 21.69 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 21.689028 | VERIFICADO |
| 98 | README tabela urgencia h=15 LSTM MASE | 0.761 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.761485 | VERIFICADO |
| 99 | README tabela urgencia h=30 LSTM MAE | 22.69 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=lstm,feature_set=AR_CAL,MAE_medio | 22.692952 | VERIFICADO |
| 100 | README tabela urgencia h=30 LSTM MASE | 0.692 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.691514 | VERIFICADO |
| 101 | README tabela urgencia h=1 INGARCH-NB MAE | 14.94 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 14.939200 | VERIFICADO |
| 102 | README tabela urgencia h=1 INGARCH-NB MASE | 0.753 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 0.753057 | VERIFICADO |
| 103 | README tabela urgencia h=5 INGARCH-NB MAE | 18.41 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 18.406056 | VERIFICADO |
| 104 | README tabela urgencia h=5 INGARCH-NB MASE | 0.697 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.696832 | VERIFICADO |
| 105 | README tabela urgencia h=7 INGARCH-NB MAE | 19.18 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 19.181673 | VERIFICADO |
| 106 | README tabela urgencia h=7 INGARCH-NB MASE | 0.898 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 0.898133 | VERIFICADO |
| 107 | README tabela urgencia h=15 INGARCH-NB MAE | 21.52 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 21.519316 | VERIFICADO |
| 108 | README tabela urgencia h=15 INGARCH-NB MASE | 0.759 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.759111 | VERIFICADO |
| 109 | README tabela urgencia h=30 INGARCH-NB MAE | 21.71 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=ingarch_nb,feature_set=AR_CAL,MAE_medio | 21.713570 | VERIFICADO |
| 110 | README tabela urgencia h=30 INGARCH-NB MASE | 0.661 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.660833 | VERIFICADO |
| 111 | README tabela urgencia h=1 GAM-NB MAE | 16.65 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 16.650977 | VERIFICADO |
| 112 | README tabela urgencia h=1 GAM-NB MASE | 0.838 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 0.838277 | VERIFICADO |
| 113 | README tabela urgencia h=5 GAM-NB MAE | 19.94 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 19.939961 | VERIFICADO |
| 114 | README tabela urgencia h=5 GAM-NB MASE | 0.754 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.753889 | VERIFICADO |
| 115 | README tabela urgencia h=7 GAM-NB MAE | 20.08 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 20.084591 | VERIFICADO |
| 116 | README tabela urgencia h=7 GAM-NB MASE | 0.939 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 0.938720 | VERIFICADO |
| 117 | README tabela urgencia h=15 GAM-NB MAE | 22.46 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 22.460084 | VERIFICADO |
| 118 | README tabela urgencia h=15 GAM-NB MASE | 0.788 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.788109 | VERIFICADO |
| 119 | README tabela urgencia h=30 GAM-NB MAE | 23.57 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=gam_nb,feature_set=AR_CAL,MAE_medio | 23.574919 | VERIFICADO |
| 120 | README tabela urgencia h=30 GAM-NB MASE | 0.712 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.712115 | VERIFICADO |
| 121 | README tabela urgencia h=1 Naive MAE | 19.81 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 19.813889 | VERIFICADO |
| 122 | README tabela urgencia h=1 Naive MASE | 1.000 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 123 | README tabela urgencia h=5 Naive MAE | 26.36 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 26.359722 | VERIFICADO |
| 124 | README tabela urgencia h=5 Naive MASE | 1.000 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 125 | README tabela urgencia h=7 Naive MAE | 21.36 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 21.359722 | VERIFICADO |
| 126 | README tabela urgencia h=7 Naive MASE | 1.000 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 127 | README tabela urgencia h=15 Naive MAE | 28.39 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 28.390278 | VERIFICADO |
| 128 | README tabela urgencia h=15 Naive MASE | 1.000 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 129 | README tabela urgencia h=30 Naive MAE | 32.85 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=naive,feature_set=baseline,MAE_medio | 32.848611 | VERIFICADO |
| 130 | README tabela urgencia h=30 Naive MASE | 1.000 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 131 | README tabela urgencia h=1 Seasonal Naive MAE | 21.36 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 21.359722 | VERIFICADO |
| 132 | README tabela urgencia h=1 Seasonal Naive MASE | 1.076 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | MASE_medio | 1.075769 | VERIFICADO |
| 133 | README tabela urgencia h=5 Seasonal Naive MAE | 21.36 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 21.359722 | VERIFICADO |
| 134 | README tabela urgencia h=5 Seasonal Naive MASE | 0.809 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | MASE_medio | 0.809036 | VERIFICADO |
| 135 | README tabela urgencia h=7 Seasonal Naive MAE | 21.36 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 21.359722 | VERIFICADO |
| 136 | README tabela urgencia h=7 Seasonal Naive MASE | 1.000 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | MASE_medio | 1.000000 | VERIFICADO |
| 137 | README tabela urgencia h=15 Seasonal Naive MAE | 27.05 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 27.048611 | VERIFICADO |
| 138 | README tabela urgencia h=15 Seasonal Naive MASE | 0.952 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | MASE_medio | 0.951775 | VERIFICADO |
| 139 | README tabela urgencia h=30 Seasonal Naive MAE | 30.41 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=seasonal_naive,feature_set=baseline,MAE_medio | 30.411111 | VERIFICADO |
| 140 | README tabela urgencia h=30 Seasonal Naive MASE | 0.922 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | MASE_medio | 0.921580 | VERIFICADO |
| 141 | README/LESSONS commit exibido h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | e6a63c3 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_commit | e6a63c3 | VERIFICADO |
| 142 | README/LESSONS run h1_v02_cetesb_cetesb_classicos_full_20261022-211834 árvore limpa | yes / false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_sujo | False | VERIFICADO |
| 143 | README run h1_v02_cetesb_cetesb_classicos_full_20261022-211834 previsões | 95,040 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 144 | LESSONS 4 run h1_v02_cetesb_cetesb_classicos_full_20261022-211834 repo mudou durante a run | false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 145 | README/LESSONS run h1_v02_cetesb_cetesb_classicos_full_20261022-211834 modo full | full | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | modo | full | VERIFICADO |
| 146 | app/README gate PASS h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | PASS | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/data_quality.json` | veredito | PASS | VERIFICADO |
| 147 | README/LESSONS commit exibido mh_h5_cetesb_cetesb_full_20261110-211453 | 5436606 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_commit | 5436606 | VERIFICADO |
| 148 | README/LESSONS run mh_h5_cetesb_cetesb_full_20261110-211453 árvore limpa | yes / false | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_sujo | False | VERIFICADO |
| 149 | README run mh_h5_cetesb_cetesb_full_20261110-211453 previsões | 95,040 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 150 | LESSONS 4 run mh_h5_cetesb_cetesb_full_20261110-211453 repo mudou durante a run | false | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 151 | README/LESSONS run mh_h5_cetesb_cetesb_full_20261110-211453 modo full | full | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | modo | full | VERIFICADO |
| 152 | app/README gate PASS mh_h5_cetesb_cetesb_full_20261110-211453 | PASS | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/data_quality.json` | veredito | PASS | VERIFICADO |
| 153 | README/LESSONS commit exibido mh_h7_cetesb_cetesb_full_20261111-030322 | 49c2188 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_commit | 49c2188 | VERIFICADO |
| 154 | README/LESSONS run mh_h7_cetesb_cetesb_full_20261111-030322 árvore limpa | yes / false | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_sujo | False | VERIFICADO |
| 155 | README run mh_h7_cetesb_cetesb_full_20261111-030322 previsões | 95,040 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 156 | LESSONS 4 run mh_h7_cetesb_cetesb_full_20261111-030322 repo mudou durante a run | false | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 157 | README/LESSONS run mh_h7_cetesb_cetesb_full_20261111-030322 modo full | full | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | modo | full | VERIFICADO |
| 158 | app/README gate PASS mh_h7_cetesb_cetesb_full_20261111-030322 | PASS | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/data_quality.json` | veredito | PASS | VERIFICADO |
| 159 | README/LESSONS commit exibido mh_h15_cetesb_cetesb_full_20261111-070926 | b5bb35f | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_commit | b5bb35f | VERIFICADO |
| 160 | README/LESSONS run mh_h15_cetesb_cetesb_full_20261111-070926 árvore limpa | yes / false | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_sujo | False | VERIFICADO |
| 161 | README run mh_h15_cetesb_cetesb_full_20261111-070926 previsões | 95,040 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 162 | LESSONS 4 run mh_h15_cetesb_cetesb_full_20261111-070926 repo mudou durante a run | false | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 163 | README/LESSONS run mh_h15_cetesb_cetesb_full_20261111-070926 modo full | full | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | modo | full | VERIFICADO |
| 164 | app/README gate PASS mh_h15_cetesb_cetesb_full_20261111-070926 | PASS | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/data_quality.json` | veredito | PASS | VERIFICADO |
| 165 | README/LESSONS commit exibido mh_h30_cetesb_cetesb_full_20261113-104814 | e4828bc | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_commit | e4828bc | VERIFICADO |
| 166 | README/LESSONS run mh_h30_cetesb_cetesb_full_20261113-104814 árvore limpa | yes / false | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_sujo | False | VERIFICADO |
| 167 | README run mh_h30_cetesb_cetesb_full_20261113-104814 previsões | 95,040 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 168 | LESSONS 4 run mh_h30_cetesb_cetesb_full_20261113-104814 repo mudou durante a run | false | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 169 | README/LESSONS run mh_h30_cetesb_cetesb_full_20261113-104814 modo full | full | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | modo | full | VERIFICADO |
| 170 | app/README gate PASS mh_h30_cetesb_cetesb_full_20261113-104814 | PASS | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/data_quality.json` | veredito | PASS | VERIFICADO |
| 171 | README/LESSONS commit exibido ur_h1_cetesb_cetesb_full_20261116-191534 | eeeef00 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_commit | eeeef00 | VERIFICADO |
| 172 | README/LESSONS run ur_h1_cetesb_cetesb_full_20261116-191534 árvore limpa | yes / false | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_sujo | False | VERIFICADO |
| 173 | README run ur_h1_cetesb_cetesb_full_20261116-191534 previsões | 95,040 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 174 | LESSONS 4 run ur_h1_cetesb_cetesb_full_20261116-191534 repo mudou durante a run | false | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 175 | README/LESSONS run ur_h1_cetesb_cetesb_full_20261116-191534 modo full | full | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | modo | full | VERIFICADO |
| 176 | README status ur_h1_cetesb_cetesb_full_20261116-191534 | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 177 | app/README gate PASS ur_h1_cetesb_cetesb_full_20261116-191534 | PASS | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/data_quality.json` | veredito | PASS | VERIFICADO |
| 178 | README/LESSONS commit exibido ur_h5_cetesb_cetesb_full_20261116-222823 | 8325cee | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_commit | 8325cee | VERIFICADO |
| 179 | README/LESSONS run ur_h5_cetesb_cetesb_full_20261116-222823 árvore limpa | yes / false | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_sujo | False | VERIFICADO |
| 180 | README run ur_h5_cetesb_cetesb_full_20261116-222823 previsões | 95,040 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 181 | LESSONS 4 run ur_h5_cetesb_cetesb_full_20261116-222823 repo mudou durante a run | false | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 182 | README/LESSONS run ur_h5_cetesb_cetesb_full_20261116-222823 modo full | full | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | modo | full | VERIFICADO |
| 183 | README status ur_h5_cetesb_cetesb_full_20261116-222823 | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 184 | app/README gate PASS ur_h5_cetesb_cetesb_full_20261116-222823 | PASS | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/data_quality.json` | veredito | PASS | VERIFICADO |
| 185 | README/LESSONS commit exibido ur_h7_cetesb_cetesb_full_20261117-073926 | dfc3c57 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_commit | dfc3c57 | VERIFICADO |
| 186 | README/LESSONS run ur_h7_cetesb_cetesb_full_20261117-073926 árvore limpa | yes / false | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_sujo | False | VERIFICADO |
| 187 | README run ur_h7_cetesb_cetesb_full_20261117-073926 previsões | 95,040 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 188 | LESSONS 4 run ur_h7_cetesb_cetesb_full_20261117-073926 repo mudou durante a run | false | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 189 | README/LESSONS run ur_h7_cetesb_cetesb_full_20261117-073926 modo full | full | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | modo | full | VERIFICADO |
| 190 | README status ur_h7_cetesb_cetesb_full_20261117-073926 | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 191 | app/README gate PASS ur_h7_cetesb_cetesb_full_20261117-073926 | PASS | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/data_quality.json` | veredito | PASS | VERIFICADO |
| 192 | README/LESSONS commit exibido ur_h15_cetesb_cetesb_full_20261117-190532 | 1252ad5 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_commit | 1252ad5 | VERIFICADO |
| 193 | README/LESSONS run ur_h15_cetesb_cetesb_full_20261117-190532 árvore limpa | yes / false | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_sujo | False | VERIFICADO |
| 194 | README run ur_h15_cetesb_cetesb_full_20261117-190532 previsões | 95,040 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 195 | LESSONS 4 run ur_h15_cetesb_cetesb_full_20261117-190532 repo mudou durante a run | false | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 196 | README/LESSONS run ur_h15_cetesb_cetesb_full_20261117-190532 modo full | full | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | modo | full | VERIFICADO |
| 197 | README status ur_h15_cetesb_cetesb_full_20261117-190532 | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 198 | app/README gate PASS ur_h15_cetesb_cetesb_full_20261117-190532 | PASS | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/data_quality.json` | veredito | PASS | VERIFICADO |
| 199 | README/LESSONS commit exibido ur_h30_cetesb_cetesb_full_20261117-221426 | 8be599e | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_commit | 8be599e | VERIFICADO |
| 200 | README/LESSONS run ur_h30_cetesb_cetesb_full_20261117-221426 árvore limpa | yes / false | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_sujo | False | VERIFICADO |
| 201 | README run ur_h30_cetesb_cetesb_full_20261117-221426 previsões | 95,040 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 202 | LESSONS 4 run ur_h30_cetesb_cetesb_full_20261117-221426 repo mudou durante a run | false | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | False | VERIFICADO |
| 203 | README/LESSONS run ur_h30_cetesb_cetesb_full_20261117-221426 modo full | full | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | modo | full | VERIFICADO |
| 204 | README status ur_h30_cetesb_cetesb_full_20261117-221426 | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 205 | app/README gate PASS ur_h30_cetesb_cetesb_full_20261117-221426 | PASS | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/data_quality.json` | veredito | PASS | VERIFICADO |
| 206 | README sábado XGBoost MAE_sab | 33.31 | `erro_sabado_h1.csv` | total,XGBoost,MAE_sab | 33.3077 | VERIFICADO |
| 207 | README sábado XGBoost MAE_demais | 16.09 | `erro_sabado_h1.csv` | total,XGBoost,MAE_demais | 16.0941 | VERIFICADO |
| 208 | README sábado XGBoost razao | 2.07 | `erro_sabado_h1.csv` | total,XGBoost,razao | 2.0696 | VERIFICADO |
| 209 | README sábado urgência razao | 0.90 | `erro_sabado_h1.csv` | urgencia,XGBoost,razao | 0.9042 | VERIFICADO |
| 210 | README DM h=1 total: 4 contrastes sig. entre modelos treinados, todos vs GAM-NB | 4 / gam_nb | `A2_dm_modelos_por_h.csv` | n_sig_entre_modelos,sig_entre_modelos | 4 \| xgboost − gam_nb; sarimax − gam_nb; lstm − gam_nb; ingarch_nb − gam_nb | VERIFICADO |
| 211 | README líder nominal total h=1..15 XGBoost | xgboost | `A2_dm_modelos_por_h.csv` | lider | ['xgboost', 'xgboost', 'xgboost', 'xgboost'] | VERIFICADO |
| 212 | README líder nominal total h=30 SARIMAX | sarimax | `A2_dm_modelos_por_h.csv` | lider | sarimax | VERIFICADO |
| 213 | README líder nominal urgência h=5..15 XGBoost | xgboost | `A2_dm_modelos_por_h.csv` | lider | ['xgboost', 'xgboost', 'xgboost'] | VERIFICADO |
| 214 | README líder nominal urgência h=1 e h=30 SARIMAX | sarimax | `A2_dm_modelos_por_h.csv` | lider | ['sarimax', 'sarimax'] | VERIFICADO |
| 215 | README: XGBoost/SARIMAX/LSTM não se separam após Holm (10 runs) | nenhum par sig. | `results/testes_dm/*/dm_contrastes.csv` | familia=modelos_AR_CAL, escopo=agrupado, p_holm<0.05 | nenhum | VERIFICADO |
| 216 | README: covariáveis ambientais não melhoram AR_CAL de forma que sobreviva ao teste (contrastes de ablação sig. após Holm) | nenhum ganho sig. | `results/testes_dm/*/dm_contrastes.csv` | familia=ablacao_*, agrupado, p_holm<0.05 | [('h1_v02_cetes', 'ablacao_lstm', 'PM25_rico_sem_meteo', 6.46, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'PM25_rico_com_meteo', 4.35, 0.0), ('h1_v02_cetes', 'ablacao_lstm', 'rico_vs_media_com_meteo', 4.82, 0.0), ('h1_v02_ce … | DIVERGENTE |
| 217 | README: A_modelos_por_h × arcal_por_horizonte_dois_alvos concordam | \|diff\|<=1e-9 | `A_modelos_por_h.csv × arcal_por_horizonte_dois_alvos.csv` | MAE_ARCAL/MASE_ARCAL vs MAE/MASE | max diff 0.00e+00 | VERIFICADO |
| 218 | README: model_comparison × arcal_por_horizonte_dois_alvos (10 runs × 7 modelos) | \|diff\|<=1e-9 | `model_comparison.csv × arcal_por_horizonte_dois_alvos.csv` | MAE_medio/MASE_medio | max diff 3.55e-15 | VERIFICADO |
| 219 | README nota h=7 (total): Naïve de h=7 = Seasonal Naïve | iguais | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | naive vs seasonal_naive MAE_medio | 28.870833 vs 28.870833 | VERIFICADO |
| 220 | README nota h=7 (urgencia): Naïve de h=7 = Seasonal Naïve | iguais | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | naive vs seasonal_naive MAE_medio | 21.359722 vs 21.359722 | VERIFICADO |
| 221 | README/MODEL_CARD/data README 2,192 dias (2019-01-01..2024-12-31) | 2,192 | `sih_daily_lookahead.meta.json` | dias, periodo_epidemiologico | 2192 ['2019-01-01', '2024-12-31'] | VERIFICADO |
| 222 | README/REPRO 4 folds × 180 dias de teste, validação 180, teste 2023-01-12..2024-12-31 | 4×180; 2023-01-12..2024-12-31 | `folds.csv h1` | n_teste,n_validacao,teste_inicio,teste_fim | 4 folds, n_teste=[180], n_val=[180], 2023-01-12..2024-12-31 | VERIFICADO |
| 223 | REPRO janelas de teste por fold | 2023-01-12..2023-07-10; 2023-07-11..2024-01-06; 2024-01-07..2024-07-04; 2024-07-05..2024-12-31 | `folds.csv h1` | teste_inicio/teste_fim | 2023-01-12..2023-07-10; 2023-07-11..2024-01-06; 2024-01-07..2024-07-04; 2024-07-05..2024-12-31 | VERIFICADO |
| 224 | app Overview: mesmas janelas de teste em todas as runs | iguais | `results/runs/*/folds.csv` | teste_inicio/teste_fim | iguais nas 10 runs | VERIFICADO |
| 225 | README/REPRO sementes 42..46 | 42 to 46 | `config.json h1` | run.sementes | [42, 43, 44, 45, 46] | VERIFICADO |
| 226 | LESSONS 4 objetivo count:poisson fixo, selecionar_objetivo false | count:poisson / false | `config.json h1` | modelos.xgboost | count:poisson / False | VERIFICADO |
| 227 | LESSONS 4 objetivo fixo em h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | count:poisson/false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 228 | README/app horizonte da run h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | 1 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | experimento.horizonte | 1 | VERIFICADO |
| 229 | LESSONS 4 objetivo fixo em mh_h5_cetesb_cetesb_full_20261110-211453 | count:poisson/false | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 230 | README/app horizonte da run mh_h5_cetesb_cetesb_full_20261110-211453 | 5 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/config.json` | experimento.horizonte | 5 | VERIFICADO |
| 231 | LESSONS 4 objetivo fixo em mh_h7_cetesb_cetesb_full_20261111-030322 | count:poisson/false | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 232 | README/app horizonte da run mh_h7_cetesb_cetesb_full_20261111-030322 | 7 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/config.json` | experimento.horizonte | 7 | VERIFICADO |
| 233 | LESSONS 4 objetivo fixo em mh_h15_cetesb_cetesb_full_20261111-070926 | count:poisson/false | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 234 | README/app horizonte da run mh_h15_cetesb_cetesb_full_20261111-070926 | 15 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/config.json` | experimento.horizonte | 15 | VERIFICADO |
| 235 | LESSONS 4 objetivo fixo em mh_h30_cetesb_cetesb_full_20261113-104814 | count:poisson/false | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 236 | README/app horizonte da run mh_h30_cetesb_cetesb_full_20261113-104814 | 30 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/config.json` | experimento.horizonte | 30 | VERIFICADO |
| 237 | LESSONS 4 objetivo fixo em ur_h1_cetesb_cetesb_full_20261116-191534 | count:poisson/false | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 238 | README/app horizonte da run ur_h1_cetesb_cetesb_full_20261116-191534 | 1 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/config.json` | experimento.horizonte | 1 | VERIFICADO |
| 239 | LESSONS 4 objetivo fixo em ur_h5_cetesb_cetesb_full_20261116-222823 | count:poisson/false | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 240 | README/app horizonte da run ur_h5_cetesb_cetesb_full_20261116-222823 | 5 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/config.json` | experimento.horizonte | 5 | VERIFICADO |
| 241 | LESSONS 4 objetivo fixo em ur_h7_cetesb_cetesb_full_20261117-073926 | count:poisson/false | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 242 | README/app horizonte da run ur_h7_cetesb_cetesb_full_20261117-073926 | 7 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/config.json` | experimento.horizonte | 7 | VERIFICADO |
| 243 | LESSONS 4 objetivo fixo em ur_h15_cetesb_cetesb_full_20261117-190532 | count:poisson/false | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 244 | README/app horizonte da run ur_h15_cetesb_cetesb_full_20261117-190532 | 15 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/config.json` | experimento.horizonte | 15 | VERIFICADO |
| 245 | LESSONS 4 objetivo fixo em ur_h30_cetesb_cetesb_full_20261117-221426 | count:poisson/false | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/config.json` | modelos.xgboost.objetivo/selecionar_objetivo | count:poisson/False | VERIFICADO |
| 246 | README/app horizonte da run ur_h30_cetesb_cetesb_full_20261117-221426 | 30 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/config.json` | experimento.horizonte | 30 | VERIFICADO |

**LESSONS / data card / ARCHITECTURE / REPRODUCIBILITY** — 66 números, 66 VERIFICADO

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 247 | LESSONS 1 tabela XGBoost MAE sábados | 33.31 | `erro_sabado_h1.csv` | total,XGBoost,MAE_sab | 33.3077 | VERIFICADO |
| 248 | LESSONS 1 tabela XGBoost MAE demais | 16.09 | `erro_sabado_h1.csv` | total,XGBoost,MAE_demais | 16.0941 | VERIFICADO |
| 249 | LESSONS 1 tabela XGBoost razão | 2.07 | `erro_sabado_h1.csv` | total,XGBoost,razao | 2.0696 | VERIFICADO |
| 250 | LESSONS 1 tabela SARIMAX MAE sábados | 37.08 | `erro_sabado_h1.csv` | total,SARIMAX,MAE_sab | 37.0816 | VERIFICADO |
| 251 | LESSONS 1 tabela SARIMAX MAE demais | 15.89 | `erro_sabado_h1.csv` | total,SARIMAX,MAE_demais | 15.8914 | VERIFICADO |
| 252 | LESSONS 1 tabela SARIMAX razão | 2.33 | `erro_sabado_h1.csv` | total,SARIMAX,razao | 2.3334 | VERIFICADO |
| 253 | LESSONS 1 tabela LSTM MAE sábados | 33.79 | `erro_sabado_h1.csv` | total,LSTM,MAE_sab | 33.7937 | VERIFICADO |
| 254 | LESSONS 1 tabela LSTM MAE demais | 16.54 | `erro_sabado_h1.csv` | total,LSTM,MAE_demais | 16.5436 | VERIFICADO |
| 255 | LESSONS 1 tabela LSTM razão | 2.04 | `erro_sabado_h1.csv` | total,LSTM,razao | 2.0427 | VERIFICADO |
| 256 | LESSONS 1 tabela INGARCH-NB MAE sábados | 35.86 | `erro_sabado_h1.csv` | total,INGARCH-NB,MAE_sab | 35.8648 | VERIFICADO |
| 257 | LESSONS 1 tabela INGARCH-NB MAE demais | 16.82 | `erro_sabado_h1.csv` | total,INGARCH-NB,MAE_demais | 16.8217 | VERIFICADO |
| 258 | LESSONS 1 tabela INGARCH-NB razão | 2.13 | `erro_sabado_h1.csv` | total,INGARCH-NB,razao | 2.1321 | VERIFICADO |
| 259 | LESSONS 1 tabela GAM-NB MAE sábados | 43.72 | `erro_sabado_h1.csv` | total,GAM-NB,MAE_sab | 43.7183 | VERIFICADO |
| 260 | LESSONS 1 tabela GAM-NB MAE demais | 18.26 | `erro_sabado_h1.csv` | total,GAM-NB,MAE_demais | 18.2638 | VERIFICADO |
| 261 | LESSONS 1 tabela GAM-NB razão | 2.39 | `erro_sabado_h1.csv` | total,GAM-NB,razao | 2.3937 | VERIFICADO |
| 262 | LESSONS 1 urgência XGBoost 13.64 / 15.08 / 0.90 | 13.64/15.08/0.90 | `erro_sabado_h1.csv` | urgencia,XGBoost | 13.6389/15.0843/0.9042 | VERIFICADO |
| 263 | LESSONS 1: razão < 1 para todo modelo (urgência) | <1 | `erro_sabado_h1.csv` | urgencia, razao | [0.946, 0.977, 0.891, 0.999, 0.904] | VERIFICADO |
| 264 | LESSONS 1 / README: sábado é o pior dia para todo modelo (total) — razão > 2 | >2 | `erro_sabado_h1.csv` | total, razao | [2.394, 2.132, 2.043, 2.333, 2.07] | VERIFICADO |
| 265 | LESSONS 1: 103 sábados de 720 datas de teste | 103 de 720 | `saida.txt` | seção C | presente | VERIFICADO |
| 266 | LESSONS 1 CNES 2091550 eletivas aos sábados 2019 | 244 | `estabelecimentos_ano.csv` | CNES=2091550,ano=2019,eletivas_sabado | 244.0 | VERIFICADO |
| 267 | LESSONS 1 CNES 2091550 eletivas aos sábados 2021 | 302 | `estabelecimentos_ano.csv` | CNES=2091550,ano=2021,eletivas_sabado | 302.0 | VERIFICADO |
| 268 | LESSONS 1 CNES 2091550 eletivas aos sábados 2022 | 1291 | `estabelecimentos_ano.csv` | CNES=2091550,ano=2022,eletivas_sabado | 1291.0 | VERIFICADO |
| 269 | LESSONS 1 CNES 2091550 eletivas aos sábados 2023 | 1562 | `estabelecimentos_ano.csv` | CNES=2091550,ano=2023,eletivas_sabado | 1562.0 | VERIFICADO |
| 270 | LESSONS 1 CNES 2091550 eletivas aos sábados 2024 | 1343 | `estabelecimentos_ano.csv` | CNES=2091550,ano=2024,eletivas_sabado | 1343.0 | VERIFICADO |
| 271 | LESSONS 1: 2022–2024 total == eletivas (CNES 2091550) | total==eletivas | `estabelecimentos_ano.csv` | 2022..2024 | [True, True, True] | VERIFICADO |
| 272 | LESSONS 1 perfil eletiva/sábado/CNES 2091550: 6,870 / 9 anos / 69.8% / 0 dias / 99.7% / 0.0% | 6870/9/69.8/0/99.7/0.0 | `perfil.csv` | Eletiva, sábado, CNES 2091550 | 6870.0/9.0/69.8/0.0/99.7/0.0 | VERIFICADO |
| 273 | LESSONS 1 perfil não eletiva: permanência mediana 5 dias, 10.2% óbitos | 5 / 10.2 | `perfil.csv` | Não eletiva | 5.0/10.2 | VERIFICADO |
| 274 | LESSONS 1 J30–J39: 39,243 / 35,958 eletivas / 11,206 CNES 2091550 | 39243/35958/11206 | `grupos_cid.csv` | J30–J39 | 39243/35958/11206 | VERIFICADO |
| 275 | LESSONS 1 J12–J18: 4,811 eletivas de 153,309 | 4811/153309 | `grupos_cid.csv` | J12–J18 | 4811/153309 | VERIFICADO |
| 276 | LESSONS 1 grupos com mecanismo plausível = J00–J06, J09–J11, J12–J18, J20–J22, J40–J47 | 5 grupos | `grupos_cid.csv` | sensivel=True | ['J00–J06', 'J09–J11', 'J12–J18', 'J20–J22', 'J40–J47'] | VERIFICADO |
| 277 | LESSONS 1 fração eletiva 12% a 14% em 2019–2024, sobe depois | 12–14% | `diario.csv` | sum(eletivo)/sum(total) por ano | {2019: 13.6, 2020: 12.0, 2021: 12.5, 2022: 12.4, 2023: 13.7, 2024: 14.1, 2025: 16.8, 2026: 25.0} | VERIFICADO |
| 278 | LESSONS 1 / data README urgência 263,399 mantidas | 263,399 | `sih_daily_lookahead_urgencia.meta.json` | total_aih_distintas | 263399 | VERIFICADO |
| 279 | LESSONS 1 / data README 39,896 eletivas excluídas | 39,896 | `sih_daily_lookahead_urgencia.meta.json` | filtro_carater_internacao (valor 39896) | presente | VERIFICADO |
| 280 | data README urgência: só códigos 01 e 02 ocorrem | 01, 02 | `sih_daily_lookahead_urgencia.meta.json` | filtro_carater_internacao | {"modo": "nao_eletivo", "campo": "CAR_INT", "codigos_aceitos": ["02", "03", "04", "05", "06"], "tabela_oficial": "Portaria SAS/MS 719/2007, art. 4: 01 eletivo, 02 urgencia, 03-06 acidentes/lesoes", "regra": "a primeira o … | VERIFICADO |
| 281 | data README urgência totais anuais 45,197; 34,734; 38,445; 46,159; 48,893; 49,971 | ... | `sih_daily_lookahead_urgencia.meta.json` | totais_anuais | {'2019': 45197, '2020': 34734, '2021': 38445, '2022': 46159, '2023': 48893, '2024': 49971} | VERIFICADO |
| 282 | data README urgência construída em 2026-11-16 | 2026-11-16 | `sih_daily_lookahead_urgencia.meta.json` | extraido_em | 2026-11-16T18:01:11 | VERIFICADO |
| 283 | data README urgência 2,192 dias | 2,192 | `sih_daily_lookahead_urgencia.meta.json` | dias | 2192 | VERIFICADO |
| 284 | LESSONS 3 / data README 303,295 / 77 duplicatas / 29,700 fora / 0 inválidas / 0 dias zero | 303295/77/29700/0/0 | `sih_daily_lookahead.meta.json` | total_aih_distintas,duplicatas_entre_competencias,registros_fora_do_periodo,dt_inter_invalidas,dias_com_zero | 303295/77/29700/0/0 | VERIFICADO |
| 285 | data README totais anuais 52,335; 39,482; 43,941; 52,718; 56,640; 58,179 | ... | `sih_daily_lookahead.meta.json` | totais_anuais | {'2019': 52335, '2020': 39482, '2021': 43941, '2022': 52718, '2023': 56640, '2024': 58179} | VERIFICADO |
| 286 | data README / REPRO 78 arquivos mensais 2019-01..2025-06 | 78 | `sih_daily_lookahead.meta.json` | len(competencias), min, max | 78 201901..202506 | VERIFICADO |
| 287 | data README look-ahead 6 competências; 4 capturam 99,8% | 6 / 99.8% | `sih_daily_lookahead.meta.json` | look_ahead_competencias / look_ahead_justificativa | 6 / medido: 4 competencias posteriores capturam 99,8% das internacoes do mes | VERIFICADO |
| 288 | data README municipio 355030 / DT_INTER / DIAG_PRINC J | 355030/DT_INTER/J | `sih_daily_lookahead.meta.json` | criterio_espacial, campo_data, regra_cid | MUNIC_RES (residencia) startswith 355030 \| DT_INTER \| str(DIAG_PRINC).strip().upper().startswith('J') | VERIFICADO |
| 289 | LESSONS 3 / data README TabNet: 72 meses, correlação 0.999983, viés -0.34% | 72/0.999983/-0.34 | `config.json h1` | dados.alvo.validacao | 72/0.999983/-0.34 | VERIFICADO |
| 290 | LESSONS 2 / data README CAMS 2,192 dias; n_obs 8 em 2,191 dias e 7 em um; sem NaN | 2192; 8:2191; 7:1 | `cams_daily_v2.csv` | len, n_obs.value_counts, isna | 2192 {8: 2191, 7: 1} NaN=0 | VERIFICADO |
| 291 | data README CAMS colunas | data,d2m,pm10,pm2p5,sp,t2m,u10,v10,t2m_c,d2m_c,rh,ws10,n_obs | `cams_daily_v2.csv` | columns | data,d2m,pm10,pm2p5,sp,t2m,u10,v10,t2m_c,d2m_c,rh,ws10,n_obs | VERIFICADO |
| 292 | data README poluentes 2,192 dias | 2,192 | `cetesb_poluentes_daily.csv` | len | 2192 | VERIFICADO |
| 293 | data README colunas poluentes co,no2,o3,pm10,pm25,so2 × _media,_n_estacoes,_dt | 19 colunas | `cetesb_poluentes_daily.csv` | columns | data,co_media,co_n_estacoes,co_dt,no2_media,no2_n_estacoes,no2_dt,o3_media,o3_n_estacoes,o3_dt,pm10_media,pm10_n_estacoes,pm10_dt,pm25_media,pm25_n_estacoes,pm25_dt,so2_media,so2_n_estacoes,so2_dt | VERIFICADO |
| 294 | data README SO2 2,190 dias com média, 2,108 com _dt; 2 dias sem estação (2021-01-10, 2021-01-11); 84 sem _dt | 2190/2108/2/84 | `cetesb_poluentes_daily.csv` | so2_media.notna, so2_dt.notna | 2190/2108/2/84 datas sem média: ['2021-01-10', '2021-01-11'] | VERIFICADO |
| 295 | data README / ARCHITECTURE 88 células NaN, todas em SO2 | 88 | `cetesb_poluentes_daily.csv` | isna().sum() | total 88, so2 88 | VERIFICADO |
| 296 | data README todos os poluentes cobrem 2,192 dias exceto SO2 | 0 NaN fora de SO2 | `cetesb_poluentes_daily.csv` | isna | 0 | VERIFICADO |
| 297 | ARCHITECTURE / data README gate h=1: um WARN cobertura_cetesb_poluentes (88 NaN em SO2) | 1 WARN | `data_quality.json h1` | checagens status!=PASS | [{"nome": "cobertura_cetesb_poluentes", "status": "WARN", "detalhe": "2192/2192 dias (100.0%), 88 células NaN", "dados": {"n_dias_comuns": 2192, "cobertura": 1.0, "n_celulas_nan": 88, "colunas": ["co_media", "co_n_estaco … | VERIFICADO |
| 298 | ARCHITECTURE / REPRO 79 features: AR 6, CAL 8, METEO 30, PM25 15, POLUENTES 20, PM25_MEDIA 5 | 79 | `manifest.json h1` | relatorio_dataset.n_features/features_por_bloco | 79 {'AR': 6, 'CAL': 8, 'METEO': 30, 'PM25': 15, 'POLUENTES': 20, 'PM25_MEDIA': 5} | VERIFICADO |
| 299 | data README POLUENTES usa pm10, no2, o3, co; SO2 descartado | 4 colunas | `manifest.json h1` | relatorio_dataset.colunas_poluentes/poluentes_descartados | ['pm10_media', 'no2_media', 'o3_media', 'co_media'] {'so2_media': {'n_nan': 2, 'exemplos': ['2021-01-10', '2021-01-11']}} | VERIFICADO |
| 300 | data README fonte_pm25 e fonte_meteo = cetesb nas runs | cetesb | `manifest.json h1` | fonte_pm25/fonte_meteo | cetesb/cetesb | VERIFICADO |
| 301 | app Models page: PM25 = média, nº estações, dispersão | 3 canais | `manifest.json h1` | relatorio_dataset.colunas_pm25 | ['pm25_media', 'pm25_n_estacoes', 'pm25_dt'] | VERIFICADO |
| 302 | app Models page: METEO 6 variáveis | 6 | `manifest.json h1` | relatorio_dataset.colunas_meteo | ['temp_media', 'temp_min', 'temp_max', 'temp_amplitude', 'ur_media', 'vv_media'] | VERIFICADO |
| 303 | REPRO versões numpy 2.4.1, pandas 3.0.0, xgboost 3.2.0, tensorflow 2.20.0, sklearn 1.8.0, statsmodels 0.14.6, scipy 1.17.0 | ... | `manifest.json h1` | versoes | {'python': '3.11.0', 'numpy': '2.4.1', 'pandas': '3.0.0', 'xgboost': '3.2.0', 'tensorflow': '2.20.0', 'scikit-learn': '1.8.0', 'statsmodels': '0.14.6', 'scipy': '1.17.0', 'plataforma': 'Windows-10-10.0.26200-SP0'} | VERIFICADO |
| 304 | REPRO runs executadas em Windows | Windows | `manifest.json h1` | versoes.plataforma | Windows-10-10.0.26200-SP0 | VERIFICADO |
| 305 | REPRO h=1 começou 2026-10-22 21:18:34 e terminou 23:43:02 | 21:18:34 / 23:43:02 | `manifest.json h1` | proveniencia.inicio/fim | 2026-10-22T21:18:34 / 2026-10-22T23:43:02 | VERIFICADO |
| 306 | REPRO validacao_metricas: métricas recalculadas batem a ~1e-14 | ~1e-14 | `validacao_metricas.json h1` | dif_max_* | 1.4e-14 | VERIFICADO |
| 307 | ARCHITECTURE DM: T=180 por fold e 720 agrupado; 528 linhas by_fold; 52 model_comparison | 720/528/52 | `validacao_metricas.json h1` | n_datas_teste, n_linhas_* | 720/528/52 | VERIFICADO |
| 308 | app Models page: família modelos_AR_CAL tem 21 contrastes agrupados, T=720 | 21 / 720 | `dm_contrastes.csv h1` | familia=modelos_AR_CAL, escopo=agrupado | 21 contrastes, T=[720] | VERIFICADO |
| 309 | data README meteo 2,192 dias, sem NaN | 2192 / 0 NaN | `cetesb_meteo_daily.csv` | len, isna | 2192 / 0 | VERIFICADO |
| 310 | data README meteo colunas | data,temp_media,temp_n_estacoes,temp_min,temp_max,temp_amplitude,ur_media,ur_n_estacoes,vv_media,vv_n_estacoes | `cetesb_meteo_daily.csv` | columns | data,temp_media,temp_n_estacoes,temp_min,temp_max,temp_amplitude,ur_media,ur_n_estacoes,vv_media,vv_n_estacoes | VERIFICADO |
| 311 | data README 23 estações no município, 19 com PM2.5 no cadastro | 23 / 19 | `estacoes_municipio_sp.csv` | len, mede_pm25 | 23 / 19 | VERIFICADO |
| 312 | data README disponibilidade_qualar: 19 estações × 6 parâmetros, 2019–2024 | 19×6=114 | `disponibilidade_qualar.csv` | nunique codigo, nunique parametro, len | 19 × 6 = 114; colunas ['codigo_qualar', 'nome', 'parametro', 'a2019', 'a2020', 'a2021', 'a2022', 'a2023', 'a2024'] | VERIFICADO |

**MODEL_CARD / api README / app** — 76 números, 76 VERIFICADO

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 313 | MODEL_CARD gerado em 2026-11-23T19:13:21+00:00 | 2026-11-23T19:13:21+00:00 | `models_demo/metadata.json` | data_treino | 2026-11-23T19:13:21+00:00 | VERIFICADO |
| 314 | MODEL_CARD / api README versão ba6d6c40-20261123 | ba6d6c40-20261123 | `models_demo/metadata.json` | versao | ba6d6c40-20261123 | VERIFICADO |
| 315 | MODEL_CARD sha256 do alvo ba6d6c40f2… | ba6d6c40f227648e49cf730276957b7db41082ffde189fa402aa233de166dfa9 | `models_demo/metadata.json` | entradas.sih.sha256 | ba6d6c40f227648e49cf730276957b7db41082ffde189fa402aa233de166dfa9 | VERIFICADO |
| 316 | MODEL_CARD horizontes 1, 7, 30; seed 42 | [1,7,30] / 42 | `models_demo/metadata.json` | horizontes, seed | [1, 7, 30] / 42 | VERIFICADO |
| 317 | MODEL_CARD libs xgboost 3.2.0, numpy 2.4.1, pandas 3.0.0, Python 3.11.0 | ... | `models_demo/metadata.json` | ambiente | {'python': '3.11.0', 'xgboost': '3.2.0', 'numpy': '2.4.1', 'pandas': '3.0.0'} | VERIFICADO |
| 318 | MODEL_CARD h=1 config | configs/h1_v02_cetesb_cetesb_classicos.yaml | `models_demo/metadata.json` | config | configs/h1_v02_cetesb_cetesb_classicos.yaml | VERIFICADO |
| 319 | MODEL_CARD h=1 AR lags | [1, 2, 3, 7, 14, 28] | `models_demo/metadata.json` | lags_alvo | [1, 2, 3, 7, 14, 28] | VERIFICADO |
| 320 | MODEL_CARD h=1 lags iguais ao config da dissertação | [1, 2, 3, 7, 14, 28] | `configs/h1_v02_cetesb_cetesb_classicos.yaml` | experimento.lags_alvo | [1, 2, 3, 7, 14, 28] | VERIFICADO |
| 321 | MODEL_CARD h=1 colunas de calendário | dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | `models_demo/metadata.json` | features | y_lag1,y_lag2,y_lag3,y_lag7,y_lag14,y_lag28,dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | VERIFICADO |
| 322 | MODEL_CARD h=1 n features | 14 | `models_demo/metadata.json` | len(features) | 14 | VERIFICADO |
| 323 | MODEL_CARD h=1 linhas de treino | 2164 | `models_demo/metadata.json` | n_linhas_treino | 2164 | VERIFICADO |
| 324 | MODEL_CARD h=1 primeira..última data alvo | 2019-01-29..2024-12-31 | `models_demo/metadata.json` | primeira_data_alvo/ultima_data_alvo | 2019-01-29..2024-12-31 | VERIFICADO |
| 325 | MODEL_CARD h=1 hiperparâmetros 600/5/0.05/0.8/0.8/5.0/1.0, sem early stopping | ... | `models_demo/metadata.json` | hiperparametros | {'objective': 'count:poisson', 'seed': 42, 'tree_method': 'hist', 'n_jobs': 4, 'early_stopping': False, 'n_estimators': 600, 'max_depth': 5, 'learning_rate': 0.05, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_we … | VERIFICADO |
| 326 | MODEL_CARD avaliação h=1: MAE ± std, RMSE, MASE, Naïve MAE | 18.56/2.34/24.79/0.645/28.71 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | xgboost AR_CAL MAE_medio, MAE_std_fold, RMSE_medio, MASE_medio; naive MAE_medio | 18.56/2.34/24.79/0.645/28.71 | VERIFICADO |
| 327 | MODEL_CARD avaliação h=1: 4 folds × 5 sementes | 4 × 5 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | n_folds, n_sementes | 4 × 5 | VERIFICADO |
| 328 | MODEL_CARD h=1 referência em metadata == model_comparison | iguais | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | referencia.xgboost_ar_cal | 18.556640 vs 18.556640 | VERIFICADO |
| 329 | MODEL_CARD h=1 run id de referência | h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | run_id | h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | VERIFICADO |
| 330 | MODEL_CARD h=7 config | configs/multihorizonte/mh_h7_cetesb_cetesb.yaml | `models_demo/metadata.json` | config | configs/multihorizonte/mh_h7_cetesb_cetesb.yaml | VERIFICADO |
| 331 | MODEL_CARD h=7 AR lags | [7, 8, 9, 13, 20, 34] | `models_demo/metadata.json` | lags_alvo | [7, 8, 9, 13, 20, 34] | VERIFICADO |
| 332 | MODEL_CARD h=7 lags iguais ao config da dissertação | [7, 8, 9, 13, 20, 34] | `configs/multihorizonte/mh_h7_cetesb_cetesb.yaml` | experimento.lags_alvo | [7, 8, 9, 13, 20, 34] | VERIFICADO |
| 333 | MODEL_CARD h=7 colunas de calendário | dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | `models_demo/metadata.json` | features | y_lag7,y_lag8,y_lag9,y_lag13,y_lag20,y_lag34,dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | VERIFICADO |
| 334 | MODEL_CARD h=7 n features | 14 | `models_demo/metadata.json` | len(features) | 14 | VERIFICADO |
| 335 | MODEL_CARD h=7 linhas de treino | 2158 | `models_demo/metadata.json` | n_linhas_treino | 2158 | VERIFICADO |
| 336 | MODEL_CARD h=7 primeira..última data alvo | 2019-02-04..2024-12-31 | `models_demo/metadata.json` | primeira_data_alvo/ultima_data_alvo | 2019-02-04..2024-12-31 | VERIFICADO |
| 337 | MODEL_CARD h=7 hiperparâmetros 600/5/0.05/0.8/0.8/5.0/1.0, sem early stopping | ... | `models_demo/metadata.json` | hiperparametros | {'objective': 'count:poisson', 'seed': 42, 'tree_method': 'hist', 'n_jobs': 4, 'early_stopping': False, 'n_estimators': 600, 'max_depth': 5, 'learning_rate': 0.05, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_we … | VERIFICADO |
| 338 | MODEL_CARD avaliação h=7: MAE ± std, RMSE, MASE, Naïve MAE | 23.40/3.45/30.93/0.810/28.87 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | xgboost AR_CAL MAE_medio, MAE_std_fold, RMSE_medio, MASE_medio; naive MAE_medio | 23.40/3.45/30.93/0.810/28.87 | VERIFICADO |
| 339 | MODEL_CARD avaliação h=7: 4 folds × 5 sementes | 4 × 5 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | n_folds, n_sementes | 4 × 5 | VERIFICADO |
| 340 | MODEL_CARD h=7 referência em metadata == model_comparison | iguais | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | referencia.xgboost_ar_cal | 23.397313 vs 23.397313 | VERIFICADO |
| 341 | MODEL_CARD h=7 run id de referência | mh_h7_cetesb_cetesb_full_20261111-030322 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | run_id | mh_h7_cetesb_cetesb_full_20261111-030322 | VERIFICADO |
| 342 | MODEL_CARD h=30 config | configs/multihorizonte/mh_h30_cetesb_cetesb.yaml | `models_demo/metadata.json` | config | configs/multihorizonte/mh_h30_cetesb_cetesb.yaml | VERIFICADO |
| 343 | MODEL_CARD h=30 AR lags | [30, 31, 32, 36, 43, 57] | `models_demo/metadata.json` | lags_alvo | [30, 31, 32, 36, 43, 57] | VERIFICADO |
| 344 | MODEL_CARD h=30 lags iguais ao config da dissertação | [30, 31, 32, 36, 43, 57] | `configs/multihorizonte/mh_h30_cetesb_cetesb.yaml` | experimento.lags_alvo | [30, 31, 32, 36, 43, 57] | VERIFICADO |
| 345 | MODEL_CARD h=30 colunas de calendário | dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | `models_demo/metadata.json` | features | y_lag30,y_lag31,y_lag32,y_lag36,y_lag43,y_lag57,dow,mes,feriado,fim_de_semana,sin1,cos1,sin2,cos2 | VERIFICADO |
| 346 | MODEL_CARD h=30 n features | 14 | `models_demo/metadata.json` | len(features) | 14 | VERIFICADO |
| 347 | MODEL_CARD h=30 linhas de treino | 2135 | `models_demo/metadata.json` | n_linhas_treino | 2135 | VERIFICADO |
| 348 | MODEL_CARD h=30 primeira..última data alvo | 2019-02-27..2024-12-31 | `models_demo/metadata.json` | primeira_data_alvo/ultima_data_alvo | 2019-02-27..2024-12-31 | VERIFICADO |
| 349 | MODEL_CARD h=30 hiperparâmetros 600/5/0.05/0.8/0.8/5.0/1.0, sem early stopping | ... | `models_demo/metadata.json` | hiperparametros | {'objective': 'count:poisson', 'seed': 42, 'tree_method': 'hist', 'n_jobs': 4, 'early_stopping': False, 'n_estimators': 600, 'max_depth': 5, 'learning_rate': 0.05, 'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_we … | VERIFICADO |
| 350 | MODEL_CARD avaliação h=30: MAE ± std, RMSE, MASE, Naïve MAE | 26.36/7.41/33.67/0.698/37.84 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | xgboost AR_CAL MAE_medio, MAE_std_fold, RMSE_medio, MASE_medio; naive MAE_medio | 26.36/7.41/33.67/0.698/37.84 | VERIFICADO |
| 351 | MODEL_CARD avaliação h=30: 4 folds × 5 sementes | 4 × 5 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | n_folds, n_sementes | 4 × 5 | VERIFICADO |
| 352 | MODEL_CARD h=30 referência em metadata == model_comparison | iguais | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | referencia.xgboost_ar_cal | 26.362735 vs 26.362735 | VERIFICADO |
| 353 | MODEL_CARD h=30 run id de referência | mh_h30_cetesb_cetesb_full_20261113-104814 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | run_id | mh_h30_cetesb_cetesb_full_20261113-104814 | VERIFICADO |
| 354 | api README /health origens válidas h=1 | 2019-01-28 / 2024-12-30 | `models_demo/metadata.json` | primeira_origem_valida/ultima_origem_valida | 2019-01-28 / 2024-12-30 | VERIFICADO |
| 355 | api README origem = alvo − h (h=1) | 2019-01-28 / 2024-12-30 | `models_demo/metadata.json` | primeira_data_alvo − h, 2024-12-31 − h | 2019-01-28 / 2024-12-30 | VERIFICADO |
| 356 | api README /health origens válidas h=7 | 2019-01-28 / 2024-12-24 | `models_demo/metadata.json` | primeira_origem_valida/ultima_origem_valida | 2019-01-28 / 2024-12-24 | VERIFICADO |
| 357 | api README origem = alvo − h (h=7) | 2019-01-28 / 2024-12-24 | `models_demo/metadata.json` | primeira_data_alvo − h, 2024-12-31 − h | 2019-01-28 / 2024-12-24 | VERIFICADO |
| 358 | api README /health origens válidas h=30 | 2019-01-28 / 2024-12-01 | `models_demo/metadata.json` | primeira_origem_valida/ultima_origem_valida | 2019-01-28 / 2024-12-01 | VERIFICADO |
| 359 | api README origem = alvo − h (h=30) | 2019-01-28 / 2024-12-01 | `models_demo/metadata.json` | primeira_data_alvo − h, 2024-12-31 − h | 2019-01-28 / 2024-12-01 | VERIFICADO |
| 360 | api README histórico 2019-01-01..2024-12-31 | 2019-01-01 / 2024-12-31 | `models_demo/metadata.json` | entradas.periodo | ['2019-01-01', '2024-12-31'] | VERIFICADO |
| 361 | api README: treino 'a few seconds' | segundos | `models_demo/metadata.json` | segundos_treino | [0.74, 0.36, 0.36] | VERIFICADO |
| 362 | api README exemplo de erro: h=30, origem 2019-01-01 → histórico insuficiente | 2019-01-01 < 2019-01-28 | `models_demo/metadata.json` | primeira_origem_valida h=30 | 2019-01-28 | VERIFICADO |
| 363 | api README exemplo de erro: h=7, origem 2024-12-31 → alvo além do fim | 2024-12-31 > 2024-12-24 | `models_demo/metadata.json` | ultima_origem_valida h=7 | 2024-12-24 | VERIFICADO |
| 364 | MODEL_CARD h=1 linhas removidas no warm-up = max lag; 2192 − removidas = linhas | 28 | `models_demo/metadata.json` | linhas_removidas_warmup | 28 | VERIFICADO |
| 365 | MODEL_CARD h=7 linhas removidas no warm-up = max lag; 2192 − removidas = linhas | 34 | `models_demo/metadata.json` | linhas_removidas_warmup | 34 | VERIFICADO |
| 366 | MODEL_CARD h=30 linhas removidas no warm-up = max lag; 2192 − removidas = linhas | 57 | `models_demo/metadata.json` | linhas_removidas_warmup | 57 | VERIFICADO |
| 367 | app Data page: 4 folds × 180 teste, 180 validação, treino mínimo 730 | 4/180/180/730 | `config.json h1` | split | {'protocolo': 'rolling_origin', 'n_folds': 4, 'dias_teste': 180, 'dias_validacao': 180, 'treino_minimo': 730} | VERIFICADO |
| 368 | app Data page: lags alvo [1,2,3,7,14,28], exógenas [1,2,3,7,14], período sazonal 7 | ... | `config.json h1` | experimento | {'lags_alvo': [1, 2, 3, 7, 14, 28], 'lags_exogenas': [1, 2, 3, 7, 14], 'periodo_sazonal': 7} | VERIFICADO |
| 369 | app Overview PM2.5 média (runtime, de cetesb_poluentes_daily.csv) | 15.5 | `cetesb_poluentes_daily.csv` | pm25_media.mean() | 15.5409 | VERIFICADO |
| 370 | app Overview estações/dia PM2.5 (runtime) | 10.6 | `cetesb_poluentes_daily.csv` | pm25_n_estacoes.mean() | 10.5981 | VERIFICADO |
| 371 | data README PM2.5 18 estações, 10.6/dia | 18 / 10.6 | `cetesb_poluentes_daily.meta.json` | por_poluente[pm25] | 18 / 10.6 | VERIFICADO |
| 372 | app Overview estações/dia PM2.5 (csv) ≈ meta n_est_medio | 10.6 | `cetesb_poluentes_daily.csv × meta` | pm25_n_estacoes.mean() vs n_est_medio | 10.60 vs 10.6 | VERIFICADO |
| 373 | data README PM10 14 estações (9.5/dia) | 14 / 9.5 | `cetesb_poluentes_daily.meta.json` | por_poluente[pm10] | 14 / 9.47 / dias 2192 / dias_com_dt 2192 | VERIFICADO |
| 374 | data README NO2 10 estações (7.3/dia) | 10 / 7.3 | `cetesb_poluentes_daily.meta.json` | por_poluente[no2] | 10 / 7.3 / dias 2192 / dias_com_dt 2192 | VERIFICADO |
| 375 | data README O3 15 estações (12.8/dia) | 15 / 12.8 | `cetesb_poluentes_daily.meta.json` | por_poluente[o3] | 15 / 12.83 / dias 2192 / dias_com_dt 2192 | VERIFICADO |
| 376 | data README CO 9 estações (7.4/dia) | 9 / 7.4 | `cetesb_poluentes_daily.meta.json` | por_poluente[co] | 9 / 7.38 / dias 2192 / dias_com_dt 2192 | VERIFICADO |
| 377 | data README SO2 7 estações (3.1/dia) | 7 / 3.1 | `cetesb_poluentes_daily.meta.json` | por_poluente[so2] | 7 / 3.12 / dias 2190 / dias_com_dt 2108 | VERIFICADO |
| 378 | data README SO2 2,190 dias com média, 2,108 com _dt (meta) | 2190 / 2108 | `cetesb_poluentes_daily.meta.json` | por_poluente[so2].dias/dias_com_dt | 2190 / 2108 | VERIFICADO |
| 379 | data README poluentes: 191 exportações usadas, 14 ignoradas | 191 / 14 | `cetesb_poluentes_daily.meta.json` | coleta.arquivos_usados/ignorados | 191 / 14 | VERIFICADO |
| 380 | data README poluentes: 21 estações de outros municípios excluídas | 21 | `cetesb_poluentes_daily.meta.json` | coleta.estacoes_fora_do_municipio | 21 | VERIFICADO |
| 381 | data README poluentes: horários 3,954,672 antes, 3,722,808 após dedup | 3954672 / 3722808 | `cetesb_poluentes_daily.meta.json` | coleta (registros) | [('arquivos_usados', 191), ('arquivos_ignorados', 14), ('registros_antes_dedup', 3954672), ('registros_apos_dedup', 3722808), ('repeticoes_descartadas', 231864)] | VERIFICADO |
| 382 | data README regra diária >= 18 de 24; D_t >= 2 estações | 18/24; >=2 | `cetesb_poluentes_daily.meta.json` | regra_diaria, regra_dt | média das horas válidas, exigindo >= 18 de 24 \| sigma amostral (ddof=1)/(media+1e-9), exigindo >= 2 estações | VERIFICADO |
| 383 | data README meteo: 54 exportações usadas, 14 ignoradas; 5 estações metropolitanas excluídas | 54 / 14 / 5 | `cetesb_meteo_daily.meta.json` | coleta | 54 / 14 / 5 | VERIFICADO |
| 384 | data README meteo temp 6 (4.2/dia), ur 6 (3.6/dia), vv 10 (7.5/dia), 2,192 dias | ... | `cetesb_meteo_daily.meta.json` | por_variavel | {'temp': (6, 4.17, 2192), 'ur': (6, 3.6, 2192), 'vv': (10, 7.47, 2192)} | VERIFICADO |
| 385 | data README meteo descartados por cobertura temp 524, ur 454, vv 483 | 524/454/483 | `cetesb_meteo_daily.meta.json` | dias_descartados_por_cobertura | {'temp': 524, 'ur': 454, 'vv': 483} | VERIFICADO |
| 386 | data README meteo regra >= 18 de 24, sem D_t | 18/24 | `cetesb_meteo_daily.meta.json` | regra_diaria, sem_dt | média/min/max das horas válidas, exigindo >= 18 de 24 | VERIFICADO |
| 387 | app Home: melhor MAE h=1 (runtime) | XGBoost 18.56 / MASE 0.645 | `arcal_por_horizonte_dois_alvos.csv` | min MAE total h=1 | XGBoost 18.5566 | VERIFICADO |
| 388 | app Home: AIH distintas total / urgência (runtime) | 303,295 / 263,399 | `meta.json` | total_aih_distintas | lido do meta | VERIFICADO |

**tempos** — 2 números, 0 VERIFICADO

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 389 | README L97 / Makefile: suíte de testes 'about 5 minutes' | ~5 min | `(nenhum artefato)` | medido nesta auditoria | 3m52s (e87d574, esta máquina); 1m44s (clone limpo do gerente, 44946b4) | SEM FONTE |
| 390 | REPRODUCIBILITY L82: `--smoke` 'takes about a minute' | ~1 min | `(nenhum artefato)` | medido nesta auditoria | 10,5 s (configs/smoke.yaml, esta máquina) | SEM FONTE |

## (d) Legado e escopo

| Checagem | Comando / fonte | Resultado |
|---|---|---|
| Lista "fica fora" em `git ls-files` | grep por `src/main.py`, `join_and_lstm`, `src/tests/`, `metrics/`, `reports/metrics`, `fetch_sih_bq`, `sih_datasus_pipeline`, `microdados`, `environment.yml`, `handoff`, `CLAUDE.md`, `preliminar_`, `.env`, `.cdsapirc`, `env/` | **0 ocorrências** (389 arquivos versionados em `e87d574`; mesmos arquivos + `verificar_inventario.py` em `0bd6c0a`). |
| Mesma lista no histórico | `git log --all --diff-filter=A --name-only` | nenhum desses caminhos jamais adicionado; nenhum arquivo removido no histórico. |
| `src/` só com módulos do inventário | `comm` entre `git ls-files src tests configs data` e a coluna `destino` de `docs/INVENTARIO_FASE0.tsv` | `src/` (34 módulos) = inventário, sem sobra. Fora do inventário só o que foi escrito para o portfólio: `configs/smoke.yaml`, `data/README.md`, `tests/test_api_forecast.py`, `tests/test_app_smoke.py`, `tests/test_tracking_importar_runs.py`. Nenhum destino do inventário falta no Git. |
| Sha256 do inventário vs working copy | script próprio (hashlib) + `docs/scripts/verificar_inventario.py` | 338/339 exatos; `notebooks/gerar_notebook.py` difere porque foi editado pelo WP3 (leitura de `dados_painel/` em vez do Drive) — declarado em `EDITADOS_DEPOIS`; o TSV ainda traz o sha da origem (f753a7…), o que é coerente com a definição do TSV ("sha256 na origem"). |
| Rótulo provisório | `grep -ci provision` | README 6×; `app/ui.py` (`aviso_provisorio` chamado em `Home.py` e nas 4 páginas; `ui.fonte` acrescenta "provisional (pre-defense)" a toda legenda); `app/pages/4_…:114`; `models_demo/MODEL_CARD.md` 2×; `CITATION.cff` 2×; `docs/LESSONS.md` e `docs/REPRODUCIBILITY.md` 1× cada. `api/README.md` não usa a palavra, mas abre com "Demonstration, not a dissertation result" e remete ao model card (aceitável). |
| CAMS como "fonte principal"? | grep `cams … (fonte principal\|main source\|primary source)` e inverso | 3 ocorrências, todas dizendo que a **CETESB** é a principal e o CAMS alternativa (`README.md:16`, `CITATION.cff:31`, `docs/LESSONS.md:38`); `data/README.md` §4 e `app/pages/4_…:449` idem. **OK.** |
| "dobra" (deve ser "fold") | `grep -niw "dobra\|dobras"` | 0 em README, docs, app, api, model card, data card, figuras. 5 ocorrências em **comentários de código herdado**: `src/models/sarimax_model.py:90-91`, `tests/test_sarimax_model.py:305,315,347` ("na dobra 4 do conjunto COMPLETO"). Não é texto da dissertação nem legenda; fica como item de baixa prioridade (item 11). |
| Desempenho de TCN / TFT / SHAP | `grep -niE "\bTCN\b\|\bTFT\b\|\bSHAP\b"` fora de `src/`, `tests/`, `configs/` | `README.md:131` e `app/pages/4_…:123` dizem explicitamente que **não** foram executados; `results/runs/*/summary.md` ("TCN e TCN–LSTM fora de escopo"). Nenhuma afirmação de desempenho. **OK.** |
| Runs `preliminar_*` | — | nenhuma copiada; `docs/LESSONS.md` história 4 cita `preliminar_h1_full_20260727-163313` só como registro de defeitos (sem números), e o comentário de `run_preliminary.py:409-412` sobre `preliminar_h1_full_20260727-161742` existe como descrito. |

**Veredito (d): OK.**

## (e) Consistência entre pacotes

| Item | Esperado | Encontrado | Veredito |
|---|---|---|---|
| `docker-compose.yml` → app | `streamlit run app/Home.py` | `command: ["streamlit", "run", "app/Home.py", …]`, porta 8501, volumes `results/`, `data/`, `notebooks/dados_painel/` somente leitura | OK |
| `docker-compose.yml` → api | `uvicorn api.main:app` | `["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]`, healthcheck em `/health`, volumes `models_demo/` e `data/` | OK |
| `docker-compose.yml` → mlflow | file store `./mlruns` (o que `tracking/importar_runs.py` grava: `TRACKING_URI_PADRAO = "file:./mlruns"`) | `--backend-store-uri /app/mlruns` montado de `./mlruns`, `MLFLOW_ALLOW_FILE_STORE=true` | OK |
| `docker-compose.yml` → `build:` | cada serviço constrói ou reaproveita a imagem | só `app` tem `build: *build`; `api` e `mlflow` só `image:`. `docker compose up` (tudo) funciona porque `app` constrói a imagem; **`docker compose up api` sozinho — exatamente o comando do `api/README.md:24` — falha se a imagem `sp-respiratory-admissions-forecast:local` ainda não existir** (tenta `pull`). Não testado com daemon (indisponível nesta máquina, como o Makefile registra); leitura do arquivo. | ACHADO (menor) |
| `Makefile` | `app`, `api`, `mlflow`, `test`, `smoke` | `streamlit run app/Home.py --server.port 8501`; `uvicorn api.main:app --host 127.0.0.1 --port 8000`; `mlflow server … --backend-store-uri ./mlruns` com `MLFLOW_ALLOW_FILE_STORE=true`; `pytest -q`; smoke com `configs/smoke.yaml` | OK |
| `Dockerfile` | instala os extras | `uv sync --frozen --no-dev --extra app --extra api --extra tracking`; `COPY . /app` protegido por `.dockerignore` (`.env`, `.env.*` exceto `.env.example`, `.cdsapirc`, `*.pem`, `*.key`, `.git`, `.venv`, `reports`, `mlruns`, `data/raw`, `hourly_*`, `*microdados*`, `handoff*`) | OK |
| Extra `app` vs imports de `app/` | `streamlit`, `plotly` (+ `pandas`, `numpy` do núcleo) | `app/*.py` e `app/pages/*.py` importam `streamlit`, `plotly.graph_objects`, `plotly.subplots`, `pandas`, `numpy`, `json`, `pathlib`; extra `app = ["streamlit==1.67.0", "plotly==7.1.0"]` | OK |
| Extra `api` vs imports de `api/` | `fastapi`, `uvicorn` (+ `pydantic` via fastapi, `xgboost`/`pandas` do núcleo) | `api/main.py` importa `fastapi`, `pydantic`, `xgboost`, `pandas`, `models_demo.comum`, `src.features…`; extra `api = ["fastapi==0.165.0", "uvicorn==0.54.0"]`; `httpx` (TestClient) no grupo `dev` | OK |
| Extra `tracking` vs imports de `tracking/` | `mlflow` | `tracking/importar_runs.py` importa `mlflow`, `MlflowClient`, `mlflow.entities`; extra `tracking = ["mlflow==3.18.0"]` | OK |
| `models_demo/` | só núcleo | `yaml`, `xgboost`, `numpy`, `pandas`, `src.*` — todos no núcleo | OK |
| CI (`.github/workflows/ci.yml`) | mesmas receitas | `uv sync --all-extras`, `uv run pytest -q`, smoke com `configs/smoke.yaml`, ruff só em `app api tracking models_demo` | OK |
| README sobre a API | "só origens cujo alvo `origem + h` cai dentro de 2019–2024 (in-sample por construção)"; `GET /health`, `GET /forecast`; modelos de demonstração, 1 semente, série inteira | `api/main.py:185-211` recusa origem fora de `hist_inicio..hist_fim`, abaixo de `primeira_origem` e acima de `ultima_origem = ultima_data_alvo − h`; janelas no `metadata.json` (h=1: 2019-01-28..2024-12-30; h=7: ..2024-12-24; h=30: ..2024-12-01) batem com `api/README.md` e com `2024-12-31 − h`; `MODEL_CARD.md` "Limitations" diz o mesmo | OK |
| README sobre MLflow | "copia `config.json`, `manifest.json`, `metrics.json`; nada é recalculado" | docstring de `tracking/importar_runs.py` e `docs/ARCHITECTURE.md` idem; teste `tests/test_tracking_importar_runs.py` passa | OK |
| `data/README.md` §6 "What is not here: Any other municipality or period" | — | o painel do sábado (`diario.csv`, `estabelecimentos_ano.csv`) cobre **2025-01-01 a 2026-02-28**, além do período 2019–2024; o app avisa que 2025–2026 não foi conferido contra o TabNet, mas o data card nega a existência de outro período | ACHADO (menor) |
| `pyproject.toml` / `CITATION.cff` | versão e data | `version = "0.1.0"` nos dois; `date-released: 2026-11-23`; dependências do núcleo iguais ao `requirements-executado-…` e ao `environment.txt` das runs (numpy 2.4.1, pandas 3.0.0, xgboost 3.2.0, tensorflow 2.20.0, keras 3.13.1, scikit-learn 1.8.0, statsmodels 0.14.6, scipy 1.17.0, pyarrow 23.0.0, matplotlib 3.10.8, PyYAML 6.0.3, joblib 1.5.3, patsy 1.0.2, Jinja2 3.1.6, tabulate 0.10.0, datasus-dbc 0.1.3, dbc-to-dbf 1.0.1, dbfread 2.0.7) | OK |
| `.pre-commit-config.yaml` | "maior arquivo versionado hoje: ~2,2 MB" (`--maxkb=2500`) | maior arquivo: `notebooks/dados_painel/erros_modelos_ar_cal.csv`, 2.204.207 bytes | OK |
| `docs/ARCHITECTURE.md` vs código | nomes e regras citadas | `teste_dm_v02.py:107` (`> 1e-6` → falha); `run_preliminary.py:217` (`_validar_chaves`), `CHAVES_POR_MODELO`; `base.py:25` (`usa_semente`); `metrics.py` (`mae`, `rmse`, `r2`, `mase`, `skill`); `splits.py` (`class Fold`, `rolling_origin`); `sih_build_lookahead.py` (`--carater nao_eletivo`); `cams_rebuild_daily.py:24-30,105` (`--comparar`, saída 2); `forecasting_features.py:53-68` (EAC4 single-level sem NO2/O3/CO/SO2 em superfície) | OK |

**Veredito (e): ACHADO (menor)** — dois itens de baixa gravidade (itens 6 e 8 da lista).

## (f) Testes

| Comando | Commit | Resultado | Tempo |
|---|---|---|---|
| `uv run pytest -q` (nesta máquina, `.venv` sincronizado com `--all-extras`) | `e87d574` | **225 passed, 0 failed, 0 error** (exit 0; 225 marcadores de progresso: 72 + 72 + 72 + 9). Avisos: `StarletteDeprecationWarning` (httpx/testclient) e um `RuntimeWarning: overflow in exp` esperado em `test_ingarch_nb::test_predict_falha_alto_se_previsao_sair_da_faixa_do_alvo` | 3m52s (`time`) |
| `uv run pytest -q` (clone limpo do gerente, reportado) | `44946b4` | 225 passed | 1m44s |
| `uv run python -m src.experiments.run_preliminary --config configs/smoke.yaml --smoke` | `e87d574` | exit 0; `STATUS: PRELIMINARY_VALIDATED_TARGET`; 1 fold (teste 2024-12-02..2024-12-31, 30 dias), Naïve, Seasonal Naïve, XGBoost `AR`/`AR_CAL`; artefatos em `reports/experiments/smoke_smoke_20261123-162611/` (git-ignorado). **Nunca é resultado.** | 10,5 s |
| smoke (clone limpo do gerente, reportado) | `44946b4` | PASS | 10 s |
| `uv run python docs/scripts/verificar_inventario.py` | `0bd6c0a` | `exatos=338 iguais_apos_eol=0 editados_declarados=1 erros=0` | < 5 s |
| `uv run --with pre-commit pre-commit run gitleaks --all-files` | `44946b4` | Passed | — |

A suíte não foi repetida em `44946b4`/`0bd6c0a` (a pedido do gerente; os commits só alteram fim de linha no índice e acrescentam um script fora de `tests/`).

## Itens a corrigir

| # | Arquivo : linha | Problema | Correção sugerida | Dono |
|---:|---|---|---|---|
| 1 | `README.md:88` e `README.md:137` | DIVERGENTE: "covariáveis ambientais não melhoram `AR_CAL` de forma que sobreviva ao teste pareado" — 6 contrastes de ablação com DM < 0 e p Holm < 0,05 (SARIMAX urgência h = 1 vs `AR_CAL`: p 0,005 e 0,014; XGBoost urgência h = 15 `POLUENTES` dado `METEO`: p 0,001; LSTM `PM25MEDIA` dado `METEO` em total h = 7, urgência h = 5 e 7). | Restringir a frase ao alvo total em h = 1 (onde é verdadeira) e mencionar as exceções do alvo de urgência, ou citar `B2_dm_ablacao_por_h.csv` com a contagem (53 piores / 6 melhores de 59 significativos). Mesma correção no Resumo em português. | WP5 |
| 2 | `notebooks/dados_painel/estabelecimentos_ano.csv` (col. `nome`, 8 linhas do CNES 2091550); `notebooks/gerar_notebook.py:146`; `notebooks/painel_carater_internacao.ipynb`; `notebooks/preparar_dados_painel.py:88`; colunas `cema`/`eletivas_cema` | Nome "Instituto CEMA" além do que D7 autoriza ("citar o código"). | Decisão do gerente: (a) ampliar D7 em `docs/DECISOES.md` para nome + código (informação pública do CNES), ou (b) gerar o CSV com `nome = "CNES 2091550"`, regenerar o notebook e atualizar o sha256 em `docs/INVENTARIO_FASE0.tsv` + `verificar_inventario.py`. | gerente |
| 3 | `docs/LESSONS.md:19` | Diz que o estabelecimento está "named in `estabelecimentos_ano.csv`" — depende do item 2. | Se (b): trocar por "identified by its CNES code in …". | WP5 |
| 4 | `app/pages/3_The_Saturday_case.py:377` | Legenda "names: consult CNES/DATASUS" enquanto o CSV já traz o nome do CNES 2091550. | Alinhar com a decisão do item 2. | WP3 |
| 5 | `notebooks/dados_painel/diario.csv` (col. `cema`) | 298 células estabelecimento × dia com 1–4 internações de um estabelecimento identificado; a regra de supressão só cobre estabelecimento × ano. | Decidir: estender a regra (suprimir < 5 ou publicar `cema` agregado por semana) ou registrar em `manifest.json`/`DECISOES.md` que contagens diárias de um estabelecimento público são aceitas. | gerente |
| 6 | `data/README.md:70` | "Any other municipality or period" não está aqui, mas o painel do sábado cobre 2025-01 a 2026-02. | Acrescentar exceção: "except the Saturday panel in `notebooks/dados_painel/`, which extends to 2026-02-28 (unchecked against TabNet)". | WP5 |
| 7 | `README.md:97`, `Makefile:6`, `docs/REPRODUCIBILITY.md:82` | SEM FONTE: "about 5 minutes" (medido 3m52s aqui, 1m44s no clone limpo) e "`--smoke` … about a minute" (medido 10,5 s). | Trocar por "a few minutes" / "about ten seconds" ou citar a máquina de referência. | WP5 |
| 8 | `docker-compose.yml` (serviços `api` e `mlflow`) | Sem `build:`; `docker compose up api` (comando do `api/README.md:24`) falha se a imagem ainda não foi construída. | Acrescentar `build: *build` aos três serviços (compose constrói uma vez) ou trocar o comando do `api/README.md` por `docker compose up --build api`. | WP1 / WP4 |
| 9 | `app/pages/3_The_Saturday_case.py:455-528` (seções 6 e tabela h = 1) | Duas definições de MAE na mesma página (média das sementes por data vs todas as sementes): XGBoost h = 1 sábado 33,21 vs 33,31; MAE 18,45 vs 18,56 do README. | Nota curta na seção 6: "MAE here is computed on seed-mean predictions, so it is ≤ the seed-mean MAE of the README (18.56 at h = 1)". | WP3 |
| 10 | `src/ingestion/cetesb_build_poluentes.py:16`, `cetesb_build_meteo.py:47`, `cetesb_build_daily.py:20` | Nome de usuário em exemplos de uso (`C:/Users/mathe/Downloads`). | Trocar por `<pasta das exportações do QUALAR>`; como `src/` é cópia curada, declarar em `verificar_inventario.py` (`EDITADOS_DEPOIS`). | gerente |
| 11 | `src/models/sarimax_model.py:90-91`; `tests/test_sarimax_model.py:305,315,347` | "dobra" em comentários de código herdado (regra do projeto: "fold"). | Baixa prioridade; se tocar nesses arquivos por outro motivo, trocar por "fold" e declarar no inventário. | gerente |
| 12 | `docs/INVENTARIO_FASE0.tsv` (linha `notebooks/gerar_notebook.py`) | Sha da origem (f753a7…) não é o do arquivo versionado (edição do WP3); já declarado em `verificar_inventario.py` (0bd6c0a), então **resolvido**; fica registrado. | Opcional: coluna/nota "editado depois" no próprio TSV. | — |

## O que não foi possível verificar

- `docker compose up` / `docker build` não foram executados (sem daemon Docker nesta máquina, como o `Makefile` registra); a consistência do compose é leitura de arquivo.
- As afirmações do `docs/LESSONS.md` que remetem a documentos da dissertação não copiados (PROTOCOLO §0.17, §0.23, CHANGELOG, cabeçalho de `fetch_sih_bq_enriquecido.py`) foram conferidas **só por leitura** no repositório da dissertação (`D:\Project\dataspell_workspace_template`, somente leitura): o cabeçalho do script de BigQuery usa de fato `br_ms_sih.servicos_profissionais` e `id_municipio_estabelecimento_aih`; o PROTOCOLO §0.17 contém os 35 % / r 0,95 que o LESSONS diz omitir de propósito. Nenhum número desses documentos foi trazido para cá.
- O `.venv` desta máquina foi usado para os testes; a reprodução bit a bit em outro SO não foi tentada (o `REPRODUCIBILITY.md` já diz que não é garantida).

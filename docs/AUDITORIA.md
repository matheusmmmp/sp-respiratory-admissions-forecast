# Auditoria WP-A (segunda rodada) — sp-respiratory-admissions-forecast

- **Data:** 2026-11-26
- **Commit auditado:** `b90f3e2` (`chore(release): versão 0.1.1 para o arquivamento no Zenodo`), `main` = `origin/main`, versão 0.1.1. Árvore limpa (`git status --porcelain` vazio) no início e no fim. Escopo: os 23 commits `44946b4..b90f3e2` (124 arquivos, +13.854/−853 linhas), com conferência completa de segredos, privacidade e legado no repositório inteiro e no histórico (30 commits, todas as refs).
- **Método:** tudo conferido com `uv run python` (pandas/json/hashlib), `git`, `gh` e `curl`, nunca de cabeça. Os scripts de conferência (`c1.py` a `c4.py`, `app_dump.py`) ficaram no scratchpad da sessão e não entram no repositório. O app foi renderizado de verdade (`streamlit.testing.v1.AppTest`, cinco páginas × duas línguas) e os valores mostrados foram comparados com cálculos próprios sobre os arquivos de origem. `docs/scripts/conferir_numeros.py`, `build_site.py --check` e `verificar_inventario.py` foram executados e registrados, mas **não** usados como fonte: a conferência é independente e lê os artefatos primários (`model_comparison.csv`, `metrics_by_fold.csv`, `manifest.json`, `dm_contrastes.csv` das 10 runs) em vez das tabelas já agregadas, sempre que possível.
- **Efeito colateral registrado:** `conferir_numeros.py` regrava `docs/CONFERENCIA_NUMEROS_WP5.md` a cada execução (carimbo de hora e CRLF no Windows), o que sujou a árvore; o arquivo foi restaurado com `git checkout --` e nada mais foi tocado (ver item 7).

## Veredito por seção

| Seção | Veredito | Resumo |
|---|---|---|
| (a) Segredos | **OK** | gitleaks v8.24.3 sobre o histórico inteiro (`gitleaks git --log-opts=--all`, 30 commits, 38 MB) e sobre a árvore de `HEAD` exportada (`git archive`): *no leaks found*. detect-secrets (27 plugins) em `git ls-files`: 667 achados em 40 arquivos: 657 "Hex High Entropy", **todos** sha256 (634) ou hashes de commit (23), e 10 "Base64", que são caminhos. Varredura própria por padrões de token (GitHub, AWS, HF, Slack, OpenAI, Google, chave privada, `CDSAPI_KEY=` com valor) em `git ls-files` e em `git log -p --all` (1.388.113 linhas): zero. Nenhum `.env`, `.cdsapirc`, `*.pem`, `*.key` jamais adicionado. **Ressalva de método:** o hook `gitleaks` do pre-commit só varre o diff *staged*, então `pre-commit run gitleaks --all-files` passa sem varrer nada (a auditoria anterior se apoiou nele; esta não). |
| (b) Privacidade | **OK** | Todos os dados versionados são agregados; `site/data/` são 16 cópias byte a byte de `results/` + um JSON derivado (médias por modelo × h). Nenhum `N_AIH` como coluna, nenhum `predictions.csv`, nenhum arquivo do MLflow local (`mlruns/`, `mlflow.db`, `catalogo_runs.yaml`, `D:\Project\mlflow_pesquisa`) no índice nem no histórico. Os dois achados de privacidade da rodada anterior foram resolvidos por decisão do autor (D7 ampliada, D8). O único `C:\Users\…` (docstrings da CETESB) saiu. Restam caminhos `D:\Project\…` sem nome de usuário, todos aceitáveis (proveniência ou exemplo de uso local). |
| (c) Números | **934 VERIFICADO / 4 DIVERGENTE / 6 SEM FONTE** (944) | As 560 células MAE/MASE (README EN, README PT, página EN, página PT), as 100 linhas de metadados de run, o texto corrido dos READMEs (80), as legendas, a tabela DM e o resumo das páginas (106), os 22 `.prov.json` + `build_provenance.json`, o app nas duas línguas (58) e os números novos de `docs/` batem com os artefatos. Divergentes: "Saturday is the worst day for **every** model" (o Naïve tem o pior erro no domingo; EN e PT), "no trained weights" (há três modelos XGBoost treinados em `models_demo/`) e "byte-identical" aplicado a `predictions.csv`. Sem fonte: dois tempos de execução datados, "~uma ordem de grandeza menor" da imagem enxuta, "~1 GB de wheels", a minor do uv que gerou o lock e J34/J35 no app. |
| (d) Legado e escopo | **OK** | Nenhum arquivo da lista "fica fora" em `git ls-files` nem no histórico (nenhum arquivo jamais removido); `src/` só com módulos do inventário (`verificar_inventario.py`: `exatos=317 iguais_apos_eol=17 editados_declarados=5 erros=0`; as cinco edições estão declaradas em `EDITADOS_DEPOIS`); rótulo provisório em README EN (7×) e PT (7×), app (faixa em toda página, nas duas línguas, conferida pelo teste e pela renderização), página (24× em cada língua), model card (2×), `CITATION.cff` (2×); CAMS nunca "fonte principal"; "dobra" só em comentários de código herdado; TCN/TFT/SHAP só como "não executados"; nenhum DOI inventado. Ressalva: a página do projeto não diz que a API é in-sample nem que não está publicada (item 9). |
| (e) Consistência | **ACHADO (médio)** | Versão 0.1.1 coerente em `pyproject.toml`, `uv.lock`, `CITATION.cff` e no BibTeX de `site/` versionado, **mas** a página publicada no GitHub Pages ainda mostra `version = {0.1.0}` (deploy manual anterior ao bump) e os READMEs citam a release `v0.1.0`. A prova "sem `--mlflow` a saída é idêntica à do runner de referência" (`test_sem_mlflow_identico_ao_runner_de_referencia`) passa localmente mas é **pulada no CI e no contêiner** (checkout raso; `.git` fora da imagem), então o CI nunca exerce a afirmação do README/ARCHITECTURE/D9. `.gitattributes` × pre-commit, `.dockerignore` × testes, extras × imports, compose × Makefile × CI: coerentes; menor: o ruff do pre-commit não cobre `deploy/`, que o CI e o Makefile cobrem. READMEs EN e PT: mesma estrutura (11 títulos), mesmos links (fora o selo traduzido), mesmos números. CI mais recente (`b90f3e2`): verde. |
| (f) Testes | **278 passed / 0 failed / 0 skipped** | `uv run pytest -q`: 278 testes coletados, 278 pontos de progresso, exit 0, 7m18s nesta máquina (com gitleaks e detect-secrets rodando em paralelo); `tests/test_runner_mlflow.py -v`: 8 passed em 1m56s, inclusive a prova de referência. Smoke: exit 0, `STATUS: PRELIMINARY_VALIDATED_TARGET`, 8,98 s. CI `b90f3e2`: pytest 277 + 1 skip; docker (pytest + smoke no contêiner) idem. |

### Comparação com a auditoria anterior (`44946b4`)

| Item anterior | Situação em `b90f3e2` | Evidência |
|---|---|---|
| 1. README: "covariáveis não melhoram `AR_CAL`" contrariado por 6 contrastes | **Resolvido** | README EN/PT L94 reescrito: 500 contrastes, 59 significativos após Holm, 53 piores e 6 melhores, com os seis p de Holm; todos reconferidos a partir dos `dm_contrastes.csv` das 10 runs (tabela c.3, linhas 4–14). |
| 2. Nome "Instituto CEMA" além da D7 | **Resolvido (decisão)** | D7 ampliada em 2026-11-23: nome e código podem aparecer juntos. App lê o nome do csv (`sab.nota_estab`). |
| 3. `LESSONS.md:19` "named in" | **Resolvido** | Coerente com a D7 ampliada. |
| 4. Legenda do app "names: consult CNES/DATASUS" | **Resolvido** | Texto atual: "the highlighted establishment is {nome}, name read from the column `nome` of this csv". |
| 5. `diario.csv` coluna `cema` com células diárias < 5 | **Resolvido (decisão)** | D8: aceitas como estão, motivo registrado. |
| 6. `data/README.md` §6 "nenhum outro período" | **Resolvido** | Exceção do painel do sábado até 2026-02-28 acrescentada. |
| 7. Tempos SEM FONTE (suíte "~5 min", smoke "~1 min") | **Parcial** | Agora "a few minutes (3m52s … 2026-11-23)" e "about ten seconds (10.5 s … 2026-11-23)": medições datadas, ainda sem artefato. Hoje: 7m18s local (com carga), 3m46s no CI, smoke 8,98 s. Mantido como SEM FONTE de baixa gravidade (item 17). |
| 8. `docker compose up api` sem `build:` | **Resolvido** | Os três serviços têm `build: *build`; o CI sobe o `api` com `--no-build` depois do build e espera `/health`. |
| 9. Duas definições de MAE na página do sábado | **Resolvido** | Nota `sab.nota_mae` explica: 18,56 / 33,31 (média dos MAE por semente) contra 18,45 / 33,21 (previsão média das sementes). |
| 10. `C:/Users/<usuário>/Downloads` nas docstrings da CETESB | **Resolvido** | Trocado por `<pasta das exportacoes do QUALAR>`; declarado em `EDITADOS_DEPOIS`. |
| 11. "dobra" em comentários de código herdado | **Pendente** (baixa) | `src/models/sarimax_model.py:90-91`, `tests/test_sarimax_model.py:305,315,347`. |
| 12. Sha do `gerar_notebook.py` no inventário | **Resolvido** | Declarado; `verificar_inventario.py` sem erros. |

---

## (a) Segredos

### a.1 Ferramentas executadas

| Ferramenta | Comando | Resultado |
|---|---|---|
| gitleaks v8.24.3 (binário do cache do pre-commit), histórico | `gitleaks git --log-opts="--all" --redact -v .` | 30 commits, ~38,0 MB, **no leaks found** |
| gitleaks, árvore de `HEAD` | `git archive HEAD \| tar -x -C <scratch>` + `gitleaks dir --redact <scratch>` | ~25,2 MB, **no leaks found** |
| hook do pre-commit | `uv run pre-commit run gitleaks --all-files` (e com `--with pre-commit`) | `Passed` — **vazio**: a entrada do hook é `gitleaks git --pre-commit --redact --staged`, que só lê o diff staged; com a árvore limpa não há nada a varrer. Não conta como evidência. |
| detect-secrets 1.5 | `uv run --with detect-secrets detect-secrets scan` (usa `git ls-files`), resultado filtrado de novo por `git ls-files` | 667 achados em 40 arquivos versionados, 0 em não versionados: 657 "Hex High Entropy String" (634 linhas com sha256, 23 com hash de commit de 40 hex), 10 "Base64 High Entropy String" (caminhos: `app/dados.py:24-25`, 8 caminhos `reports\\experiments\\TESTES_DM_*` em `proveniencia.json`). |
| padrões próprios, arquivos versionados | `git ls-files -z \| xargs -0 grep -nIiE "cdsapirc\|CDSAPI_KEY\|ghp_…\|github_pat_\|AKIA…\|BEGIN … PRIVATE\|password\|secret\|api[_-]?key\|token\|hf_…\|xox[bap]-\|sk-…\|AIza…\|bearer "` | 70 linhas, classificadas em a.2; nenhum valor de credencial. |
| padrões próprios, histórico | `git log -p --all` (1.388.113 linhas) + regex só de **valores** (`ghp_`, `github_pat_`, `AKIA`, `BEGIN … PRIVATE KEY`, `hf_`, `sk-`, `AIza`, `CDSAPI_KEY=` seguido de valor, `password[:=]` com valor) | **0** linhas. Linhas removidas (`-`) com "token/secret/cdsapi" no histórico: só `asttokens==3.0.1` e `cdsapi==0.7.7` (regravação de fim de linha do `44946b4`). |
| arquivos sensíveis já adicionados | `git log --all --diff-filter=A --name-only` | só `.env.example` |
| e-mails no conteúdo versionado | regex de e-mail em `git ls-files` | **0** |

### a.2 Classificação das ocorrências

| Arquivo:linha | Trecho | Classificação |
|---|---|---|
| `.env.example:8` | `CDSAPI_KEY=<uid>:<api-key>` | placeholder (permitido) |
| `.env.example:5`, `.gitignore:3`, `.dockerignore:8`, `Dockerfile:54`, `api/Dockerfile:15`, `docs/REPRODUCIBILITY.md:52`, `deploy/hf_space/LEIA-ME.md:85` | menção a `.cdsapirc`/`.env`/token como coisa a nunca versionar | regra de exclusão (falso positivo) |
| `deploy/hf_space/LEIA-ME.md:3,20,28,30` | instruções de criar o token do Hugging Face "digitado por você, nunca fica em arquivo do repositório" | instrução, sem valor |
| `.github/workflows/pages.yml:21` | `id-token: write` | permissão do GitHub Actions (OIDC do Pages), não é segredo |
| `src/ingestion/cams_download_chunked.py:27-37, 180-219, 442` | lê `CDSAPI_URL`/`CDSAPI_KEY` do ambiente; exemplo `key: SEU_PERSONAL_ACCESS_TOKEN`; `CDSAPI_KEY=<token>`; linha 196 diz que o caminho `./.cdsapirc` "já vazou uma vez" (no repositório da dissertação) | código de leitura + placeholder; a frase é histórica e não traz valor. Informativo: se aquela chave nunca foi revogada, revogar é decisão do autor, fora deste repositório. |
| `src/experiments/preflight.py:44-79` | `CREDENCIAIS = ["CDSAPI_KEY", "CDSAPI_URL"]` e checagem de presença | nome de variável |
| `docs/requirements-executado-…:24`, `results/runs/*/environment.txt:11` (10) | `asttokens==3.0.1` | nome de pacote |
| `site/static/css/fontawesome.all.min.css:8` | "token" dentro do CSS minificado | falso positivo |
| `docs/AUDITORIA.md` (versão anterior) | comandos e regex de busca | texto da auditoria |
| 40 arquivos do detect-secrets | `manifest.json` (6 hashes × 10), `proveniencia.json` (2), `*.meta.json`, `models_demo/metadata.json`, `notebooks/dados_painel/manifest.json`, `site/build_provenance.json`, `site/data/a_modelos_por_h.json`, 22 `site/static/images/*.prov.json`, `tests/test_runner_mlflow.py:44` (`COMMIT_REFERENCIA`) | sha256 / commits de proveniência (falso positivo) |
| metadados do Git (não é conteúdo) | autores dos 30 commits: 29 com um endereço `…@gmail.com`, 1 (`94e53a5 Added Dev Container Folder`, feito pela interface web) com um endereço `…@hotmail.com` | informativo: dois e-mails pessoais do autor já estão públicos no `git log`; não é segredo. |

**Veredito (a): OK — nenhum segredo.**

## (b) Privacidade

### b.1 Arquivos de dados novos desde `44946b4` (lidos com pandas)

`git diff --stat 44946b4..HEAD -- data/processed results models_demo notebooks` é **vazio**: nenhum dado, artefato de run, modelo ou arquivo do painel mudou. Os arquivos de dados novos estão todos em `site/`:

| Arquivo | Forma | Origem (sha256 idêntico) | Veredito |
|---|---|---|---|
| `site/data/A_modelos_por_h.csv` | 170 × 15 (base × h × modelo: MAE, RMSE, MASE, dp) | `results/analise_multihorizonte/…/A_modelos_por_h.csv` | agregado |
| `site/data/A2_dm_modelos_por_h.csv` | 10 × 13 (base × h: líder, nº de pares significativos) | `…/A2_dm_modelos_por_h.csv` | agregado |
| `site/data/arcal_por_horizonte_dois_alvos.csv` | 70 × 5 | `results/numeros_texto_urgencia/…/arcal_por_horizonte_dois_alvos.csv` | agregado |
| `site/data/erro_sabado_h1.csv` | 12 × 6 | `…/erro_sabado_h1.csv` | agregado |
| `site/data/runs/*/model_comparison.csv` (10) | 52 × 13 cada | `results/runs/<RUN_ID>/model_comparison.csv` | agregado |
| `site/data/runs/{h1_v02…,ur_h1…}/metrics_by_fold.csv` (2) | 528 × 13 (modelo × conjunto × semente × fold) | `results/runs/<RUN_ID>/metrics_by_fold.csv` | agregado |
| `site/data/a_modelos_por_h.json` | gerado por `build_site.py`: médias por modelo × h × alvo, ids de run, commits, sha256 das origens | derivado (sem cópia idêntica) | agregado |
| `site/static/images/*.png` (24 figuras + `app_screenshot.png`) | gráficos de métricas agregadas; captura da Home pública do app | `.prov.json` ao lado de cada uma | ok |
| `configs/smoke_mlflow.yaml` | configuração de teste | — | ok |

Os arquivos de dados anteriores (`data/processed/*`, `notebooks/dados_painel/*`, `results/**`, `models_demo/*`) foram inventariados na rodada anterior e não mudaram; os sha256 continuam batendo (`verificar_inventario.py`, `build_site.py --check` e os 22 `.prov.json`, tabela c.4).

### b.2 Checagens específicas

| Checagem | Resultado |
|---|---|
| MLflow da pesquisa / catálogo no repositório | `git ls-files` e o histórico (`--diff-filter=A`) sem `mlruns`, `mlartifacts`, `mlflow.db`, `catalogo_runs.yaml`, `mlflow_pesquisa`. A pasta local `D:\Project\mlflow_pesquisa\` existe (com `mlflow.db`, `catalogo_runs.yaml`, `artifacts/`) e fica fora. `tracking/importar_pesquisa.py` não embute o catálogo; só o exemplo de uso cita os caminhos locais. `mlruns/` e `reports/` estão no `.gitignore` e no `.dockerignore`. |
| `predictions.csv` em `results/` ou `site/` | ausente |
| `N_AIH` como coluna/registro | nenhuma coluna; aparece só como regra (data card, meta, manifests, READMEs). |
| CNES 2091550 | nome e código no app, na página (EN/PT) e no painel: coberto pela D7 ampliada. Contagens diárias da coluna `cema`: cobertas pela D8. |
| Frase "no establishment-level record beyond the aggregated Saturday panel (establishment × year with fewer than 5 admissions suppressed)" (README EN L141, PT L143, página) | verdadeira, mas omite que o painel traz também a série **diária** de um estabelecimento identificado, aceita pela D8. Baixa (item 13). |

### b.3 Caminhos com nome de usuário ou de máquina em arquivos versionados

| Onde | Trecho | Classificação |
|---|---|---|
| (qualquer arquivo versionado) | `C:\Users\…`, `/c/Users/…`, `AppData`, `/home/<usuário>` | **0** ocorrências (fora `api/Dockerfile:51` `HOME=/home/user`, usuário genérico exigido pelo HF Spaces). O item 10 anterior foi corrigido. |
| `docs/DECISOES.md:16` (D9) | `D:\Project\mlflow_pesquisa` | aceitável: documentação de uso local, sem nome de usuário |
| `tracking/importar_pesquisa.py:12-15, 718` | `D:/Project/dataspell_workspace_template/reports/experiments`, `D:/Project/mlflow_pesquisa/…` em exemplo e `help` | aceitável: exemplo de uso local |
| `notebooks/dados_painel/manifest.json:3-11`, `notebooks/preparar_dados_painel.py:20-21` | `D:\Project\dados_extensao_2026-11\…`, `D:\Project\dataspell_workspace_template\…` | aceitável: proveniência histórica (inalterado) |
| `results/runs/*/environment.txt:1` (10), `docs/requirements-executado-…:14` | `# executável: D:\Project\dataspell_workspace_template\env\.venv311\…` | aceitável: proveniência |
| `src/experiments/run_preliminary.py:85`, `src/ingestion/cams_rebuild_daily.py:26-29`, `src/ingestion/sih_build_lookahead.py:3`, `tests/test_caminhos_config.py:4` | `D:/Project/dados_rebaixa_2026-10/…` | aceitável: exemplo |

**Veredito (b): OK.**

## (c) Números

Regra: MAE com 2 casas, MASE/skill/p com 3, contagens exatas; PT com vírgula decimal e ponto de milhar onde o texto usa (as tabelas mantêm o ponto dos arquivos de origem, como dizem os READMEs). Cada célula foi lida do artefato primário: as tabelas MAE/MASE de `results/runs/<RUN_ID>/model_comparison.csv` (não de `A_modelos_por_h.csv`); contagens de contrastes recontadas nos `dm_contrastes.csv` das 10 runs (não no `B2`/`A2`, que foram conferidos contra a recontagem); MAE por fold e dispersão recalculados de `metrics_by_fold.csv`; o app renderizado e comparado com cálculos próprios sobre os parquet/csv.

### c.0 Saídas dos scripts do repositório (registradas, não usadas como fonte)

| Comando | Saída | Tempo |
|---|---|---|
| `uv run python docs/scripts/conferir_numeros.py` | `588 checks; DIVERGENTE: 0`, exit 0 — **regravou** `docs/CONFERENCIA_NUMEROS_WP5.md` (carimbo 14:33 → 14:42, CRLF no Windows); restaurado com `git checkout --` | ~2 s |
| `uv run python docs/scripts/build_site.py --check` | `site/ is up to date`, exit 0 | ~3 s |
| `uv run python docs/scripts/verificar_inventario.py` | `exatos=317 iguais_apos_eol=17 editados_declarados=5 erros=0`, exit 0. Os 17 "iguais após EOL" são código/testes copiados com CRLF da origem (nenhum sob `-text`); os 5 editados são os declarados (`gerar_notebook.py`, três `cetesb_build_*.py`, `run_preliminary.py`). | < 1 s |
| `uv run python docs/scripts/tabela_readme.py --lang en` / `--lang pt` (para o scratchpad) | blocos idênticos aos dos READMEs | — |

### c.1 Total

| Bloco | Números | VERIFICADO | DIVERGENTE | SEM FONTE |
|---|---:|---:|---:|---:|
| Tabelas MAE/MASE (README EN, README PT, página EN, página PT: 140 células cada) | 560 | 560 | 0 | 0 |
| Metadados de run nas tabelas/frases (commit, árvore limpa, previsões, status) | 100 | 100 | 0 | 0 |
| README EN/PT, texto corrido (c.3) | 80 | 78 | 2 | 0 |
| Páginas: resumo, tabela DM, legendas das 12 figuras, BibTeX (c.4) | 106 | 106 | 0 | 0 |
| `.prov.json` (22) + `build_provenance.json` (c.4) | 22 | 22 | 0 | 0 |
| App, cinco páginas × duas línguas (c.5) | 58 | 58 | 0 | 0 |
| Docs e LEIA-MEs novos, conferência manual (c.6) | 18 | 10 | 2 | 6 |
| **Total** | **944** | **934** | **4** | **6** |

### c.2 DIVERGENTE e SEM FONTE

Os 4 DIVERGENTE da contagem são D1 (README EN e README PT, conferido automaticamente nas duas línguas), D2 e D3 (conferidos à mão, uma linha cada em c.6, embora apareçam em quatro lugares).

| # | Onde | Exibido | Lido / fato | Status |
|---:|---|---|---|---|
| D1 | `README.md:95`, `README.pt-BR.md:95` | "On the total target, Saturday is the worst day for every model" | `notebooks/dados_painel/erros_modelos_ar_cal.csv` (total, h = 1, 720 datas por modelo), MAE por dia da semana: o sábado é o pior para XGBoost (33,21), SARIMAX, LSTM, INGARCH-NB, GAM-NB e Seasonal Naïve, mas o **Naïve** tem domingo 42,02 > segunda 38,84 > sábado 35,80. `erro_sabado_h1.csv` só compara sábado × demais dias (razão > 1 para todos, Naïve 1,30), o que não é "pior dia". | **DIVERGENTE** (baixa) |
| D2 | `README.md:142`, `README.pt-BR.md:144`, `site/index.html:293`, `site/index.pt-BR.html:293` | "Nothing is published about the LSTM (or any model) beyond what is in `results/`: **no trained weights**, no per-seed artefacts…" | `models_demo/xgboost_ar_cal_h{1,7,30}.ubj` são pesos XGBoost treinados, versionados (1,5 MB o de h = 1), servidos pela API e destinados ao HF Space; `models_demo/` não está em `results/`. A frase já existia em `44946b4` e a rodada anterior não a apontou; agora também está na página. | **DIVERGENTE** (média) |
| D3 | `docs/ARCHITECTURE.md:56`; também `README.md:122`, `README.pt-BR.md:122`, `docs/DECISOES.md:16` (D9) | "The run outputs (`metrics.json`, **`predictions.csv`**, …) are byte-identical with and without it" | `tests/test_runner_mlflow.py::_comparar_saidas` compara byte a byte `metrics.json`, `model_comparison.csv`, `metrics_by_fold.csv`, `folds.csv`, `feature_ablation.csv`; `predictions.csv` só depois de trocar o `run_id` por `<RUN_ID>` (a coluna `run_id` difere entre quaisquer duas execuções); `manifest.json` sem os campos de tempo e de RUN_ID. A afirmação é verdadeira para cinco arquivos e "igual exceto `run_id`/tempos" para os outros dois. | **DIVERGENTE** (baixa) |
| S1 | `README.md:103`, `README.pt-BR.md:103` | suíte "3m52s on the author's machine, 2026-11-23" | sem artefato; hoje 7m18s nesta máquina (com outras varreduras em paralelo), 3m46s no CI (`45862942820`) | **SEM FONTE** (baixa, datado) |
| S2 | `docs/REPRODUCIBILITY.md:30` | smoke "10.5 s measured on the author's machine, 2026-11-23" | sem artefato; hoje 8,98 s | **SEM FONTE** (baixa, datado) |
| S3 | `deploy/hf_space/LEIA-ME.md:5-6` | imagem enxuta "~uma ordem de grandeza menor que a imagem principal" | sem artefato no repo; o log do CI de `b90f3e2` (job docker, passo "Tamanho das imagens") mostra `api 920MB`, `local 5.59GB`, `test 5.72GB`: ~6×, não 10× | **SEM FONTE** (baixa) |
| S4 | `.devcontainer/LEIA-ME.md:9-12` | "a versão fica fixada na mesma minor que gerou o `uv.lock` (0.13.x)" | o `uv.lock` (`version = 1`, `revision = 5`) não registra a versão do uv que o gerou; o uv local é 0.13.7; o CI usa 0.13.10 (`setup-uv` sem `version:`) | **SEM FONTE** (baixa) |
| S5 | `.devcontainer/LEIA-ME.md:24-25` | "~1 GB de wheels" | nenhum arquivo mede isso | **SEM FONTE** (baixa) |
| S6 | `app/i18n.py:273-274, 279-280` (página do sábado, EN e PT) | "mostly tonsils/adenoids, **J35**, and nasal septum, **J34**" | `notebooks/dados_painel/grupos_cid.csv` só tem o grupo J30–J39 (39.243 internações, 35.958 eletivas, 11.206 no CNES 2091550); nenhum arquivo versionado separa J34/J35. Texto herdado de `44946b4` (`app/pages/3_…:26`); a fonte é o PROTOCOLO §0.23 da dissertação, não copiado. | **SEM FONTE** (baixa, herdado) |

### c.3 a c.5 Tabelas detalhadas

Contagem das tabelas MAE/MASE e dos metadados de run (cada célula comparada com `MAE_medio`/`MASE_medio` do `model_comparison.csv` da run do h e alvo, `feature_set = AR_CAL` para os modelos treinados e `baseline` para os ingênuos; commit = `git_commit[:7]` do `manifest.json`; árvore limpa = `proveniencia.git_sujo_no_inicio = false`; previsões = `n_predicoes`):

| Documento | Bloco | VERIFICADO | DIVERGENTE |
|---|---|---:|---:|
| `README.md` | células MAE/MASE | 140 | 0 |
| `README.md` | tabela de runs (commit, árvore limpa, previsões, status) | 20 | 0 |
| `README.pt-BR.md` | células MAE/MASE | 140 | 0 |
| `README.pt-BR.md` | tabela de runs (commit, árvore limpa, previsões, status) | 20 | 0 |
| `site/index.html` | células MAE/MASE | 140 | 0 |
| `site/index.html` | tabela de runs (commit, árvore limpa, previsões, status) | 30 | 0 |
| `site/index.pt-BR.html` | células MAE/MASE | 140 | 0 |
| `site/index.pt-BR.html` | tabela de runs (commit, árvore limpa, previsões, status) | 30 | 0 |

### c.3 README EN/PT — texto corrido

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 1 | README.md: L94 '10 contrastes de ablação por modelo' (total h=1) | 10 | results/testes_dm/TESTES_DM_h1_v02_…/dm_contrastes.csv | ablacao_*, agrupado, contagem por família | 10 | VERIFICADO |
| 2 | README.md: L94 contrastes sig. total h=1 | 7 | idem | p_holm<0.05 | 7 | VERIFICADO |
| 3 | README.md: L94 'todos com a covariável pior' (DM>0) | 7 | idem | p_holm<0.05 & DM>0 | 7 | VERIFICADO |
| 4 | README.md: L94 500 contrastes | 500 | B2_dm_ablacao_por_h.csv; dm_contrastes das 10 runs | linhas de B2 nas bases cetesb+urgencia / contrastes agrupados nas 10 runs | 500/500 | VERIFICADO |
| 5 | README.md: L94 59 significativos | 59 | dm_contrastes das 10 runs | agrupado, ablacao_*, p_holm<0.05 | 59 | VERIFICADO |
| 6 | README.md: L94 53 piores | 53 | idem | DM>0 | 53 | VERIFICADO |
| 7 | README.md: L94 6 melhores | 6 | idem | DM<0 | 6 | VERIFICADO |
| 8 | README.md: L94 59/53/6 no B2 citado | 59/53/6 | B2_dm_ablacao_por_h.csv | bases cetesb+urgencia, p_holm<0.05 | 59/53/6 | VERIFICADO |
| 9 | README.md: L94 ablacao_sarimax urgencia h=1 AR_CAL_PM25MEDIA vs AR_CAL p Holm | 0.005 | results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | A=AR_CAL_PM25MEDIA,B=AR_CAL,agrupado | 0.005 (DM<0) | VERIFICADO |
| 10 | README.md: L94 ablacao_sarimax urgencia h=1 AR_CAL_POLUENTES vs AR_CAL p Holm | 0.014 | results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | A=AR_CAL_POLUENTES,B=AR_CAL,agrupado | 0.014 (DM<0) | VERIFICADO |
| 11 | README.md: L94 ablacao_xgboost urgencia h=15 AR_CAL_METEO_POLUENTES vs AR_CAL_METEO p Holm | 0.001 | results/testes_dm/TESTES_DM_ur_h15_cetesb_cetesb_full_20261117-190532/dm_contrastes.csv | A=AR_CAL_METEO_POLUENTES,B=AR_CAL_METEO,agrupado | 0.001 (DM<0) | VERIFICADO |
| 12 | README.md: L94 ablacao_lstm total h=7 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0.001 | results/testes_dm/TESTES_DM_mh_h7_cetesb_cetesb_full_20261111-030322/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0.001 (DM<0) | VERIFICADO |
| 13 | README.md: L94 ablacao_lstm urgencia h=5 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0.007 | results/testes_dm/TESTES_DM_ur_h5_cetesb_cetesb_full_20261116-222823/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0.007 (DM<0) | VERIFICADO |
| 14 | README.md: L94 ablacao_lstm urgencia h=7 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0.026 | results/testes_dm/TESTES_DM_ur_h7_cetesb_cetesb_full_20261117-073926/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0.026 (DM<0) | VERIFICADO |
| 15 | README.md: L92 líder XGBoost total h=1..15 | xgboost×4 | A2_dm_modelos_por_h.csv | base=cetesb, lider | xgboost,xgboost,xgboost,xgboost | VERIFICADO |
| 16 | README.md: L92 líder XGBoost urgência h=5..15 | xgboost×3 | A2 | base=urgencia, lider | xgboost,xgboost,xgboost | VERIFICADO |
| 17 | README.md: L92 SARIMAX lidera h=30 (2 alvos) e urgência h=1 | sarimax×3 | A2 | lider | sarimax,sarimax,sarimax | VERIFICADO |
| 18 | README.md: L92 líder total h=1 (recalculado) | xgboost | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 19 | README.md: L92 líder total h=5 (recalculado) | xgboost | results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 20 | README.md: L92 líder total h=7 (recalculado) | xgboost | results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 21 | README.md: L92 líder total h=15 (recalculado) | xgboost | results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 22 | README.md: L92 líder total h=30 (recalculado) | sarimax | results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 23 | README.md: L92 líder urgencia h=1 (recalculado) | sarimax | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 24 | README.md: L92 líder urgencia h=5 (recalculado) | xgboost | results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 25 | README.md: L92 líder urgencia h=7 (recalculado) | xgboost | results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 26 | README.md: L92 líder urgencia h=15 (recalculado) | xgboost | results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 27 | README.md: L92 líder urgencia h=30 (recalculado) | sarimax | results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 28 | README.md: L92 'os quatro contra o GAM-NB' (total h=1) | 4, todos com gam_nb | dm_contrastes (h1 total) e A2 | modelos_AR_CAL agrupado, treinados, p_holm<0.05 | 4: xgboost-gam_nb; sarimax-gam_nb; lstm-gam_nb; ingarch_nb-gam_nb | VERIFICADO |
| 29 | README.md: L92 XGBoost, SARIMAX e LSTM não se separam (todo h, 2 alvos) | 0 pares sig. | dm_contrastes das 10 runs | modelos_AR_CAL agrupado, pares entre os três | 0 de 30 | VERIFICADO |
| 30 | README.md: L95 XGBoost total h=1 MAE_sab | 33.31 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,MAE_sab | 33.31 | VERIFICADO |
| 31 | README.md: L95 XGBoost total h=1 MAE_demais | 16.09 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,MAE_demais | 16.09 | VERIFICADO |
| 32 | README.md: L95 XGBoost total h=1 razao | 2.07 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,razao | 2.07 | VERIFICADO |
| 33 | README.md: L95 razão urgência | 0.90 | erro_sabado_h1.csv | urgencia,XGBoost,razao | 0.90 | VERIFICADO |
| 34 | README.md: L95 sábado pior que os demais dias para todos os modelos (total) | razão>1 em todos | erro_sabado_h1.csv | razao | GAM-NB:2.39,INGARCH-NB:2.13,LSTM:2.04,Naïve:1.30,SARIMAX:2.33,XGBoost:2.07 | VERIFICADO |
| 35 | README.md: L95 sábado = pior dia da semana (total, h=1; previsão média das sementes) | dow=5 em todos | notebooks/dados_painel/erros_modelos_ar_cal.csv | argmax MAE por dia da semana | gam_nb:5,ingarch_nb:5,lstm:5,naive:6,sarimax:5,seasonal_naive:5,xgboost:5 | **DIVERGENTE** |
| 36 | README.md: L27 dez runs, 95.040 previsões cada | 10×95040 | manifest.json das 10 runs | n_predicoes | 10×95040 | VERIFICADO |
| 37 | README.md: decisões D1 a D13 | D1..D13 | docs/DECISOES.md | linhas da tabela | D1..D13 (13) | VERIFICADO |
| 38 | README.md: L124 'cinco pacotes' de app/requirements.txt | 5 | app/requirements.txt | linhas não comentadas | 5 | VERIFICADO |
| 39 | README.md: L50 4 folds × 180 dias, 2023-01-12 a 2024-12-31 | 4×180, 2023-01-12..2024-12-31 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv | n, teste_inicio/fim | 4×[180], 2023-01-12..2024-12-31 | VERIFICADO |
| 40 | README.md: L50 cinco sementes 42 a 46 | [42..46] | manifest.json das 10 runs | sementes | [(42, 43, 44, 45, 46)] | VERIFICADO |
| 41 | README.pt-BR.md: L94 '10 contrastes de ablação por modelo' (total h=1) | 10 | results/testes_dm/TESTES_DM_h1_v02_…/dm_contrastes.csv | ablacao_*, agrupado, contagem por família | 10 | VERIFICADO |
| 42 | README.pt-BR.md: L94 contrastes sig. total h=1 | 7 | idem | p_holm<0.05 | 7 | VERIFICADO |
| 43 | README.pt-BR.md: L94 'todos com a covariável pior' (DM>0) | 7 | idem | p_holm<0.05 & DM>0 | 7 | VERIFICADO |
| 44 | README.pt-BR.md: L94 500 contrastes | 500 | B2_dm_ablacao_por_h.csv; dm_contrastes das 10 runs | linhas de B2 nas bases cetesb+urgencia / contrastes agrupados nas 10 runs | 500/500 | VERIFICADO |
| 45 | README.pt-BR.md: L94 59 significativos | 59 | dm_contrastes das 10 runs | agrupado, ablacao_*, p_holm<0.05 | 59 | VERIFICADO |
| 46 | README.pt-BR.md: L94 53 piores | 53 | idem | DM>0 | 53 | VERIFICADO |
| 47 | README.pt-BR.md: L94 6 melhores | 6 | idem | DM<0 | 6 | VERIFICADO |
| 48 | README.pt-BR.md: L94 59/53/6 no B2 citado | 59/53/6 | B2_dm_ablacao_por_h.csv | bases cetesb+urgencia, p_holm<0.05 | 59/53/6 | VERIFICADO |
| 49 | README.pt-BR.md: L94 ablacao_sarimax urgencia h=1 AR_CAL_PM25MEDIA vs AR_CAL p Holm | 0,005 | results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | A=AR_CAL_PM25MEDIA,B=AR_CAL,agrupado | 0,005 (DM<0) | VERIFICADO |
| 50 | README.pt-BR.md: L94 ablacao_sarimax urgencia h=1 AR_CAL_POLUENTES vs AR_CAL p Holm | 0,014 | results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | A=AR_CAL_POLUENTES,B=AR_CAL,agrupado | 0,014 (DM<0) | VERIFICADO |
| 51 | README.pt-BR.md: L94 ablacao_xgboost urgencia h=15 AR_CAL_METEO_POLUENTES vs AR_CAL_METEO p Holm | 0,001 | results/testes_dm/TESTES_DM_ur_h15_cetesb_cetesb_full_20261117-190532/dm_contrastes.csv | A=AR_CAL_METEO_POLUENTES,B=AR_CAL_METEO,agrupado | 0,001 (DM<0) | VERIFICADO |
| 52 | README.pt-BR.md: L94 ablacao_lstm total h=7 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0,001 | results/testes_dm/TESTES_DM_mh_h7_cetesb_cetesb_full_20261111-030322/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0,001 (DM<0) | VERIFICADO |
| 53 | README.pt-BR.md: L94 ablacao_lstm urgencia h=5 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0,007 | results/testes_dm/TESTES_DM_ur_h5_cetesb_cetesb_full_20261116-222823/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0,007 (DM<0) | VERIFICADO |
| 54 | README.pt-BR.md: L94 ablacao_lstm urgencia h=7 AR_CAL_METEO_PM25MEDIA vs AR_CAL_METEO p Holm | 0,026 | results/testes_dm/TESTES_DM_ur_h7_cetesb_cetesb_full_20261117-073926/dm_contrastes.csv | A=AR_CAL_METEO_PM25MEDIA,B=AR_CAL_METEO,agrupado | 0,026 (DM<0) | VERIFICADO |
| 55 | README.pt-BR.md: L92 líder XGBoost total h=1..15 | xgboost×4 | A2_dm_modelos_por_h.csv | base=cetesb, lider | xgboost,xgboost,xgboost,xgboost | VERIFICADO |
| 56 | README.pt-BR.md: L92 líder XGBoost urgência h=5..15 | xgboost×3 | A2 | base=urgencia, lider | xgboost,xgboost,xgboost | VERIFICADO |
| 57 | README.pt-BR.md: L92 SARIMAX lidera h=30 (2 alvos) e urgência h=1 | sarimax×3 | A2 | lider | sarimax,sarimax,sarimax | VERIFICADO |
| 58 | README.pt-BR.md: L92 líder total h=1 (recalculado) | xgboost | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 59 | README.pt-BR.md: L92 líder total h=5 (recalculado) | xgboost | results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 60 | README.pt-BR.md: L92 líder total h=7 (recalculado) | xgboost | results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 61 | README.pt-BR.md: L92 líder total h=15 (recalculado) | xgboost | results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 62 | README.pt-BR.md: L92 líder total h=30 (recalculado) | sarimax | results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 63 | README.pt-BR.md: L92 líder urgencia h=1 (recalculado) | sarimax | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 64 | README.pt-BR.md: L92 líder urgencia h=5 (recalculado) | xgboost | results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 65 | README.pt-BR.md: L92 líder urgencia h=7 (recalculado) | xgboost | results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 66 | README.pt-BR.md: L92 líder urgencia h=15 (recalculado) | xgboost | results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | xgboost | VERIFICADO |
| 67 | README.pt-BR.md: L92 líder urgencia h=30 (recalculado) | sarimax | results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv | argmin MAE_medio, AR_CAL, treinados | sarimax | VERIFICADO |
| 68 | README.pt-BR.md: L92 'os quatro contra o GAM-NB' (total h=1) | 4, todos com gam_nb | dm_contrastes (h1 total) e A2 | modelos_AR_CAL agrupado, treinados, p_holm<0.05 | 4: xgboost-gam_nb; sarimax-gam_nb; lstm-gam_nb; ingarch_nb-gam_nb | VERIFICADO |
| 69 | README.pt-BR.md: L92 XGBoost, SARIMAX e LSTM não se separam (todo h, 2 alvos) | 0 pares sig. | dm_contrastes das 10 runs | modelos_AR_CAL agrupado, pares entre os três | 0 de 30 | VERIFICADO |
| 70 | README.pt-BR.md: L95 XGBoost total h=1 MAE_sab | 33,31 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,MAE_sab | 33,31 | VERIFICADO |
| 71 | README.pt-BR.md: L95 XGBoost total h=1 MAE_demais | 16,09 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,MAE_demais | 16,09 | VERIFICADO |
| 72 | README.pt-BR.md: L95 XGBoost total h=1 razao | 2,07 | results/numeros_texto_urgencia/…/erro_sabado_h1.csv | total,XGBoost,razao | 2,07 | VERIFICADO |
| 73 | README.pt-BR.md: L95 razão urgência | 0,90 | erro_sabado_h1.csv | urgencia,XGBoost,razao | 0,90 | VERIFICADO |
| 74 | README.pt-BR.md: L95 sábado pior que os demais dias para todos os modelos (total) | razão>1 em todos | erro_sabado_h1.csv | razao | GAM-NB:2.39,INGARCH-NB:2.13,LSTM:2.04,Naïve:1.30,SARIMAX:2.33,XGBoost:2.07 | VERIFICADO |
| 75 | README.pt-BR.md: L95 sábado = pior dia da semana (total, h=1; previsão média das sementes) | dow=5 em todos | notebooks/dados_painel/erros_modelos_ar_cal.csv | argmax MAE por dia da semana | gam_nb:5,ingarch_nb:5,lstm:5,naive:6,sarimax:5,seasonal_naive:5,xgboost:5 | **DIVERGENTE** |
| 76 | README.pt-BR.md: L27 dez runs, 95.040 previsões cada | 10×95040 | manifest.json das 10 runs | n_predicoes | 10×95040 | VERIFICADO |
| 77 | README.pt-BR.md: decisões D1 a D13 | D1..D13 | docs/DECISOES.md | linhas da tabela | D1..D13 (13) | VERIFICADO |
| 78 | README.pt-BR.md: L124 'cinco pacotes' de app/requirements.txt | 5 | app/requirements.txt | linhas não comentadas | 5 | VERIFICADO |
| 79 | README.pt-BR.md: L50 4 folds × 180 dias, 2023-01-12 a 2024-12-31 | 4×180, 2023-01-12..2024-12-31 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv | n, teste_inicio/fim | 4×[180], 2023-01-12..2024-12-31 | VERIFICADO |
| 80 | README.pt-BR.md: L50 cinco sementes 42 a 46 | [42..46] | manifest.json das 10 runs | sementes | [(42, 43, 44, 45, 46)] | VERIFICADO |

### c.4 Páginas `site/index.html` e `site/index.pt-BR.html` — resumo, tabela DM, legendas, BibTeX e `.prov.json`

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 1 | site/index.html: resumo '7 modelos' | 7 | model_comparison.csv (h1 total) | modelos distintos | 7 | VERIFICADO |
| 2 | site/index.html: resumo '10 runs, árvore limpa' | 10 | manifest.json | git_sujo_no_inicio=False | 10 | VERIFICADO |
| 3 | site/index.html: resumo '95.040 previsões por run' | 95040 | manifest.json | n_predicoes | 95040 | VERIFICADO |
| 4 | site/index.html: resumo menor MAE h=1 total | 18.56/0.645 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | xgboost AR_CAL | 18.56/0.645 | VERIFICADO |
| 5 | site/index.html: tabela DM total h=1 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_h1_v02_cetesb_cetesb_classicos_full_20261022-211834/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 6 | site/index.html: tabela DM total h=5 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h5_cetesb_cetesb_full_20261110-211453/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 7 | site/index.html: tabela DM total h=7 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h7_cetesb_cetesb_full_20261111-030322/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 8 | site/index.html: tabela DM total h=15 líder + pares sig. | XGBoost \| XGBoost – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h15_cetesb_cetesb_full_20261111-070926/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 1 pares | VERIFICADO |
| 9 | site/index.html: tabela DM total h=30 líder + pares sig. | SARIMAX \| none | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h30_cetesb_cetesb_full_20261113-104814/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 0 pares | VERIFICADO |
| 10 | site/index.html: tabela DM urgencia h=1 líder + pares sig. | SARIMAX \| XGBoost – GAM-NB; SARIMAX – INGARCH-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 5 pares | VERIFICADO |
| 11 | site/index.html: tabela DM urgencia h=5 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h5_cetesb_cetesb_full_20261116-222823/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 12 | site/index.html: tabela DM urgencia h=7 líder + pares sig. | XGBoost \| SARIMAX – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h7_cetesb_cetesb_full_20261117-073926/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 1 pares | VERIFICADO |
| 13 | site/index.html: tabela DM urgencia h=15 líder + pares sig. | XGBoost \| none | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h15_cetesb_cetesb_full_20261117-190532/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 0 pares | VERIFICADO |
| 14 | site/index.html: tabela DM urgencia h=30 líder + pares sig. | SARIMAX \| none | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h30_cetesb_cetesb_full_20261117-221426/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 0 pares | VERIFICADO |
| 15 | site/index.html: legenda MAE por h (total) h=1 | h = 1: XGBoost 18.56 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio AR_CAL | h = 1: XGBoost 18.56 | VERIFICADO |
| 16 | site/index.html: legenda MAE por h (total) h=5 | h = 5: XGBoost 22.50 | results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv | argmin MAE_medio AR_CAL | h = 5: XGBoost 22.50 | VERIFICADO |
| 17 | site/index.html: legenda MAE por h (total) h=7 | h = 7: XGBoost 23.40 | results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv | argmin MAE_medio AR_CAL | h = 7: XGBoost 23.40 | VERIFICADO |
| 18 | site/index.html: legenda MAE por h (total) h=15 | h = 15: XGBoost 24.34 | results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv | argmin MAE_medio AR_CAL | h = 15: XGBoost 24.34 | VERIFICADO |
| 19 | site/index.html: legenda MAE por h (total) h=30 | h = 30: SARIMAX 25.32 | results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv | argmin MAE_medio AR_CAL | h = 30: SARIMAX 25.32 | VERIFICADO |
| 20 | site/index.html: legenda MAE por h (urgencia) h=1 | h = 1: SARIMAX 14.26 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio AR_CAL | h = 1: SARIMAX 14.26 | VERIFICADO |
| 21 | site/index.html: legenda MAE por h (urgencia) h=5 | h = 5: XGBoost 17.61 | results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv | argmin MAE_medio AR_CAL | h = 5: XGBoost 17.61 | VERIFICADO |
| 22 | site/index.html: legenda MAE por h (urgencia) h=7 | h = 7: XGBoost 18.51 | results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv | argmin MAE_medio AR_CAL | h = 7: XGBoost 18.51 | VERIFICADO |
| 23 | site/index.html: legenda MAE por h (urgencia) h=15 | h = 15: XGBoost 20.99 | results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv | argmin MAE_medio AR_CAL | h = 15: XGBoost 20.99 | VERIFICADO |
| 24 | site/index.html: legenda MAE por h (urgencia) h=30 | h = 30: SARIMAX 21.46 | results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv | argmin MAE_medio AR_CAL | h = 30: SARIMAX 21.46 | VERIFICADO |
| 25 | site/index.html: legenda skill total máximo | xgboost h=1 0.354 | model_comparison.csv das 5 runs do alvo | 1−MAE/min(naive,snaive), treinados | xgboost h=1 0.354 | VERIFICADO |
| 26 | site/index.html: legenda skill total mínimo | gam_nb h=7 0.090 | idem | idem | gam_nb h=7 0.090 | VERIFICADO |
| 27 | site/index.html: legenda skill urgencia máximo | sarimax h=30 0.294 | model_comparison.csv das 5 runs do alvo | 1−MAE/min(naive,snaive), treinados | sarimax h=30 0.294 | VERIFICADO |
| 28 | site/index.html: legenda skill urgencia mínimo | gam_nb h=7 0.060 | idem | idem | gam_nb h=7 0.060 | VERIFICADO |
| 29 | site/index.html: legenda MAE por fold total xgboost mínimo | 16.36 (fold 2) | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/metrics_by_fold.csv | média das sementes por fold | 16.36 (fold 2) | VERIFICADO |
| 30 | site/index.html: legenda MAE por fold total xgboost máximo | 21.81 (fold 1) | idem | idem | 21.81 (fold 1) | VERIFICADO |
| 31 | site/index.html: legenda MAE por fold total: xgboost é o líder h=1 | xgboost | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin | xgboost | VERIFICADO |
| 32 | site/index.html: legenda '180 dias de teste por fold' (total) | [180] | folds.csv | n_teste | [180] | VERIFICADO |
| 33 | site/index.html: legenda MAE por fold urgencia sarimax mínimo | 12.37 (fold 2) | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/metrics_by_fold.csv | média das sementes por fold | 12.37 (fold 2) | VERIFICADO |
| 34 | site/index.html: legenda MAE por fold urgencia sarimax máximo | 15.38 (fold 4) | idem | idem | 15.38 (fold 4) | VERIFICADO |
| 35 | site/index.html: legenda MAE por fold urgencia: sarimax é o líder h=1 | sarimax | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin | sarimax | VERIFICADO |
| 36 | site/index.html: legenda '180 dias de teste por fold' (urgencia) | [180] | folds.csv | n_teste | [180] | VERIFICADO |
| 37 | site/index.html: legenda ablação total h=1 melhor conjunto XGBoost | XGBoost AR_CAL 18.56 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | XGBoost AR_CAL 18.56 | VERIFICADO |
| 38 | site/index.html: legenda ablação total h=1 melhor conjunto SARIMAX | SARIMAX AR_CAL_POLUENTES 18.72 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | SARIMAX AR_CAL_POLUENTES 18.72 | VERIFICADO |
| 39 | site/index.html: legenda ablação total h=1 melhor conjunto LSTM | LSTM AR_CAL 19.01 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | LSTM AR_CAL 19.01 | VERIFICADO |
| 40 | site/index.html: legenda ablação total h=1 melhor conjunto INGARCH-NB | INGARCH-NB AR_CAL_POLUENTES 19.25 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | INGARCH-NB AR_CAL_POLUENTES 19.25 | VERIFICADO |
| 41 | site/index.html: legenda ablação total h=1 melhor conjunto GAM-NB | GAM-NB AR_CAL_POLUENTES 21.58 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | GAM-NB AR_CAL_POLUENTES 21.58 | VERIFICADO |
| 42 | site/index.html: legenda ablação urgencia h=1 melhor conjunto XGBoost | XGBoost AR_CAL_METEO_PM25 14.57 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | XGBoost AR_CAL_METEO_PM25 14.57 | VERIFICADO |
| 43 | site/index.html: legenda ablação urgencia h=1 melhor conjunto SARIMAX | SARIMAX AR_CAL_METEO_PM25MEDIA 13.85 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | SARIMAX AR_CAL_METEO_PM25MEDIA 13.85 | VERIFICADO |
| 44 | site/index.html: legenda ablação urgencia h=1 melhor conjunto LSTM | LSTM AR_CAL_PM25MEDIA 14.63 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | LSTM AR_CAL_PM25MEDIA 14.63 | VERIFICADO |
| 45 | site/index.html: legenda ablação urgencia h=1 melhor conjunto INGARCH-NB | INGARCH-NB AR_CAL_POLUENTES 14.55 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | INGARCH-NB AR_CAL_POLUENTES 14.55 | VERIFICADO |
| 46 | site/index.html: legenda ablação urgencia h=1 melhor conjunto GAM-NB | GAM-NB AR_CAL_POLUENTES 16.41 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | GAM-NB AR_CAL_POLUENTES 16.41 | VERIFICADO |
| 47 | site/index.html: legenda sábado XGBoost total MAE_sab | 33.31 | erro_sabado_h1.csv | total,XGBoost,MAE_sab | 33.31 | VERIFICADO |
| 48 | site/index.html: legenda sábado XGBoost total MAE_demais | 16.09 | erro_sabado_h1.csv | total,XGBoost,MAE_demais | 16.09 | VERIFICADO |
| 49 | site/index.html: legenda sábado XGBoost total razao | 2.07 | erro_sabado_h1.csv | total,XGBoost,razao | 2.07 | VERIFICADO |
| 50 | site/index.html: legenda sábado razão urgência | 0.90 | erro_sabado_h1.csv | urgencia,XGBoost,razao | 0.90 | VERIFICADO |
| 51 | site/index.html: legenda dispersão: maior dp entre sementes | LSTM total h=30 1.37 | model_comparison.csv (10 runs), MAE_std_semente; conferido com metrics_by_fold | max | LSTM total h=30 1.37 | VERIFICADO |
| 52 | site/index.html: legenda dispersão: dp entre folds XGBoost h=1 total | 2.34 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | MAE_std_fold (e std ddof=1 das médias por fold) | 2.34 / 2.34 | VERIFICADO |
| 53 | site/index.html: BibTeX version/year/month | 0.1.1/2026/11 | CITATION.cff | version, date-released | 0.1.1/2026/11 | VERIFICADO |
| 54 | site/index.pt-BR.html: resumo '7 modelos' | 7 | model_comparison.csv (h1 total) | modelos distintos | 7 | VERIFICADO |
| 55 | site/index.pt-BR.html: resumo '10 runs, árvore limpa' | 10 | manifest.json | git_sujo_no_inicio=False | 10 | VERIFICADO |
| 56 | site/index.pt-BR.html: resumo '95.040 previsões por run' | 95040 | manifest.json | n_predicoes | 95040 | VERIFICADO |
| 57 | site/index.pt-BR.html: resumo menor MAE h=1 total | 18,56/0,645 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | xgboost AR_CAL | 18,56/0,645 | VERIFICADO |
| 58 | site/index.pt-BR.html: tabela DM total h=1 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_h1_v02_cetesb_cetesb_classicos_full_20261022-211834/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 59 | site/index.pt-BR.html: tabela DM total h=5 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h5_cetesb_cetesb_full_20261110-211453/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 60 | site/index.pt-BR.html: tabela DM total h=7 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h7_cetesb_cetesb_full_20261111-030322/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 61 | site/index.pt-BR.html: tabela DM total h=15 líder + pares sig. | XGBoost \| XGBoost – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h15_cetesb_cetesb_full_20261111-070926/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 1 pares | VERIFICADO |
| 62 | site/index.pt-BR.html: tabela DM total h=30 líder + pares sig. | SARIMAX \| nenhum | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_mh_h30_cetesb_cetesb_full_20261113-104814/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 0 pares | VERIFICADO |
| 63 | site/index.pt-BR.html: tabela DM urgencia h=1 líder + pares sig. | SARIMAX \| XGBoost – GAM-NB; SARIMAX – INGARCH-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h1_cetesb_cetesb_full_20261116-191534/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 5 pares | VERIFICADO |
| 64 | site/index.pt-BR.html: tabela DM urgencia h=5 líder + pares sig. | XGBoost \| XGBoost – GAM-NB; SARIMAX – GAM-NB; LSTM – GAM-NB; INGARCH-NB – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h5_cetesb_cetesb_full_20261116-222823/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 4 pares | VERIFICADO |
| 65 | site/index.pt-BR.html: tabela DM urgencia h=7 líder + pares sig. | XGBoost \| SARIMAX – GAM-NB | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h7_cetesb_cetesb_full_20261117-073926/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 1 pares | VERIFICADO |
| 66 | site/index.pt-BR.html: tabela DM urgencia h=15 líder + pares sig. | XGBoost \| nenhum | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h15_cetesb_cetesb_full_20261117-190532/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | XGBoost \| 0 pares | VERIFICADO |
| 67 | site/index.pt-BR.html: tabela DM urgencia h=30 líder + pares sig. | SARIMAX \| nenhum | A2_dm_modelos_por_h.csv; results/testes_dm/TESTES_DM_ur_h30_cetesb_cetesb_full_20261117-221426/dm_contrastes.csv | lider; pares treinados p_holm<0.05 (recontados) | SARIMAX \| 0 pares | VERIFICADO |
| 68 | site/index.pt-BR.html: legenda MAE por h (total) h=1 | h = 1: XGBoost 18,56 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio AR_CAL | h = 1: XGBoost 18,56 | VERIFICADO |
| 69 | site/index.pt-BR.html: legenda MAE por h (total) h=5 | h = 5: XGBoost 22,50 | results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv | argmin MAE_medio AR_CAL | h = 5: XGBoost 22,50 | VERIFICADO |
| 70 | site/index.pt-BR.html: legenda MAE por h (total) h=7 | h = 7: XGBoost 23,40 | results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv | argmin MAE_medio AR_CAL | h = 7: XGBoost 23,40 | VERIFICADO |
| 71 | site/index.pt-BR.html: legenda MAE por h (total) h=15 | h = 15: XGBoost 24,34 | results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv | argmin MAE_medio AR_CAL | h = 15: XGBoost 24,34 | VERIFICADO |
| 72 | site/index.pt-BR.html: legenda MAE por h (total) h=30 | h = 30: SARIMAX 25,32 | results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv | argmin MAE_medio AR_CAL | h = 30: SARIMAX 25,32 | VERIFICADO |
| 73 | site/index.pt-BR.html: legenda MAE por h (urgencia) h=1 | h = 1: SARIMAX 14,26 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio AR_CAL | h = 1: SARIMAX 14,26 | VERIFICADO |
| 74 | site/index.pt-BR.html: legenda MAE por h (urgencia) h=5 | h = 5: XGBoost 17,61 | results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv | argmin MAE_medio AR_CAL | h = 5: XGBoost 17,61 | VERIFICADO |
| 75 | site/index.pt-BR.html: legenda MAE por h (urgencia) h=7 | h = 7: XGBoost 18,51 | results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv | argmin MAE_medio AR_CAL | h = 7: XGBoost 18,51 | VERIFICADO |
| 76 | site/index.pt-BR.html: legenda MAE por h (urgencia) h=15 | h = 15: XGBoost 20,99 | results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv | argmin MAE_medio AR_CAL | h = 15: XGBoost 20,99 | VERIFICADO |
| 77 | site/index.pt-BR.html: legenda MAE por h (urgencia) h=30 | h = 30: SARIMAX 21,46 | results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv | argmin MAE_medio AR_CAL | h = 30: SARIMAX 21,46 | VERIFICADO |
| 78 | site/index.pt-BR.html: legenda skill total máximo | xgboost h=1 0,354 | model_comparison.csv das 5 runs do alvo | 1−MAE/min(naive,snaive), treinados | xgboost h=1 0,354 | VERIFICADO |
| 79 | site/index.pt-BR.html: legenda skill total mínimo | gam_nb h=7 0,090 | idem | idem | gam_nb h=7 0,090 | VERIFICADO |
| 80 | site/index.pt-BR.html: legenda skill urgencia máximo | sarimax h=30 0,294 | model_comparison.csv das 5 runs do alvo | 1−MAE/min(naive,snaive), treinados | sarimax h=30 0,294 | VERIFICADO |
| 81 | site/index.pt-BR.html: legenda skill urgencia mínimo | gam_nb h=7 0,060 | idem | idem | gam_nb h=7 0,060 | VERIFICADO |
| 82 | site/index.pt-BR.html: legenda MAE por fold total xgboost mínimo | 16,36 (fold 2) | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/metrics_by_fold.csv | média das sementes por fold | 16,36 (fold 2) | VERIFICADO |
| 83 | site/index.pt-BR.html: legenda MAE por fold total xgboost máximo | 21,81 (fold 1) | idem | idem | 21,81 (fold 1) | VERIFICADO |
| 84 | site/index.pt-BR.html: legenda MAE por fold total: xgboost é o líder h=1 | xgboost | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin | xgboost | VERIFICADO |
| 85 | site/index.pt-BR.html: legenda '180 dias de teste por fold' (total) | [180] | folds.csv | n_teste | [180] | VERIFICADO |
| 86 | site/index.pt-BR.html: legenda MAE por fold urgencia sarimax mínimo | 12,37 (fold 2) | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/metrics_by_fold.csv | média das sementes por fold | 12,37 (fold 2) | VERIFICADO |
| 87 | site/index.pt-BR.html: legenda MAE por fold urgencia sarimax máximo | 15,38 (fold 4) | idem | idem | 15,38 (fold 4) | VERIFICADO |
| 88 | site/index.pt-BR.html: legenda MAE por fold urgencia: sarimax é o líder h=1 | sarimax | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin | sarimax | VERIFICADO |
| 89 | site/index.pt-BR.html: legenda '180 dias de teste por fold' (urgencia) | [180] | folds.csv | n_teste | [180] | VERIFICADO |
| 90 | site/index.pt-BR.html: legenda ablação total h=1 melhor conjunto XGBoost | XGBoost AR_CAL 18,56 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | XGBoost AR_CAL 18,56 | VERIFICADO |
| 91 | site/index.pt-BR.html: legenda ablação total h=1 melhor conjunto SARIMAX | SARIMAX AR_CAL_POLUENTES 18,72 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | SARIMAX AR_CAL_POLUENTES 18,72 | VERIFICADO |
| 92 | site/index.pt-BR.html: legenda ablação total h=1 melhor conjunto LSTM | LSTM AR_CAL 19,01 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | LSTM AR_CAL 19,01 | VERIFICADO |
| 93 | site/index.pt-BR.html: legenda ablação total h=1 melhor conjunto INGARCH-NB | INGARCH-NB AR_CAL_POLUENTES 19,25 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | INGARCH-NB AR_CAL_POLUENTES 19,25 | VERIFICADO |
| 94 | site/index.pt-BR.html: legenda ablação total h=1 melhor conjunto GAM-NB | GAM-NB AR_CAL_POLUENTES 21,58 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | GAM-NB AR_CAL_POLUENTES 21,58 | VERIFICADO |
| 95 | site/index.pt-BR.html: legenda ablação urgencia h=1 melhor conjunto XGBoost | XGBoost AR_CAL_METEO_PM25 14,57 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | XGBoost AR_CAL_METEO_PM25 14,57 | VERIFICADO |
| 96 | site/index.pt-BR.html: legenda ablação urgencia h=1 melhor conjunto SARIMAX | SARIMAX AR_CAL_METEO_PM25MEDIA 13,85 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | SARIMAX AR_CAL_METEO_PM25MEDIA 13,85 | VERIFICADO |
| 97 | site/index.pt-BR.html: legenda ablação urgencia h=1 melhor conjunto LSTM | LSTM AR_CAL_PM25MEDIA 14,63 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | LSTM AR_CAL_PM25MEDIA 14,63 | VERIFICADO |
| 98 | site/index.pt-BR.html: legenda ablação urgencia h=1 melhor conjunto INGARCH-NB | INGARCH-NB AR_CAL_POLUENTES 14,55 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | INGARCH-NB AR_CAL_POLUENTES 14,55 | VERIFICADO |
| 99 | site/index.pt-BR.html: legenda ablação urgencia h=1 melhor conjunto GAM-NB | GAM-NB AR_CAL_POLUENTES 16,41 | results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv | argmin MAE_medio por modelo, todos os conjuntos | GAM-NB AR_CAL_POLUENTES 16,41 | VERIFICADO |
| 100 | site/index.pt-BR.html: legenda sábado XGBoost total MAE_sab | 33,31 | erro_sabado_h1.csv | total,XGBoost,MAE_sab | 33,31 | VERIFICADO |
| 101 | site/index.pt-BR.html: legenda sábado XGBoost total MAE_demais | 16,09 | erro_sabado_h1.csv | total,XGBoost,MAE_demais | 16,09 | VERIFICADO |
| 102 | site/index.pt-BR.html: legenda sábado XGBoost total razao | 2,07 | erro_sabado_h1.csv | total,XGBoost,razao | 2,07 | VERIFICADO |
| 103 | site/index.pt-BR.html: legenda sábado razão urgência | 0,90 | erro_sabado_h1.csv | urgencia,XGBoost,razao | 0,90 | VERIFICADO |
| 104 | site/index.pt-BR.html: legenda dispersão: maior dp entre sementes | LSTM total h=30 1,37 | model_comparison.csv (10 runs), MAE_std_semente; conferido com metrics_by_fold | max | LSTM total h=30 1,37 | VERIFICADO |
| 105 | site/index.pt-BR.html: legenda dispersão: dp entre folds XGBoost h=1 total | 2,34 | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | MAE_std_fold (e std ddof=1 das médias por fold) | 2,34 / 2,34 | VERIFICADO |
| 106 | site/index.pt-BR.html: BibTeX version/year/month | 0.1.1/2026/11 | CITATION.cff | version, date-released | 0.1.1/2026/11 | VERIFICADO |
| 107 | prov.json: app_screenshot.prov.json | f2f7aeeaa728 | site/static/images/app_screenshot.prov.json | sha256 do PNG | f2f7aeeaa728 | VERIFICADO |
| 108 | prov.json: fig_ablacao_h1_total_en.prov.json | 3 origens; runs=1 | site/static/images/fig_ablacao_h1_total_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 109 | prov.json: fig_ablacao_h1_total_pt.prov.json | 3 origens; runs=1 | site/static/images/fig_ablacao_h1_total_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 110 | prov.json: fig_ablacao_h1_urgencia_en.prov.json | 3 origens; runs=1 | site/static/images/fig_ablacao_h1_urgencia_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 111 | prov.json: fig_ablacao_h1_urgencia_pt.prov.json | 3 origens; runs=1 | site/static/images/fig_ablacao_h1_urgencia_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 112 | prov.json: fig_dispersao_sementes_en.prov.json | 12 origens; runs=10 | site/static/images/fig_dispersao_sementes_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 113 | prov.json: fig_dispersao_sementes_pt.prov.json | 12 origens; runs=10 | site/static/images/fig_dispersao_sementes_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 114 | prov.json: fig_mae_por_fold_h1_total_en.prov.json | 3 origens; runs=1 | site/static/images/fig_mae_por_fold_h1_total_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 115 | prov.json: fig_mae_por_fold_h1_total_pt.prov.json | 3 origens; runs=1 | site/static/images/fig_mae_por_fold_h1_total_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 116 | prov.json: fig_mae_por_fold_h1_urgencia_en.prov.json | 3 origens; runs=1 | site/static/images/fig_mae_por_fold_h1_urgencia_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 117 | prov.json: fig_mae_por_fold_h1_urgencia_pt.prov.json | 3 origens; runs=1 | site/static/images/fig_mae_por_fold_h1_urgencia_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 118 | prov.json: fig_mae_por_h_total_en.prov.json | 12 origens; runs=5 | site/static/images/fig_mae_por_h_total_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 119 | prov.json: fig_mae_por_h_total_pt.prov.json | 12 origens; runs=5 | site/static/images/fig_mae_por_h_total_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 120 | prov.json: fig_mae_por_h_urgencia_en.prov.json | 12 origens; runs=5 | site/static/images/fig_mae_por_h_urgencia_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 121 | prov.json: fig_mae_por_h_urgencia_pt.prov.json | 12 origens; runs=5 | site/static/images/fig_mae_por_h_urgencia_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 122 | prov.json: fig_sabado_razao_h1_en.prov.json | 1 origens; runs=2 | site/static/images/fig_sabado_razao_h1_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 123 | prov.json: fig_sabado_razao_h1_pt.prov.json | 1 origens; runs=2 | site/static/images/fig_sabado_razao_h1_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 124 | prov.json: fig_skill_por_h_total_en.prov.json | 12 origens; runs=5 | site/static/images/fig_skill_por_h_total_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 125 | prov.json: fig_skill_por_h_total_pt.prov.json | 12 origens; runs=5 | site/static/images/fig_skill_por_h_total_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 126 | prov.json: fig_skill_por_h_urgencia_en.prov.json | 12 origens; runs=5 | site/static/images/fig_skill_por_h_urgencia_en.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 127 | prov.json: fig_skill_por_h_urgencia_pt.prov.json | 12 origens; runs=5 | site/static/images/fig_skill_por_h_urgencia_pt.prov.json | sha256 das origens == arquivo atual; runs existem em results/; descrição == legenda da página | sha ruins=0; runs ok=True; legenda igual=True | VERIFICADO |
| 128 | prov.json: site/build_provenance.json entradas | 43 entradas | site/build_provenance.json | sha256 de cada entrada == arquivo atual | divergentes: [] | VERIFICADO |

### c.5 App (duas línguas, renderizado com `streamlit.testing.AppTest`)

| # | Onde | Exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 1 | app Home (en): dias na série | 2,192 | data/processed/sih_daily_lookahead.parquet | nº de linhas (e meta.dias) | 2,192 | VERIFICADO |
| 2 | app Home (en): AIH distintas total | 303,295 | sih_daily_lookahead.parquet | soma de internacoes (e meta.total_aih_distintas) | 303,295 | VERIFICADO |
| 3 | app Home (en): AIH distintas urgência | 263,399 | sih_daily_lookahead_urgencia.parquet | soma (e meta) | 263,399 | VERIFICADO |
| 4 | app Home (en): melhor MAE h=1 | Best MAE, h = 1 (XGBoost) = 18.56 (MASE 0.645 · AR_CAL) | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin AR_CAL | XGBoost 18.56 MASE 0.645 | VERIFICADO |
| 5 | app Overview (en): média internações/dia | 138.4 | sih_daily_lookahead.parquet | mean | 138.4 | VERIFICADO |
| 6 | app Overview (en): dias com zero | 0 | sih_daily_lookahead.parquet | (internacoes==0).sum() | 0 | VERIFICADO |
| 7 | app Overview (en): PM2,5 médio | 15.5 | data/processed/cetesb_poluentes_daily.csv | pm25_media.mean() | 15.5 | VERIFICADO |
| 8 | app Overview (en): estações/dia | 10.6 | cetesb_poluentes_daily.csv | pm25_n_estacoes.mean() | 10.6 | VERIFICADO |
| 9 | app Overview (en): dias sem estação válida | 0 | cetesb_poluentes_daily.csv | pm25_media.isna().sum() | 0 | VERIFICADO |
| 10 | app Sábado (en): internações jan/2019–fev/2026 | 368,758 | notebooks/dados_painel/diario.csv | total.sum() | 368,758 | VERIFICADO |
| 11 | app Sábado (en): média/dia | 141.0 | diario.csv | total.mean() | 141.0 | VERIFICADO |
| 12 | app Sábado (en): parcela eletiva | 13.9% | diario.csv | eletivo.sum()/total.sum() | 13.9% | VERIFICADO |
| 13 | app Sábado (en): sábados atípicos desde 2022 (total → urgência) | 43 → 0 | diario.csv | razão > 1,3 sobre mediana móvel centrada de 29 dias (min 15), sábados ≥ 2022 | 43 → 0 | VERIFICADO |
| 14 | app Sábado (en): grupos sensíveis '8,315' | 8,315 | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 8,315 | VERIFICADO |
| 15 | app Sábado (en): grupos sensíveis '277,006' | 277,006 | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 277,006 | VERIFICADO |
| 16 | app Sábado (en): grupos sensíveis '3.0%' | 3.0% | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 3.0% | VERIFICADO |
| 17 | app Sábado (en): grupos sensíveis '**4**' | **4** | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | **4** | VERIFICADO |
| 18 | app Sábado (en): correlação grupos sensíveis 2019–2024 (título do gráfico) | (calculado no app) | diario.csv | corr mensal sens_nao_eletivo × sens_eletivo | 0.04 | VERIFICADO |
| 19 | app Sábado (en): '15 estabelecimentos' | 15 | notebooks/dados_painel/estabelecimentos_ano.csv | CNES.nunique() | 15 | VERIFICADO |
| 20 | app Sábado (en): tabela de atraso soma 100% por dia | 100 | notebooks/dados_painel/atraso_registro_2022_mais.csv | soma das colunas 0–4 por linha | 100.00,100.01,100.01,100.00,100.00,99.99,99.99 | VERIFICADO |
| 21 | app Sábado (en): 'o sábado não é registrado mais tarde' | sáb. dentro da faixa | atraso_registro_2022_mais.csv | % no mês 0 por dia (sábado=5) | sáb 66.36; faixa 59.05–66.36 | VERIFICADO |
| 22 | app Sábado (en): pico nos três primeiros sábados do mês (2022+) | k=1..3 > k=4..5 | diario.csv | mediana da razão por posição do sábado | 1:1.19, 2:1.05, 3:1.10, 4:0.80, 5:0.64 | VERIFICADO |
| 23 | app Sábado (en): 'sobretudo J30–J39' sai do alvo | J30–J39 maior nº de eletivas | grupos_cid.csv | argmax eletivas | J30–J39 outras doenças das vias aéreas sup. (35958 de 51418) | VERIFICADO |
| 24 | app Dados (en): tabela de construção do alvo (coluna total) | 303,372\|303,295\|77\|0\|2,192\|0 | data/processed/sih_daily_lookahead.meta.json | total_linhas_somadas, total_aih_distintas, duplicatas, dt_inter_invalidas, dias, dias_com_zero | 303,372\|303,295\|77\|0\|2,192\|0 | VERIFICADO |
| 25 | app Dados (en): tabela de construção do alvo (coluna urgência) | 263,403\|263,399\|4\|0\|2,192\|0 | data/processed/sih_daily_lookahead_urgencia.meta.json | idem | 263,403\|263,399\|4\|0\|2,192\|0 | VERIFICADO |
| 26 | app Dados (en): tabela das 10 runs (commit, status, git_sujo, previsões) | 10 linhas | results/runs/*/manifest.json | git_commit[:7], status, git_sujo, n_predicoes | iguais | VERIFICADO |
| 27 | app Modelos (en): 'família de 21 contrastes', T = 720 | 21 / 720 | results/testes_dm/TESTES_DM_h1_v02_cetesb_cetesb_classicos_full_20261022-211834/dm_contrastes.csv | modelos_AR_CAL agrupado: nº de linhas, T | 21 / [720] | VERIFICADO |
| 28 | app Modelos (en): '4 de 10 pares entre os cinco modelos' (h=1) | 4 of 10 pairs | idem | pares entre treinados; p_holm<0.05 | 4 de 10 | VERIFICADO |
| 29 | app Modelos (en): tabela MAE/MASE por h (alvo total, 35 linhas) | 35 linhas | model_comparison.csv das 5 runs | MAE_medio, MASE_medio | 0 diferenças | VERIFICADO |
| 30 | app Home (pt): dias na série | 2.192 | data/processed/sih_daily_lookahead.parquet | nº de linhas (e meta.dias) | 2.192 | VERIFICADO |
| 31 | app Home (pt): AIH distintas total | 303.295 | sih_daily_lookahead.parquet | soma de internacoes (e meta.total_aih_distintas) | 303.295 | VERIFICADO |
| 32 | app Home (pt): AIH distintas urgência | 263.399 | sih_daily_lookahead_urgencia.parquet | soma (e meta) | 263.399 | VERIFICADO |
| 33 | app Home (pt): melhor MAE h=1 | Melhor MAE, h = 1 (XGBoost) = 18,56 (MASE 0,645 · AR_CAL) | results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv | argmin AR_CAL | XGBoost 18,56 MASE 0,645 | VERIFICADO |
| 34 | app Overview (pt): média internações/dia | 138,4 | sih_daily_lookahead.parquet | mean | 138,4 | VERIFICADO |
| 35 | app Overview (pt): dias com zero | 0 | sih_daily_lookahead.parquet | (internacoes==0).sum() | 0 | VERIFICADO |
| 36 | app Overview (pt): PM2,5 médio | 15,5 | data/processed/cetesb_poluentes_daily.csv | pm25_media.mean() | 15,5 | VERIFICADO |
| 37 | app Overview (pt): estações/dia | 10,6 | cetesb_poluentes_daily.csv | pm25_n_estacoes.mean() | 10,6 | VERIFICADO |
| 38 | app Overview (pt): dias sem estação válida | 0 | cetesb_poluentes_daily.csv | pm25_media.isna().sum() | 0 | VERIFICADO |
| 39 | app Sábado (pt): internações jan/2019–fev/2026 | 368.758 | notebooks/dados_painel/diario.csv | total.sum() | 368.758 | VERIFICADO |
| 40 | app Sábado (pt): média/dia | 141,0 | diario.csv | total.mean() | 141,0 | VERIFICADO |
| 41 | app Sábado (pt): parcela eletiva | 13,9% | diario.csv | eletivo.sum()/total.sum() | 13,9% | VERIFICADO |
| 42 | app Sábado (pt): sábados atípicos desde 2022 (total → urgência) | 43 → 0 | diario.csv | razão > 1,3 sobre mediana móvel centrada de 29 dias (min 15), sábados ≥ 2022 | 43 → 0 | VERIFICADO |
| 43 | app Sábado (pt): grupos sensíveis '8.315' | 8.315 | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 8.315 | VERIFICADO |
| 44 | app Sábado (pt): grupos sensíveis '277.006' | 277.006 | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 277.006 | VERIFICADO |
| 45 | app Sábado (pt): grupos sensíveis '3,0%' | 3,0% | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | 3,0% | VERIFICADO |
| 46 | app Sábado (pt): grupos sensíveis '**4**' | **4** | notebooks/dados_painel/grupos_cid.csv | sensivel=True: eletivas, total, %, eletivas_cema | **4** | VERIFICADO |
| 47 | app Sábado (pt): correlação grupos sensíveis 2019–2024 (título do gráfico) | (calculado no app) | diario.csv | corr mensal sens_nao_eletivo × sens_eletivo | 0,04 | VERIFICADO |
| 48 | app Sábado (pt): '15 estabelecimentos' | 15 | notebooks/dados_painel/estabelecimentos_ano.csv | CNES.nunique() | 15 | VERIFICADO |
| 49 | app Sábado (pt): tabela de atraso soma 100% por dia | 100 | notebooks/dados_painel/atraso_registro_2022_mais.csv | soma das colunas 0–4 por linha | 100.00,100.01,100.01,100.00,100.00,99.99,99.99 | VERIFICADO |
| 50 | app Sábado (pt): 'o sábado não é registrado mais tarde' | sáb. dentro da faixa | atraso_registro_2022_mais.csv | % no mês 0 por dia (sábado=5) | sáb 66.36; faixa 59.05–66.36 | VERIFICADO |
| 51 | app Sábado (pt): pico nos três primeiros sábados do mês (2022+) | k=1..3 > k=4..5 | diario.csv | mediana da razão por posição do sábado | 1:1.19, 2:1.05, 3:1.10, 4:0.80, 5:0.64 | VERIFICADO |
| 52 | app Sábado (pt): 'sobretudo J30–J39' sai do alvo | J30–J39 maior nº de eletivas | grupos_cid.csv | argmax eletivas | J30–J39 outras doenças das vias aéreas sup. (35958 de 51418) | VERIFICADO |
| 53 | app Dados (pt): tabela de construção do alvo (coluna total) | 303.372\|303.295\|77\|0\|2.192\|0 | data/processed/sih_daily_lookahead.meta.json | total_linhas_somadas, total_aih_distintas, duplicatas, dt_inter_invalidas, dias, dias_com_zero | 303.372\|303.295\|77\|0\|2.192\|0 | VERIFICADO |
| 54 | app Dados (pt): tabela de construção do alvo (coluna urgência) | 263.403\|263.399\|4\|0\|2.192\|0 | data/processed/sih_daily_lookahead_urgencia.meta.json | idem | 263.403\|263.399\|4\|0\|2.192\|0 | VERIFICADO |
| 55 | app Dados (pt): tabela das 10 runs (commit, status, git_sujo, previsões) | 10 linhas | results/runs/*/manifest.json | git_commit[:7], status, git_sujo, n_predicoes | iguais | VERIFICADO |
| 56 | app Modelos (pt): 'família de 21 contrastes', T = 720 | 21 / 720 | results/testes_dm/TESTES_DM_h1_v02_cetesb_cetesb_classicos_full_20261022-211834/dm_contrastes.csv | modelos_AR_CAL agrupado: nº de linhas, T | 21 / [720] | VERIFICADO |
| 57 | app Modelos (pt): '4 de 10 pares entre os cinco modelos' (h=1) | 4 de 10 pares | idem | pares entre treinados; p_holm<0.05 | 4 de 10 | VERIFICADO |
| 58 | app Modelos (pt): tabela MAE/MASE por h (alvo total, 35 linhas) | 35 linhas | model_comparison.csv das 5 runs | MAE_medio, MASE_medio | 0 diferenças | VERIFICADO |


Observações sobre c.4:

- **Dispersão entre sementes** (`fig_dispersao_sementes_*`): o 1,37 da LSTM (total, h = 30) é `MAE_std_semente` do `model_comparison.csv`, que o runner define como **média, sobre os 4 folds, do desvio-padrão entre sementes dentro de cada fold** (`run_preliminary.py:685`). O desvio-padrão entre sementes do MAE médio de cada semente, que é o que a legenda "Standard deviation of the MAE across the 5 seeds" sugere, é 1,03. O número está certo para a coluna que cita; a legenda é ambígua (item 10). O 2,34 do XGBoost entre folds é `MAE_std_fold` e coincide com o desvio-padrão amostral das médias por fold.
- **Tabela DM da página**: para cada alvo × h, o líder e os pares significativos foram recontados em `dm_contrastes.csv` (família `modelos_AR_CAL`, escopo agrupado, só pares entre modelos treinados, `p_holm < 0,05`) e conferidos contra `A2_dm_modelos_por_h.csv`: 10/10 iguais. XGBoost, SARIMAX e LSTM: 0 pares significativos em 30 (10 runs × 3 pares).
- **`.prov.json`**: os 22 `.prov.json` das figuras citam só arquivos de `results/` cujo sha256 bate com o arquivo atual, citam só runs presentes em `results/runs/`, e a `descricao` de cada um é idêntica à legenda da página na língua correspondente. `app_screenshot.prov.json`: sha256 do PNG confere. `build_provenance.json`: 0 entradas divergentes.
- **Página publicada**: `https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/` e `/index.pt-BR.html` respondem 200, mas o `index.html` publicado tem o sha256 do `site/index.html` de `2f7bf9c`/`06a3d24` (BibTeX `version = {0.1.0}`), não o de `b90f3e2` (`0.1.1`). O Pages é manual e não foi reexecutado depois do bump (item 3).

### c.6 Docs e LEIA-MEs novos (conferência manual)

| # | Onde | Exibido | Arquivo / comando | Valor lido | Status |
|---:|---|---|---|---|---|
| 1 | `docs/REPRODUCIBILITY.md:30` | run h = 1 de 2026-10-22 21:18:34 a 23:43:02 | `results/runs/h1_v02_…/manifest.json`, `proveniencia.inicio/fim` | `2026-10-22T21:18:34` / `2026-10-22T23:43:02` | VERIFICADO |
| 2 | `docs/DECISOES.md:17` (D10) | tópicos do repositório aplicados (14) | `gh repo view --json repositoryTopics` | 14 tópicos | VERIFICADO |
| 3 | `docs/DECISOES.md:17` (D10) | release `v0.1.0` no commit `2f7bf9c` | `git rev-list -n1 v0.1.0` | `2f7bf9cb…` | VERIFICADO |
| 4 | `docs/DECISOES.md:17` (D10) | página responde (EN e PT); campo de site aponta para a página | `curl -w %{http_code}`; `gh repo view --json homepageUrl` | 200 / 200; `https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/` | VERIFICADO |
| 5 | `docs/DECISOES.md:20` (D13) | 14 figuras de `reports/figs/resultados_v02/` vêm da run `…_20261022-092503`, uma também de runs CAMS | leitura do repositório da dissertação (somente leitura): 28 arquivos `.pdf`/`.png`, 14 `.prov.json` citam `092503`, 1 cita `cams_cams` | 14 / 14 / 1 | VERIFICADO |
| 6 | `docs/DECISOES.md:16` (D9) | MLflow local em `D:\Project\mlflow_pesquisa` (SQLite), catálogo fora do repo | `ls` | `mlflow.db`, `catalogo_runs.yaml`, `artifacts/` presentes; nenhum no Git | VERIFICADO |
| 7 | `deploy/hf_space/LEIA-ME.md:83` | imagem roda como `uid 1000` na porta 7860 | `api/Dockerfile` + passo "Imagem enxuta - uid 1000 e sem tensorflow" do CI `b90f3e2` | ok / passou | VERIFICADO |
| 8 | `deploy/hf_space/LEIA-ME.md:51-52` | `configs/` dos três horizontes e os quatro arquivos de `data/processed/` | `deploy/hf_space/montar_space.py:60-66` | 3 configs, 4 arquivos | VERIFICADO |
| 9 | `.devcontainer/LEIA-ME.md:17-18` | portas 8501, 8000, 5000 | `.devcontainer/devcontainer.json` (`forwardPorts`, `portsAttributes`) | iguais | VERIFICADO |
| 10 | `api/README.md:45-53` | `versao` `ba6d6c40-20261123`; origens válidas h = 1/7/30: 2019-01-28 a 2024-12-30 / 12-24 / 12-01 | `models_demo/metadata.json` | iguais | VERIFICADO |
| 11 | `docs/ARCHITECTURE.md:56` e mais 3 lugares | "byte-identical" incluindo `predictions.csv` | ver D3 | — | **DIVERGENTE** |
| 12 | `README.md:142` e mais 3 lugares | "no trained weights" | ver D2 | — | **DIVERGENTE** |
| 13 | `README.md:103` / PT | 3m52s | ver S1 | — | **SEM FONTE** |
| 14 | `docs/REPRODUCIBILITY.md:30` | 10.5 s | ver S2 | — | **SEM FONTE** |
| 15 | `deploy/hf_space/LEIA-ME.md:5` | ~uma ordem de grandeza | ver S3 | — | **SEM FONTE** |
| 16 | `.devcontainer/LEIA-ME.md:11` | minor 0.13.x do lock | ver S4 | — | **SEM FONTE** |
| 17 | `.devcontainer/LEIA-ME.md:25` | ~1 GB | ver S5 | — | **SEM FONTE** |
| 18 | `app/i18n.py:273` | J35/J34 | ver S6 | — | **SEM FONTE** |

`data/README.md` e `models_demo/MODEL_CARD.md`: o diff desde `44946b4` é só fim de linha (`git diff -w --ignore-cr-at-eol` vazio para o data card; o model card não mudou); os números foram conferidos na rodada anterior e continuam cobertos por `conferir_numeros.py`.

## (d) Legado e escopo

| Checagem | Comando / fonte | Resultado |
|---|---|---|
| Lista "fica fora" em `git ls-files` | regex com `src/main.py`, `join_and_lstm`, `src/tests/`, `metrics/`, `reports/metrics`, `Version `, `fetch_sih_bq`, `sih_datasus_pipeline`, `microdados`, `environment.yml`, `handoff`, `CLAUDE.md`, `preliminar_`, `.env`, `.cdsapirc`, `env/`, `mlruns`, `mlflow_pesquisa`, `catalogo_runs`, `mlflow.db` | **0** (483 arquivos versionados) |
| Mesma lista no histórico | `git log --all --diff-filter=A --name-only` | 0; e nenhum arquivo jamais removido (`--diff-filter=D` vazio) |
| `src/` só com módulos do inventário | `comm -23 <(git ls-files src tests configs data) <(coluna destino do INVENTARIO_FASE0.tsv)` | `src/`: nada fora do inventário. Fora do inventário só arquivos escritos para o portfólio: `configs/smoke.yaml`, `configs/smoke_mlflow.yaml`, `data/README.md` e 7 testes novos (`test_api_forecast`, `test_app_smoke`, `test_build_site`, `test_deploy_montar_space`, `test_runner_mlflow`, `test_tracking_importar_pesquisa`, `test_tracking_importar_runs`). |
| Edições em `src/` declaradas | `verificar_inventario.py` (`EDITADOS_DEPOIS`) e `git diff 44946b4..HEAD -- src` | `run_preliminary.py` (opção `--mlflow`, D9) e as três docstrings da CETESB: todas declaradas. O diff do runner só acrescenta ganchos atrás de `if reg is not None` / `if mlflow_opcoes`, import tardio de `tracking.registro_mlflow`, e erro de CLI se `--mlflow-uri`/`--mlflow-experimento` vierem sem `--mlflow`. |
| Rótulo provisório | `grep -ci provisional\|provisório` + renderização do app | README EN 7×, PT 7×; página EN 24×, PT 24× (faixa no topo, ao lado de cada tabela e bloco de figuras, `a_modelos_por_h.json` com `status`); app: `st.warning` em todas as páginas nas duas línguas (conferido no `AppTest` e por `test_app_smoke`); `MODEL_CARD.md` 2×; `CITATION.cff` 2× (`message` e `abstract`). `api/README.md` e `deploy/hf_space/LEIA-ME.md` dizem "Demonstration, not a dissertation result" / "demonstração, não resultado da dissertação" (aceitável). |
| CAMS como "fonte principal" | grep nos dois sentidos | só "CETESB (main source) … CAMS (alternative source)": README EN/PT L22, `CITATION.cff:33`, `LESSONS.md:38`, app (`dl.fontes`), página (tabela de fontes). Os 10 manifests têm `fonte_pm25 = fonte_meteo = cetesb`, o que sustenta "none of its columns enters a feature in the runs shown here". |
| "dobra" | `git ls-files \| xargs grep -nIiw "dobra\|dobras"` | texto novo: 0 (README, página, app, docs). Só `src/models/sarimax_model.py:90-91` e `tests/test_sarimax_model.py:305,315,347` (comentários herdados) e as checagens que proíbem a palavra (`conferir_numeros.py:1327`, `test_build_site.py:143`). |
| TCN / TFT / SHAP | grep fora de `src/ tests/ configs/ results/` | README EN L144, PT L146, página L293, app `dl.limites` ("Not executed … no claims are made about them"). Nenhuma afirmação de desempenho. |
| API demonstração in-sample e "ainda não publicada" | README, `api/README.md`, `MODEL_CARD.md`, app, página | README EN L116/L121 e PT: "**The API is not yet deployed**", "in-sample by construction"; `MODEL_CARD.md:84` "In-sample by construction"; `api/README.md:101-104` (todas as datas no treino); app (`dl.limites`): demonstração treinada em todo o histórico. **A página** só diz "engineering demonstration … not the benchmark models": não diz in-sample nem "não publicada" (o botão "API docs" aponta para `api/README.md`, não para um endpoint; item 9). |
| DOI inventado | grep `doi`, `10.5281`, `doi.org` | nenhum DOI. `CITATION.cff:46` "no DOI"; README "No DOI yet"; página "Zenodo DOI: pending author decision" e "no paper, preprint or DOI exists"; BibTeX sem campo `doi`. |
| Runs `preliminar_*` | — | nenhuma copiada; nenhuma citada com números. |

**Veredito (d): OK** (com a ressalva da página sobre a API, baixa).

## (e) Consistência

| Item | Esperado | Encontrado | Veredito |
|---|---|---|---|
| Versão | 0.1.1 em todo lugar | `pyproject.toml:3` 0.1.1; `uv.lock:1951` 0.1.1; `CITATION.cff` `version: 0.1.1`, `date-released: "2026-11-26"`; BibTeX de `site/index.html` e `site/index.pt-BR.html` versionados: `version = {0.1.1}`, `year = {2026}`, `month = {11}` | OK |
| Página publicada | igual a `site/` de `HEAD` | publicada = `site/index.html` de `2f7bf9c`/`06a3d24` (`version = {0.1.0}`); o workflow `pages.yml` é manual e rodou às 16:54 (antes do bump) | **ACHADO** (item 3) |
| Release citada nos READMEs | a release vigente | README EN L148 / PT L150: `v0.1.0` (existe, tag em `2f7bf9c`); a v0.1.1 está sendo criada em paralelo e, pela D10, é a que gera o DOI no Zenodo; os READMEs dizem "No DOI yet … do not cite a DOI". Hoje correto; fica desatualizado assim que a v0.1.1 e o DOI existirem. | ACHADO (menor, item 3) |
| READMEs EN × PT | mesma estrutura e mesmo conteúdo factual | 11 títulos, na mesma ordem; URLs idênticos exceto o selo da página (traduzido); blocos de código e números idênticos (comparação por `Counter` após normalizar a vírgula decimal e o ponto de milhar); a PT tem uma linha a mais (L130, aviso de que `docs/` e o data card estão em inglês — impreciso: `DECISOES.md`, `AUDITORIA.md` e os dois `LEIA-ME.md` estão em português; item 14) | OK |
| `.gitattributes` `-text` × fixadores do pre-commit | tudo que é `-text` fora de `trailing-whitespace`, `end-of-file-fixer`, `mixed-line-ending` | `-text`: `data/**`, `results/**`, `site/data/**`, `notebooks/dados_painel/**`, `configs/**`; `exclude` dos três hooks: `^(data/\|results/\|site/data/\|notebooks/\|configs/\|src/\|docs/requirements-executado-\|docs/CONFERENCIA_NUMEROS_WP5\.md\|models_demo/(MODEL_CARD\.md\|metadata\.json))` ⊇ `-text` | OK |
| Arquivos com sha256 registrado | bytes estáveis em qualquer checkout | dados/artefatos/configs: `-text`; `*.ubj`/`*.png`/`*.parquet`: `binary`; código copiado: comparado após EOL pelo verificador; `README.md`, `CITATION.cff`, `data/README.md`, `app/graficos.py` (entradas do `build_provenance.json`): `text=auto eol=lf`, LF em qualquer SO | OK |
| `.dockerignore` × testes no contêiner | nada que os testes leiam está excluído | os testes leem `README.md`, `README.pt-BR.md`, `CITATION.cff`, `data/README.md`, `site/`, `docs/INVENTARIO_FASE0.tsv`, `docs/scripts/`, `api/Dockerfile`, `deploy/`, `configs/smoke_mlflow.yaml`, `models_demo/`, `results/`: nenhum excluído. Excluídos e não lidos: `.github`, `.gitattributes` (os testes leem o `.gitattributes` **gerado** pelo `montar_space.py`), `Dockerfile`, `docker-compose.yml`, `Makefile`. **Exceção:** `.git` está excluído, por isso `test_sem_mlflow_identico_ao_runner_de_referencia` é pulado no contêiner (1 `s` no log do job docker). | OK, com o achado abaixo |
| Prova "sem `--mlflow` a saída não muda" | exercida pelo CI | local: `tests/test_runner_mlflow.py -v` → 8 passed, inclusive `test_sem_mlflow_identico_ao_runner_de_referencia` e `test_com_mlflow_identico_a_sem_mlflow`. CI: o job `pytest` usa `actions/checkout@v4` sem `fetch-depth` (clone raso), o `COMMIT_REFERENCIA = 2be070b` não está no clone e o teste é **pulado** (log de `45868887453`: `….s....`); no contêiner também. A afirmação do README/ARCHITECTURE/D9 só tem prova local. `test_com_mlflow_identico_a_sem_mlflow` (com × sem a opção) roda no CI. | **ACHADO** (item 1) |
| Extras × imports | `app`, `api`, `tracking` cobrem os imports | `app/`: `streamlit`, `plotly`, `pandas`, `numpy` → extra `app` + núcleo; `app/requirements.txt` (Community Cloud): 5 pacotes (`streamlit`, `plotly`, `pandas`, `numpy`, `pyarrow`), versões iguais às do lock. `api/`: `fastapi`, `pydantic`, `xgboost`, `pandas` → extra `api` + núcleo (`pydantic` só como dependência do `fastapi`; explícito em `api/requirements.txt`). `tracking/`: `mlflow`, `yaml`, `numpy`, `pandas` → extra `tracking` + núcleo. `docs/scripts/`: `jinja2`, `markupsafe` (via jinja2), `matplotlib` → núcleo. `deploy/`: só stdlib. `api/requirements.txt` × `uv.lock`: o job `api-slim` do CI exige versão igual e passa. | OK |
| `docker-compose.yml` × `Makefile` × `ci.yml` × Dockerfiles | mesmos comandos, portas e alvos | compose: `app` 8501 (`app/Home.py`), `api` 8000 (`api.main:app`, healthcheck `/health`), `mlflow` 5000 (`./mlruns`, `MLFLOW_ALLOW_FILE_STORE=true`), os três com `build: *build` (alvo `runtime`). Makefile: `app`, `api`, `mlflow` iguais; `docker-test` usa `--target test`; `docker-api` usa `api/Dockerfile` e 7860; `up` = `docker compose up --build`. CI: build `runtime`, `test`, `api`; `docker run …:test` (pytest + smoke); `docker compose up -d --no-build api` + `/health`; imagem enxuta em 7860, uid 1000, sem TensorFlow. | OK |
| `.devcontainer/devcontainer.json` | coerente com CI e pyproject | imagem `python:1-3.11-bookworm` (pyproject `>=3.11,<3.12`); `uv sync --frozen --all-extras` (= job `test`); `app/Home.py` e `openFiles` existem; portas 8501/8000/5000; `MLFLOW_ALLOW_FILE_STORE`. O CI valida tudo isso (job `lint`, passo "devcontainer.json válido"). Menor: `pipx install uv==0.13.7` aqui × `setup-uv@v6` sem versão no CI (0.13.10 no log). `postAttachCommand` desliga CORS/XSRF do Streamlit: aceitável só no Codespaces (porta encaminhada autenticada), como o LEIA-ME diz. | OK (informativo, item 16) |
| `.pre-commit-config.yaml` × CI × Makefile (lint) | mesmos caminhos | CI e `Makefile` (`LINT_PATHS`) incluem `deploy/`; os hooks `ruff-check`/`ruff-format` usam `files: ^(app\|api\|tracking\|models_demo)/` (L43, L46), sem `deploy/`. `rev: v0.17.6` = `ruff` 0.17.6 do `uv.lock`. | ACHADO (menor, item 8) |
| `gitleaks` no pre-commit | o README L105 e o cabeçalho do config (L5-6: "gitleaks … cobrem o repositório inteiro") | o hook varre só o staged; `make precommit` (`--all-files`) não varre o repositório. Nenhum job do CI roda gitleaks. | ACHADO (menor, item 6) |
| `conferir_numeros.py` | conferência sem efeito colateral | sempre regrava `docs/CONFERENCIA_NUMEROS_WP5.md` (linha 1431, `write_text` sem `newline`), com novo carimbo de hora; no Windows com CRLF. Rodar a conferência suja a árvore — contra a regra de árvore limpa. | ACHADO (menor, item 7) |
| CI mais recente | verde | `gh run list --limit 3`: `45868887453` (CI, `b90f3e2`) success 16m40s; `45862989953` (Project page, manual) success; `45862942820` (CI, `2f7bf9c`) success. O commit `06a3d24` foi enviado junto com `b90f3e2` (sem CI próprio). Antes, `45858536476` (`737db3e`) falhou e foi corrigido em `2f7bf9c`. | OK |

**Veredito (e): ACHADO (médio)** — a prova de byte-identidade não roda no CI; página publicada desatualizada; três menores.

## (f) Testes

| Comando | Commit | Resultado | Tempo |
|---|---|---|---|
| `uv run pytest -q` (`.venv` local, `--all-extras`) | `b90f3e2` | **278 coletados, 278 passed, 0 failed, 0 skipped**, exit 0. A linha-resumo não aparece porque `addopts = "-q"` no `pyproject.toml` somado ao `-q` da linha de comando vira `-qq`; contagem por `--collect-only` (278) e pelos 278 pontos de progresso sem `s`/`F`/`E`. Avisos: `StarletteDeprecationWarning` (httpx/testclient) e `RuntimeWarning: overflow in exp` esperado em `test_ingarch_nb::test_predict_falha_alto_se_previsao_sair_da_faixa_do_alvo`. | 7m18s (com gitleaks/detect-secrets em paralelo) |
| `uv run pytest tests/test_runner_mlflow.py -v -rs -o addopts=""` | `b90f3e2` | 8 passed, 0 skipped (inclusive a prova contra `2be070b`) | 1m56s |
| `uv run python -m src.experiments.run_preliminary --config configs/smoke.yaml --smoke` | `b90f3e2` | exit 0; `STATUS: PRELIMINARY_VALIDATED_TARGET`; 1 fold, Naïve, Seasonal Naïve, XGBoost `AR`/`AR_CAL`; artefatos em `reports/experiments/smoke_smoke_20261126-144340/` (git-ignorado). **Nunca é resultado.** | 8,98 s |
| CI `45868887453`, job `pytest` | `b90f3e2` | 277 passed + 1 skipped (`test_sem_mlflow_identico_ao_runner_de_referencia`, clone raso) | 3m46s em `45862942820` |
| CI `45868887453`, job `docker` (pytest + smoke na imagem `test`) | `b90f3e2` | idem, 1 skipped (`.git` fora da imagem); compose `/health` 200; imagem enxuta `/health` 200, uid 1000, sem TensorFlow | 16m40s o workflow |
| `streamlit.testing.v1.AppTest`, Home + 4 páginas × `en`/`pt` (script próprio) | `b90f3e2` | 10 renderizações, 0 exceções | ~10 s |

**Veredito (f): OK.**

## Itens a corrigir

Gravidade: **alta** = número errado ou dado sensível exposto; **média** = afirmação pública contrariada pelo próprio repositório ou garantia anunciada sem prova no CI; **baixa** = imprecisão, documentação desatualizada ou ferramenta com efeito colateral; **info** = sem ação obrigatória. Nenhum item de gravidade alta.

| # | Arquivo : linha | Problema | Correção sugerida | Gravidade |
|---:|---|---|---|---|
| 1 | `.github/workflows/ci.yml:84` (checkout do job `pytest`); `tests/test_runner_mlflow.py:135-149` | A prova "sem `--mlflow` a saída é idêntica à do runner de antes dos ganchos" é pulada no CI (clone raso) e no contêiner (`.git` excluído); README L122, `ARCHITECTURE.md:56` e D9 anunciam a garantia com base só em execução local. | No job `pytest`: `actions/checkout@v4` com `fetch-depth: 0` (ou um passo `git fetch --depth=1 origin 2be070bedeaff286fcca4682c7d52de3ccaa4782`). Opcional: fazer o teste falhar, não pular, quando `CI=true` e o commit não existir. | média |
| 2 | `README.md:142`, `README.pt-BR.md:144` (e, por geração, `site/index.html:293`, `site/index.pt-BR.html:293`) | "no trained weights" — há três modelos XGBoost treinados versionados em `models_demo/` (servidos pela API, destinados ao HF Space). | "No trained weights of the benchmark models (the only versioned weights are the three demonstration XGBoost models in `models_demo/`, see the model card), no per-seed artefacts…"; mesma correção em PT; depois `uv run python docs/scripts/build_site.py` e `conferir_numeros.py`. | média |
| 3 | GitHub Pages (página publicada); `README.md:148`, `README.pt-BR.md:150` | Página publicada mostra o BibTeX `version = {0.1.0}`; o `site/` de `HEAD` diz 0.1.1. Os READMEs citam a release `v0.1.0`. | Depois de criar a release v0.1.1: rodar o workflow "Project page" de novo; trocar a release citada por `v0.1.1`; quando o Zenodo emitir o DOI, atualizar `CITATION.cff` (`doi:`), READMEs, D10 e o BibTeX gerado. | média |
| 4 | `README.md:95`, `README.pt-BR.md:95` | "Saturday is the worst day for every model": o Naïve tem o maior erro no domingo (42,02) e na segunda (38,84), não no sábado (35,80). | "…the worst day for every trained model (and for the Seasonal Naïve)…" ou "Saturday errors exceed the other days for every model (ratio 1.30 for the Naïve to 2.39 for GAM-NB)". | baixa |
| 5 | `docs/ARCHITECTURE.md:56`; `README.md:122`; `README.pt-BR.md:122`; `docs/DECISOES.md:16` (D9) | "byte-identical" inclui `predictions.csv`, que só é igual depois de normalizar a coluna `run_id`; o `manifest.json` difere em tempo e RUN_ID. | "`metrics.json`, `model_comparison.csv`, `metrics_by_fold.csv`, `folds.csv` and `feature_ablation.csv` are byte-identical; `predictions.csv` and `manifest.json` are identical except for the run id and timestamps". | baixa |
| 6 | `.pre-commit-config.yaml:5-7`; `README.md:105`, `README.pt-BR.md:105` | O hook `gitleaks` só varre o staged; `make precommit` / `pre-commit run --all-files` passa sem varrer o repositório, e nenhum job do CI roda gitleaks. | Acrescentar ao CI um passo `gitleaks git --log-opts=--all` (ou `gitleaks/gitleaks-action`), ou um alvo `make secrets`; corrigir o comentário do config ("o hook varre só o diff staged"). | baixa |
| 7 | `docs/scripts/conferir_numeros.py:1431` | A conferência sempre regrava `docs/CONFERENCIA_NUMEROS_WP5.md` (novo carimbo de hora; CRLF no Windows), sujando a árvore. | Opção `--check` que só compara e sai com 1 se divergir; e/ou gravar com `newline="\n"` só quando o conteúdo (sem o carimbo) mudar. | baixa |
| 8 | `.pre-commit-config.yaml:43,46` | ruff do pre-commit não cobre `deploy/`; CI (`ci.yml`, job `lint`) e `Makefile` (`LINT_PATHS`) cobrem. | `files: ^(app\|api\|tracking\|models_demo\|deploy)/`. | baixa |
| 9 | `docs/scripts/build_site.py` (bloco "What this repository is not", L367; texto vindo do README) → `site/index*.html:293` | A página não diz que a API é in-sample nem que não está publicada (o README diz as duas coisas). | Acrescentar ao bullet da API: "in-sample by construction; not yet deployed (run it locally, see api/README.md)" / PT equivalente; regenerar `site/`. | baixa |
| 10 | `docs/scripts/build_site.py:889, 896` (legenda de `fig_dispersao_sementes_*`) | "Standard deviation of the MAE across the 5 seeds" é ambíguo: o número é a média, sobre os folds, do dp entre sementes em cada fold (`MAE_std_semente`); o dp entre sementes do MAE médio por semente é outro (LSTM total h = 30: 1,03 contra 1,37). | "Mean over the 4 folds of the standard deviation of the MAE across the 5 seeds (`MAE_std_semente`)…" / PT equivalente; regenerar `site/`. | baixa |
| 11 | `deploy/hf_space/LEIA-ME.md:5-6`; `.devcontainer/LEIA-ME.md:11-12, 24-25` | SEM FONTE: "~uma ordem de grandeza menor" (CI mostra 920 MB × 5,59 GB, ~6×); "~1 GB de wheels"; "mesma minor que gerou o `uv.lock`". | "cerca de 6× menor (920 MB × 5,6 GB no CI de 2026-11-26)"; tirar o "~1 GB" ou citar a medição; trocar a frase do lock por "mesma versão do uv usada localmente (0.13.7)" e fixar `version: "0.13.7"` no `setup-uv` do CI. | baixa |
| 12 | `app/i18n.py:273-274, 279-280` | SEM FONTE no repositório: "J35" e "J34" (o painel só tem o grupo J30–J39). Herdado de `44946b4`. | Reescrever como "mostly scheduled upper-airway surgery (ICD-10 group J30–J39)" ou citar a fonte (PROTOCOLO §0.23 da dissertação) na legenda. | baixa |
| 13 | `README.md:141`, `README.pt-BR.md:143` (→ página); `docs/DECISOES.md:26` | A frase sobre registros por estabelecimento omite a série diária do CNES 2091550 aceita pela D8. A "consequência prática" da D5 ("nenhum `git push`, nenhum repositório remoto até a Fase 4") está desatualizada: o repositório é público. | Acrescentar "and the daily series of CNES 2091550 (decision D8)"; marcar a consequência da D5 como superada pela publicação (com data). | baixa |
| 14 | `README.pt-BR.md:130`; `site/index.pt-BR.html` (tabela "Fontes de dados") | "A documentação em `docs/` e o data card estão em inglês (só o README existe nas duas línguas)": `DECISOES.md`, `AUDITORIA.md`, `deploy/hf_space/LEIA-ME.md` e `.devcontainer/LEIA-ME.md` estão em português, e app e página são bilíngues. A tabela de fontes da página PT mostra as colunas de fonte e licença em inglês (copiadas do data card). | "Os demais documentos de `docs/` (exceto `DECISOES.md` e `AUDITORIA.md`) e o data card estão em inglês; app e página têm as duas línguas"; aceitar ou traduzir a tabela da página PT. | baixa |
| 15 | `src/models/sarimax_model.py:90-91`; `tests/test_sarimax_model.py:305,315,347` | "dobra" em comentários de código herdado (pendente da rodada anterior). | Se esses arquivos forem tocados por outro motivo, trocar por "fold" e declarar em `EDITADOS_DEPOIS`. | baixa |
| 16 | `.github/workflows/ci.yml` (`astral-sh/setup-uv@v6` sem `version`) | CI usa uv 0.13.10, devcontainer 0.13.7. | Fixar `version: "0.13.7"` (ver item 11). | info |
| 17 | `README.md:103`, `README.pt-BR.md:103`; `docs/REPRODUCIBILITY.md:30` | Tempos datados sem artefato (3m52s; 10,5 s). Hoje: 7m18s local sob carga, 3m46s no CI; smoke 8,98 s. | Aceitável como medição datada; opcional citar o tempo do job do CI em vez do da máquina. | info |

## O que não foi possível verificar

- **Docker local**: `docker build`/`compose up` não foram executados nesta máquina; a consistência vem da leitura dos arquivos e do log do job `docker` do CI `45868887453` (verde).
- **App público e Space**: o app no Streamlit Community Cloud não foi aberto (o conteúdo conferido é o do código em `b90f3e2`, renderizado localmente com `AppTest`; se o deploy público estiver em outro commit, pode diferir). O Space do Hugging Face não existe ainda (o README diz "not yet deployed"), então nada a conferir.
- **Release v0.1.1 e Zenodo**: estão sendo criados em paralelo; o estado final da release e do DOI não foi visto.
- **Interatividade da página**: `site/static/js/results_explorer.js` lê `data/a_modelos_por_h.json`; os números do JSON foram conferidos indiretamente (mesmas origens e sha256 do `build_provenance.json`), mas a renderização no navegador não foi testada.
- **Figuras (PNG)**: conferi a legenda, o `.prov.json` e o sha256 das origens; não conferi pixel a pixel que a curva desenhada corresponde ao CSV (o `build_site.py --check` regenera e compara tudo menos os bytes dos PNG).
- **J34/J35, PROTOCOLO §0.23 e figuras da D13**: conferidos só por leitura no repositório da dissertação (somente leitura); nenhum número de lá foi trazido para cá.

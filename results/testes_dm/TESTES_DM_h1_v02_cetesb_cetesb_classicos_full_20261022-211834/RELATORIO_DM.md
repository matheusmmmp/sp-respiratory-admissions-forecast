# Validação e teste pareado de perdas — run `h1_v02_cetesb_cetesb_classicos_full_20261022-211834`

Gerado por `src/experiments/teste_dm_v02.py`. h = 1; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 7.1e-15, RMSE 1.4e-14, R2 2.2e-16, MASE 2.2e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 2.7e-15, RMSE_medio 7.1e-15, R2_medio 1.7e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,366 | -0,85 | 0,394 | 1,000 | 3− | não (1/4) |
| xgboost − lstm | -0,455 | -1,29 | 0,199 | 0,795 | nenhum | não (0/4) |
| xgboost − ingarch_nb | -0,989 | -2,43 | 0,015 | 0,107 | 3− | não (0/4) |
| xgboost − gam_nb | -3,349 | -7,44 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − naive | -10,154 | -14,59 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -10,314 | -10,54 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | -0,089 | -0,20 | 0,839 | 1,000 | 3+ | não (2/4) |
| sarimax − ingarch_nb | -0,623 | -1,64 | 0,101 | 0,605 | nenhum | sim (4/4) |
| sarimax − gam_nb | -2,982 | -6,26 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − naive | -9,788 | -11,68 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -9,948 | -10,71 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -0,535 | -1,54 | 0,124 | 0,620 | 3− | não (1/4) |
| lstm − gam_nb | -2,894 | -6,16 | 0,000 | 0,000 | 1−, 3−, 4− | sim (4/4) |
| lstm − naive | -9,700 | -14,14 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -9,860 | -10,42 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -2,359 | -5,10 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − naive | -9,165 | -13,80 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -9,325 | -10,69 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -6,806 | -10,66 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -6,966 | -8,27 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| naive − seasonal_naive | -0,160 | -0,14 | 0,888 | 1,000 | nenhum | não (2/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,099 | 0,62 | 0,533 | 1,000 | nenhum | não (2/4) |
| H2_media_com_meteo | -0,021 | -0,31 | 0,753 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | 0,181 | 0,82 | 0,414 | 1,000 | nenhum | não (0/4) |
| PM25_rico_com_meteo | 0,075 | 0,79 | 0,428 | 1,000 | nenhum | não (0/4) |
| rico_vs_media_com_meteo | 0,096 | 1,10 | 0,271 | 1,000 | nenhum | não (0/4) |
| POLUENTES_sem_meteo | 0,428 | 2,01 | 0,044 | 0,399 | 4+ | não (0/4) |
| POLUENTES_com_meteo | 0,126 | 1,32 | 0,187 | 1,000 | nenhum | não (0/4) |
| METEO | 0,544 | 2,08 | 0,038 | 0,382 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo | 0,125 | 1,04 | 0,298 | 1,000 | 1−, 3+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | -0,000 | -0,00 | 0,998 | 1,000 | 1− | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,179 | -1,76 | 0,080 | 0,795 | 3− | não (1/4) |
| H2_media_com_meteo | -0,030 | -0,71 | 0,476 | 1,000 | nenhum | sim (4/4) |
| PM25_rico_sem_meteo | -0,077 | -0,64 | 0,524 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,049 | 0,60 | 0,551 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,080 | 1,18 | 0,238 | 1,000 | 2+ | não (1/4) |
| POLUENTES_sem_meteo | -0,201 | -1,50 | 0,134 | 1,000 | 3− | não (2/4) |
| POLUENTES_com_meteo | -0,007 | -0,08 | 0,937 | 1,000 | 2+ | sim (3/4) |
| METEO | -0,090 | -0,59 | 0,553 | 1,000 | 1+, 3− | não (1/4) |
| COMPLETO_vs_meteo | 0,071 | 0,60 | 0,549 | 1,000 | 2+ | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,078 | 1,00 | 0,316 | 1,000 | 2+ | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,029 | 0,13 | 0,898 | 1,000 | 4+ | não (1/4) |
| H2_media_com_meteo | -0,057 | -0,25 | 0,806 | 1,000 | 1−, 4+ | não (0/4) |
| PM25_rico_sem_meteo | 3,172 | 6,46 | 0,000 | 0,000 | 1+, 2+, 3+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 2,383 | 4,35 | 0,000 | 0,000 | 1−, 3+, 4+ | não (0/4) |
| rico_vs_media_com_meteo | 2,440 | 4,82 | 0,000 | 0,000 | 1+, 3+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | 0,637 | 2,11 | 0,035 | 0,142 | nenhum | não (1/4) |
| POLUENTES_com_meteo | -0,123 | -0,47 | 0,636 | 1,000 | 1− | não (0/4) |
| METEO | 1,456 | 4,35 | 0,000 | 0,000 | 1+ | sim (3/4) |
| COMPLETO_vs_meteo | 2,076 | 4,07 | 0,000 | 0,000 | 1−, 2+, 3+, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 2,199 | 5,10 | 0,000 | 0,000 | 2+, 3+, 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,217 | -1,63 | 0,103 | 0,515 | 3− | sim (3/4) |
| H2_media_com_meteo | 0,113 | 1,86 | 0,063 | 0,377 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | 0,019 | 0,10 | 0,920 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,363 | 2,74 | 0,006 | 0,057 | 4+ | sim (4/4) |
| rico_vs_media_com_meteo | 0,249 | 2,14 | 0,033 | 0,228 | 2+, 4+ | não (1/4) |
| POLUENTES_sem_meteo | -0,296 | -1,38 | 0,169 | 0,678 | 3− | sim (3/4) |
| POLUENTES_com_meteo | 0,213 | 0,88 | 0,380 | 1,000 | nenhum | não (2/4) |
| METEO | 0,106 | 0,49 | 0,622 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 0,709 | 2,51 | 0,012 | 0,098 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo_poluentes | 0,496 | 2,97 | 0,003 | 0,031 | 4+ | sim (3/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,227 | -1,98 | 0,048 | 0,484 | 3− | não (1/4) |
| H2_media_com_meteo | 0,022 | 0,26 | 0,795 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 0,100 | 0,53 | 0,596 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,201 | 1,35 | 0,176 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,179 | 1,39 | 0,165 | 1,000 | nenhum | não (1/4) |
| POLUENTES_sem_meteo | -0,329 | -1,92 | 0,055 | 0,499 | 3− | sim (4/4) |
| POLUENTES_com_meteo | -0,199 | -1,45 | 0,147 | 1,000 | 3− | não (1/4) |
| METEO | 0,090 | 0,56 | 0,573 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 0,092 | 0,46 | 0,647 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,291 | 1,55 | 0,122 | 0,979 | nenhum | sim (4/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

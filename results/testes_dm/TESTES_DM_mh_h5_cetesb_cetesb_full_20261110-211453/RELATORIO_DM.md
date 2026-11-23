# Validação e teste pareado de perdas — run `mh_h5_cetesb_cetesb_full_20261110-211453`

Gerado por `src/experiments/teste_dm_v02.py`. h = 5; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 1.1e-14, RMSE 7.1e-15, R2 4.0e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 4.0e-15, RMSE_medio 7.1e-15, R2_medio 1.4e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,537 | -0,91 | 0,364 | 1,000 | nenhum | não (1/4) |
| xgboost − lstm | -0,060 | -0,12 | 0,906 | 1,000 | 2− | não (2/4) |
| xgboost − ingarch_nb | -1,087 | -1,88 | 0,061 | 0,365 | 2− | não (1/4) |
| xgboost − gam_nb | -2,849 | -4,49 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − naive | -11,625 | -14,24 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -6,368 | -9,58 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | 0,477 | 0,75 | 0,452 | 1,000 | nenhum | não (1/4) |
| sarimax − ingarch_nb | -0,550 | -1,60 | 0,110 | 0,457 | nenhum | sim (4/4) |
| sarimax − gam_nb | -2,312 | -4,59 | 0,000 | 0,000 | 1−, 2−, 3− | sim (4/4) |
| sarimax − naive | -11,087 | -14,45 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -5,830 | -9,47 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -1,027 | -1,69 | 0,091 | 0,457 | 4− | não (1/4) |
| lstm − gam_nb | -2,789 | -4,13 | 0,000 | 0,000 | 3−, 4− | sim (4/4) |
| lstm − naive | -11,565 | -12,33 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -6,308 | -8,14 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -1,762 | -3,36 | 0,001 | 0,006 | 1− | sim (4/4) |
| ingarch_nb − naive | -10,537 | -12,67 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -5,280 | -8,75 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -8,776 | -12,49 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -3,519 | -4,74 | 0,000 | 0,000 | 1−, 4− | sim (4/4) |
| naive − seasonal_naive | 5,257 | 5,55 | 0,000 | 0,000 | 1+, 2+, 3+ | sim (4/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,057 | 0,38 | 0,703 | 1,000 | nenhum | não (0/4) |
| H2_media_com_meteo | -0,022 | -0,27 | 0,786 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | 0,208 | 0,95 | 0,342 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,065 | 0,55 | 0,582 | 1,000 | nenhum | não (0/4) |
| rico_vs_media_com_meteo | 0,086 | 0,88 | 0,382 | 1,000 | nenhum | não (0/4) |
| POLUENTES_sem_meteo | 0,225 | 1,17 | 0,243 | 1,000 | nenhum | não (0/4) |
| POLUENTES_com_meteo | 0,092 | 0,80 | 0,427 | 1,000 | nenhum | não (1/4) |
| METEO | 0,393 | 1,41 | 0,159 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 0,349 | 2,76 | 0,006 | 0,056 | 3+ | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,257 | 2,78 | 0,006 | 0,056 | nenhum | não (1/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,031 | -0,73 | 0,466 | 1,000 | nenhum | não (2/4) |
| H2_media_com_meteo | -0,034 | -0,48 | 0,632 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | 0,001 | 0,01 | 0,992 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_com_meteo | 0,060 | 0,55 | 0,584 | 1,000 | nenhum | sim (3/4) |
| rico_vs_media_com_meteo | 0,094 | 1,24 | 0,215 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | -0,003 | -0,03 | 0,978 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_com_meteo | 0,061 | 0,50 | 0,616 | 1,000 | nenhum | sim (3/4) |
| METEO | -0,056 | -0,36 | 0,718 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,073 | 0,43 | 0,665 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,011 | 0,11 | 0,913 | 1,000 | nenhum | não (2/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,037 | 0,13 | 0,897 | 1,000 | 1− | não (0/4) |
| H2_media_com_meteo | -0,343 | -1,42 | 0,156 | 0,467 | 1−, 3+ | não (0/4) |
| PM25_rico_sem_meteo | 4,388 | 5,22 | 0,000 | 0,000 | 1+, 2+, 3+, 4+ | sim (3/4) |
| PM25_rico_com_meteo | 2,042 | 4,20 | 0,000 | 0,000 | 3+, 4+ | não (0/4) |
| rico_vs_media_com_meteo | 2,386 | 4,80 | 0,000 | 0,000 | 1+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | -0,032 | -0,07 | 0,942 | 1,000 | nenhum | não (0/4) |
| POLUENTES_com_meteo | 0,603 | 1,65 | 0,099 | 0,398 | 3+ | não (0/4) |
| METEO | 1,691 | 2,96 | 0,003 | 0,019 | 1+, 4+ | não (1/4) |
| COMPLETO_vs_meteo | 1,875 | 3,82 | 0,000 | 0,001 | 3+, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,272 | 2,21 | 0,028 | 0,139 | 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,130 | 0,42 | 0,674 | 1,000 | nenhum | não (2/4) |
| H2_media_com_meteo | 0,162 | 1,35 | 0,176 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 0,563 | 1,21 | 0,225 | 1,000 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,750 | 1,87 | 0,062 | 0,624 | 1+, 4+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,588 | 1,60 | 0,111 | 0,998 | 1+ | sim (3/4) |
| POLUENTES_sem_meteo | -0,190 | -0,52 | 0,603 | 1,000 | nenhum | não (2/4) |
| POLUENTES_com_meteo | -0,008 | -0,02 | 0,984 | 1,000 | nenhum | sim (3/4) |
| METEO | 0,260 | 0,65 | 0,514 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,600 | 0,97 | 0,334 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,608 | 1,18 | 0,238 | 1,000 | 4+ | sim (3/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,088 | 0,42 | 0,677 | 1,000 | 3− | não (2/4) |
| H2_media_com_meteo | 0,185 | 1,41 | 0,160 | 1,000 | nenhum | não (1/4) |
| PM25_rico_sem_meteo | 0,219 | 0,59 | 0,552 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_com_meteo | 0,293 | 0,88 | 0,380 | 1,000 | nenhum | sim (4/4) |
| rico_vs_media_com_meteo | 0,108 | 0,35 | 0,728 | 1,000 | nenhum | sim (4/4) |
| POLUENTES_sem_meteo | -0,481 | -1,77 | 0,078 | 0,776 | 3− | não (1/4) |
| POLUENTES_com_meteo | -0,144 | -0,50 | 0,618 | 1,000 | nenhum | não (1/4) |
| METEO | -0,095 | -0,32 | 0,751 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,156 | 0,30 | 0,762 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,300 | 0,68 | 0,499 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

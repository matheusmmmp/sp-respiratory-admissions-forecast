# Validação e teste pareado de perdas — run `mh_h30_cetesb_cetesb_full_20261113-104814`

Gerado por `src/experiments/teste_dm_v02.py`. h = 30; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 1.1e-14, RMSE 7.1e-15, R2 2.2e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 4.9e-15, RMSE_medio 7.1e-15, R2_medio 1.7e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | 1,047 | 0,57 | 0,571 | 1,000 | 1+ | não (1/4) |
| xgboost − lstm | -0,395 | -0,53 | 0,593 | 1,000 | 2− | não (1/4) |
| xgboost − ingarch_nb | 0,893 | 0,50 | 0,617 | 1,000 | nenhum | não (2/4) |
| xgboost − gam_nb | -1,160 | -0,76 | 0,449 | 1,000 | 4− | não (1/4) |
| xgboost − naive | -11,479 | -5,49 | 0,000 | 0,000 | 2−, 3−, 4− | sim (3/4) |
| xgboost − seasonal_naive | -8,490 | -3,08 | 0,002 | 0,026 | 2−, 4− | não (0/4) |
| sarimax − lstm | -1,441 | -0,86 | 0,391 | 1,000 | 4+ | não (2/4) |
| sarimax − ingarch_nb | -0,154 | -0,18 | 0,857 | 1,000 | nenhum | não (2/4) |
| sarimax − gam_nb | -2,207 | -1,86 | 0,063 | 0,566 | 1− | sim (3/4) |
| sarimax − naive | -12,526 | -11,33 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -9,537 | -5,48 | 0,000 | 0,000 | 1−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | 1,288 | 0,71 | 0,480 | 1,000 | nenhum | não (2/4) |
| lstm − gam_nb | -0,765 | -0,46 | 0,649 | 1,000 | nenhum | não (1/4) |
| lstm − naive | -11,084 | -5,86 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -8,095 | -3,14 | 0,002 | 0,023 | 4− | sim (4/4) |
| ingarch_nb − gam_nb | -2,053 | -2,73 | 0,006 | 0,071 | 1−, 3−, 4− | sim (3/4) |
| ingarch_nb − naive | -12,372 | -9,28 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -9,383 | -4,76 | 0,000 | 0,000 | 3−, 4− | sim (4/4) |
| gam_nb − naive | -10,319 | -7,17 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -7,330 | -3,39 | 0,001 | 0,010 | 3− | sim (4/4) |
| naive − seasonal_naive | 2,989 | 2,10 | 0,036 | 0,362 | 2+ | sim (4/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,503 | 2,65 | 0,008 | 0,081 | 1+, 4+ | não (2/4) |
| H2_media_com_meteo | -0,022 | -0,27 | 0,787 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | 0,853 | 1,65 | 0,100 | 0,903 | 4+ | não (0/4) |
| PM25_rico_com_meteo | 0,555 | 1,26 | 0,209 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | 0,577 | 1,30 | 0,196 | 1,000 | 4+ | não (2/4) |
| POLUENTES_sem_meteo | 0,144 | 0,47 | 0,642 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | -0,103 | -0,49 | 0,626 | 1,000 | nenhum | não (0/4) |
| METEO | 0,444 | 1,36 | 0,174 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,223 | 0,65 | 0,515 | 1,000 | 4+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 0,327 | 0,78 | 0,434 | 1,000 | 4+ | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,015 | 0,26 | 0,793 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,078 | 0,69 | 0,488 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 0,049 | 0,38 | 0,707 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_com_meteo | 0,064 | 0,32 | 0,750 | 1,000 | 1+, 3− | sim (3/4) |
| rico_vs_media_com_meteo | -0,014 | -0,08 | 0,933 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | 0,179 | 1,25 | 0,210 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_com_meteo | 0,370 | 2,36 | 0,019 | 0,187 | nenhum | sim (4/4) |
| METEO | -0,110 | -0,80 | 0,425 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 0,320 | 1,29 | 0,199 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,049 | -0,30 | 0,763 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,019 | 0,05 | 0,960 | 1,000 | 3− | não (0/4) |
| H2_media_com_meteo | -0,577 | -0,87 | 0,385 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 3,931 | 4,08 | 0,000 | 0,001 | 1+, 4+ | sim (3/4) |
| PM25_rico_com_meteo | 2,053 | 2,03 | 0,043 | 0,346 | 3+ | não (0/4) |
| rico_vs_media_com_meteo | 2,630 | 3,14 | 0,002 | 0,016 | 4+ | sim (3/4) |
| POLUENTES_sem_meteo | 0,029 | 0,03 | 0,977 | 1,000 | 4+ | não (0/4) |
| POLUENTES_com_meteo | 0,288 | 0,39 | 0,697 | 1,000 | 1− | não (0/4) |
| METEO | 1,050 | 1,35 | 0,178 | 1,000 | 4+ | não (1/4) |
| COMPLETO_vs_meteo | 1,140 | 1,12 | 0,261 | 1,000 | 1−, 3+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 0,853 | 1,27 | 0,206 | 1,000 | 1−, 3+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,502 | 2,09 | 0,037 | 0,245 | 4+ | não (1/4) |
| H2_media_com_meteo | 0,007 | 0,02 | 0,984 | 0,984 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | 4,386 | 3,76 | 0,000 | 0,002 | 2+, 3+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 3,123 | 2,96 | 0,003 | 0,029 | 2+, 3+ | não (1/4) |
| rico_vs_media_com_meteo | 3,117 | 2,73 | 0,006 | 0,051 | 2+, 3+ | não (1/4) |
| POLUENTES_sem_meteo | 1,208 | 1,40 | 0,163 | 0,552 | 4+ | não (1/4) |
| POLUENTES_com_meteo | 1,283 | 1,55 | 0,123 | 0,552 | 4+ | não (2/4) |
| METEO | 0,955 | 1,35 | 0,178 | 0,552 | 2+ | sim (3/4) |
| COMPLETO_vs_meteo | 4,565 | 2,11 | 0,035 | 0,245 | 3+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 3,282 | 1,60 | 0,110 | 0,552 | 3+ | não (2/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,134 | -0,68 | 0,497 | 1,000 | nenhum | sim (4/4) |
| H2_media_com_meteo | 0,457 | 2,89 | 0,004 | 0,040 | 3+ | sim (4/4) |
| PM25_rico_sem_meteo | -0,363 | -0,44 | 0,659 | 1,000 | 2+, 3− | não (2/4) |
| PM25_rico_com_meteo | -0,052 | -0,08 | 0,940 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | -0,510 | -0,73 | 0,466 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | -1,294 | -1,97 | 0,049 | 0,396 | 1− | sim (3/4) |
| POLUENTES_com_meteo | -1,232 | -1,54 | 0,123 | 0,744 | 1−, 3− | não (2/4) |
| METEO | 0,695 | 2,02 | 0,044 | 0,396 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | -1,700 | -1,62 | 0,106 | 0,744 | 1−, 3− | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,469 | -0,49 | 0,627 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

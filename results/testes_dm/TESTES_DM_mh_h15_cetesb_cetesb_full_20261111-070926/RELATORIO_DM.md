# Validação e teste pareado de perdas — run `mh_h15_cetesb_cetesb_full_20261111-070926`

Gerado por `src/experiments/teste_dm_v02.py`. h = 15; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 1.4e-14, RMSE 7.1e-15, R2 4.4e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 3.6e-15, MAE_std_fold 5.8e-15, RMSE_medio 7.1e-15, R2_medio 2.2e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -1,502 | -1,56 | 0,118 | 0,546 | 2− | não (1/4) |
| xgboost − lstm | -0,980 | -1,69 | 0,091 | 0,546 | 2− | não (0/4) |
| xgboost − ingarch_nb | -2,051 | -2,27 | 0,023 | 0,207 | 2−, 4− | não (1/4) |
| xgboost − gam_nb | -2,899 | -3,05 | 0,002 | 0,026 | 2−, 4− | não (1/4) |
| xgboost − naive | -12,714 | -12,58 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -8,916 | -5,32 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | 0,522 | 0,64 | 0,524 | 0,546 | 1− | não (1/4) |
| sarimax − ingarch_nb | -0,549 | -1,17 | 0,241 | 0,546 | nenhum | sim (4/4) |
| sarimax − gam_nb | -1,397 | -2,03 | 0,043 | 0,300 | 1−, 3− | sim (3/4) |
| sarimax − naive | -11,212 | -13,68 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -7,414 | -5,66 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -1,071 | -1,34 | 0,180 | 0,546 | 1+, 4− | não (1/4) |
| lstm − gam_nb | -1,919 | -2,28 | 0,023 | 0,207 | 4− | não (0/4) |
| lstm − naive | -11,734 | -13,24 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -7,936 | -5,02 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -0,848 | -1,61 | 0,108 | 0,546 | 3− | sim (3/4) |
| ingarch_nb − naive | -10,663 | -13,33 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -6,865 | -4,98 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -9,816 | -11,32 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -6,017 | -4,44 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| naive − seasonal_naive | 3,799 | 2,80 | 0,005 | 0,052 | 1+, 2+ | sim (4/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,219 | 1,11 | 0,266 | 1,000 | nenhum | não (1/4) |
| H2_media_com_meteo | -0,062 | -0,63 | 0,530 | 1,000 | 1− | não (0/4) |
| PM25_rico_sem_meteo | 0,151 | 0,32 | 0,746 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | -0,039 | -0,15 | 0,878 | 1,000 | 1−, 4+ | não (2/4) |
| rico_vs_media_com_meteo | 0,023 | 0,10 | 0,923 | 1,000 | nenhum | não (1/4) |
| POLUENTES_sem_meteo | -0,572 | -1,53 | 0,128 | 0,893 | 1− | não (2/4) |
| POLUENTES_com_meteo | -0,470 | -2,15 | 0,032 | 0,285 | 1− | não (2/4) |
| METEO | 0,919 | 2,91 | 0,004 | 0,037 | 1+ | sim (3/4) |
| COMPLETO_vs_meteo | -0,615 | -2,09 | 0,037 | 0,293 | 1− | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,145 | -0,62 | 0,532 | 1,000 | nenhum | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,050 | 0,60 | 0,546 | 1,000 | nenhum | não (2/4) |
| H2_media_com_meteo | 0,017 | 0,38 | 0,702 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 0,196 | 0,94 | 0,348 | 1,000 | 1− | não (2/4) |
| PM25_rico_com_meteo | 0,120 | 0,64 | 0,520 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,104 | 0,57 | 0,568 | 1,000 | 1− | não (2/4) |
| POLUENTES_sem_meteo | 0,069 | 0,65 | 0,518 | 1,000 | nenhum | não (2/4) |
| POLUENTES_com_meteo | 0,016 | 0,17 | 0,862 | 1,000 | nenhum | sim (3/4) |
| METEO | 0,219 | 1,75 | 0,080 | 0,800 | 2+ | sim (3/4) |
| COMPLETO_vs_meteo | 0,190 | 1,00 | 0,320 | 1,000 | nenhum | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 0,174 | 1,09 | 0,276 | 1,000 | nenhum | não (1/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,294 | -1,04 | 0,297 | 0,595 | 1− | não (0/4) |
| H2_media_com_meteo | -0,740 | -1,85 | 0,064 | 0,322 | 1− | não (1/4) |
| PM25_rico_sem_meteo | 4,791 | 4,54 | 0,000 | 0,000 | 1+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 2,139 | 2,56 | 0,011 | 0,063 | 2+, 4+ | não (2/4) |
| rico_vs_media_com_meteo | 2,879 | 3,67 | 0,000 | 0,002 | 1+, 2+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | 1,379 | 2,90 | 0,004 | 0,027 | 2+, 3+, 4+ | não (0/4) |
| POLUENTES_com_meteo | -0,016 | -0,03 | 0,978 | 0,978 | 1− | não (0/4) |
| METEO | 1,787 | 3,71 | 0,000 | 0,002 | 1+, 4+ | não (2/4) |
| COMPLETO_vs_meteo | 1,482 | 1,85 | 0,065 | 0,322 | 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,498 | 1,79 | 0,074 | 0,322 | 4+ | não (2/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,114 | 0,73 | 0,468 | 0,954 | nenhum | sim (4/4) |
| H2_media_com_meteo | 0,129 | 1,25 | 0,213 | 0,954 | 1+ | sim (3/4) |
| PM25_rico_sem_meteo | 1,428 | 2,28 | 0,023 | 0,162 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,985 | 2,75 | 0,006 | 0,060 | 1+ | sim (4/4) |
| rico_vs_media_com_meteo | 0,856 | 2,46 | 0,014 | 0,129 | 1+ | sim (4/4) |
| POLUENTES_sem_meteo | 1,187 | 1,34 | 0,181 | 0,954 | 2+ | sim (3/4) |
| POLUENTES_com_meteo | 1,608 | 1,30 | 0,193 | 0,954 | 2+ | sim (3/4) |
| METEO | 1,620 | 2,39 | 0,017 | 0,135 | 4+ | sim (3/4) |
| COMPLETO_vs_meteo | 1,744 | 1,41 | 0,159 | 0,954 | 2+ | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,136 | 0,17 | 0,868 | 0,954 | 2− | não (2/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,257 | 0,93 | 0,353 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,116 | 0,96 | 0,339 | 1,000 | nenhum | não (1/4) |
| PM25_rico_sem_meteo | 0,305 | 0,42 | 0,677 | 1,000 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,227 | 0,39 | 0,694 | 1,000 | 1+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,111 | 0,19 | 0,847 | 1,000 | 1+ | sim (3/4) |
| POLUENTES_sem_meteo | -0,518 | -1,14 | 0,257 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_com_meteo | -0,823 | -1,67 | 0,095 | 0,858 | nenhum | sim (4/4) |
| METEO | 0,649 | 2,12 | 0,034 | 0,341 | 1+ | sim (3/4) |
| COMPLETO_vs_meteo | -0,961 | -1,09 | 0,278 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | -0,138 | -0,17 | 0,864 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

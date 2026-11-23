# Validação e teste pareado de perdas — run `ur_h15_cetesb_cetesb_full_20261117-190532`

Gerado por `src/experiments/teste_dm_v02.py`. h = 15; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 7.1e-15, RMSE 7.1e-15, R2 4.4e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 2.3e-15, RMSE_medio 7.1e-15, R2_medio 1.7e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,182 | -0,19 | 0,850 | 1,000 | nenhum | não (1/4) |
| xgboost − lstm | -0,698 | -1,16 | 0,247 | 1,000 | nenhum | não (0/4) |
| xgboost − ingarch_nb | -0,528 | -0,65 | 0,513 | 1,000 | nenhum | não (1/4) |
| xgboost − gam_nb | -1,469 | -1,61 | 0,107 | 1,000 | nenhum | não (1/4) |
| xgboost − naive | -7,399 | -7,22 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -6,057 | -3,95 | 0,000 | 0,001 | 2−, 3−, 4− | não (0/4) |
| sarimax − lstm | -0,515 | -0,67 | 0,500 | 1,000 | 3− | não (1/4) |
| sarimax − ingarch_nb | -0,346 | -0,58 | 0,561 | 1,000 | nenhum | sim (3/4) |
| sarimax − gam_nb | -1,286 | -2,02 | 0,044 | 0,483 | 3− | sim (3/4) |
| sarimax − naive | -7,217 | -9,25 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -5,875 | -5,21 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | 0,170 | 0,23 | 0,816 | 1,000 | 3+ | não (0/4) |
| lstm − gam_nb | -0,771 | -1,03 | 0,301 | 1,000 | nenhum | não (2/4) |
| lstm − naive | -6,701 | -6,79 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -5,360 | -3,91 | 0,000 | 0,001 | 2−, 4− | sim (3/4) |
| ingarch_nb − gam_nb | -0,941 | -1,56 | 0,118 | 1,000 | 3− | sim (3/4) |
| ingarch_nb − naive | -6,871 | -8,32 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -5,529 | -4,41 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -5,930 | -7,58 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -4,589 | -3,70 | 0,000 | 0,003 | 2−, 3−, 4− | sim (4/4) |
| naive − seasonal_naive | 1,342 | 1,26 | 0,207 | 1,000 | 1+ | sim (3/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,135 | -0,66 | 0,511 | 1,000 | nenhum | não (0/4) |
| H2_media_com_meteo | -0,106 | -1,19 | 0,236 | 1,000 | 1− | não (0/4) |
| PM25_rico_sem_meteo | 0,171 | 0,39 | 0,693 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | -0,018 | -0,07 | 0,941 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | 0,088 | 0,37 | 0,712 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | -0,820 | -2,51 | 0,012 | 0,112 | 1− | sim (3/4) |
| POLUENTES_com_meteo | -0,836 | -3,93 | 0,000 | 0,001 | 1−, 3− | sim (4/4) |
| METEO | 0,484 | 1,58 | 0,114 | 0,798 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | -0,662 | -2,50 | 0,013 | 0,112 | 1−, 3− | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,174 | 0,90 | 0,367 | 1,000 | nenhum | não (1/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,006 | -0,08 | 0,935 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,071 | 1,02 | 0,310 | 1,000 | nenhum | sim (4/4) |
| PM25_rico_sem_meteo | 0,153 | 0,77 | 0,441 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,212 | 1,08 | 0,282 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,142 | 0,86 | 0,390 | 1,000 | nenhum | não (1/4) |
| POLUENTES_sem_meteo | 0,052 | 0,50 | 0,614 | 1,000 | nenhum | não (2/4) |
| POLUENTES_com_meteo | -0,033 | -0,40 | 0,687 | 1,000 | nenhum | sim (3/4) |
| METEO | 0,180 | 1,54 | 0,125 | 0,998 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo | 0,347 | 1,63 | 0,103 | 0,927 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo_poluentes | 0,380 | 2,00 | 0,046 | 0,457 | 2+ | sim (4/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,751 | -2,03 | 0,043 | 0,222 | 3− | não (0/4) |
| H2_media_com_meteo | -0,620 | -1,80 | 0,072 | 0,286 | 1− | não (1/4) |
| PM25_rico_sem_meteo | 4,079 | 5,44 | 0,000 | 0,000 | 1+, 3+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 2,859 | 4,90 | 0,000 | 0,000 | 2+, 3+, 4+ | não (1/4) |
| rico_vs_media_com_meteo | 3,479 | 5,70 | 0,000 | 0,000 | 1+, 2+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | -0,417 | -0,90 | 0,369 | 0,773 | 3− | não (0/4) |
| POLUENTES_com_meteo | -0,150 | -0,24 | 0,810 | 0,810 | 1− | não (0/4) |
| METEO | 0,598 | 1,13 | 0,258 | 0,773 | 1+, 3−, 4+ | não (1/4) |
| COMPLETO_vs_meteo | 1,337 | 2,09 | 0,037 | 0,222 | 1−, 2+, 4+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 1,486 | 2,60 | 0,010 | 0,067 | 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,106 | 1,03 | 0,305 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,140 | 1,90 | 0,058 | 0,348 | 2+ | sim (4/4) |
| PM25_rico_sem_meteo | 1,220 | 2,29 | 0,022 | 0,177 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,938 | 2,50 | 0,013 | 0,115 | 1+ | sim (4/4) |
| rico_vs_media_com_meteo | 0,797 | 2,25 | 0,025 | 0,177 | 1+ | sim (4/4) |
| POLUENTES_sem_meteo | 0,269 | 0,41 | 0,680 | 1,000 | nenhum | não (2/4) |
| POLUENTES_com_meteo | 1,407 | 1,07 | 0,283 | 1,000 | 2+ | sim (3/4) |
| METEO | 1,372 | 2,65 | 0,008 | 0,083 | 4+ | sim (4/4) |
| COMPLETO_vs_meteo | 1,506 | 1,24 | 0,214 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,099 | 0,12 | 0,905 | 1,000 | 2− | não (2/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,348 | 1,33 | 0,184 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,047 | 0,49 | 0,622 | 1,000 | nenhum | não (2/4) |
| PM25_rico_sem_meteo | 0,456 | 0,58 | 0,562 | 1,000 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,266 | 0,41 | 0,678 | 1,000 | 1+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,218 | 0,34 | 0,736 | 1,000 | 1+ | não (2/4) |
| POLUENTES_sem_meteo | -0,495 | -1,00 | 0,318 | 1,000 | 3− | sim (3/4) |
| POLUENTES_com_meteo | -0,959 | -1,91 | 0,057 | 0,513 | 3− | sim (4/4) |
| METEO | 0,834 | 2,77 | 0,006 | 0,058 | 1+ | sim (3/4) |
| COMPLETO_vs_meteo | -0,755 | -0,83 | 0,408 | 1,000 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo_poluentes | 0,204 | 0,24 | 0,807 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

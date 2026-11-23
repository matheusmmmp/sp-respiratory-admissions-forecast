# Validação e teste pareado de perdas — run `ur_h5_cetesb_cetesb_full_20261116-222823`

Gerado por `src/experiments/teste_dm_v02.py`. h = 5; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 7.1e-15, RMSE 7.1e-15, R2 3.3e-16, MASE 2.2e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 3.6e-15, MAE_std_fold 2.7e-15, RMSE_medio 3.6e-15, R2_medio 1.1e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,045 | -0,09 | 0,928 | 1,000 | nenhum | não (1/4) |
| xgboost − lstm | -0,376 | -0,88 | 0,380 | 1,000 | 2− | não (1/4) |
| xgboost − ingarch_nb | -0,792 | -1,73 | 0,085 | 0,424 | 2− | não (1/4) |
| xgboost − gam_nb | -2,326 | -3,70 | 0,000 | 0,002 | 2−, 3−, 4− | sim (4/4) |
| xgboost − naive | -8,746 | -11,35 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -3,746 | -6,39 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | -0,331 | -0,69 | 0,490 | 1,000 | nenhum | não (1/4) |
| sarimax − ingarch_nb | -0,747 | -2,67 | 0,008 | 0,054 | nenhum | sim (4/4) |
| sarimax − gam_nb | -2,281 | -4,85 | 0,000 | 0,000 | 1−, 2−, 3− | sim (4/4) |
| sarimax − naive | -8,701 | -11,69 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -3,701 | -8,09 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -0,416 | -0,95 | 0,343 | 1,000 | nenhum | não (1/4) |
| lstm − gam_nb | -1,950 | -3,12 | 0,002 | 0,017 | 3− | sim (4/4) |
| lstm − naive | -8,370 | -9,59 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -3,370 | -5,53 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -1,534 | -3,11 | 0,002 | 0,017 | 1−, 3− | sim (4/4) |
| ingarch_nb − naive | -7,954 | -10,85 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -2,954 | -6,40 | 0,000 | 0,000 | 1−, 2−, 4− | sim (4/4) |
| gam_nb − naive | -6,420 | -10,69 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -1,420 | -2,27 | 0,023 | 0,139 | 4− | sim (3/4) |
| naive − seasonal_naive | 5,000 | 5,80 | 0,000 | 0,000 | 1+, 2+, 3+, 4+ | sim (4/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,065 | 0,40 | 0,687 | 1,000 | nenhum | não (1/4) |
| H2_media_com_meteo | 0,209 | 2,56 | 0,011 | 0,106 | 2+ | não (1/4) |
| PM25_rico_sem_meteo | 0,164 | 0,76 | 0,448 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,113 | 1,05 | 0,293 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | -0,097 | -0,98 | 0,328 | 1,000 | nenhum | não (0/4) |
| POLUENTES_sem_meteo | 0,022 | 0,09 | 0,925 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | 0,149 | 1,51 | 0,132 | 1,000 | 3+ | não (0/4) |
| METEO | -0,032 | -0,11 | 0,912 | 1,000 | nenhum | não (1/4) |
| COMPLETO_vs_meteo | 0,028 | 0,24 | 0,813 | 1,000 | nenhum | não (0/4) |
| COMPLETO_vs_meteo_poluentes | -0,121 | -1,42 | 0,156 | 1,000 | 3− | não (1/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,031 | -0,58 | 0,559 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,036 | 0,64 | 0,525 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | -0,023 | -0,32 | 0,750 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,085 | 1,12 | 0,262 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,049 | 0,63 | 0,526 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | -0,056 | -0,58 | 0,563 | 1,000 | nenhum | não (2/4) |
| POLUENTES_com_meteo | 0,147 | 1,52 | 0,129 | 1,000 | nenhum | sim (3/4) |
| METEO | -0,105 | -0,70 | 0,484 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,099 | 0,84 | 0,403 | 1,000 | 2+ | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | -0,049 | -0,76 | 0,450 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,109 | -0,52 | 0,605 | 1,000 | nenhum | não (0/4) |
| H2_media_com_meteo | -0,658 | -3,27 | 0,001 | 0,007 | 1− | não (0/4) |
| PM25_rico_sem_meteo | 3,841 | 5,33 | 0,000 | 0,000 | 1+, 3+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 2,483 | 5,12 | 0,000 | 0,000 | 2+, 3+, 4+ | não (0/4) |
| rico_vs_media_com_meteo | 3,141 | 6,48 | 0,000 | 0,000 | 1+, 3+, 4+ | não (1/4) |
| POLUENTES_sem_meteo | 0,129 | 0,28 | 0,777 | 1,000 | nenhum | não (0/4) |
| POLUENTES_com_meteo | -0,046 | -0,15 | 0,884 | 1,000 | 1− | não (0/4) |
| METEO | 1,588 | 3,45 | 0,001 | 0,004 | 1+, 4+ | não (2/4) |
| COMPLETO_vs_meteo | 1,362 | 3,06 | 0,002 | 0,011 | 1−, 2+, 3+, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,408 | 3,08 | 0,002 | 0,011 | 1−, 2+, 3+, 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,049 | 0,19 | 0,847 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,157 | 1,04 | 0,300 | 1,000 | nenhum | não (1/4) |
| PM25_rico_sem_meteo | 0,242 | 0,54 | 0,588 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,473 | 1,12 | 0,264 | 1,000 | 1+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,316 | 0,83 | 0,407 | 1,000 | 1+ | sim (3/4) |
| POLUENTES_sem_meteo | -0,534 | -1,44 | 0,151 | 1,000 | 3− | sim (3/4) |
| POLUENTES_com_meteo | -0,276 | -0,65 | 0,518 | 1,000 | nenhum | não (2/4) |
| METEO | -0,005 | -0,01 | 0,988 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,094 | 0,15 | 0,881 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,370 | 0,78 | 0,438 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,058 | 0,31 | 0,758 | 1,000 | nenhum | não (2/4) |
| H2_media_com_meteo | 0,087 | 0,86 | 0,390 | 1,000 | nenhum | não (1/4) |
| PM25_rico_sem_meteo | 0,148 | 0,47 | 0,637 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_com_meteo | 0,055 | 0,21 | 0,833 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | -0,031 | -0,13 | 0,900 | 1,000 | nenhum | não (1/4) |
| POLUENTES_sem_meteo | -0,393 | -1,62 | 0,105 | 1,000 | 3− | sim (3/4) |
| POLUENTES_com_meteo | -0,031 | -0,12 | 0,908 | 1,000 | nenhum | sim (3/4) |
| METEO | 0,108 | 0,44 | 0,662 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | -0,009 | -0,02 | 0,984 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,022 | 0,06 | 0,950 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

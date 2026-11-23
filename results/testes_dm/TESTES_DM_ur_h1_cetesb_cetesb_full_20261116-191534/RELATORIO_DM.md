# Validação e teste pareado de perdas — run `ur_h1_cetesb_cetesb_full_20261116-191534`

Gerado por `src/experiments/teste_dm_v02.py`. h = 1; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 7.1e-15, RMSE 7.1e-15, R2 2.2e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 3.6e-15, MAE_std_fold 3.1e-15, RMSE_medio 3.6e-15, R2_medio 1.1e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | 0,615 | 2,14 | 0,032 | 0,195 | 1+ | sim (4/4) |
| xgboost − lstm | 0,119 | 0,49 | 0,623 | 1,000 | nenhum | não (1/4) |
| xgboost − ingarch_nb | -0,062 | -0,23 | 0,821 | 1,000 | nenhum | não (2/4) |
| xgboost − gam_nb | -1,773 | -4,79 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − naive | -4,936 | -10,91 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -6,482 | -7,95 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | -0,496 | -1,85 | 0,064 | 0,320 | 1− | não (2/4) |
| sarimax − ingarch_nb | -0,677 | -2,86 | 0,004 | 0,030 | 1− | sim (4/4) |
| sarimax − gam_nb | -2,389 | -6,35 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − naive | -5,552 | -11,93 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -7,098 | -8,87 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -0,181 | -0,66 | 0,507 | 1,000 | nenhum | não (1/4) |
| lstm − gam_nb | -1,893 | -5,19 | 0,000 | 0,000 | 1−, 3−, 4− | sim (4/4) |
| lstm − naive | -5,056 | -10,67 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -6,602 | -8,31 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -1,712 | -4,42 | 0,000 | 0,000 | 1−, 3−, 4− | sim (4/4) |
| ingarch_nb − naive | -4,875 | -11,87 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -6,421 | -8,25 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -3,163 | -7,35 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -4,709 | -6,27 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| naive − seasonal_naive | -1,546 | -1,72 | 0,086 | 0,342 | nenhum | sim (3/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,148 | -1,38 | 0,168 | 1,000 | nenhum | não (1/4) |
| H2_media_com_meteo | 0,039 | 0,79 | 0,429 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | -0,167 | -1,23 | 0,220 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | -0,026 | -0,34 | 0,734 | 1,000 | nenhum | não (0/4) |
| rico_vs_media_com_meteo | -0,065 | -0,90 | 0,368 | 1,000 | nenhum | não (0/4) |
| POLUENTES_sem_meteo | -0,220 | -1,44 | 0,150 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | 0,074 | 1,03 | 0,302 | 1,000 | nenhum | não (0/4) |
| METEO | -0,280 | -1,65 | 0,098 | 0,984 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,106 | 1,10 | 0,273 | 1,000 | 1+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 0,032 | 0,49 | 0,623 | 1,000 | 1+ | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,315 | -3,50 | 0,000 | 0,005 | 3− | sim (4/4) |
| H2_media_com_meteo | -0,078 | -1,66 | 0,098 | 0,489 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | -0,278 | -2,70 | 0,007 | 0,057 | 3− | sim (3/4) |
| PM25_rico_com_meteo | 0,052 | 0,78 | 0,434 | 0,983 | 3+ | não (1/4) |
| rico_vs_media_com_meteo | 0,130 | 2,53 | 0,012 | 0,069 | 3+ | não (1/4) |
| POLUENTES_sem_meteo | -0,353 | -3,17 | 0,002 | 0,014 | 3− | sim (3/4) |
| POLUENTES_com_meteo | 0,007 | 0,08 | 0,936 | 0,983 | 1− | não (1/4) |
| METEO | -0,330 | -2,64 | 0,008 | 0,059 | 3− | não (1/4) |
| COMPLETO_vs_meteo | 0,102 | 0,98 | 0,328 | 0,983 | 1−, 2+, 3+ | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,095 | 1,46 | 0,144 | 0,577 | 3+ | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,124 | -0,76 | 0,445 | 0,891 | 3− | não (2/4) |
| H2_media_com_meteo | -0,377 | -2,41 | 0,016 | 0,065 | 1− | não (0/4) |
| PM25_rico_sem_meteo | 2,230 | 5,93 | 0,000 | 0,000 | 1+, 3+, 4+ | sim (4/4) |
| PM25_rico_com_meteo | 2,178 | 5,07 | 0,000 | 0,000 | 3+, 4+ | não (2/4) |
| rico_vs_media_com_meteo | 2,555 | 6,79 | 0,000 | 0,000 | 1+, 3+, 4+ | sim (4/4) |
| POLUENTES_sem_meteo | 0,406 | 1,85 | 0,064 | 0,193 | nenhum | não (0/4) |
| POLUENTES_com_meteo | 0,084 | 0,42 | 0,673 | 0,891 | 1−, 4+ | não (0/4) |
| METEO | 0,850 | 3,44 | 0,001 | 0,003 | 1+ | não (1/4) |
| COMPLETO_vs_meteo | 2,069 | 4,44 | 0,000 | 0,000 | 1−, 2+, 3+, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,985 | 4,50 | 0,000 | 0,000 | 2+, 3+, 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,233 | -2,43 | 0,015 | 0,122 | 3− | sim (4/4) |
| H2_media_com_meteo | 0,199 | 2,74 | 0,006 | 0,062 | 4+ | sim (4/4) |
| PM25_rico_sem_meteo | -0,227 | -1,61 | 0,107 | 0,430 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,294 | 2,61 | 0,009 | 0,084 | 4+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,095 | 1,01 | 0,313 | 0,537 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | -0,391 | -2,01 | 0,045 | 0,317 | nenhum | sim (4/4) |
| POLUENTES_com_meteo | 0,228 | 1,11 | 0,268 | 0,537 | nenhum | sim (4/4) |
| METEO | -0,241 | -1,51 | 0,132 | 0,430 | 3− | não (1/4) |
| COMPLETO_vs_meteo | 0,437 | 1,82 | 0,070 | 0,368 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo_poluentes | 0,209 | 1,87 | 0,061 | 0,368 | 4+ | sim (3/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,155 | -1,42 | 0,157 | 1,000 | 3− | não (2/4) |
| H2_media_com_meteo | 0,058 | 0,88 | 0,378 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | 0,126 | 0,71 | 0,475 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,209 | 1,55 | 0,121 | 1,000 | nenhum | não (1/4) |
| rico_vs_media_com_meteo | 0,151 | 1,27 | 0,204 | 1,000 | 2+ | não (1/4) |
| POLUENTES_sem_meteo | -0,240 | -1,63 | 0,104 | 1,000 | 3− | sim (4/4) |
| POLUENTES_com_meteo | -0,039 | -0,36 | 0,722 | 1,000 | 3− | não (2/4) |
| METEO | -0,150 | -1,07 | 0,287 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,153 | 0,84 | 0,400 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,192 | 1,14 | 0,255 | 1,000 | nenhum | sim (3/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

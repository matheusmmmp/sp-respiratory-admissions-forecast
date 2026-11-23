# Validação e teste pareado de perdas — run `ur_h30_cetesb_cetesb_full_20261117-221426`

Gerado por `src/experiments/teste_dm_v02.py`. h = 30; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 1.1e-14, RMSE 7.1e-15, R2 4.6e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 3.6e-15, MAE_std_fold 3.1e-15, RMSE_medio 7.1e-15, R2_medio 1.5e-16, MASE_medio 1.1e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | 0,991 | 0,54 | 0,592 | 1,000 | nenhum | não (1/4) |
| xgboost − lstm | -0,246 | -0,27 | 0,786 | 1,000 | 2− | não (1/4) |
| xgboost − ingarch_nb | 0,734 | 0,45 | 0,652 | 1,000 | nenhum | não (1/4) |
| xgboost − gam_nb | -1,128 | -0,74 | 0,457 | 1,000 | nenhum | não (2/4) |
| xgboost − naive | -10,401 | -4,73 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -7,964 | -2,88 | 0,004 | 0,049 | 3−, 4− | sim (3/4) |
| sarimax − lstm | -1,237 | -0,81 | 0,417 | 1,000 | nenhum | não (2/4) |
| sarimax − ingarch_nb | -0,258 | -0,25 | 0,802 | 1,000 | nenhum | não (2/4) |
| sarimax − gam_nb | -2,119 | -1,80 | 0,073 | 0,656 | nenhum | sim (3/4) |
| sarimax − naive | -11,393 | -8,40 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -8,955 | -5,21 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | 0,979 | 0,60 | 0,550 | 1,000 | nenhum | não (2/4) |
| lstm − gam_nb | -0,882 | -0,58 | 0,561 | 1,000 | nenhum | não (2/4) |
| lstm − naive | -10,156 | -5,30 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -7,718 | -3,23 | 0,001 | 0,018 | 4− | sim (4/4) |
| ingarch_nb − gam_nb | -1,861 | -2,46 | 0,014 | 0,151 | 1−, 3−, 4− | sim (3/4) |
| ingarch_nb − naive | -11,135 | -7,21 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -8,698 | -4,21 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -9,274 | -5,86 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -6,836 | -3,17 | 0,002 | 0,021 | 2−, 3− | sim (4/4) |
| naive − seasonal_naive | 2,438 | 2,47 | 0,014 | 0,151 | 2+ | sim (4/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,236 | -1,69 | 0,092 | 0,645 | nenhum | não (0/4) |
| H2_media_com_meteo | -0,033 | -0,36 | 0,716 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | 0,348 | 0,72 | 0,470 | 1,000 | nenhum | não (0/4) |
| PM25_rico_com_meteo | 0,822 | 2,08 | 0,038 | 0,304 | nenhum | sim (4/4) |
| rico_vs_media_com_meteo | 0,855 | 2,13 | 0,034 | 0,302 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | -0,528 | -2,39 | 0,017 | 0,171 | 1− | não (2/4) |
| POLUENTES_com_meteo | 0,143 | 0,64 | 0,522 | 1,000 | nenhum | não (0/4) |
| METEO | -0,279 | -0,87 | 0,387 | 1,000 | nenhum | não (0/4) |
| COMPLETO_vs_meteo | 0,512 | 1,61 | 0,107 | 0,645 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,368 | 1,05 | 0,295 | 1,000 | nenhum | não (2/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,090 | 1,20 | 0,229 | 1,000 | nenhum | sim (4/4) |
| H2_media_com_meteo | 0,056 | 0,31 | 0,760 | 1,000 | 1+ | não (2/4) |
| PM25_rico_sem_meteo | 0,185 | 1,54 | 0,124 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_com_meteo | 0,097 | 0,40 | 0,691 | 1,000 | nenhum | sim (3/4) |
| rico_vs_media_com_meteo | 0,042 | 0,20 | 0,842 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | 0,291 | 1,48 | 0,140 | 1,000 | nenhum | sim (4/4) |
| POLUENTES_com_meteo | 0,035 | 0,14 | 0,887 | 1,000 | nenhum | sim (3/4) |
| METEO | 0,091 | 0,52 | 0,600 | 1,000 | nenhum | não (1/4) |
| COMPLETO_vs_meteo | 0,300 | 1,15 | 0,250 | 1,000 | 1+ | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,266 | 0,94 | 0,349 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,013 | -0,05 | 0,957 | 1,000 | nenhum | não (0/4) |
| H2_media_com_meteo | -0,549 | -1,02 | 0,308 | 1,000 | 1− | não (2/4) |
| PM25_rico_sem_meteo | 3,287 | 4,14 | 0,000 | 0,000 | 1+, 3+, 4+ | não (2/4) |
| PM25_rico_com_meteo | 2,180 | 2,55 | 0,011 | 0,087 | 3+ | não (0/4) |
| rico_vs_media_com_meteo | 2,729 | 3,66 | 0,000 | 0,002 | 1+ | não (1/4) |
| POLUENTES_sem_meteo | -0,304 | -0,42 | 0,673 | 1,000 | nenhum | não (0/4) |
| POLUENTES_com_meteo | -0,063 | -0,09 | 0,924 | 1,000 | 1−, 3+ | não (0/4) |
| METEO | 0,532 | 0,59 | 0,556 | 1,000 | 1+, 3− | não (1/4) |
| COMPLETO_vs_meteo | 1,394 | 1,48 | 0,140 | 0,838 | 1−, 3+ | não (1/4) |
| COMPLETO_vs_meteo_poluentes | 1,457 | 2,47 | 0,014 | 0,097 | 3+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,627 | 2,47 | 0,014 | 0,096 | 4+ | não (1/4) |
| H2_media_com_meteo | 0,163 | 0,58 | 0,565 | 1,000 | 1+ | sim (3/4) |
| PM25_rico_sem_meteo | 3,717 | 3,53 | 0,000 | 0,004 | 3+, 4+ | não (1/4) |
| PM25_rico_com_meteo | 2,724 | 2,94 | 0,003 | 0,030 | 3+ | não (1/4) |
| rico_vs_media_com_meteo | 2,561 | 2,62 | 0,009 | 0,073 | 3+ | não (1/4) |
| POLUENTES_sem_meteo | 1,396 | 1,26 | 0,207 | 0,947 | 4+ | sim (3/4) |
| POLUENTES_com_meteo | 1,549 | 1,31 | 0,189 | 0,947 | 4+ | não (2/4) |
| METEO | 0,215 | 0,38 | 0,702 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 3,948 | 1,83 | 0,068 | 0,408 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 2,400 | 1,07 | 0,284 | 0,947 | 3+ | não (2/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,094 | -0,43 | 0,666 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,397 | 2,91 | 0,004 | 0,037 | nenhum | sim (4/4) |
| PM25_rico_sem_meteo | -0,415 | -0,49 | 0,627 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | -0,174 | -0,22 | 0,827 | 1,000 | 2+ | não (2/4) |
| rico_vs_media_com_meteo | -0,571 | -0,71 | 0,481 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | -1,659 | -2,23 | 0,026 | 0,232 | 1− | sim (3/4) |
| POLUENTES_com_meteo | -1,499 | -1,76 | 0,079 | 0,629 | 1−, 3− | sim (3/4) |
| METEO | 0,504 | 1,31 | 0,191 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | -1,801 | -1,61 | 0,109 | 0,762 | 1− | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,302 | -0,30 | 0,767 | 1,000 | nenhum | não (2/4) |

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

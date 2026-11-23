# Validação e teste pareado de perdas — run `ur_h7_cetesb_cetesb_full_20261117-073926`

Gerado por `src/experiments/teste_dm_v02.py`. h = 7; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 7.1e-15, RMSE 7.1e-15, R2 3.3e-16, MASE 4.4e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 3.1e-15, RMSE_medio 7.1e-15, R2_medio 1.7e-16, MASE_medio 2.2e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,212 | -0,36 | 0,721 | 1,000 | nenhum | não (1/4) |
| xgboost − lstm | -0,265 | -0,56 | 0,575 | 1,000 | nenhum | não (0/4) |
| xgboost − ingarch_nb | -0,671 | -1,19 | 0,233 | 1,000 | nenhum | não (1/4) |
| xgboost − gam_nb | -1,574 | -2,53 | 0,011 | 0,103 | nenhum | sim (4/4) |
| xgboost − naive | -2,849 | -4,37 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -2,849 | -4,37 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | -0,053 | -0,10 | 0,919 | 1,000 | nenhum | não (0/4) |
| sarimax − ingarch_nb | -0,458 | -1,59 | 0,111 | 0,668 | nenhum | sim (4/4) |
| sarimax − gam_nb | -1,361 | -3,62 | 0,000 | 0,004 | 1− | sim (4/4) |
| sarimax − naive | -2,636 | -6,35 | 0,000 | 0,000 | 1−, 2−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -2,636 | -6,35 | 0,000 | 0,000 | 1−, 2−, 4− | sim (4/4) |
| lstm − ingarch_nb | -0,406 | -0,80 | 0,424 | 1,000 | nenhum | não (0/4) |
| lstm − gam_nb | -1,309 | -2,17 | 0,030 | 0,212 | nenhum | sim (4/4) |
| lstm − naive | -2,584 | -3,84 | 0,000 | 0,002 | 4− | sim (4/4) |
| lstm − seasonal_naive | -2,584 | -3,84 | 0,000 | 0,002 | 4− | sim (4/4) |
| ingarch_nb − gam_nb | -0,903 | -2,22 | 0,026 | 0,212 | 1− | sim (4/4) |
| ingarch_nb − naive | -2,178 | -4,35 | 0,000 | 0,000 | 2−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -2,178 | -4,35 | 0,000 | 0,000 | 2−, 4− | sim (4/4) |
| gam_nb − naive | -1,275 | -3,02 | 0,003 | 0,029 | 2−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -1,275 | -3,02 | 0,003 | 0,029 | 2−, 4− | sim (4/4) |
| naive − seasonal_naive | 0,000 | — | — | — | nenhum | não (0/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,053 | -0,30 | 0,764 | 1,000 | nenhum | não (0/4) |
| H2_media_com_meteo | 0,162 | 2,36 | 0,018 | 0,183 | 1+ | não (0/4) |
| PM25_rico_sem_meteo | 0,108 | 0,42 | 0,675 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,025 | 0,22 | 0,827 | 1,000 | nenhum | não (0/4) |
| rico_vs_media_com_meteo | -0,138 | -1,21 | 0,226 | 1,000 | 1− | não (1/4) |
| POLUENTES_sem_meteo | -0,193 | -0,73 | 0,463 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | -0,121 | -1,18 | 0,240 | 1,000 | nenhum | não (1/4) |
| METEO | 0,191 | 0,63 | 0,531 | 1,000 | nenhum | não (0/4) |
| COMPLETO_vs_meteo | -0,169 | -1,32 | 0,187 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,049 | -0,52 | 0,600 | 1,000 | nenhum | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,126 | -1,11 | 0,267 | 1,000 | nenhum | sim (4/4) |
| H2_media_com_meteo | 0,049 | 0,99 | 0,323 | 1,000 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | -0,073 | -0,56 | 0,577 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,094 | 0,95 | 0,342 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | 0,045 | 0,56 | 0,578 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | -0,277 | -1,68 | 0,094 | 0,913 | nenhum | sim (4/4) |
| POLUENTES_com_meteo | 0,026 | 0,27 | 0,785 | 1,000 | nenhum | não (1/4) |
| METEO | -0,299 | -1,58 | 0,115 | 0,924 | nenhum | não (1/4) |
| COMPLETO_vs_meteo | 0,176 | 1,37 | 0,171 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,150 | 1,69 | 0,091 | 0,913 | 3+ | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,088 | -0,37 | 0,714 | 1,000 | 1− | não (0/4) |
| H2_media_com_meteo | -0,720 | -2,86 | 0,004 | 0,026 | 1− | não (0/4) |
| PM25_rico_sem_meteo | 3,885 | 5,14 | 0,000 | 0,000 | 1+, 3+, 4+ | sim (3/4) |
| PM25_rico_com_meteo | 2,134 | 4,23 | 0,000 | 0,000 | 3+, 4+ | não (0/4) |
| rico_vs_media_com_meteo | 2,854 | 5,63 | 0,000 | 0,000 | 1+, 3+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | -0,097 | -0,19 | 0,849 | 1,000 | nenhum | não (0/4) |
| POLUENTES_com_meteo | -0,202 | -0,59 | 0,556 | 1,000 | nenhum | não (1/4) |
| METEO | 1,685 | 2,97 | 0,003 | 0,022 | 1+, 4+ | não (2/4) |
| COMPLETO_vs_meteo | 1,266 | 2,68 | 0,008 | 0,030 | 1−, 2+, 3+, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,468 | 2,85 | 0,004 | 0,026 | 1−, 2+, 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,269 | 0,87 | 0,386 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,252 | 1,93 | 0,053 | 0,534 | nenhum | sim (4/4) |
| PM25_rico_sem_meteo | 0,817 | 1,41 | 0,159 | 1,000 | 1+ | não (2/4) |
| PM25_rico_com_meteo | 0,535 | 1,08 | 0,280 | 1,000 | 1+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,283 | 0,60 | 0,546 | 1,000 | 1+ | não (2/4) |
| POLUENTES_sem_meteo | -0,471 | -1,07 | 0,287 | 1,000 | 3− | sim (3/4) |
| POLUENTES_com_meteo | -0,572 | -1,45 | 0,146 | 1,000 | nenhum | sim (4/4) |
| METEO | 0,127 | 0,31 | 0,759 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,287 | 0,37 | 0,711 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo_poluentes | 0,859 | 1,39 | 0,166 | 1,000 | 1+ | sim (4/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,195 | -0,74 | 0,462 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,065 | 0,62 | 0,537 | 1,000 | nenhum | não (1/4) |
| PM25_rico_sem_meteo | 0,086 | 0,22 | 0,829 | 1,000 | nenhum | não (2/4) |
| PM25_rico_com_meteo | 0,055 | 0,17 | 0,867 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | -0,010 | -0,03 | 0,976 | 1,000 | nenhum | não (2/4) |
| POLUENTES_sem_meteo | -0,507 | -1,53 | 0,127 | 1,000 | 3− | sim (4/4) |
| POLUENTES_com_meteo | -0,285 | -0,91 | 0,361 | 1,000 | nenhum | não (2/4) |
| METEO | -0,020 | -0,07 | 0,945 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,002 | 0,00 | 0,997 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,287 | 0,58 | 0,565 | 1,000 | nenhum | não (2/4) |

## Contrastes fora do Holm (perdas idênticas em todas as datas)

As duas previsões coincidem em todas as datas-alvo; d_t ≡ 0, o DM não é definido e o contraste sai da família antes do ajuste de Holm (o p Holm das demais usa só os contrastes testáveis). Quando o par é Naïve × Seasonal Naïve (h = 7, defasagem igual à sazonal), os contrastes de cada modelo contra os dois baselines são duplicados e ambos permanecem na família, o que torna o Holm conservador.

- modelos_AR_CAL: naive − seasonal_naive (naive:baseline vs seasonal_naive:baseline)

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

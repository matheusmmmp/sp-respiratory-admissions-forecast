# Validação e teste pareado de perdas — run `mh_h7_cetesb_cetesb_full_20261111-030322`

Gerado por `src/experiments/teste_dm_v02.py`. h = 7; 95040 previsões; 720 datas-alvo em 4 folds.

## 1. Métricas recalculadas de `predictions.csv`

- Por (modelo, conjunto, semente, fold): 528 linhas; diferença máxima contra `metrics_by_fold.csv`: MAE 1.1e-14, RMSE 1.1e-14, R2 3.3e-16, MASE 3.3e-16
- Agregados (sementes dentro da fold, depois folds): 52 linhas; diferença máxima contra `model_comparison.csv`: MAE_medio 7.1e-15, MAE_std_fold 3.1e-15, RMSE_medio 7.1e-15, R2_medio 1.7e-16, MASE_medio 2.2e-16

## 2. Diebold–Mariano — método

Perda = erro absoluto por data-alvo (média das sementes para XGBoost e LSTM; demais determinísticos). d_t = L_A − L_B nas mesmas datas; variância de longo prazo de Newey–West (Bartlett, largura ⌊T^{1/3}⌋), correção de Harvey–Leybourne–Newbold, p bicaudal na t(T−1). Por fold (T = 180) e agrupado (T = 720, janelas contíguas). p de Holm dentro de cada família. **DM < 0 favorece A.** O critério §0.7 (descritivo) aparece ao lado.

## Família `modelos_AR_CAL`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| xgboost − sarimax | -0,973 | -1,41 | 0,160 | 0,640 | 3− | não (1/4) |
| xgboost − lstm | -0,244 | -0,42 | 0,672 | 0,778 | nenhum | não (0/4) |
| xgboost − ingarch_nb | -1,313 | -1,88 | 0,061 | 0,367 | nenhum | não (1/4) |
| xgboost − gam_nb | -2,884 | -4,80 | 0,000 | 0,000 | 2−, 3−, 4− | sim (4/4) |
| xgboost − naive | -5,474 | -7,86 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| xgboost − seasonal_naive | -5,474 | -7,86 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − lstm | 0,729 | 1,13 | 0,259 | 0,778 | nenhum | não (0/4) |
| sarimax − ingarch_nb | -0,339 | -1,00 | 0,315 | 0,778 | nenhum | sim (4/4) |
| sarimax − gam_nb | -1,911 | -3,74 | 0,000 | 0,002 | 1− | sim (4/4) |
| sarimax − naive | -4,500 | -8,02 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| sarimax − seasonal_naive | -4,500 | -8,02 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − ingarch_nb | -1,068 | -1,66 | 0,098 | 0,492 | 4− | não (0/4) |
| lstm − gam_nb | -2,640 | -3,66 | 0,000 | 0,002 | 1−, 4− | sim (4/4) |
| lstm − naive | -5,229 | -6,70 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| lstm − seasonal_naive | -5,229 | -6,70 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − gam_nb | -1,571 | -2,95 | 0,003 | 0,023 | 1− | sim (4/4) |
| ingarch_nb − naive | -4,161 | -6,88 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| ingarch_nb − seasonal_naive | -4,161 | -6,88 | 0,000 | 0,000 | 1−, 2−, 3−, 4− | sim (4/4) |
| gam_nb − naive | -2,589 | -4,91 | 0,000 | 0,000 | 1−, 2−, 4− | sim (4/4) |
| gam_nb − seasonal_naive | -2,589 | -4,91 | 0,000 | 0,000 | 1−, 2−, 4− | sim (4/4) |
| naive − seasonal_naive | 0,000 | — | — | — | nenhum | não (0/4) |

## Família `ablacao_xgboost`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,176 | 0,84 | 0,400 | 1,000 | nenhum | não (1/4) |
| H2_media_com_meteo | 0,017 | 0,22 | 0,822 | 1,000 | nenhum | não (0/4) |
| PM25_rico_sem_meteo | 0,425 | 1,53 | 0,127 | 1,000 | 4+ | não (0/4) |
| PM25_rico_com_meteo | 0,144 | 1,13 | 0,260 | 1,000 | 3+ | não (0/4) |
| rico_vs_media_com_meteo | 0,127 | 1,22 | 0,224 | 1,000 | 3+ | não (0/4) |
| POLUENTES_sem_meteo | 0,711 | 2,45 | 0,015 | 0,132 | nenhum | sim (3/4) |
| POLUENTES_com_meteo | -0,100 | -0,87 | 0,385 | 1,000 | nenhum | não (0/4) |
| METEO | 1,268 | 3,54 | 0,000 | 0,004 | 4+ | sim (3/4) |
| COMPLETO_vs_meteo | -0,219 | -1,30 | 0,193 | 1,000 | 1− | não (1/4) |
| COMPLETO_vs_meteo_poluentes | -0,119 | -1,02 | 0,306 | 1,000 | 1− | não (0/4) |

## Família `ablacao_sarimax`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,058 | -0,49 | 0,623 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | -0,027 | -0,55 | 0,586 | 1,000 | 2+ | não (2/4) |
| PM25_rico_sem_meteo | -0,092 | -0,71 | 0,476 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,034 | 0,40 | 0,692 | 1,000 | 1+ | não (1/4) |
| rico_vs_media_com_meteo | 0,061 | 0,72 | 0,469 | 1,000 | 1+ | sim (3/4) |
| POLUENTES_sem_meteo | -0,194 | -1,17 | 0,244 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | 0,043 | 0,29 | 0,772 | 1,000 | nenhum | não (1/4) |
| METEO | -0,172 | -0,89 | 0,371 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | 0,022 | 0,13 | 0,898 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | -0,021 | -0,15 | 0,882 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_lstm`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,026 | 0,10 | 0,918 | 1,000 | nenhum | não (1/4) |
| H2_media_com_meteo | -0,915 | -3,79 | 0,000 | 0,001 | 1−, 4− | não (0/4) |
| PM25_rico_sem_meteo | 3,102 | 3,98 | 0,000 | 0,001 | 1+, 4+ | sim (3/4) |
| PM25_rico_com_meteo | 1,610 | 3,48 | 0,001 | 0,004 | 3+, 4+ | não (0/4) |
| rico_vs_media_com_meteo | 2,525 | 4,80 | 0,000 | 0,000 | 1+, 3+, 4+ | não (2/4) |
| POLUENTES_sem_meteo | -0,336 | -0,62 | 0,534 | 1,000 | nenhum | não (1/4) |
| POLUENTES_com_meteo | -0,153 | -0,43 | 0,671 | 1,000 | nenhum | não (1/4) |
| METEO | 1,895 | 3,04 | 0,002 | 0,015 | 1+, 4+ | não (2/4) |
| COMPLETO_vs_meteo | 1,151 | 2,21 | 0,027 | 0,110 | 1−, 4+ | não (0/4) |
| COMPLETO_vs_meteo_poluentes | 1,304 | 2,31 | 0,021 | 0,106 | 1−, 4+ | não (0/4) |

## Família `ablacao_ingarch_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | 0,183 | 0,58 | 0,561 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,226 | 1,80 | 0,072 | 0,673 | nenhum | sim (3/4) |
| PM25_rico_sem_meteo | 1,132 | 1,83 | 0,067 | 0,673 | 1+ | sim (3/4) |
| PM25_rico_com_meteo | 0,782 | 1,68 | 0,094 | 0,754 | 1+ | sim (3/4) |
| rico_vs_media_com_meteo | 0,556 | 1,27 | 0,203 | 1,000 | 1+ | não (2/4) |
| POLUENTES_sem_meteo | -0,159 | -0,34 | 0,731 | 1,000 | 2+, 3− | sim (3/4) |
| POLUENTES_com_meteo | 0,126 | 0,32 | 0,752 | 1,000 | nenhum | não (2/4) |
| METEO | 0,068 | 0,17 | 0,868 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo | 0,888 | 1,14 | 0,253 | 1,000 | nenhum | sim (4/4) |
| COMPLETO_vs_meteo_poluentes | 0,762 | 1,13 | 0,259 | 1,000 | nenhum | sim (3/4) |

## Família `ablacao_gam_nb`

| Contraste (A − B) | d̄ agrupado | DM | p | p Holm | folds com p<0,05 (sinal) | §0.7 (folds) |
|---|---|---|---|---|---|---|
| H2_media_sem_meteo | -0,129 | -0,47 | 0,638 | 1,000 | nenhum | sim (3/4) |
| H2_media_com_meteo | 0,185 | 1,43 | 0,152 | 1,000 | 3+ | sim (3/4) |
| PM25_rico_sem_meteo | -0,159 | -0,39 | 0,700 | 1,000 | nenhum | não (1/4) |
| PM25_rico_com_meteo | 0,123 | 0,35 | 0,727 | 1,000 | nenhum | não (2/4) |
| rico_vs_media_com_meteo | -0,061 | -0,18 | 0,854 | 1,000 | nenhum | sim (3/4) |
| POLUENTES_sem_meteo | -0,405 | -1,26 | 0,210 | 1,000 | 3− | não (1/4) |
| POLUENTES_com_meteo | -0,320 | -1,10 | 0,274 | 1,000 | 2− | não (1/4) |
| METEO | 0,039 | 0,13 | 0,898 | 1,000 | nenhum | sim (3/4) |
| COMPLETO_vs_meteo | -0,031 | -0,05 | 0,957 | 1,000 | nenhum | não (2/4) |
| COMPLETO_vs_meteo_poluentes | 0,289 | 0,55 | 0,580 | 1,000 | nenhum | sim (4/4) |

## Contrastes fora do Holm (perdas idênticas em todas as datas)

As duas previsões coincidem em todas as datas-alvo; d_t ≡ 0, o DM não é definido e o contraste sai da família antes do ajuste de Holm (o p Holm das demais usa só os contrastes testáveis). Quando o par é Naïve × Seasonal Naïve (h = 7, defasagem igual à sazonal), os contrastes de cada modelo contra os dois baselines são duplicados e ambos permanecem na família, o que torna o Holm conservador.

- modelos_AR_CAL: naive − seasonal_naive (naive:baseline vs seasonal_naive:baseline)

## Limitações

- O DM supõe d_t fracamente estacionário dentro da janela; a HAC corrige autocorrelação, não quebras.
- A média das sementes por data reduz a variância de treino, mas o teste não modela a variância entre sementes explicitamente; o critério §0.7 cobre essa dimensão de forma descritiva.
- O p agrupado e os p por fold usam as mesmas datas; não são independentes.
- Famílias grandes (21 pares de modelos) com Holm são conservadoras; não há Model Confidence Set.
- Nenhum valor foi digitado; todos vêm dos artefatos da run identificada.

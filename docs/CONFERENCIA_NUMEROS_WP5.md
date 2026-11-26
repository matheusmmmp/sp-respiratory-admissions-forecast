# Conferência de números — WP5 (README.md, README.pt-BR.md, docs/, data/README.md)

Gerado por `docs/scripts/conferir_numeros.py` em 2026-11-26 15:18. Cada linha: onde o número aparece, o número como exibido, o arquivo de origem, a chave/seletor e o valor lido. Arredondamento: MAE 2 casas, MASE e skill 3 casas, contagens exatas. As tabelas dos dois READMEs são geradas por `docs/scripts/tabela_readme.py` (`--lang en` / `--lang pt`; mesmas células, ponto decimal dos arquivos de origem), que também exige igualdade (|diff| <= 1e-9) entre `model_comparison.csv`, `A_modelos_por_h.csv` e `arcal_por_horizonte_dois_alvos.csv`; a conferência verifica que cada bloco de tabela aparece literalmente em `README.md` e em `README.pt-BR.md`. Números do texto corrido do `README.pt-BR.md` usam vírgula decimal e são conferidos à parte (linhas 'README.pt-BR.md prose').

Total: 624 números; VERIFICADO: 624; DIVERGENTE: 0.

| # | Onde | Número exibido | Arquivo | Chave / seletor | Valor lido | Status |
|---:|---|---|---|---|---|---|
| 1 | README total table h=1 XGBoost MAE | 18.56 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=xgboost, MAE_medio | 18.55664036220974 | VERIFICADO |
| 2 | README total table h=1 XGBoost MASE | 0.645 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=xgboost, MASE_medio | 0.6450363220356312 | VERIFICADO |
| 3 | README total table h=1 SARIMAX MAE | 18.92 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=sarimax, MAE_medio | 18.92278742459551 | VERIFICADO |
| 4 | README total table h=1 SARIMAX MASE | 0.660 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=sarimax, MASE_medio | 0.6599211007178614 | VERIFICADO |
| 5 | README total table h=1 LSTM MAE | 19.01 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=lstm, MAE_medio | 19.01129075580173 | VERIFICADO |
| 6 | README total table h=1 LSTM MASE | 0.662 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=lstm, MASE_medio | 0.6620856881760778 | VERIFICADO |
| 7 | README total table h=1 INGARCH-NB MAE | 19.55 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=ingarch_nb, MAE_medio | 19.545888441103493 | VERIFICADO |
| 8 | README total table h=1 INGARCH-NB MASE | 0.681 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.6807878896739885 | VERIFICADO |
| 9 | README total table h=1 GAM-NB MAE | 21.91 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=gam_nb, MAE_medio | 21.905190687108103 | VERIFICADO |
| 10 | README total table h=1 GAM-NB MASE | 0.763 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7627496418327373 | VERIFICADO |
| 11 | README total table h=1 Naive MAE | 28.71 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=naive, MAE_medio | 28.71111111111111 | VERIFICADO |
| 12 | README total table h=1 Naive MASE | 1.000 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 13 | README total table h=1 Seasonal Naive MAE | 28.87 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=seasonal_naive, MAE_medio | 28.870833333333334 | VERIFICADO |
| 14 | README total table h=1 Seasonal Naive MASE | 1.007 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | model=seasonal_naive, MASE_medio | 1.0067604969036266 | VERIFICADO |
| 15 | README runs total h=1 run id | h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | run_id | h1_v02_cetesb_cetesb_classicos_full_20261022-211834 | VERIFICADO |
| 16 | README runs total h=1 commit | e6a63c3 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_commit[:7] | e6a63c3 | VERIFICADO |
| 17 | README runs total h=1 clean tree | yes | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_sujo | yes | VERIFICADO |
| 18 | README runs total h=1 predictions | 95,040 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 19 | LESSONS 4 table h1_v02_cetesb_cetesb_classicos_full_20261022-211834 git_sujo | false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_sujo | false | VERIFICADO |
| 20 | LESSONS 4 table h1_v02_cetesb_cetesb_classicos_full_20261022-211834 repo changed | false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 21 | LESSONS 4 table h1_v02_cetesb_cetesb_classicos_full_20261022-211834 commit | e6a63c3 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | git_commit[:7] | e6a63c3 | VERIFICADO |
| 22 | README total table h=5 XGBoost MAE | 22.50 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=xgboost, MAE_medio | 22.503195099300807 | VERIFICADO |
| 23 | README total table h=5 XGBoost MASE | 0.656 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=xgboost, MASE_medio | 0.6563870004812085 | VERIFICADO |
| 24 | README total table h=5 SARIMAX MAE | 23.04 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=sarimax, MAE_medio | 23.0404528082138 | VERIFICADO |
| 25 | README total table h=5 SARIMAX MASE | 0.674 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=sarimax, MASE_medio | 0.6737883395872428 | VERIFICADO |
| 26 | README total table h=5 LSTM MAE | 22.56 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=lstm, MAE_medio | 22.56317355685764 | VERIFICADO |
| 27 | README total table h=5 LSTM MASE | 0.660 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=lstm, MASE_medio | 0.6601359903458155 | VERIFICADO |
| 28 | README total table h=5 INGARCH-NB MAE | 23.59 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=ingarch_nb, MAE_medio | 23.59042134560887 | VERIFICADO |
| 29 | README total table h=5 INGARCH-NB MASE | 0.690 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.690078407790947 | VERIFICADO |
| 30 | README total table h=5 GAM-NB MAE | 25.35 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=gam_nb, MAE_medio | 25.352119003995178 | VERIFICADO |
| 31 | README total table h=5 GAM-NB MASE | 0.741 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=gam_nb, MASE_medio | 0.741490849469305 | VERIFICADO |
| 32 | README total table h=5 Naive MAE | 34.13 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=naive, MAE_medio | 34.12777777777778 | VERIFICADO |
| 33 | README total table h=5 Naive MASE | 1.000 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 34 | README total table h=5 Seasonal Naive MAE | 28.87 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=seasonal_naive, MAE_medio | 28.870833333333334 | VERIFICADO |
| 35 | README total table h=5 Seasonal Naive MASE | 0.844 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.8441749869638578 | VERIFICADO |
| 36 | README runs total h=5 run id | mh_h5_cetesb_cetesb_full_20261110-211453 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | run_id | mh_h5_cetesb_cetesb_full_20261110-211453 | VERIFICADO |
| 37 | README runs total h=5 commit | 5436606 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_commit[:7] | 5436606 | VERIFICADO |
| 38 | README runs total h=5 clean tree | yes | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_sujo | yes | VERIFICADO |
| 39 | README runs total h=5 predictions | 95,040 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 40 | LESSONS 4 table mh_h5_cetesb_cetesb_full_20261110-211453 git_sujo | false | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_sujo | false | VERIFICADO |
| 41 | LESSONS 4 table mh_h5_cetesb_cetesb_full_20261110-211453 repo changed | false | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 42 | LESSONS 4 table mh_h5_cetesb_cetesb_full_20261110-211453 commit | 5436606 | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/manifest.json` | git_commit[:7] | 5436606 | VERIFICADO |
| 43 | README total table h=7 XGBoost MAE | 23.40 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=xgboost, MAE_medio | 23.397312622070316 | VERIFICADO |
| 44 | README total table h=7 XGBoost MASE | 0.810 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=xgboost, MASE_medio | 0.809546395994956 | VERIFICADO |
| 45 | README total table h=7 SARIMAX MAE | 24.37 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=sarimax, MAE_medio | 24.370407259757435 | VERIFICADO |
| 46 | README total table h=7 SARIMAX MASE | 0.845 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=sarimax, MASE_medio | 0.845018316485488 | VERIFICADO |
| 47 | README total table h=7 LSTM MAE | 23.64 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=lstm, MAE_medio | 23.641746537950304 | VERIFICADO |
| 48 | README total table h=7 LSTM MASE | 0.821 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=lstm, MASE_medio | 0.8206435082250865 | VERIFICADO |
| 49 | README total table h=7 INGARCH-NB MAE | 24.71 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=ingarch_nb, MAE_medio | 24.709864040408053 | VERIFICADO |
| 50 | README total table h=7 INGARCH-NB MASE | 0.857 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.8568314129459542 | VERIFICADO |
| 51 | README total table h=7 GAM-NB MAE | 26.28 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=gam_nb, MAE_medio | 26.281345392039167 | VERIFICADO |
| 52 | README total table h=7 GAM-NB MASE | 0.909 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=gam_nb, MASE_medio | 0.909077397058716 | VERIFICADO |
| 53 | README total table h=7 Naive MAE | 28.87 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=naive, MAE_medio | 28.870833333333334 | VERIFICADO |
| 54 | README total table h=7 Naive MASE | 1.000 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 55 | README total table h=7 Seasonal Naive MAE | 28.87 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=seasonal_naive, MAE_medio | 28.870833333333334 | VERIFICADO |
| 56 | README total table h=7 Seasonal Naive MASE | 1.000 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | model=seasonal_naive, MASE_medio | 1.0 | VERIFICADO |
| 57 | README runs total h=7 run id | mh_h7_cetesb_cetesb_full_20261111-030322 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | run_id | mh_h7_cetesb_cetesb_full_20261111-030322 | VERIFICADO |
| 58 | README runs total h=7 commit | 49c2188 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_commit[:7] | 49c2188 | VERIFICADO |
| 59 | README runs total h=7 clean tree | yes | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_sujo | yes | VERIFICADO |
| 60 | README runs total h=7 predictions | 95,040 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 61 | LESSONS 4 table mh_h7_cetesb_cetesb_full_20261111-030322 git_sujo | false | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_sujo | false | VERIFICADO |
| 62 | LESSONS 4 table mh_h7_cetesb_cetesb_full_20261111-030322 repo changed | false | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 63 | LESSONS 4 table mh_h7_cetesb_cetesb_full_20261111-030322 commit | 49c2188 | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/manifest.json` | git_commit[:7] | 49c2188 | VERIFICADO |
| 64 | README total table h=15 XGBoost MAE | 24.34 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=xgboost, MAE_medio | 24.338430718315973 | VERIFICADO |
| 65 | README total table h=15 XGBoost MASE | 0.654 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=xgboost, MASE_medio | 0.6544892964969911 | VERIFICADO |
| 66 | README total table h=15 SARIMAX MAE | 25.84 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=sarimax, MAE_medio | 25.840538029459665 | VERIFICADO |
| 67 | README total table h=15 SARIMAX MASE | 0.698 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=sarimax, MASE_medio | 0.697969694161429 | VERIFICADO |
| 68 | README total table h=15 LSTM MAE | 25.32 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=lstm, MAE_medio | 25.318614366319444 | VERIFICADO |
| 69 | README total table h=15 LSTM MASE | 0.683 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=lstm, MASE_medio | 0.6825348606654911 | VERIFICADO |
| 70 | README total table h=15 INGARCH-NB MAE | 26.39 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=ingarch_nb, MAE_medio | 26.38952767550589 | VERIFICADO |
| 71 | README total table h=15 INGARCH-NB MASE | 0.713 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.7127363513562217 | VERIFICADO |
| 72 | README total table h=15 GAM-NB MAE | 27.24 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=gam_nb, MAE_medio | 27.23718850257185 | VERIFICADO |
| 73 | README total table h=15 GAM-NB MASE | 0.734 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7338379384028475 | VERIFICADO |
| 74 | README total table h=15 Naive MAE | 37.05 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=naive, MAE_medio | 37.05277777777778 | VERIFICADO |
| 75 | README total table h=15 Naive MASE | 1.000 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 76 | README total table h=15 Seasonal Naive MAE | 33.25 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=seasonal_naive, MAE_medio | 33.25416666666666 | VERIFICADO |
| 77 | README total table h=15 Seasonal Naive MASE | 0.897 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.8965216641864637 | VERIFICADO |
| 78 | README runs total h=15 run id | mh_h15_cetesb_cetesb_full_20261111-070926 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | run_id | mh_h15_cetesb_cetesb_full_20261111-070926 | VERIFICADO |
| 79 | README runs total h=15 commit | b5bb35f | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_commit[:7] | b5bb35f | VERIFICADO |
| 80 | README runs total h=15 clean tree | yes | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_sujo | yes | VERIFICADO |
| 81 | README runs total h=15 predictions | 95,040 | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 82 | LESSONS 4 table mh_h15_cetesb_cetesb_full_20261111-070926 git_sujo | false | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_sujo | false | VERIFICADO |
| 83 | LESSONS 4 table mh_h15_cetesb_cetesb_full_20261111-070926 repo changed | false | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 84 | LESSONS 4 table mh_h15_cetesb_cetesb_full_20261111-070926 commit | b5bb35f | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/manifest.json` | git_commit[:7] | b5bb35f | VERIFICADO |
| 85 | README total table h=30 XGBoost MAE | 26.36 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=xgboost, MAE_medio | 26.36273511250814 | VERIFICADO |
| 86 | README total table h=30 XGBoost MASE | 0.698 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=xgboost, MASE_medio | 0.6975282381140449 | VERIFICADO |
| 87 | README total table h=30 SARIMAX MAE | 25.32 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=sarimax, MAE_medio | 25.315812282978456 | VERIFICADO |
| 88 | README total table h=30 SARIMAX MASE | 0.668 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=sarimax, MASE_medio | 0.6683242023008517 | VERIFICADO |
| 89 | README total table h=30 LSTM MAE | 26.76 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=lstm, MAE_medio | 26.75730324003432 | VERIFICADO |
| 90 | README total table h=30 LSTM MASE | 0.710 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=lstm, MASE_medio | 0.7095758009119727 | VERIFICADO |
| 91 | README total table h=30 INGARCH-NB MAE | 25.47 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=ingarch_nb, MAE_medio | 25.469708612596868 | VERIFICADO |
| 92 | README total table h=30 INGARCH-NB MASE | 0.674 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.6739409046913544 | VERIFICADO |
| 93 | README total table h=30 GAM-NB MAE | 27.52 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=gam_nb, MAE_medio | 27.522542807383903 | VERIFICADO |
| 94 | README total table h=30 GAM-NB MASE | 0.726 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7260406426660545 | VERIFICADO |
| 95 | README total table h=30 Naive MAE | 37.84 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=naive, MAE_medio | 37.84166666666667 | VERIFICADO |
| 96 | README total table h=30 Naive MASE | 1.000 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 97 | README total table h=30 Seasonal Naive MAE | 34.85 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=seasonal_naive, MAE_medio | 34.85277777777778 | VERIFICADO |
| 98 | README total table h=30 Seasonal Naive MASE | 0.917 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.9168681246217404 | VERIFICADO |
| 99 | README runs total h=30 run id | mh_h30_cetesb_cetesb_full_20261113-104814 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | run_id | mh_h30_cetesb_cetesb_full_20261113-104814 | VERIFICADO |
| 100 | README runs total h=30 commit | e4828bc | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_commit[:7] | e4828bc | VERIFICADO |
| 101 | README runs total h=30 clean tree | yes | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_sujo | yes | VERIFICADO |
| 102 | README runs total h=30 predictions | 95,040 | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 103 | LESSONS 4 table mh_h30_cetesb_cetesb_full_20261113-104814 git_sujo | false | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_sujo | false | VERIFICADO |
| 104 | LESSONS 4 table mh_h30_cetesb_cetesb_full_20261113-104814 repo changed | false | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 105 | LESSONS 4 table mh_h30_cetesb_cetesb_full_20261113-104814 commit | e4828bc | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/manifest.json` | git_commit[:7] | e4828bc | VERIFICADO |
| 106 | README urgent table h=1 XGBoost MAE | 14.88 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=xgboost, MAE_medio | 14.877528518040975 | VERIFICADO |
| 107 | README urgent table h=1 XGBoost MASE | 0.749 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=xgboost, MASE_medio | 0.7493985742063238 | VERIFICADO |
| 108 | README urgent table h=1 SARIMAX MAE | 14.26 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=sarimax, MAE_medio | 14.262206114304536 | VERIFICADO |
| 109 | README urgent table h=1 SARIMAX MASE | 0.719 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=sarimax, MASE_medio | 0.7188438309333273 | VERIFICADO |
| 110 | README urgent table h=1 LSTM MAE | 14.76 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=lstm, MAE_medio | 14.758034693400065 | VERIFICADO |
| 111 | README urgent table h=1 LSTM MASE | 0.744 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=lstm, MASE_medio | 0.7439845864554522 | VERIFICADO |
| 112 | README urgent table h=1 INGARCH-NB MAE | 14.94 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=ingarch_nb, MAE_medio | 14.93920029628974 | VERIFICADO |
| 113 | README urgent table h=1 INGARCH-NB MASE | 0.753 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.7530570305777435 | VERIFICADO |
| 114 | README urgent table h=1 GAM-NB MAE | 16.65 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=gam_nb, MAE_medio | 16.650977402986733 | VERIFICADO |
| 115 | README urgent table h=1 GAM-NB MASE | 0.838 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=gam_nb, MASE_medio | 0.8382765840924642 | VERIFICADO |
| 116 | README urgent table h=1 Naive MAE | 19.81 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=naive, MAE_medio | 19.81388888888889 | VERIFICADO |
| 117 | README urgent table h=1 Naive MASE | 1.000 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 118 | README urgent table h=1 Seasonal Naive MAE | 21.36 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=seasonal_naive, MAE_medio | 21.359722222222224 | VERIFICADO |
| 119 | README urgent table h=1 Seasonal Naive MASE | 1.076 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | model=seasonal_naive, MASE_medio | 1.075768913649277 | VERIFICADO |
| 120 | README runs urgencia h=1 run id | ur_h1_cetesb_cetesb_full_20261116-191534 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | run_id | ur_h1_cetesb_cetesb_full_20261116-191534 | VERIFICADO |
| 121 | README runs urgencia h=1 commit | eeeef00 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_commit[:7] | eeeef00 | VERIFICADO |
| 122 | README runs urgencia h=1 clean tree | yes | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_sujo | yes | VERIFICADO |
| 123 | README runs urgencia h=1 predictions | 95,040 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 124 | README runs urgencia h=1 status | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 125 | LESSONS 4 table ur_h1_cetesb_cetesb_full_20261116-191534 git_sujo | false | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_sujo | false | VERIFICADO |
| 126 | LESSONS 4 table ur_h1_cetesb_cetesb_full_20261116-191534 repo changed | false | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 127 | LESSONS 4 table ur_h1_cetesb_cetesb_full_20261116-191534 commit | eeeef00 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | git_commit[:7] | eeeef00 | VERIFICADO |
| 128 | README urgent table h=5 XGBoost MAE | 17.61 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=xgboost, MAE_medio | 17.614207666185166 | VERIFICADO |
| 129 | README urgent table h=5 XGBoost MASE | 0.665 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=xgboost, MASE_medio | 0.665219991135082 | VERIFICADO |
| 130 | README urgent table h=5 SARIMAX MAE | 17.66 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=sarimax, MAE_medio | 17.659148806068085 | VERIFICADO |
| 131 | README urgent table h=5 SARIMAX MASE | 0.668 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=sarimax, MASE_medio | 0.6682833142381159 | VERIFICADO |
| 132 | README urgent table h=5 LSTM MAE | 17.99 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=lstm, MAE_medio | 17.990163016849095 | VERIFICADO |
| 133 | README urgent table h=5 LSTM MASE | 0.681 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=lstm, MASE_medio | 0.6808978424321165 | VERIFICADO |
| 134 | README urgent table h=5 INGARCH-NB MAE | 18.41 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=ingarch_nb, MAE_medio | 18.406055661382076 | VERIFICADO |
| 135 | README urgent table h=5 INGARCH-NB MASE | 0.697 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.6968320614397961 | VERIFICADO |
| 136 | README urgent table h=5 GAM-NB MAE | 19.94 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=gam_nb, MAE_medio | 19.939961059482027 | VERIFICADO |
| 137 | README urgent table h=5 GAM-NB MASE | 0.754 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7538886244214059 | VERIFICADO |
| 138 | README urgent table h=5 Naive MAE | 26.36 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=naive, MAE_medio | 26.359722222222224 | VERIFICADO |
| 139 | README urgent table h=5 Naive MASE | 1.000 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 140 | README urgent table h=5 Seasonal Naive MAE | 21.36 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=seasonal_naive, MAE_medio | 21.359722222222224 | VERIFICADO |
| 141 | README urgent table h=5 Seasonal Naive MASE | 0.809 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.8090362514092603 | VERIFICADO |
| 142 | README runs urgencia h=5 run id | ur_h5_cetesb_cetesb_full_20261116-222823 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | run_id | ur_h5_cetesb_cetesb_full_20261116-222823 | VERIFICADO |
| 143 | README runs urgencia h=5 commit | 8325cee | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_commit[:7] | 8325cee | VERIFICADO |
| 144 | README runs urgencia h=5 clean tree | yes | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_sujo | yes | VERIFICADO |
| 145 | README runs urgencia h=5 predictions | 95,040 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 146 | README runs urgencia h=5 status | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 147 | LESSONS 4 table ur_h5_cetesb_cetesb_full_20261116-222823 git_sujo | false | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_sujo | false | VERIFICADO |
| 148 | LESSONS 4 table ur_h5_cetesb_cetesb_full_20261116-222823 repo changed | false | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 149 | LESSONS 4 table ur_h5_cetesb_cetesb_full_20261116-222823 commit | 8325cee | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | git_commit[:7] | 8325cee | VERIFICADO |
| 150 | README urgent table h=7 XGBoost MAE | 18.51 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=xgboost, MAE_medio | 18.51086163626777 | VERIFICADO |
| 151 | README urgent table h=7 XGBoost MASE | 0.865 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=xgboost, MASE_medio | 0.8652995656802502 | VERIFICADO |
| 152 | README urgent table h=7 SARIMAX MAE | 18.72 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=sarimax, MAE_medio | 18.72325664381616 | VERIFICADO |
| 153 | README urgent table h=7 SARIMAX MASE | 0.876 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=sarimax, MASE_medio | 0.8764246043621855 | VERIFICADO |
| 154 | README urgent table h=7 LSTM MAE | 18.78 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=lstm, MAE_medio | 18.775988409254285 | VERIFICADO |
| 155 | README urgent table h=7 LSTM MASE | 0.879 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=lstm, MASE_medio | 0.8788889948470904 | VERIFICADO |
| 156 | README urgent table h=7 INGARCH-NB MAE | 19.18 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=ingarch_nb, MAE_medio | 19.18167251879772 | VERIFICADO |
| 157 | README urgent table h=7 INGARCH-NB MASE | 0.898 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.8981330183603998 | VERIFICADO |
| 158 | README urgent table h=7 GAM-NB MAE | 20.08 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=gam_nb, MAE_medio | 20.084590981444578 | VERIFICADO |
| 159 | README urgent table h=7 GAM-NB MASE | 0.939 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=gam_nb, MASE_medio | 0.9387195692556558 | VERIFICADO |
| 160 | README urgent table h=7 Naive MAE | 21.36 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=naive, MAE_medio | 21.359722222222224 | VERIFICADO |
| 161 | README urgent table h=7 Naive MASE | 1.000 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 162 | README urgent table h=7 Seasonal Naive MAE | 21.36 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=seasonal_naive, MAE_medio | 21.359722222222224 | VERIFICADO |
| 163 | README urgent table h=7 Seasonal Naive MASE | 1.000 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | model=seasonal_naive, MASE_medio | 1.0 | VERIFICADO |
| 164 | README runs urgencia h=7 run id | ur_h7_cetesb_cetesb_full_20261117-073926 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | run_id | ur_h7_cetesb_cetesb_full_20261117-073926 | VERIFICADO |
| 165 | README runs urgencia h=7 commit | dfc3c57 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_commit[:7] | dfc3c57 | VERIFICADO |
| 166 | README runs urgencia h=7 clean tree | yes | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_sujo | yes | VERIFICADO |
| 167 | README runs urgencia h=7 predictions | 95,040 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 168 | README runs urgencia h=7 status | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 169 | LESSONS 4 table ur_h7_cetesb_cetesb_full_20261117-073926 git_sujo | false | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_sujo | false | VERIFICADO |
| 170 | LESSONS 4 table ur_h7_cetesb_cetesb_full_20261117-073926 repo changed | false | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 171 | LESSONS 4 table ur_h7_cetesb_cetesb_full_20261117-073926 commit | dfc3c57 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | git_commit[:7] | dfc3c57 | VERIFICADO |
| 172 | README urgent table h=15 XGBoost MAE | 20.99 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=xgboost, MAE_medio | 20.991515465842355 | VERIFICADO |
| 173 | README urgent table h=15 XGBoost MASE | 0.738 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=xgboost, MASE_medio | 0.7379888636642162 | VERIFICADO |
| 174 | README urgent table h=15 SARIMAX MAE | 21.17 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=sarimax, MAE_medio | 21.17359847401398 | VERIFICADO |
| 175 | README urgent table h=15 SARIMAX MASE | 0.746 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=sarimax, MASE_medio | 0.7462052277721897 | VERIFICADO |
| 176 | README urgent table h=15 LSTM MAE | 21.69 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=lstm, MAE_medio | 21.689027548895943 | VERIFICADO |
| 177 | README urgent table h=15 LSTM MASE | 0.761 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=lstm, MASE_medio | 0.7614850243704652 | VERIFICADO |
| 178 | README urgent table h=15 INGARCH-NB MAE | 21.52 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=ingarch_nb, MAE_medio | 21.519316322074676 | VERIFICADO |
| 179 | README urgent table h=15 INGARCH-NB MASE | 0.759 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.7591108140845907 | VERIFICADO |
| 180 | README urgent table h=15 GAM-NB MAE | 22.46 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=gam_nb, MAE_medio | 22.460084333584668 | VERIFICADO |
| 181 | README urgent table h=15 GAM-NB MASE | 0.788 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7881088759707341 | VERIFICADO |
| 182 | README urgent table h=15 Naive MAE | 28.39 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=naive, MAE_medio | 28.390277777777776 | VERIFICADO |
| 183 | README urgent table h=15 Naive MASE | 1.000 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 184 | README urgent table h=15 Seasonal Naive MAE | 27.05 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=seasonal_naive, MAE_medio | 27.04861111111111 | VERIFICADO |
| 185 | README urgent table h=15 Seasonal Naive MASE | 0.952 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.9517746700636917 | VERIFICADO |
| 186 | README runs urgencia h=15 run id | ur_h15_cetesb_cetesb_full_20261117-190532 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | run_id | ur_h15_cetesb_cetesb_full_20261117-190532 | VERIFICADO |
| 187 | README runs urgencia h=15 commit | 1252ad5 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_commit[:7] | 1252ad5 | VERIFICADO |
| 188 | README runs urgencia h=15 clean tree | yes | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_sujo | yes | VERIFICADO |
| 189 | README runs urgencia h=15 predictions | 95,040 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 190 | README runs urgencia h=15 status | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 191 | LESSONS 4 table ur_h15_cetesb_cetesb_full_20261117-190532 git_sujo | false | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_sujo | false | VERIFICADO |
| 192 | LESSONS 4 table ur_h15_cetesb_cetesb_full_20261117-190532 repo changed | false | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 193 | LESSONS 4 table ur_h15_cetesb_cetesb_full_20261117-190532 commit | 1252ad5 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | git_commit[:7] | 1252ad5 | VERIFICADO |
| 194 | README urgent table h=30 XGBoost MAE | 22.45 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=xgboost, MAE_medio | 22.447150202857124 | VERIFICADO |
| 195 | README urgent table h=30 XGBoost MASE | 0.683 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=xgboost, MASE_medio | 0.6827820443743224 | VERIFICADO |
| 196 | README urgent table h=30 SARIMAX MAE | 21.46 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=sarimax, MAE_medio | 21.45590827506612 | VERIFICADO |
| 197 | README urgent table h=30 SARIMAX MASE | 0.652 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=sarimax, MASE_medio | 0.6523839752948778 | VERIFICADO |
| 198 | README urgent table h=30 LSTM MAE | 22.69 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=lstm, MAE_medio | 22.692952467600502 | VERIFICADO |
| 199 | README urgent table h=30 LSTM MASE | 0.692 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=lstm, MASE_medio | 0.6915144566007632 | VERIFICADO |
| 200 | README urgent table h=30 INGARCH-NB MAE | 21.71 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=ingarch_nb, MAE_medio | 21.713569502853318 | VERIFICADO |
| 201 | README urgent table h=30 INGARCH-NB MASE | 0.661 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=ingarch_nb, MASE_medio | 0.6608332423468166 | VERIFICADO |
| 202 | README urgent table h=30 GAM-NB MAE | 23.57 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=gam_nb, MAE_medio | 23.57491934180965 | VERIFICADO |
| 203 | README urgent table h=30 GAM-NB MASE | 0.712 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=gam_nb, MASE_medio | 0.7121145491971601 | VERIFICADO |
| 204 | README urgent table h=30 Naive MAE | 32.85 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=naive, MAE_medio | 32.84861111111111 | VERIFICADO |
| 205 | README urgent table h=30 Naive MASE | 1.000 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=naive, MASE_medio | 1.0 | VERIFICADO |
| 206 | README urgent table h=30 Seasonal Naive MAE | 30.41 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=seasonal_naive, MAE_medio | 30.41111111111111 | VERIFICADO |
| 207 | README urgent table h=30 Seasonal Naive MASE | 0.922 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | model=seasonal_naive, MASE_medio | 0.921580071883653 | VERIFICADO |
| 208 | README runs urgencia h=30 run id | ur_h30_cetesb_cetesb_full_20261117-221426 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | run_id | ur_h30_cetesb_cetesb_full_20261117-221426 | VERIFICADO |
| 209 | README runs urgencia h=30 commit | 8be599e | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_commit[:7] | 8be599e | VERIFICADO |
| 210 | README runs urgencia h=30 clean tree | yes | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_sujo | yes | VERIFICADO |
| 211 | README runs urgencia h=30 predictions | 95,040 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 212 | README runs urgencia h=30 status | PRELIMINARY_UNVALIDATED_TARGET | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | status | PRELIMINARY_UNVALIDATED_TARGET | VERIFICADO |
| 213 | LESSONS 4 table ur_h30_cetesb_cetesb_full_20261117-221426 git_sujo | false | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_sujo | false | VERIFICADO |
| 214 | LESSONS 4 table ur_h30_cetesb_cetesb_full_20261117-221426 repo changed | false | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | proveniencia.repositorio_mudou_durante_a_run | false | VERIFICADO |
| 215 | LESSONS 4 table ur_h30_cetesb_cetesb_full_20261117-221426 commit | 8be599e | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | git_commit[:7] | 8be599e | VERIFICADO |
| 216 | README tables cross-check | A_modelos_por_h.csv == model_comparison.csv (|diff|<=1e-9) | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A_modelos_por_h.csv` | MAE_ARCAL, MASE_ARCAL, skill_vs_ref (base=cetesb) | A_modelos_por_h.csv == model_comparison.csv (|diff|<=1e-9) | VERIFICADO |
| 217 | README tables cross-check | arcal_por_horizonte_dois_alvos.csv == model_comparison.csv (|diff|<=1e-9) | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/arcal_por_horizonte_dois_alvos.csv` | MAE, MASE | arcal_por_horizonte_dois_alvos.csv == model_comparison.csv (|diff|<=1e-9) | VERIFICADO |
| 218 | README protocol: number of folds | 4 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | rows | 4 | VERIFICADO |
| 219 | README protocol: test days per fold | 180 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | n_teste (all rows) | 180 | VERIFICADO |
| 220 | README protocol: validation days | 180 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | n_validacao (all rows) | 180 | VERIFICADO |
| 221 | README protocol: first test date | 2023-01-12 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_inicio (fold 1) | 2023-01-12 | VERIFICADO |
| 222 | README protocol: last test date | 2024-12-31 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_fim (fold 4) | 2024-12-31 | VERIFICADO |
| 223 | REPRODUCIBILITY fold 1 test window | 2023-01-12 to 2023-07-10 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | fold=1, teste_inicio..teste_fim | 2023-01-12 to 2023-07-10 | VERIFICADO |
| 224 | REPRODUCIBILITY fold 2 test window | 2023-07-11 to 2024-01-06 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | fold=2, teste_inicio..teste_fim | 2023-07-11 to 2024-01-06 | VERIFICADO |
| 225 | REPRODUCIBILITY fold 3 test window | 2024-01-07 to 2024-07-04 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | fold=3, teste_inicio..teste_fim | 2024-01-07 to 2024-07-04 | VERIFICADO |
| 226 | REPRODUCIBILITY fold 4 test window | 2024-07-05 to 2024-12-31 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | fold=4, teste_inicio..teste_fim | 2024-07-05 to 2024-12-31 | VERIFICADO |
| 227 | README protocol: seeds | 42 to 46 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | sementes | 42 to 46 | VERIFICADO |
| 228 | README protocol: seed count | 5 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | len(sementes) | 5 | VERIFICADO |
| 229 | README/ARCHITECTURE: number of features (h=1) | 79 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.n_features | 79 | VERIFICADO |
| 230 | ARCHITECTURE: features in block AR | 6 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.AR | 6 | VERIFICADO |
| 231 | ARCHITECTURE: features in block CAL | 8 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.CAL | 8 | VERIFICADO |
| 232 | ARCHITECTURE: features in block METEO | 30 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.METEO | 30 | VERIFICADO |
| 233 | ARCHITECTURE: features in block PM25 | 15 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.PM25 | 15 | VERIFICADO |
| 234 | ARCHITECTURE: features in block POLUENTES | 20 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.POLUENTES | 20 | VERIFICADO |
| 235 | ARCHITECTURE: features in block PM25_MEDIA | 5 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.features_por_bloco.PM25_MEDIA | 5 | VERIFICADO |
| 236 | README: feature sets in the h=1 run | 10 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | len(feature_sets) | 10 | VERIFICADO |
| 237 | README: 7 models active | 7 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | len(modelos) | 7 | VERIFICADO |
| 238 | LESSONS 4 / ARCHITECTURE: XGBoost objective | count:poisson | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | modelos.xgboost.objetivo | count:poisson | VERIFICADO |
| 239 | LESSONS 4: selecionar_objetivo | false | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | modelos.xgboost.selecionar_objetivo | false | VERIFICADO |
| 240 | REPRODUCIBILITY: h=1 run start | 2026-10-22 21:18:34 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | proveniencia.inicio | 2026-10-22 21:18:34 | VERIFICADO |
| 241 | REPRODUCIBILITY: h=1 run end | 23:43:02 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | proveniencia.fim | 23:43:02 | VERIFICADO |
| 242 | REPRODUCIBILITY: numpy version | 2.4.1 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.numpy | 2.4.1 | VERIFICADO |
| 243 | REPRODUCIBILITY: pandas version | 3.0.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.pandas | 3.0.0 | VERIFICADO |
| 244 | REPRODUCIBILITY: xgboost version | 3.2.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.xgboost | 3.2.0 | VERIFICADO |
| 245 | REPRODUCIBILITY: tensorflow version | 2.20.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.tensorflow | 2.20.0 | VERIFICADO |
| 246 | REPRODUCIBILITY: scikit-learn version | 1.8.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.scikit-learn | 1.8.0 | VERIFICADO |
| 247 | REPRODUCIBILITY: statsmodels version | 0.14.6 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.statsmodels | 0.14.6 | VERIFICADO |
| 248 | REPRODUCIBILITY: scipy version | 1.17.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.scipy | 1.17.0 | VERIFICADO |
| 249 | REPRODUCIBILITY: python version | 3.11.0 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.python | 3.11.0 | VERIFICADO |
| 250 | REPRODUCIBILITY: platform | Windows | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | versoes.plataforma (prefix) | Windows | VERIFICADO |
| 251 | data/README: SO2 NaN days in the h=1 run | 2 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.poluentes_descartados.so2_media.n_nan | 2 | VERIFICADO |
| 252 | data/README: SO2 NaN example dates | 2021-01-10, 2021-01-11 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.poluentes_descartados.so2_media.exemplos | 2021-01-10, 2021-01-11 | VERIFICADO |
| 253 | data/README: POLUENTES columns used | pm10, no2, o3, co | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | relatorio_dataset.colunas_poluentes | pm10, no2, o3, co | VERIFICADO |
| 254 | ARCHITECTURE/data/README: gate WARN count (h=1) | 1 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/data_quality.json` | checagens[status==WARN] | 1 | VERIFICADO |
| 255 | ARCHITECTURE/data/README: WARN name | cobertura_cetesb_poluentes | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/data_quality.json` | checagens[WARN].nome | cobertura_cetesb_poluentes | VERIFICADO |
| 256 | ARCHITECTURE/data/README: NaN cells in CETESB pollutants | 88 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/data_quality.json` | checagens[WARN].dados.n_celulas_nan | 88 | VERIFICADO |
| 257 | data/README: NaN cells all in SO2 columns | so2_media, so2_n_estacoes, so2_dt | `data/processed/cetesb_poluentes_daily.csv` | columns with NaN | so2_media, so2_n_estacoes, so2_dt | VERIFICADO |
| 258 | data/README: SO2 days without _dt | 84 | `data/processed/cetesb_poluentes_daily.csv` | so2_dt NaN count | 84 | VERIFICADO |
| 259 | data/README: total NaN cells | 88 | `data/processed/cetesb_poluentes_daily.csv` | sum of NaN | 88 | VERIFICADO |
| 260 | LESSONS 3 / data/README: TabNet months compared | 72 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | dados.alvo.validacao.meses_comparados | 72 | VERIFICADO |
| 261 | LESSONS 3 / data/README: TabNet monthly correlation | 0.999983 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | dados.alvo.validacao.correlacao_mensal | 0.999983 | VERIFICADO |
| 262 | LESSONS 3 / data/README: TabNet bias % | -0.34 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/config.json` | dados.alvo.validacao.vies_sistematico_pct | -0.34 | VERIFICADO |
| 263 | README reading: DM pairs at h=1 | 21 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=1,n_pares | 21 | VERIFICADO |
| 264 | README reading: significant after Holm (all pairs) h=1 | 14 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=1,n_sig_holm | 14 | VERIFICADO |
| 265 | README reading: significant among trained models h=1 | 4 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=1,n_sig_entre_modelos | 4 | VERIFICADO |
| 266 | README reading: all four involve GAM-NB | xgboost − gam_nb; sarimax − gam_nb; lstm − gam_nb; ingarch_nb − gam_nb | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=1,sig_entre_modelos | xgboost − gam_nb; sarimax − gam_nb; lstm − gam_nb; ingarch_nb − gam_nb | VERIFICADO |
| 267 | README reading: nominal leader cetesb h=1 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=1,lider | xgboost | VERIFICADO |
| 268 | README reading: nominal leader cetesb h=5 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=5,lider | xgboost | VERIFICADO |
| 269 | README reading: nominal leader cetesb h=7 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=7,lider | xgboost | VERIFICADO |
| 270 | README reading: nominal leader cetesb h=15 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=15,lider | xgboost | VERIFICADO |
| 271 | README reading: nominal leader cetesb h=30 | sarimax | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=cetesb,h=30,lider | sarimax | VERIFICADO |
| 272 | README reading: nominal leader urgencia h=1 | sarimax | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=urgencia,h=1,lider | sarimax | VERIFICADO |
| 273 | README reading: nominal leader urgencia h=5 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=urgencia,h=5,lider | xgboost | VERIFICADO |
| 274 | README reading: nominal leader urgencia h=7 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=urgencia,h=7,lider | xgboost | VERIFICADO |
| 275 | README reading: nominal leader urgencia h=15 | xgboost | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=urgencia,h=15,lider | xgboost | VERIFICADO |
| 276 | README reading: nominal leader urgencia h=30 | sarimax | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/A2_dm_modelos_por_h.csv` | base=urgencia,h=30,lider | sarimax | VERIFICADO |
| 277 | README reading: lowest MAE total h=1 | XGBoost | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 278 | README reading: lowest MAE total h=5 | XGBoost | `results/runs/mh_h5_cetesb_cetesb_full_20261110-211453/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 279 | README reading: lowest MAE total h=7 | XGBoost | `results/runs/mh_h7_cetesb_cetesb_full_20261111-030322/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 280 | README reading: lowest MAE total h=15 | XGBoost | `results/runs/mh_h15_cetesb_cetesb_full_20261111-070926/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 281 | README reading: lowest MAE total h=30 | SARIMAX | `results/runs/mh_h30_cetesb_cetesb_full_20261113-104814/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | SARIMAX | VERIFICADO |
| 282 | README reading: lowest MAE urgencia h=1 | SARIMAX | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | SARIMAX | VERIFICADO |
| 283 | README reading: lowest MAE urgencia h=5 | XGBoost | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 284 | README reading: lowest MAE urgencia h=7 | XGBoost | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 285 | README reading: lowest MAE urgencia h=15 | XGBoost | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | XGBoost | VERIFICADO |
| 286 | README reading: lowest MAE urgencia h=30 | SARIMAX | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/model_comparison.csv` | argmin MAE_medio over trained models, AR_CAL | SARIMAX | VERIFICADO |
| 287 | README reading: ablation contrasts in the 10 runs | 500 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | rows with base in (cetesb, urgencia) | 500 | VERIFICADO |
| 288 | README reading: significant after Holm | 59 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 | 59 | VERIFICADO |
| 289 | README reading: significant with covariate worse | 53 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 and DM > 0 | 53 | VERIFICADO |
| 290 | README reading: significant with covariate better | 6 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 and DM < 0 | 6 | VERIFICADO |
| 291 | README reading: total h=1 significant contrasts | 7 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=1,p_holm<0.05 | 7 | VERIFICADO |
| 292 | README reading: total h=1 contrasts with covariate better | 0 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=1,p_holm<0.05 and DM<0 | 0 | VERIFICADO |
| 293 | README reading: ablation contrasts per model | 10 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | nunique(contraste) | 10 | VERIFICADO |
| 294 | README reading: p Holm urgencia h=1 ablacao_sarimax H2_media_sem_meteo | 0.005 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=H2_media_sem_meteo,p_holm | 0.0049108177199466 | VERIFICADO |
| 295 | README reading: p Holm urgencia h=1 ablacao_sarimax POLUENTES_sem_meteo | 0.014 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=POLUENTES_sem_meteo,p_holm | 0.0141556291920838 | VERIFICADO |
| 296 | README reading: p Holm urgencia h=15 ablacao_xgboost POLUENTES_com_meteo | 0.001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=15,familia=ablacao_xgboost,contraste=POLUENTES_com_meteo,p_holm | 0.0009194373719768 | VERIFICADO |
| 297 | README reading: p Holm cetesb h=7 ablacao_lstm H2_media_com_meteo | 0.001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0012874477281496 | VERIFICADO |
| 298 | README reading: p Holm urgencia h=5 ablacao_lstm H2_media_com_meteo | 0.007 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=5,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0067240168712517 | VERIFICADO |
| 299 | README reading: p Holm urgencia h=7 ablacao_lstm H2_media_com_meteo | 0.026 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0259100754499556 | VERIFICADO |
| 300 | README/LESSONS 1: XGBoost MAE Saturday (total) | 33.31 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_sab | 33.30770688843958 | VERIFICADO |
| 301 | README/LESSONS 1: XGBoost MAE other days (total) | 16.09 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_demais | 16.09414465361708 | VERIFICADO |
| 302 | README/LESSONS 1: XGBoost ratio (total) | 2.07 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,razao | 2.069554338257662 | VERIFICADO |
| 303 | README/LESSONS 1: SARIMAX MAE Saturday (total) | 37.08 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=SARIMAX,MAE_sab | 37.08164383154383 | VERIFICADO |
| 304 | README/LESSONS 1: SARIMAX MAE other days (total) | 15.89 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=SARIMAX,MAE_demais | 15.891406209173018 | VERIFICADO |
| 305 | README/LESSONS 1: SARIMAX ratio (total) | 2.33 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=SARIMAX,razao | 2.333440058321531 | VERIFICADO |
| 306 | README/LESSONS 1: LSTM MAE Saturday (total) | 33.79 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=LSTM,MAE_sab | 33.79374826672008 | VERIFICADO |
| 307 | README/LESSONS 1: LSTM MAE other days (total) | 16.54 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=LSTM,MAE_demais | 16.54355473696123 | VERIFICADO |
| 308 | README/LESSONS 1: LSTM ratio (total) | 2.04 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=LSTM,razao | 2.0427138425829887 | VERIFICADO |
| 309 | README/LESSONS 1: INGARCH-NB MAE Saturday (total) | 35.86 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=INGARCH-NB,MAE_sab | 35.86477785821118 | VERIFICADO |
| 310 | README/LESSONS 1: INGARCH-NB MAE other days (total) | 16.82 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=INGARCH-NB,MAE_demais | 16.821665410370766 | VERIFICADO |
| 311 | README/LESSONS 1: INGARCH-NB ratio (total) | 2.13 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=INGARCH-NB,razao | 2.1320586864187714 | VERIFICADO |
| 312 | README/LESSONS 1: GAM-NB MAE Saturday (total) | 43.72 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=GAM-NB,MAE_sab | 43.71834711455449 | VERIFICADO |
| 313 | README/LESSONS 1: GAM-NB MAE other days (total) | 18.26 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=GAM-NB,MAE_demais | 18.263772353190795 | VERIFICADO |
| 314 | README/LESSONS 1: GAM-NB ratio (total) | 2.39 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=GAM-NB,razao | 2.393719450128638 | VERIFICADO |
| 315 | README/LESSONS 1: XGBoost MAE Saturday (urgent) | 13.64 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia,modelo=XGBoost,MAE_sab | 13.638909238056073 | VERIFICADO |
| 316 | README/LESSONS 1: XGBoost MAE other days (urgent) | 15.08 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia,modelo=XGBoost,MAE_demais | 15.084299645818032 | VERIFICADO |
| 317 | README/LESSONS 1: XGBoost ratio (urgent) | 0.90 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia,modelo=XGBoost,razao | 0.9041791503947828 | VERIFICADO |
| 318 | LESSONS 1: every urgent ratio below 1 | True | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia, razao < 1 for all trained models | True | VERIFICADO |
| 319 | LESSONS 1: Saturdays in the test set | 103 of 720 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/saida.txt` | section C 'sábados: N de M' | 103 of 720 | VERIFICADO |
| 320 | LESSONS 1: CNES 2091550 elective Saturdays 2019 | 244 | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2019,eletivas_sabado | 244 | VERIFICADO |
| 321 | LESSONS 1: CNES 2091550 elective Saturdays 2021 | 302 | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2021,eletivas_sabado | 302 | VERIFICADO |
| 322 | LESSONS 1: CNES 2091550 elective Saturdays 2022 | 1,291 | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2022,eletivas_sabado | 1291 | VERIFICADO |
| 323 | LESSONS 1: CNES 2091550 elective Saturdays 2023 | 1,562 | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2023,eletivas_sabado | 1562 | VERIFICADO |
| 324 | LESSONS 1: CNES 2091550 elective Saturdays 2024 | 1,343 | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2024,eletivas_sabado | 1343 | VERIFICADO |
| 325 | LESSONS 1: CNES 2091550 total == eletivas 2022 | True | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2022,total==eletivas | True | VERIFICADO |
| 326 | LESSONS 1: CNES 2091550 total == eletivas 2023 | True | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2023,total==eletivas | True | VERIFICADO |
| 327 | LESSONS 1: CNES 2091550 total == eletivas 2024 | True | `notebooks/dados_painel/estabelecimentos_ano.csv` | CNES=2091550,ano=2024,total==eletivas | True | VERIFICADO |
| 328 | LESSONS 1: CEMA slice admissions | 6,870 | `notebooks/dados_painel/perfil.csv` | recorte='Eletiva, sábado, CNES 2091550',internacoes | 6870.0 | VERIFICADO |
| 329 | LESSONS 1: CEMA slice median age | 9 | `notebooks/dados_painel/perfil.csv` | same row, idade_mediana | 9.0 | VERIFICADO |
| 330 | LESSONS 1: CEMA slice % under 15 | 69.8 | `notebooks/dados_painel/perfil.csv` | same row, pct_menor_15 | 69.8 | VERIFICADO |
| 331 | LESSONS 1: CEMA slice median stay | 0 | `notebooks/dados_painel/perfil.csv` | same row, permanencia_mediana | 0.0 | VERIFICADO |
| 332 | LESSONS 1: CEMA slice % stay <= 1 day | 99.7 | `notebooks/dados_painel/perfil.csv` | same row, pct_permanencia_ate_1_dia | 99.7 | VERIFICADO |
| 333 | LESSONS 1: CEMA slice % deaths | 0.0 | `notebooks/dados_painel/perfil.csv` | same row, pct_obito | 0.0 | VERIFICADO |
| 334 | LESSONS 1: non-elective median stay | 5 | `notebooks/dados_painel/perfil.csv` | recorte='Não eletiva',permanencia_mediana | 5.0 | VERIFICADO |
| 335 | LESSONS 1: non-elective % deaths | 10.2 | `notebooks/dados_painel/perfil.csv` | recorte='Não eletiva',pct_obito | 10.2 | VERIFICADO |
| 336 | LESSONS 1: J30-J39 total | 39,243 | `notebooks/dados_painel/grupos_cid.csv` | grupo J30–J39,total | 39243 | VERIFICADO |
| 337 | LESSONS 1: J30-J39 elective | 35,958 | `notebooks/dados_painel/grupos_cid.csv` | grupo J30–J39,eletivas | 35958 | VERIFICADO |
| 338 | LESSONS 1: J30-J39 elective at CEMA | 11,206 | `notebooks/dados_painel/grupos_cid.csv` | grupo J30–J39,eletivas_cema | 11206 | VERIFICADO |
| 339 | LESSONS 1: J12-J18 elective | 4,811 | `notebooks/dados_painel/grupos_cid.csv` | grupo J12–J18,eletivas | 4811 | VERIFICADO |
| 340 | LESSONS 1: J12-J18 total | 153,309 | `notebooks/dados_painel/grupos_cid.csv` | grupo J12–J18,total | 153309 | VERIFICADO |
| 341 | data/README: Saturday panel last date | 2026-02-28 | `notebooks/dados_painel/diario.csv` | max(data) | 2026-02-28 | VERIFICADO |
| 342 | LESSONS 1: elective fraction 2019-2024 within 12% to 14% | True | `notebooks/dados_painel/diario.csv` | sum(eletivo)/sum(total) per year 2019..2024 | True | VERIFICADO |
| 343 | data/README/LESSONS 3: distinct admissions (total) | 303,295 | `data/processed/sih_daily_lookahead.meta.json` | total_aih_distintas | 303295 | VERIFICADO |
| 344 | data/README/LESSONS 3: duplicates across monthly files | 77 | `data/processed/sih_daily_lookahead.meta.json` | duplicatas_entre_competencias | 77 | VERIFICADO |
| 345 | data/README/LESSONS 3: records outside period | 29,700 | `data/processed/sih_daily_lookahead.meta.json` | registros_fora_do_periodo | 29700 | VERIFICADO |
| 346 | data/README: invalid dates | 0 | `data/processed/sih_daily_lookahead.meta.json` | dt_inter_invalidas | 0 | VERIFICADO |
| 347 | data/README: days with zero | 0 | `data/processed/sih_daily_lookahead.meta.json` | dias_com_zero | 0 | VERIFICADO |
| 348 | data/README: days | 2,192 | `data/processed/sih_daily_lookahead.meta.json` | dias | 2192 | VERIFICADO |
| 349 | data/README/REPRODUCIBILITY: monthly files read | 78 | `data/processed/sih_daily_lookahead.meta.json` | len(competencias) | 78 | VERIFICADO |
| 350 | data/README: administrative period | 2019-01 to 2025-06 | `data/processed/sih_daily_lookahead.meta.json` | periodo_administrativo | 2019-01 to 2025-06 | VERIFICADO |
| 351 | data/README: look-ahead months | 6 | `data/processed/sih_daily_lookahead.meta.json` | look_ahead_competencias | 6 | VERIFICADO |
| 352 | data/README: look-ahead justification 99.8% | 99,8% | `data/processed/sih_daily_lookahead.meta.json` | look_ahead_justificativa (substring) | 99,8% | VERIFICADO |
| 353 | data/README: annual totals (total) | 52,335; 39,482; 43,941; 52,718; 56,640; 58,179 | `data/processed/sih_daily_lookahead.meta.json` | totais_anuais 2019..2024 | 52,335; 39,482; 43,941; 52,718; 56,640; 58,179 | VERIFICADO |
| 354 | data/README/LESSONS 1: urgent admissions kept | 263,399 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | total_aih_distintas | 263399 | VERIFICADO |
| 355 | data/README/LESSONS 1: elective excluded | 39,896 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | filtro_carater_internacao.aih_excluidas_carater | 39896 | VERIFICADO |
| 356 | data/README: CAR_INT codes accepted | 02, 03, 04, 05, 06 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | filtro_carater_internacao.codigos_aceitos | 02, 03, 04, 05, 06 | VERIFICADO |
| 357 | data/README: only codes 01 and 02 occur | 01, 02 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | filtro_carater_internacao.aih_por_car_int_primeira_ocorrencia (keys) | 01, 02 | VERIFICADO |
| 358 | data/README: annual totals (urgent) | 45,197; 34,734; 38,445; 46,159; 48,893; 49,971 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | totais_anuais 2019..2024 | 45,197; 34,734; 38,445; 46,159; 48,893; 49,971 | VERIFICADO |
| 359 | data/README: urgent target built on | 2026-11-16 | `data/processed/sih_daily_lookahead_urgencia.meta.json` | extraido_em[:10] | 2026-11-16 | VERIFICADO |
| 360 | data/README: sih_daily_lookahead.parquet rows | 2,192 | `data/processed/sih_daily_lookahead.parquet` | len | 2192 | VERIFICADO |
| 361 | data/README: sih_daily_lookahead.parquet columns | internacoes, linhas_brutas | `data/processed/sih_daily_lookahead.parquet` | columns | internacoes, linhas_brutas | VERIFICADO |
| 362 | data/README: sih_daily_lookahead.parquet period | 2019-01-01 to 2024-12-31 | `data/processed/sih_daily_lookahead.parquet` | index min..max | 2019-01-01 to 2024-12-31 | VERIFICADO |
| 363 | data/README: sih_daily_lookahead_urgencia.parquet rows | 2,192 | `data/processed/sih_daily_lookahead_urgencia.parquet` | len | 2192 | VERIFICADO |
| 364 | data/README: sih_daily_lookahead_urgencia.parquet columns | internacoes, linhas_brutas | `data/processed/sih_daily_lookahead_urgencia.parquet` | columns | internacoes, linhas_brutas | VERIFICADO |
| 365 | data/README: sih_daily_lookahead_urgencia.parquet period | 2019-01-01 to 2024-12-31 | `data/processed/sih_daily_lookahead_urgencia.parquet` | index min..max | 2019-01-01 to 2024-12-31 | VERIFICADO |
| 366 | data/README: pm25 stations | 18 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[pm25].estacoes | 18 | VERIFICADO |
| 367 | data/README: pm25 mean stations/day | 10.6 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[pm25].n_est_medio | 10.6 | VERIFICADO |
| 368 | data/README: pm10 stations | 14 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[pm10].estacoes | 14 | VERIFICADO |
| 369 | data/README: pm10 mean stations/day | 9.5 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[pm10].n_est_medio | 9.47 | VERIFICADO |
| 370 | data/README: no2 stations | 10 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[no2].estacoes | 10 | VERIFICADO |
| 371 | data/README: no2 mean stations/day | 7.3 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[no2].n_est_medio | 7.3 | VERIFICADO |
| 372 | data/README: o3 stations | 15 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[o3].estacoes | 15 | VERIFICADO |
| 373 | data/README: o3 mean stations/day | 12.8 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[o3].n_est_medio | 12.83 | VERIFICADO |
| 374 | data/README: co stations | 9 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[co].estacoes | 9 | VERIFICADO |
| 375 | data/README: co mean stations/day | 7.4 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[co].n_est_medio | 7.38 | VERIFICADO |
| 376 | data/README: so2 stations | 7 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[so2].estacoes | 7 | VERIFICADO |
| 377 | data/README: so2 mean stations/day | 3.1 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[so2].n_est_medio | 3.12 | VERIFICADO |
| 378 | data/README: SO2 days with mean | 2,190 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[so2].dias | 2190 | VERIFICADO |
| 379 | data/README: SO2 days with _dt | 2,108 | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[so2].dias_com_dt | 2108 | VERIFICADO |
| 380 | data/README: other pollutants cover 2,192 days | True | `data/processed/cetesb_poluentes_daily.meta.json` | por_poluente[*].dias == 2192 except so2 | True | VERIFICADO |
| 381 | data/README: pollutant export files used | 191 | `data/processed/cetesb_poluentes_daily.meta.json` | coleta.arquivos_usados | 191 | VERIFICADO |
| 382 | data/README: pollutant export files ignored | 14 | `data/processed/cetesb_poluentes_daily.meta.json` | coleta.arquivos_ignorados | 14 | VERIFICADO |
| 383 | data/README: stations outside municipality excluded | 21 | `data/processed/cetesb_poluentes_daily.meta.json` | len(coleta.estacoes_fora_do_municipio) | 21 | VERIFICADO |
| 384 | data/README: hourly records before dedup | 3,954,672 | `data/processed/cetesb_poluentes_daily.meta.json` | coleta.registros_antes_dedup | 3954672 | VERIFICADO |
| 385 | data/README: hourly records after dedup | 3,722,808 | `data/processed/cetesb_poluentes_daily.meta.json` | coleta.registros_apos_dedup | 3722808 | VERIFICADO |
| 386 | data/README: daily rule 18 of 24 hours | >= 18 de 24 | `data/processed/cetesb_poluentes_daily.meta.json` | regra_diaria (substring) | >= 18 de 24 | VERIFICADO |
| 387 | data/README: D_t rule needs 2 stations | >= 2 | `data/processed/cetesb_poluentes_daily.meta.json` | regra_dt (substring) | >= 2 | VERIFICADO |
| 388 | data/README: meteo temp stations | 6 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[temp].estacoes | 6 | VERIFICADO |
| 389 | data/README: meteo temp mean stations/day | 4.2 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[temp].n_est_medio | 4.17 | VERIFICADO |
| 390 | data/README: meteo temp days | 2,192 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[temp].dias | 2192 | VERIFICADO |
| 391 | data/README: meteo ur stations | 6 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[ur].estacoes | 6 | VERIFICADO |
| 392 | data/README: meteo ur mean stations/day | 3.6 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[ur].n_est_medio | 3.6 | VERIFICADO |
| 393 | data/README: meteo ur days | 2,192 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[ur].dias | 2192 | VERIFICADO |
| 394 | data/README: meteo vv stations | 10 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[vv].estacoes | 10 | VERIFICADO |
| 395 | data/README: meteo vv mean stations/day | 7.5 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[vv].n_est_medio | 7.47 | VERIFICADO |
| 396 | data/README: meteo vv days | 2,192 | `data/processed/cetesb_meteo_daily.meta.json` | por_variavel[vv].dias | 2192 | VERIFICADO |
| 397 | data/README: meteo temp entries dropped by coverage | 524 | `data/processed/cetesb_meteo_daily.meta.json` | dias_descartados_por_cobertura.temp | 524 | VERIFICADO |
| 398 | data/README: meteo ur entries dropped by coverage | 454 | `data/processed/cetesb_meteo_daily.meta.json` | dias_descartados_por_cobertura.ur | 454 | VERIFICADO |
| 399 | data/README: meteo vv entries dropped by coverage | 483 | `data/processed/cetesb_meteo_daily.meta.json` | dias_descartados_por_cobertura.vv | 483 | VERIFICADO |
| 400 | data/README: meteo export files used | 54 | `data/processed/cetesb_meteo_daily.meta.json` | coleta.arquivos_usados | 54 | VERIFICADO |
| 401 | data/README: meteo export files ignored | 14 | `data/processed/cetesb_meteo_daily.meta.json` | coleta.arquivos_ignorados | 14 | VERIFICADO |
| 402 | data/README: meteo metropolitan stations excluded | 5 | `data/processed/cetesb_meteo_daily.meta.json` | len(coleta.estacoes_fora_do_recorte) | 5 | VERIFICADO |
| 403 | data/README: meteo NaN cells | 0 | `data/processed/cetesb_meteo_daily.csv` | sum of NaN | 0 | VERIFICADO |
| 404 | data/README: meteo columns | data, temp_media, temp_n_estacoes, temp_min, temp_max, temp_amplitude, ur_media, ur_n_estacoes, vv_media, vv_n_estacoes | `data/processed/cetesb_meteo_daily.csv` | columns | data, temp_media, temp_n_estacoes, temp_min, temp_max, temp_amplitude, ur_media, ur_n_estacoes, vv_media, vv_n_estacoes | VERIFICADO |
| 405 | data/README/LESSONS 2: CAMS rows | 2,192 | `data/processed/cams_daily_v2.csv` | len | 2192 | VERIFICADO |
| 406 | data/README: CAMS NaN cells | 0 | `data/processed/cams_daily_v2.csv` | sum of NaN | 0 | VERIFICADO |
| 407 | data/README/LESSONS 2: CAMS days with n_obs=8 | 2,191 | `data/processed/cams_daily_v2.csv` | n_obs value_counts[8] | 2191 | VERIFICADO |
| 408 | data/README/LESSONS 2: CAMS days with n_obs=7 | 1 | `data/processed/cams_daily_v2.csv` | n_obs value_counts[7] | 1 | VERIFICADO |
| 409 | data/README: CAMS columns | data, d2m, pm10, pm2p5, sp, t2m, u10, v10, t2m_c, d2m_c, rh, ws10, n_obs | `data/processed/cams_daily_v2.csv` | columns | data, d2m, pm10, pm2p5, sp, t2m, u10, v10, t2m_c, d2m_c, rh, ws10, n_obs | VERIFICADO |
| 410 | data/README: CAMS not used as feature source in shown runs | cetesb/cetesb | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | fonte_pm25/fonte_meteo | cetesb/cetesb | VERIFICADO |
| 411 | data/README: stations in municipality | 23 | `data/cetesb/estacoes_municipio_sp.csv` | rows | 23 | VERIFICADO |
| 412 | data/README: stations with PM2.5 in registry | 19 | `data/cetesb/estacoes_municipio_sp.csv` | mede_pm25 == True | 19 | VERIFICADO |
| 413 | data/README: disponibilidade_qualar stations | 19 | `data/cetesb/disponibilidade_qualar.csv` | nunique(codigo_qualar) | 19 | VERIFICADO |
| 414 | data/README: disponibilidade_qualar parameters | MP2.5, MP10, NO2, O3, CO, SO2 | `data/cetesb/disponibilidade_qualar.csv` | unique(parametro) | MP2.5, MP10, NO2, O3, CO, SO2 | VERIFICADO |
| 415 | REPRODUCIBILITY: DM recomputed metrics max diff about 1e-14 | < 1e-13 | `results/testes_dm/TESTES_DM_h1_v02_cetesb_cetesb_classicos_full_20261022-211834/validacao_metricas.json` | max of all scientific-notation diffs | < 1e-13 | VERIFICADO |
| 416 | ARCHITECTURE: SARIMAX range guard factor | 5 | `src/models/sarimax_model.py` | FATOR_FAIXA | 5.0 | VERIFICADO |
| 417 | ARCHITECTURE: SARIMAX degenerate sigma2 fraction | 1e-3 | `src/models/sarimax_model.py` | FRACAO_SIGMA2_MIN | 1e-3 | VERIFICADO |
| 418 | README: test count in the suite | 166 passed (uv run pytest -q, 2026-11-23) | `uv run pytest -q` | dots in -q output | 166 passed (uv run pytest -q, 2026-11-23) | VERIFICADO |
| 419 | README.md: results table total (all 35 MAE/MASE cells) identical to tabela_readme.py --lang en | verbatim | `docs/scripts/tabela_readme.py --lang en` | tabela_md(total) | verbatim | VERIFICADO |
| 420 | README.md: runs table total (ids, commits, clean tree, predictions) identical to tabela_readme.py --lang en | verbatim | `docs/scripts/tabela_readme.py --lang en` | tabela_runs_md(total) | verbatim | VERIFICADO |
| 421 | README.pt-BR.md: results table total (all 35 MAE/MASE cells) identical to tabela_readme.py --lang pt | verbatim | `docs/scripts/tabela_readme.py --lang pt` | tabela_md(total) | verbatim | VERIFICADO |
| 422 | README.pt-BR.md: runs table total (ids, commits, clean tree, predictions) identical to tabela_readme.py --lang pt | verbatim | `docs/scripts/tabela_readme.py --lang pt` | tabela_runs_md(total) | verbatim | VERIFICADO |
| 423 | README.md: results table urgencia (all 35 MAE/MASE cells) identical to tabela_readme.py --lang en | verbatim | `docs/scripts/tabela_readme.py --lang en` | tabela_md(urgencia) | verbatim | VERIFICADO |
| 424 | README.md: urgent run id h=1 present in text | ur_h1_cetesb_cetesb_full_20261116-191534 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | run_id | ur_h1_cetesb_cetesb_full_20261116-191534 | VERIFICADO |
| 425 | README.md: urgent run id h=5 present in text | ur_h5_cetesb_cetesb_full_20261116-222823 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | run_id | ur_h5_cetesb_cetesb_full_20261116-222823 | VERIFICADO |
| 426 | README.md: urgent run id h=7 present in text | ur_h7_cetesb_cetesb_full_20261117-073926 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | run_id | ur_h7_cetesb_cetesb_full_20261117-073926 | VERIFICADO |
| 427 | README.md: urgent run id h=15 present in text | ur_h15_cetesb_cetesb_full_20261117-190532 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | run_id | ur_h15_cetesb_cetesb_full_20261117-190532 | VERIFICADO |
| 428 | README.md: urgent run id h=30 present in text | ur_h30_cetesb_cetesb_full_20261117-221426 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | run_id | ur_h30_cetesb_cetesb_full_20261117-221426 | VERIFICADO |
| 429 | README.pt-BR.md: results table urgencia (all 35 MAE/MASE cells) identical to tabela_readme.py --lang pt | verbatim | `docs/scripts/tabela_readme.py --lang pt` | tabela_md(urgencia) | verbatim | VERIFICADO |
| 430 | README.pt-BR.md: urgent run id h=1 present in text | ur_h1_cetesb_cetesb_full_20261116-191534 | `results/runs/ur_h1_cetesb_cetesb_full_20261116-191534/manifest.json` | run_id | ur_h1_cetesb_cetesb_full_20261116-191534 | VERIFICADO |
| 431 | README.pt-BR.md: urgent run id h=5 present in text | ur_h5_cetesb_cetesb_full_20261116-222823 | `results/runs/ur_h5_cetesb_cetesb_full_20261116-222823/manifest.json` | run_id | ur_h5_cetesb_cetesb_full_20261116-222823 | VERIFICADO |
| 432 | README.pt-BR.md: urgent run id h=7 present in text | ur_h7_cetesb_cetesb_full_20261117-073926 | `results/runs/ur_h7_cetesb_cetesb_full_20261117-073926/manifest.json` | run_id | ur_h7_cetesb_cetesb_full_20261117-073926 | VERIFICADO |
| 433 | README.pt-BR.md: urgent run id h=15 present in text | ur_h15_cetesb_cetesb_full_20261117-190532 | `results/runs/ur_h15_cetesb_cetesb_full_20261117-190532/manifest.json` | run_id | ur_h15_cetesb_cetesb_full_20261117-190532 | VERIFICADO |
| 434 | README.pt-BR.md: urgent run id h=30 present in text | ur_h30_cetesb_cetesb_full_20261117-221426 | `results/runs/ur_h30_cetesb_cetesb_full_20261117-221426/manifest.json` | run_id | ur_h30_cetesb_cetesb_full_20261117-221426 | VERIFICADO |
| 435 | README.md prose: XGBoost MAE Saturday (total, h=1) | 33.31 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_sab | 33.30770688843958 | VERIFICADO |
| 436 | README.md prose: '33.31' present | present | `README.md` | text search | present | VERIFICADO |
| 437 | README.pt-BR.md prose: XGBoost MAE Saturday (total, h=1) | 33,31 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_sab (vírgula decimal) | 33,31 | VERIFICADO |
| 438 | README.pt-BR.md prose: '33,31' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 439 | README.md prose: XGBoost MAE other days (total, h=1) | 16.09 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_demais | 16.09414465361708 | VERIFICADO |
| 440 | README.md prose: '16.09' present | present | `README.md` | text search | present | VERIFICADO |
| 441 | README.pt-BR.md prose: XGBoost MAE other days (total, h=1) | 16,09 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,MAE_demais (vírgula decimal) | 16,09 | VERIFICADO |
| 442 | README.pt-BR.md prose: '16,09' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 443 | README.md prose: XGBoost Saturday ratio (total) | 2.07 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,razao | 2.069554338257662 | VERIFICADO |
| 444 | README.md prose: '2.07' present | present | `README.md` | text search | present | VERIFICADO |
| 445 | README.pt-BR.md prose: XGBoost Saturday ratio (total) | 2,07 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=XGBoost,razao (vírgula decimal) | 2,07 | VERIFICADO |
| 446 | README.pt-BR.md prose: '2,07' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 447 | README.md prose: XGBoost Saturday ratio (urgent) | 0.90 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia,modelo=XGBoost,razao | 0.9041791503947828 | VERIFICADO |
| 448 | README.md prose: '0.90' present | present | `README.md` | text search | present | VERIFICADO |
| 449 | README.pt-BR.md prose: XGBoost Saturday ratio (urgent) | 0,90 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=urgencia,modelo=XGBoost,razao (vírgula decimal) | 0,90 | VERIFICADO |
| 450 | README.pt-BR.md prose: '0,90' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 451 | README.md prose: smallest Saturday ratio among trained models (total, LSTM) | 2.04 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, min razao without Naïve (LSTM) | 2.0427138425829887 | VERIFICADO |
| 452 | README.md prose: '2.04' present | present | `README.md` | text search | present | VERIFICADO |
| 453 | README.pt-BR.md prose: smallest Saturday ratio among trained models (total, LSTM) | 2,04 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, min razao without Naïve (LSTM) (vírgula decimal) | 2,04 | VERIFICADO |
| 454 | README.pt-BR.md prose: '2,04' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 455 | README.md prose: largest Saturday ratio among trained models (total, GAM-NB) | 2.39 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, max razao without Naïve (GAM-NB) | 2.393719450128638 | VERIFICADO |
| 456 | README.md prose: '2.39' present | present | `README.md` | text search | present | VERIFICADO |
| 457 | README.pt-BR.md prose: largest Saturday ratio among trained models (total, GAM-NB) | 2,39 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, max razao without Naïve (GAM-NB) (vírgula decimal) | 2,39 | VERIFICADO |
| 458 | README.pt-BR.md prose: '2,39' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 459 | README.md prose: Naïve Saturday ratio (total) | 1.30 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=Naïve,razao | 1.300335818869305 | VERIFICADO |
| 460 | README.md prose: '1.30' present | present | `README.md` | text search | present | VERIFICADO |
| 461 | README.pt-BR.md prose: Naïve Saturday ratio (total) | 1,30 | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total,modelo=Naïve,razao (vírgula decimal) | 1,30 | VERIFICADO |
| 462 | README.pt-BR.md prose: '1,30' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 463 | README prose: Saturday MAE above other days for every model in the file (total) | all | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, MAE_sab > MAE_demais | all | VERIFICADO |
| 464 | README prose: models in erro_sabado_h1.csv (five trained + Naïve, no Seasonal Naïve) | GAM-NB, INGARCH-NB, LSTM, Naïve, SARIMAX, XGBoost | `results/numeros_texto_urgencia/NUMEROS_TEXTO_URGENCIA_V02_20261118/erro_sabado_h1.csv` | alvo=total, modelo (sorted) | GAM-NB, INGARCH-NB, LSTM, Naïve, SARIMAX, XGBoost | VERIFICADO |
| 465 | README.md prose: p Holm urgencia h=1 ablacao_sarimax H2_media_sem_meteo | 0.005 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=H2_media_sem_meteo,p_holm | 0.0049108177199466 | VERIFICADO |
| 466 | README.md prose: '0.005' present | present | `README.md` | text search | present | VERIFICADO |
| 467 | README.pt-BR.md prose: p Holm urgencia h=1 ablacao_sarimax H2_media_sem_meteo | 0,005 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=H2_media_sem_meteo,p_holm (vírgula decimal) | 0,005 | VERIFICADO |
| 468 | README.pt-BR.md prose: '0,005' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 469 | README.md prose: p Holm urgencia h=1 ablacao_sarimax POLUENTES_sem_meteo | 0.014 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=POLUENTES_sem_meteo,p_holm | 0.0141556291920838 | VERIFICADO |
| 470 | README.md prose: '0.014' present | present | `README.md` | text search | present | VERIFICADO |
| 471 | README.pt-BR.md prose: p Holm urgencia h=1 ablacao_sarimax POLUENTES_sem_meteo | 0,014 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=1,familia=ablacao_sarimax,contraste=POLUENTES_sem_meteo,p_holm (vírgula decimal) | 0,014 | VERIFICADO |
| 472 | README.pt-BR.md prose: '0,014' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 473 | README.md prose: p Holm urgencia h=15 ablacao_xgboost POLUENTES_com_meteo | 0.001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=15,familia=ablacao_xgboost,contraste=POLUENTES_com_meteo,p_holm | 0.0009194373719768 | VERIFICADO |
| 474 | README.md prose: '0.001' present | present | `README.md` | text search | present | VERIFICADO |
| 475 | README.pt-BR.md prose: p Holm urgencia h=15 ablacao_xgboost POLUENTES_com_meteo | 0,001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=15,familia=ablacao_xgboost,contraste=POLUENTES_com_meteo,p_holm (vírgula decimal) | 0,001 | VERIFICADO |
| 476 | README.pt-BR.md prose: '0,001' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 477 | README.md prose: p Holm cetesb h=7 ablacao_lstm H2_media_com_meteo | 0.001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0012874477281496 | VERIFICADO |
| 478 | README.md prose: '0.001' present | present | `README.md` | text search | present | VERIFICADO |
| 479 | README.pt-BR.md prose: p Holm cetesb h=7 ablacao_lstm H2_media_com_meteo | 0,001 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm (vírgula decimal) | 0,001 | VERIFICADO |
| 480 | README.pt-BR.md prose: '0,001' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 481 | README.md prose: p Holm urgencia h=5 ablacao_lstm H2_media_com_meteo | 0.007 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=5,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0067240168712517 | VERIFICADO |
| 482 | README.md prose: '0.007' present | present | `README.md` | text search | present | VERIFICADO |
| 483 | README.pt-BR.md prose: p Holm urgencia h=5 ablacao_lstm H2_media_com_meteo | 0,007 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=5,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm (vírgula decimal) | 0,007 | VERIFICADO |
| 484 | README.pt-BR.md prose: '0,007' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 485 | README.md prose: p Holm urgencia h=7 ablacao_lstm H2_media_com_meteo | 0.026 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm | 0.0259100754499556 | VERIFICADO |
| 486 | README.md prose: '0.026' present | present | `README.md` | text search | present | VERIFICADO |
| 487 | README.pt-BR.md prose: p Holm urgencia h=7 ablacao_lstm H2_media_com_meteo | 0,026 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=urgencia,h=7,familia=ablacao_lstm,contraste=H2_media_com_meteo,p_holm (vírgula decimal) | 0,026 | VERIFICADO |
| 488 | README.pt-BR.md prose: '0,026' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 489 | README.md prose: ablation contrasts in the 10 runs | 500 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | rows with base in (cetesb, urgencia) | 500 | VERIFICADO |
| 490 | README.md prose: '500' present | present | `README.md` | text search | present | VERIFICADO |
| 491 | README.pt-BR.md prose: ablation contrasts in the 10 runs | 500 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | rows with base in (cetesb, urgencia) (milhar com ponto) | 500 | VERIFICADO |
| 492 | README.pt-BR.md prose: '500' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 493 | README.md prose: significant after Holm | 59 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 | 59 | VERIFICADO |
| 494 | README.md prose: '59' present | present | `README.md` | text search | present | VERIFICADO |
| 495 | README.pt-BR.md prose: significant after Holm | 59 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 (milhar com ponto) | 59 | VERIFICADO |
| 496 | README.pt-BR.md prose: '59' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 497 | README.md prose: significant with covariate worse | 53 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 and DM > 0 | 53 | VERIFICADO |
| 498 | README.md prose: '53' present | present | `README.md` | text search | present | VERIFICADO |
| 499 | README.pt-BR.md prose: significant with covariate worse | 53 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | p_holm < 0.05 and DM > 0 (milhar com ponto) | 53 | VERIFICADO |
| 500 | README.pt-BR.md prose: '53' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 501 | README.md prose: total h=1 significant contrasts | 7 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=1,p_holm<0.05 | 7 | VERIFICADO |
| 502 | README.md prose: '7' present | present | `README.md` | text search | present | VERIFICADO |
| 503 | README.pt-BR.md prose: total h=1 significant contrasts | 7 | `results/analise_multihorizonte/ANALISE_MULTIHORIZONTE_V02_20261118/B2_dm_ablacao_por_h.csv` | base=cetesb,h=1,p_holm<0.05 (milhar com ponto) | 7 | VERIFICADO |
| 504 | README.pt-BR.md prose: '7' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 505 | README.md prose: predictions per run | 95,040 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | n_predicoes | 95040 | VERIFICADO |
| 506 | README.md prose: '95,040' present | present | `README.md` | text search | present | VERIFICADO |
| 507 | README.pt-BR.md prose: predictions per run | 95.040 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | n_predicoes (milhar com ponto) | 95.040 | VERIFICADO |
| 508 | README.pt-BR.md prose: '95.040' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 509 | README.md prose: first test date | 2023-01-12 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_inicio (fold 1) | 2023-01-12 | VERIFICADO |
| 510 | README.md prose: '2023-01-12' present | present | `README.md` | text search | present | VERIFICADO |
| 511 | README.pt-BR.md prose: first test date | 2023-01-12 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_inicio (fold 1) | 2023-01-12 | VERIFICADO |
| 512 | README.pt-BR.md prose: '2023-01-12' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 513 | README.md prose: last test date | 2024-12-31 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_fim (fold 4) | 2024-12-31 | VERIFICADO |
| 514 | README.md prose: '2024-12-31' present | present | `README.md` | text search | present | VERIFICADO |
| 515 | README.pt-BR.md prose: last test date | 2024-12-31 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | teste_fim (fold 4) | 2024-12-31 | VERIFICADO |
| 516 | README.pt-BR.md prose: '2024-12-31' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 517 | README.md prose: seeds | 42 to 46 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | sementes | 42 to 46 | VERIFICADO |
| 518 | README.md prose: '42 to 46' present | present | `README.md` | text search | present | VERIFICADO |
| 519 | README.pt-BR.md prose: seeds | 42 a 46 | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/manifest.json` | sementes | 42 a 46 | VERIFICADO |
| 520 | README.pt-BR.md prose: '42 a 46' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 521 | README.md prose: test days per fold | 180 test days | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | n_teste (all rows) | 180 test days | VERIFICADO |
| 522 | README.md prose: '180 test days' present | present | `README.md` | text search | present | VERIFICADO |
| 523 | README.pt-BR.md prose: test days per fold | 180 dias de teste | `results/runs/h1_v02_cetesb_cetesb_classicos_full_20261022-211834/folds.csv` | n_teste (all rows) | 180 dias de teste | VERIFICADO |
| 524 | README.pt-BR.md prose: '180 dias de teste' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 525 | README.md prose: pytest wall time | 3m52s | `docs/AUDITORIA.md` | tempo medido pelo auditor (2026-11-23) | 3m52s | VERIFICADO |
| 526 | README.md prose: '3m52s' present | present | `README.md` | text search | present | VERIFICADO |
| 527 | README.pt-BR.md prose: pytest wall time | 3m52s | `docs/AUDITORIA.md` | tempo medido pelo auditor (2026-11-23) | 3m52s | VERIFICADO |
| 528 | README.pt-BR.md prose: '3m52s' present | present | `README.pt-BR.md` | text search | present | VERIFICADO |
| 529 | README.md / README.pt-BR.md: same number of ## sections | 7 | `README.pt-BR.md` | count of '## ' lines | 7 | VERIFICADO |
| 530 | README.md / README.pt-BR.md: same number of ### sections | 3 | `README.pt-BR.md` | count of '### ' lines | 3 | VERIFICADO |
| 531 | README.md: every relative path cited exists in the repository | none missing | `README.md` | paths in backticks and links | none missing | VERIFICADO |
| 532 | README.pt-BR.md: every relative path cited exists in the repository | none missing | `README.pt-BR.md` | paths in backticks and links | none missing | VERIFICADO |
| 533 | README.md: no 'Resumo em português' section | absent | `README.md` | '## Resumo em português' | absent | VERIFICADO |
| 534 | README.md: language switch to README.pt-BR.md | present | `README.md` | '(README.pt-BR.md)' | present | VERIFICADO |
| 535 | README.pt-BR.md: language switch to README.md | present | `README.pt-BR.md` | '(README.md)' | present | VERIFICADO |
| 536 | README.md: app language link ?lang=pt | present | `README.md` | 'streamlit.app/?lang=pt' | present | VERIFICADO |
| 537 | README.md: no 'dobra' | absent | `README.md` | 'dobra' | absent | VERIFICADO |
| 538 | README.pt-BR.md: app language link ?lang=pt | present | `README.pt-BR.md` | 'streamlit.app/?lang=pt' | present | VERIFICADO |
| 539 | README.pt-BR.md: no 'dobra' | absent | `README.pt-BR.md` | 'dobra' | absent | VERIFICADO |
| 540 | README.md: project page badge present | present | `README.md` | 'GitHub%20Pages-blue)](https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/)' | present | VERIFICADO |
| 541 | README.md: Codespaces badge present | present | `README.md` | 'codespaces/badge.svg)](https://codespaces.new/matheusmmmp/sp-respiratory-admissions-forecast)' | present | VERIFICADO |
| 542 | README.md: badge kept (actions/workflows/ci.yml/badge.svg) | present | `README.md` | 'actions/workflows/ci.yml/badge.svg' | present | VERIFICADO |
| 543 | README.md: badge kept (streamlit_badge_black_white.svg) | present | `README.md` | 'streamlit_badge_black_white.svg' | present | VERIFICADO |
| 544 | README.md: badge kept (python-3.11-blue) | present | `README.md` | 'python-3.11-blue' | present | VERIFICADO |
| 545 | README.md: badge kept (license-MIT-green) | present | `README.md` | 'license-MIT-green' | present | VERIFICADO |
| 546 | README.md: both project page URLs present | present | `README.md` | PAGE_EN and PAGE_PT | present | VERIFICADO |
| 547 | README.md: release link present | present | `README.md` | 'https://github.com/matheusmmmp/sp-respiratory-admissions-forecast/releases/tag/v0.1.0' | present | VERIFICADO |
| 548 | README.md: no DOI cited | absent | `README.md` | 'doi.org' / '10.5281' | absent | VERIFICADO |
| 549 | README.md: no Hugging Face Space URL (API not yet deployed) | absent | `README.md` | 'huggingface.co/spaces' / 'hf.space' | absent | VERIFICADO |
| 550 | README.md: states the API is not yet deployed | present | `README.md` | 'not yet deployed' / 'ainda não está publicada' | present | VERIFICADO |
| 551 | README.md: --mlflow example command present | present | `README.md` | '--smoke --mlflow --mlflow-uri sqlite:///mlruns/mlflow.db' | present | VERIFICADO |
| 552 | README.md: pre-commit install line present | present | `README.md` | 'uv run pre-commit install' | present | VERIFICADO |
| 553 | README.pt-BR.md: project page badge present | present | `README.pt-BR.md` | 'GitHub%20Pages-blue)](https://matheusmmmp.github.io/sp-respiratory-admissions-forecast/index.pt-BR.html)' | present | VERIFICADO |
| 554 | README.pt-BR.md: Codespaces badge present | present | `README.pt-BR.md` | 'codespaces/badge.svg)](https://codespaces.new/matheusmmmp/sp-respiratory-admissions-forecast)' | present | VERIFICADO |
| 555 | README.pt-BR.md: badge kept (actions/workflows/ci.yml/badge.svg) | present | `README.pt-BR.md` | 'actions/workflows/ci.yml/badge.svg' | present | VERIFICADO |
| 556 | README.pt-BR.md: badge kept (streamlit_badge_black_white.svg) | present | `README.pt-BR.md` | 'streamlit_badge_black_white.svg' | present | VERIFICADO |
| 557 | README.pt-BR.md: badge kept (python-3.11-blue) | present | `README.pt-BR.md` | 'python-3.11-blue' | present | VERIFICADO |
| 558 | README.pt-BR.md: badge kept (license-MIT-green) | present | `README.pt-BR.md` | 'license-MIT-green' | present | VERIFICADO |
| 559 | README.pt-BR.md: both project page URLs present | present | `README.pt-BR.md` | PAGE_EN and PAGE_PT | present | VERIFICADO |
| 560 | README.pt-BR.md: release link present | present | `README.pt-BR.md` | 'https://github.com/matheusmmmp/sp-respiratory-admissions-forecast/releases/tag/v0.1.0' | present | VERIFICADO |
| 561 | README.pt-BR.md: no DOI cited | absent | `README.pt-BR.md` | 'doi.org' / '10.5281' | absent | VERIFICADO |
| 562 | README.pt-BR.md: no Hugging Face Space URL (API not yet deployed) | absent | `README.pt-BR.md` | 'huggingface.co/spaces' / 'hf.space' | absent | VERIFICADO |
| 563 | README.pt-BR.md: states the API is not yet deployed | present | `README.pt-BR.md` | 'not yet deployed' / 'ainda não está publicada' | present | VERIFICADO |
| 564 | README.pt-BR.md: --mlflow example command present | present | `README.pt-BR.md` | '--smoke --mlflow --mlflow-uri sqlite:///mlruns/mlflow.db' | present | VERIFICADO |
| 565 | README.pt-BR.md: pre-commit install line present | present | `README.pt-BR.md` | 'uv run pre-commit install' | present | VERIFICADO |
| 566 | README: release tag v0.1.0 exists in the repository | v0.1.0 | `git tag --list v0.1.0` | stdout | v0.1.0 | VERIFICADO |
| 567 | README: CITATION.cff has no DOI | absent | `CITATION.cff` | 'doi:' field | absent | VERIFICADO |
| 568 | README: slim API image port | 7860 | `api/Dockerfile` | '7860' in file | 7860 | VERIFICADO |
| 569 | README: slim API image non-root user | uid 1000 | `api/Dockerfile` | '--uid 1000' | uid 1000 | VERIFICADO |
| 570 | README: slim API requirements have no TensorFlow | absent | `api/requirements.txt` | lines starting with 'tensorflow' | absent | VERIFICADO |
| 571 | README: runner has --mlflow option | present | `src/experiments/run_preliminary.py` | add_argument('--mlflow' | present | VERIFICADO |
| 572 | README: runner has --mlflow-uri option | present | `src/experiments/run_preliminary.py` | add_argument('--mlflow-uri' | present | VERIFICADO |
| 573 | README: Codespaces postCreateCommand runs uv sync --frozen --all-extras | present | `.devcontainer/devcontainer.json` | postCreateCommand | present | VERIFICADO |
| 574 | README: Codespaces forwards ports 8501, 8000, 5000 | 8501, 8000, 5000 | `.devcontainer/devcontainer.json` | forwardPorts | 8501, 8000, 5000 | VERIFICADO |
| 575 | README: Codespaces opens the Streamlit app | present | `.devcontainer/devcontainer.json` | postAttachCommand.app | present | VERIFICADO |
| 576 | README: CI job 'docker' exists | present | `.github/workflows/ci.yml` | 'name: docker' | present | VERIFICADO |
| 577 | README: CI docker job builds api/Dockerfile | present | `.github/workflows/ci.yml` | 'file: api/Dockerfile' | present | VERIFICADO |
| 578 | README: CI docker job waits for /health via compose | present | `.github/workflows/ci.yml` | 'docker compose up -d --no-build api' and '/health' | present | VERIFICADO |
| 579 | README: CI docker job runs pytest + smoke in the test image | present | `.github/workflows/ci.yml` | 'pytest + smoke dentro do contêiner' | present | VERIFICADO |
| 580 | README: pages workflow is manual (workflow_dispatch) | present | `.github/workflows/pages.yml` | 'workflow_dispatch' | present | VERIFICADO |
| 581 | README: make target 'docker-build' exists | present | `Makefile` | 'docker-build:' line | present | VERIFICADO |
| 582 | README: make target 'docker-test' exists | present | `Makefile` | 'docker-test:' line | present | VERIFICADO |
| 583 | README: make target 'docker-api' exists | present | `Makefile` | 'docker-api:' line | present | VERIFICADO |
| 584 | README: make target 'precommit' exists | present | `Makefile` | 'precommit:' line | present | VERIFICADO |
| 585 | README: make target 'mlflow' exists | present | `Makefile` | 'mlflow:' line | present | VERIFICADO |
| 586 | README: make target 'app' exists | present | `Makefile` | 'app:' line | present | VERIFICADO |
| 587 | README: make target 'api' exists | present | `Makefile` | 'api:' line | present | VERIFICADO |
| 588 | README: make target 'test' exists | present | `Makefile` | 'test:' line | present | VERIFICADO |
| 589 | README: make target 'smoke' exists | present | `Makefile` | 'smoke:' line | present | VERIFICADO |
| 590 | README: number of author decisions (D1 to D13) | 13 | `docs/DECISOES.md` | rows starting with '| D' | 13 | VERIFICADO |
| 591 | README: D9 says the dissertation runner is unchanged | present | `docs/DECISOES.md` | D9 text | present | VERIFICADO |
| 592 | README: D10 says no DOI yet | present | `docs/DECISOES.md` | D10 text '**sem DOI**' | present | VERIFICADO |
| 593 | README: cited file exists (tracking/registro_mlflow.py) | exists | `tracking/registro_mlflow.py` | path | exists | VERIFICADO |
| 594 | README: cited file exists (tracking/importar_pesquisa.py) | exists | `tracking/importar_pesquisa.py` | path | exists | VERIFICADO |
| 595 | README: cited file exists (configs/smoke_mlflow.yaml) | exists | `configs/smoke_mlflow.yaml` | path | exists | VERIFICADO |
| 596 | README: cited file exists (tests/test_runner_mlflow.py) | exists | `tests/test_runner_mlflow.py` | path | exists | VERIFICADO |
| 597 | README: cited file exists (docs/scripts/build_site.py) | exists | `docs/scripts/build_site.py` | path | exists | VERIFICADO |
| 598 | README: cited file exists (site/index.html) | exists | `site/index.html` | path | exists | VERIFICADO |
| 599 | README: cited file exists (site/index.pt-BR.html) | exists | `site/index.pt-BR.html` | path | exists | VERIFICADO |
| 600 | README: cited file exists (deploy/hf_space/montar_space.py) | exists | `deploy/hf_space/montar_space.py` | path | exists | VERIFICADO |
| 601 | README: cited file exists (deploy/hf_space/LEIA-ME.md) | exists | `deploy/hf_space/LEIA-ME.md` | path | exists | VERIFICADO |
| 602 | README: cited file exists (.pre-commit-config.yaml) | exists | `.pre-commit-config.yaml` | path | exists | VERIFICADO |
| 603 | README: versioned demonstration weights in models_demo/ (three XGBoost) | 3 | `models_demo/*.ubj` | count of .ubj files | 3 | VERIFICADO |
| 604 | README: no other versioned weight files outside models_demo/ | none | `git ls-files` | files ending in .ubj, .keras, .h5, .pkl, .joblib, .onnx, .pt, .safetensors | none | VERIFICADO |
| 605 | README.md: 'is not' section says the API is in-sample and not deployed | present | `README.md` | 'in-sample' and 'not yet deployed' / 'ainda não está publicada' in the 'is not' section | present | VERIFICADO |
| 606 | README.md: 'is not' section names the demonstration weights in models_demo/ | present | `README.md` | 'models_demo/MODEL_CARD.md' in the 'is not' section | present | VERIFICADO |
| 607 | README.md: 'is not' section cites decision D8 for the CNES 2091550 daily series | present | `README.md` | 'CNES 2091550' and 'D8' in the 'is not' section | present | VERIFICADO |
| 608 | README.md: old Saturday sentence ('worst day for every model') gone | absent | `README.md` | 'worst day for every model' / 'pior dia para todos' | absent | VERIFICADO |
| 609 | README.pt-BR.md: 'is not' section says the API is in-sample and not deployed | present | `README.pt-BR.md` | 'in-sample' and 'not yet deployed' / 'ainda não está publicada' in the 'is not' section | present | VERIFICADO |
| 610 | README.pt-BR.md: 'is not' section names the demonstration weights in models_demo/ | present | `README.pt-BR.md` | 'models_demo/MODEL_CARD.md' in the 'is not' section | present | VERIFICADO |
| 611 | README.pt-BR.md: 'is not' section cites decision D8 for the CNES 2091550 daily series | present | `README.pt-BR.md` | 'CNES 2091550' and 'D8' in the 'is not' section | present | VERIFICADO |
| 612 | README.pt-BR.md: old Saturday sentence ('worst day for every model') gone | absent | `README.pt-BR.md` | 'worst day for every model' / 'pior dia para todos' | absent | VERIFICADO |
| 613 | DECISOES: D8 accepts the daily series of one establishment | present | `docs/DECISOES.md` | D8 row '**Aceitas como estão**' | present | VERIFICADO |
| 614 | README/ARCHITECTURE/D9: metrics.json compared byte for byte | present | `tests/test_runner_mlflow.py` | ARQUIVOS_IDENTICOS | present | VERIFICADO |
| 615 | README/ARCHITECTURE/D9: model_comparison.csv compared byte for byte | present | `tests/test_runner_mlflow.py` | ARQUIVOS_IDENTICOS | present | VERIFICADO |
| 616 | README/ARCHITECTURE/D9: metrics_by_fold.csv compared byte for byte | present | `tests/test_runner_mlflow.py` | ARQUIVOS_IDENTICOS | present | VERIFICADO |
| 617 | README/ARCHITECTURE/D9: folds.csv compared byte for byte | present | `tests/test_runner_mlflow.py` | ARQUIVOS_IDENTICOS | present | VERIFICADO |
| 618 | README/ARCHITECTURE/D9: feature_ablation.csv compared byte for byte | present | `tests/test_runner_mlflow.py` | ARQUIVOS_IDENTICOS | present | VERIFICADO |
| 619 | README/ARCHITECTURE/D9: predictions.csv compared after masking the run id | present | `tests/test_runner_mlflow.py` | '.replace(a["run_id"], "<RUN_ID>")' | present | VERIFICADO |
| 620 | README/ARCHITECTURE/D9: manifest.json compared without run id and time fields | run_id, timestamp, inicio, fim, tempo* | `tests/test_runner_mlflow.py` | _sem_chaves_volateis | run_id, timestamp, inicio, fim, tempo* | VERIFICADO |
| 621 | README/ARCHITECTURE/D9: against the pre-hook runner the git fields of the manifest are also ignored | present | `tests/test_runner_mlflow.py` | 'git_commit', 'git_branch', 'git_sujo', 'proveniencia' with ignorar_git | present | VERIFICADO |
| 622 | ARCHITECTURE: reference commit of the pre-hook runner | 2be070b | `tests/test_runner_mlflow.py` | COMMIT_REFERENCIA[:7] | 2be070b | VERIFICADO |
| 623 | README: CI job 'secrets' runs gitleaks on the whole history | present | `.github/workflows/ci.yml` | '  secrets:' and 'gitleaks" git --log-opts=--all --redact' | present | VERIFICADO |
| 624 | DECISOES: D5 practical consequence marked as superseded | present | `docs/DECISOES.md` | '**Superada em 2026-11-23**' | present | VERIFICADO |

## Números narrativos sem arquivo em `results/` (não conferidos aqui, declarados no texto)

- `docs/LESSONS.md`, história 2: percentual de diferença do PM2.5 e correlação entre o CAMS canônico e o novo download ficam no PROTOCOLO §0.17 da dissertação; o texto não os repete.
- `docs/LESSONS.md`, história 4: os defeitos da run `preliminar_h1_full_20260727-163313` vêm do `CLAUDE.md` §5 e do `CHANGELOG.md` da dissertação; nenhum número dessa run é citado.
- `docs/LESSONS.md`, história 3: a descrição da consulta BigQuery vem do cabeçalho de `src/ingestion/fetch_sih_bq_enriquecido.py` da dissertação (tabela `servicos_profissionais`, filtro por município do estabelecimento).

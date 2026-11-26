# Decisões do autor — repositório de portfólio

Registradas em 2026-11-23, antes da Fase 0, conforme §3 de `PLANO_PORTFOLIO.md`.
Respondidas por Matheus de Medeiros Pereira no chat com o gerente (Claude Code).

| # | Decisão | Resposta |
|---|---|---|
| D1 | Quando publicar | **Publicar antes da defesa**, com rótulo "provisório" em todo resultado. A publicação em si (Fase 4) continua dependendo de autorização explícita, passo a passo. |
| D2 | Redistribuir dados ambientais processados | **Incluir os CSV diários** (CETESB agregado + CAMS diário) com atribuição: CAMS sob a licença Copernicus; CETESB/QUALAR com termos a confirmar no data card (`data/README.md`). |
| D3 | Nome e idioma | **`sp-respiratory-admissions-forecast`**; README em inglês com seção em português; código mantém nomes em português. **Revisada em 2026-11-23 (pedido do autor):** duas versões integrais do README, `README.md` (inglês, padrão do GitHub) e `README.pt-BR.md` (português), com link de troca no topo; a seção-resumo deixa de existir. O app Streamlit tem seletor de idioma PT/EN (inglês padrão; `?lang=pt`). Os demais documentos (`docs/`, data card, model card) continuam em inglês. |
| D4 | Licença | **MIT** para o código; dados com a licença da fonte. |
| D5 | Commits locais | **Autorizados**, um por pacote aprovado (`feat(<wp>): ...`). Push continua bloqueado. |
| D6 | Hospedagem do app | **Streamlit Community Cloud** (depois de D1). |
| D7 | CNES 2091550 no caso do sábado | **Citar o código** (informação pública do CNES). **Ampliada em 2026-11-23 (auditoria WP-A, item 2):** o nome do estabelecimento ("Instituto CEMA") também pode aparecer ao lado do código, como no painel original; nome e código são informação pública do cadastro CNES. |
| D8 | Contagens diárias de um único estabelecimento no painel (`notebooks/dados_painel/diario.csv`, coluna `cema`) | **Aceitas como estão** (2026-11-23, auditoria WP-A, item 5): a regra de supressão de células < 5 vale para estabelecimento × ano; a série diária de internações de um hospital público identificado pelo CNES não identifica pacientes e é necessária para o gráfico dos sábados. Registrado aqui em vez de alterar o `manifest.json` copiado do painel. |
| D9 | MLflow da pesquisa e registro pelo runner | **Aplicado em 2026-11-26 (pedido do autor).** Fase A: `tracking/importar_pesquisa.py` importa todo o histórico de `reports/experiments/` da dissertação (só leitura) para um MLflow local em `D:\Project\mlflow_pesquisa` (SQLite), guiado por `catalogo_runs.yaml` fora do repo, ainda não revisado pelo autor. Fase B: o runner do **portfólio** ganhou a opção `--mlflow`, desligada por padrão, que registra a run e salva um modelo por modelo × conjunto × fold × semente; sem a opção a saída é idêntica byte a byte. O runner da dissertação **não** foi alterado: levar a mudança para lá exige PROTOCOLO e CHANGELOG, decisão do autor. |

## Consequências práticas

- D1: todo número exibido leva "provisório (pré-defesa)" e o id completo da run de origem.
- D2: `data/processed/` contém só séries diárias agregadas; nenhum microdado, nenhum `N_AIH`.
- D5: o gerente commita localmente; nenhum `git push`, nenhum repositório remoto até a Fase 4.
- D7: `notebooks/`, `app/` e `docs/` podem citar o CNES 2091550 pelo código e pelo nome, como no painel original.
- D8: nenhuma supressão adicional em `diario.csv`; a decisão e o motivo ficam neste arquivo.

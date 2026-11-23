# Decisões do autor — repositório de portfólio

Registradas em 2026-11-23, antes da Fase 0, conforme §3 de `PLANO_PORTFOLIO.md`.
Respondidas por Matheus de Medeiros Pereira no chat com o gerente (Claude Code).

| # | Decisão | Resposta |
|---|---|---|
| D1 | Quando publicar | **Publicar antes da defesa**, com rótulo "provisório" em todo resultado. A publicação em si (Fase 4) continua dependendo de autorização explícita, passo a passo. |
| D2 | Redistribuir dados ambientais processados | **Incluir os CSV diários** (CETESB agregado + CAMS diário) com atribuição: CAMS sob a licença Copernicus; CETESB/QUALAR com termos a confirmar no data card (`data/README.md`). |
| D3 | Nome e idioma | **`sp-respiratory-admissions-forecast`**; README em inglês com seção em português; código mantém nomes em português. |
| D4 | Licença | **MIT** para o código; dados com a licença da fonte. |
| D5 | Commits locais | **Autorizados**, um por pacote aprovado (`feat(<wp>): ...`). Push continua bloqueado. |
| D6 | Hospedagem do app | **Streamlit Community Cloud** (depois de D1). |
| D7 | CNES 2091550 no caso do sábado | **Citar o código** (informação pública do CNES). **Ampliada em 2026-11-23 (auditoria WP-A, item 2):** o nome do estabelecimento ("Instituto CEMA") também pode aparecer ao lado do código, como no painel original; nome e código são informação pública do cadastro CNES. |
| D8 | Contagens diárias de um único estabelecimento no painel (`notebooks/dados_painel/diario.csv`, coluna `cema`) | **Aceitas como estão** (2026-11-23, auditoria WP-A, item 5): a regra de supressão de células < 5 vale para estabelecimento × ano; a série diária de internações de um hospital público identificado pelo CNES não identifica pacientes e é necessária para o gráfico dos sábados. Registrado aqui em vez de alterar o `manifest.json` copiado do painel. |

## Consequências práticas

- D1: todo número exibido leva "provisório (pré-defesa)" e o id completo da run de origem.
- D2: `data/processed/` contém só séries diárias agregadas; nenhum microdado, nenhum `N_AIH`.
- D5: o gerente commita localmente; nenhum `git push`, nenhum repositório remoto até a Fase 4.
- D7: `notebooks/`, `app/` e `docs/` podem citar o CNES 2091550 pelo código e pelo nome, como no painel original.
- D8: nenhuma supressão adicional em `diario.csv`; a decisão e o motivo ficam neste arquivo.

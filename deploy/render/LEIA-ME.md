# API de demonstração no Render

URL: <https://sp-respiratory-admissions-forecast-api.onrender.com> (`/health`, `/forecast`, `/docs`). Publicada em 2026-11-26 pelo autor (decisão D14 em
`docs/DECISOES.md`). Demonstração de engenharia, in-sample por construção; não é resultado da dissertação.

## Configuração do serviço (painel do Render, "New Web Service")

| Campo | Valor |
|---|---|
| Source Code | Public Git Repository: `https://github.com/matheusmmmp/sp-respiratory-admissions-forecast` |
| Name | `sp-respiratory-admissions-forecast-api` |
| Language | Docker |
| Branch | `main` |
| Region | Virginia (US East) |
| Instance type | Free (0.1 CPU, 512 MB RAM) |
| Docker Build Context Directory | `.` (raiz do repositório; o `api/Dockerfile` copia caminhos a partir dela) |
| Dockerfile Path | `api/Dockerfile` |
| Health Check Path | `/health` |
| Environment variables | nenhuma: o Render define `PORT` e a imagem escuta em `${PORT:-7860}` |

## Limites do plano gratuito

A instância dorme depois de 15 minutos sem tráfego e leva cerca de um minuto para acordar; o sistema
de arquivos é efêmero (a API não grava nada em disco). Na inicialização, a API confere o sha256 de cada
arquivo de dados e de modelo contra `models_demo/metadata.json` e se recusa a subir se algo mudar.

## Atualizar

O serviço foi criado pelo modo "Public Git Repository", que **não** redeploya sozinho a cada push.
Depois de um push que mude `api/`, `models_demo/`, `src/features/`, `src/models/` ou os dados, abra o
serviço no painel e use **Manual Deploy → Deploy latest commit**. Para deploy automático, conecte a conta
do GitHub ao Render (decisão do autor) ou use um Blueprint (`render.yaml`).

## Conferir

```
curl https://sp-respiratory-admissions-forecast-api.onrender.com/health
curl "https://sp-respiratory-admissions-forecast-api.onrender.com/forecast?h=7&origem=2024-06-01"
```

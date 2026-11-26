# Publicar a API de demonstração num Hugging Face Space (Docker)

Passo a passo para o autor. Nada aqui é automático: conta, Space, token e
`push` são feitos por você, no seu terminal. O que o repositório fornece é
`api/Dockerfile` (imagem enxuta: FastAPI + XGBoost CPU, ~uma ordem de grandeza
menor que a imagem principal, que carrega TensorFlow) e o script
`deploy/hf_space/montar_space.py`, que monta a pasta do Space com o conteúdo
exato e confere cada arquivo (sha256 contra `models_demo/metadata.json`).

## 1. Criar o Space (uma vez)

1. Entre em <https://huggingface.co/new-space> com a sua conta.
2. **Space name**: por exemplo `sp-respiratory-admissions-forecast-api`.
3. **License**: MIT. **SDK**: **Docker** → template **Blank**.
4. **Hardware**: CPU basic (gratuito) basta. **Visibility**: Public.
5. Crie. O Space nasce vazio, com um `README.md` padrão — será substituído.

## 2. Autenticar no seu terminal (uma vez)

Instale a CLI do Hub e faça login; o token é digitado por você, nunca fica em
arquivo do repositório:

```bash
uv tool install "huggingface_hub[cli]"   # ou: pipx install "huggingface_hub[cli]"
hf auth login                              # CLI atual; nas versões antigas: huggingface-cli login
```

Crie o token em <https://huggingface.co/settings/tokens> com permissão
**write** (ou fine-grained com escrita só nesse Space). Alternativamente, use
`git` com credencial HTTPS: o usuário é o seu login do HF e a senha é o token.

Instale também o Git LFS (`git lfs install`), porque `*.ubj` e `*.parquet` vão
marcados para LFS/Xet no `.gitattributes` gerado.

## 3. Montar a pasta do Space

Na raiz do repositório, com o `.venv` sincronizado:

```bash
uv run python deploy/hf_space/montar_space.py --destino ../sp-resp-forecast-space
```

O destino **tem** de ficar fora do repositório. Se a pasta já tiver conteúdo
(por exemplo, um clone anterior do Space), acrescente `--sobrescrever`: o
script esvazia tudo, menos `.git/`, e regrava. Ele falha com mensagem clara se
faltar arquivo, se um sha256 não bater com `models_demo/metadata.json` ou se o
`Dockerfile` copiar algo que não foi para a pasta.

Conteúdo gerado: `Dockerfile` (= `api/Dockerfile`), `README.md` com o
cabeçalho YAML do HF (`sdk: docker`, `app_port: 7860`), `.gitattributes`,
`api/`, `models_demo/`, `src/` (só os módulos usados), `configs/` dos três
horizontes e os quatro arquivos de `data/processed/`.

## 4. Enviar para o Space

```bash
cd ../sp-resp-forecast-space
git init -b main                                   # só na primeira vez
git lfs install
git remote add origin https://huggingface.co/spaces/<seu-usuario>/<nome-do-space>
git add .
git commit -m "demo API: imagem enxuta (FastAPI + XGBoost CPU)"
git push -u origin main --force                    # --force só na 1ª vez, para substituir o README padrão
```

O HF constrói a imagem e publica em
`https://<seu-usuario>-<nome-do-space>.hf.space`. Teste:

```bash
curl https://<seu-usuario>-<nome-do-space>.hf.space/health
curl "https://<seu-usuario>-<nome-do-space>.hf.space/forecast?h=7&origem=2024-06-01"
```

## 5. Atualizar

Depois de retreinar os modelos de demonstração (`models_demo/treinar.py`) ou de
mudar `api/`, repita o passo 3 com `--sobrescrever` e o passo 4 (sem `--force`).

## Notas

- O que roda no Space é **demonstração**, não resultado da dissertação; o README
  gerado diz isso e aponta para o GitHub e para o app Streamlit.
- A imagem roda como usuário `uid 1000` e escuta em `$PORT` (7860), como o HF exige.
- Antes do primeiro `push`, confira `git status` na pasta do Space: só os
  arquivos listados acima devem aparecer; nenhum `.env`, `.cdsapirc` ou token.

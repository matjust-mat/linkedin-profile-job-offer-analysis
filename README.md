# Avaliador de Candidatos

Comparador de perfis (PDF do LinkedIn) com descrições de vaga. UI estática em HTML/JS e API em FastAPI.

## Sumário
- [Recursos](#recursos)
- [Estrutura](#estrutura)
- [Pré-requisitos](#pré-requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como rodar](#como-rodar)
- [Docker](#docker)
- [API](#api)
- [Exemplos `curl`](#exemplos-curl)
- [Frontend](#frontend)
- [Testes e qualidade](#testes-e-qualidade)
- [Erros comuns](#erros-comuns)
- [FAQ](#faq)
- [Padrões e i18n](#padrões-e-i18n)
- [Licença](#licença)

## Recursos
- Carregue 1+ PDFs exportados do LinkedIn.
- Informe a descrição da vaga (texto ou PDF).
- Receba pontuação de aderência, destaques, lacunas e justificativas.
- Suporte a `pt`, `en`, `es` via `locale`.

## Estrutura
```
.
├─ app/                 # Backend FastAPI
│  ├─ main.py
│  ├─ services/
│  ├─ models/
│  └─ tests/
├─ frontend/            # UI estática
│  ├─ index.html
│  ├─ app.js
│  └─ styles.css
├─ requirements.txt
├─ .env                 # opcional
└─ README.md
```

## Pré-requisitos
- Python 3.11+ (3.12 recomendado)
- `pip`
- (Opcional) Node 18+ se usar ferramentas de build para o frontend
- (Opcional) Docker

## Instalação
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração
Crie `.env` na raiz (opcional):
```dotenv
# Servidor
PORT=8000
LOG_LEVEL=info

# CORS (se precisar abrir para a UI local)
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173

# Integrações (adicione se necessário)
# OPENAI_API_KEY=
# PROXY_URL=
```

## Como rodar
Backend:
```bash
uvicorn app.main:app --host 127.0.0.1 --port ${PORT:-8000} --reload
```

Saúde:
```bash
curl http://127.0.0.1:8000/health
```

Frontend rápido:
```bash
# dentro de frontend/
python -m http.server 5173
# abra http://127.0.0.1:5173
```
Na UI, defina o campo **API** como `http://127.0.0.1:8000`.

## Docker
Build:
```bash
docker build -t candidatos-api -f Dockerfile .
```
Run:
```bash
docker run --rm -p 8000:8000 --env-file .env candidatos-api
```

## API
Base: `http://127.0.0.1:8000`

### `GET /health`
Retorna status.
```json
{ "status": "ok" }
```

### `POST /score`
Calcula aderência de um ou mais perfis à vaga.

- **Content-Type:** `multipart/form-data`
- **Campos:**
  - `files`: um ou mais PDFs de perfis do LinkedIn
  - `job_text`: texto da vaga (alternativo a `job_pdf`)
  - `job_pdf`: PDF da vaga (alternativo a `job_text`)
  - `locale`: `pt` | `en` | `es` (opcional)

**Resposta exemplo:**
```json
{
  "job_summary": "Síntese dos requisitos da vaga...",
  "candidates": [
    {
      "filename": "perfil1.pdf",
      "score": 82,
      "highlights": ["Kubernetes", "Go", "Cloud"],
      "gaps": ["Inglês avançado", "FinOps"],
      "rationale": "Correspondências e lacunas identificadas."
    }
  ]
}
```

## Exemplos `curl`
Múltiplos perfis + vaga em texto:
```bash
curl -X POST http://127.0.0.1:8000/score   -F "files=@/caminho/perfil1.pdf"   -F "files=@/caminho/perfil2.pdf"   -F 'job_text=Procuramos DevOps com Kubernetes, Go e Cloud...'   -F "locale=pt"
```

Vaga em PDF:
```bash
curl -X POST http://127.0.0.1:8000/score   -F "files=@/caminho/perfil1.pdf"   -F "job_pdf=@/caminho/vaga.pdf"   -F "locale=pt"
```

## Frontend
- `index.html` exibe **Avaliador de Candidatos** e campo **API** para configurar a base.
- `app.js` envia `multipart/form-data` para `/score`.
- Botão “ℹ︎” descreve como exportar PDF do LinkedIn.

Como exportar PDF do LinkedIn:
1. Abra o perfil.
2. Clique em **Mais**.
3. Escolha **Salvar em PDF**.

## Testes e qualidade
Rodar testes:
```bash
pytest -q
```
Cobertura:
```bash
pytest --cov=app --cov-report=term-missing
```
Lint/format:
```bash
ruff check .
black .
```

## Erros comuns
- Porta ocupada `8000`  
  Altere `PORT` no `.env` ou rode `--port 8001`.

- Proxy afeta `curl` para `localhost`  
  ```bash
  unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
  curl --noproxy "*" http://127.0.0.1:8000/health
  ```

- Windows PowerShell e variável `PID` protegida  
  Não sobrescreva `$PID`. Para achar processo na porta:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 | Format-List
  ```

- CORS bloqueado na UI  
  Defina `CORS_ORIGINS` no `.env` com a origem do frontend.

- PDF inválido ou truncado  
  Reexporte no LinkedIn via **Mais > Salvar em PDF**.

**Suporta quantos PDFs de candidato?**  
Vários, limite prático depende de memória e timeout do servidor.

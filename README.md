# Almamlaka TV — Bilingual RAG Chatbot

A chatbot that answers questions in Arabic and English using only three PDFs in `backend/data/`.

**Status:** Phase 1 — backend foundation. Only the health endpoint exists so far.

## Requirements

- Python 3.11

## Local setup

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env
```

## Run the API

```bash
uvicorn app.main:app --app-dir backend --reload
```

Check it:

```bash
curl http://127.0.0.1:8000/api/health
# {"status":"ok","env":"development","documents":[...3 PDFs...]}
```

Interactive API docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```

## Configuration

Settings are read from environment variables, or from `.env` in the repository root. See `.env.example`.

| Variable   | Default                    | Purpose                 |
|------------|----------------------------|-------------------------|
| `APP_NAME` | `Almamlaka TV RAG Chatbot` | API title               |
| `APP_ENV`  | `development`              | Environment label       |
| `DATA_DIR` | `backend/data`             | Location of source PDFs |

## Project layout

```
backend/
  app/
    config.py     # environment-based settings
    main.py       # FastAPI app, GET /api/health
  data/           # source PDFs (read-only)
  requirements.txt
tests/            # pytest suite
frontend/         # (later phase)
```

# Deployment

The app runs as **one service**: FastAPI serves the API under `/api/*` and the frontend at `/`.

| Route | Purpose |
|---|---|
| `GET /` | Chat frontend (static files from `frontend/`) |
| `GET /api/health` | Health check: status and the list of loaded PDFs |
| `POST /api/chat` | RAG chat: `{"question": "...", "session_id": null}` |

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | Read only from the environment. Never commit it. |
| `LLM_MODEL` | No | `qwen/qwen3-32b` | OpenRouter model ID |
| `APP_ENV` | No | `development` | Shown by `/api/health`; set `production` on Railway |
| `PORT` | Set by Railway | `8000` locally | The container binds `0.0.0.0:$PORT` |

## Docker

```bash
docker build -t almamlaka-rag .
docker run --rm -p 8080:8080 -e PORT=8080 -e OPENROUTER_API_KEY=your-key almamlaka-rag
```

Then open http://localhost:8080 and check http://localhost:8080/api/health.

What the image does:

- Uses `python:3.11-slim` with **CPU-only** PyTorch, which avoids about 2 GB of CUDA libraries.
- Downloads the embedding model (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`) **at build time**. At runtime it runs with `HF_HUB_OFFLINE=1`, so nothing is downloaded on startup.
- Runs as a non-root user with **1 worker**. Conversation memory is in-process, and every worker loads its own copy of the model.
- Excludes `.env`, `.venv`, `.git`, tests, evaluation files and dev-only frontend files (see `.dockerignore`).

## Local development (without Docker)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env   # then add OPENROUTER_API_KEY
uvicorn app.main:app --app-dir backend --port 8000
pytest
```

The UI and API are both served at http://127.0.0.1:8000.

## Railway

`railway.json` selects the Dockerfile builder, sets `/api/health` as the health check (300 s timeout, to allow model loading) and keeps 1 replica.

1. Open https://railway.com and sign in with GitHub.
2. Choose **New Project → Deploy from GitHub repo** and select `laytio/Assignment---Almamlaka-TV`, branch `main`.
3. Confirm the build log shows the **Dockerfile** being used (it is picked up from `railway.json`).
4. Open the service's **Variables** tab and add `OPENROUTER_API_KEY`. Optionally add `LLM_MODEL=qwen/qwen3-32b` and `APP_ENV=production`. Do not set `PORT`; Railway injects it.
5. Deploy. In **Build Logs**, expect the torch, requirements and model-download steps to succeed.
6. In **Deploy Logs**, expect `RAG Service ready!` followed by `Uvicorn running on http://0.0.0.0:<port>`.
7. Go to **Settings → Networking → Generate Domain** to get the public URL.

## Verifying the public URL

```bash
URL=https://<your-app>.up.railway.app
curl -i $URL/api/health                         # 200, three documents listed
curl -s -o /dev/null -w "%{http_code}\n" $URL/  # 200
curl -s -X POST $URL/api/chat -H 'Content-Type: application/json' \
     -d '{"question":"What is the total project budget?","session_id":null}'
```

The last command calls the paid LLM.

In the browser, confirm:

- The logo, styles and suggestions load.
- The English/Arabic toggle switches between LTR and RTL.
- Answers include source citations.
- Follow-up questions keep the same session.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Health check times out on first deploy | Model loading takes longer than the timeout. Raise `healthcheckTimeout` in `railway.json`. |
| Container restarts with exit code 137 | Out of memory. torch plus the model needs roughly 1–1.5 GB of RAM; raise the service memory limit. |
| `POST /api/chat` returns 500 | `OPENROUTER_API_KEY` is missing or invalid, or OpenRouter is unavailable. Check the deploy logs for `Chat API error`. |
| `GET /` returns 404 | `frontend/` is missing from the image. Check `.dockerignore` and the `COPY` lines. |
| Build fails while installing torch | The CPU wheel index (`download.pytorch.org/whl/cpu`) was unreachable. Retry the build. |
| Conversation context is lost | The service restarted (memory is in-process), or there is more than one replica or worker. Keep both at 1. |

## Rollback

- **Railway:** under **Deployments**, open a previous successful deployment and choose **Redeploy** (rollback).
- **Git:** run `git revert <commit>` and push to `main`. Railway rebuilds from the new commit. Do not force-push.

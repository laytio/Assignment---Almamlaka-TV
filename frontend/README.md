# Frontend — Almamlaka TV Knowledge Assistant

Plain HTML, CSS and JavaScript (ES modules). No build step, no npm packages. Fonts load from Google Fonts.

| File | Purpose |
|---|---|
| `index.html` | Page structure |
| `styles.css` | Visual design, responsive layout, RTL handling |
| `app.js` | Chat flow, session handling, i18n (English / Arabic) |
| `text.js` | Safe Markdown → DOM rendering of answers; text-direction detection |
| `serve.py` | Local server: serves this folder and proxies `/api/*` to FastAPI |
| `text.test.mjs` | Renderer checks (`node frontend/text.test.mjs`) |

## Run locally

```bash
# 1. Backend (from the repository root)
uvicorn app.main:app --app-dir backend --port 8000

# 2. Frontend (another terminal)
python frontend/serve.py
```

Open http://127.0.0.1:5173.

The page only calls same-origin `/api/chat` and `/api/health`, which `serve.py` forwards to the backend. Set `BACKEND_URL`, `HOST` or `PORT` to change the defaults. API keys stay on the backend.

## Behaviour notes

- **Language:** the UI toggles between English and Arabic, and the choice is remembered. Each message sets its own direction from its content, so an Arabic question in the English UI still renders right-to-left.
- **Sessions:** `session_id` comes from the first response and is sent with every follow-up question. **New chat** discards it and cancels any request in flight.
- **Safety:** answers are parsed into DOM nodes (paragraphs, lists, tables, bold, italic, code). Model text is never assigned as HTML.
- **Sources:** the passages the backend retrieved are shown under each answer: document, page and similarity score, with duplicates merged.

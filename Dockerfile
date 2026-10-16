FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# CPU-only PyTorch first: the default Linux wheel bundles ~2 GB of unused CUDA libraries.
# requirements.txt pins torch==2.2.2, which this 2.2.2+cpu build satisfies.
RUN pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

USER app
ENV HF_HOME=/home/app/.cache/huggingface

# Bake the embedding model into the image so the container never downloads it at startup.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', device='cpu')"
ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY --chown=app backend/ backend/
COPY --chown=app frontend/ frontend/

EXPOSE 8000

# One worker: conversation memory lives in-process, and each worker would load its own model.
# Railway injects PORT; 8000 is only a local fallback.
CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]

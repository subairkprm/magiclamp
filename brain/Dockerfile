FROM python:3.11-slim

WORKDIR /app

ARG INCLUDE_RAG_MODEL=false

RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model only when RAG is going to be enabled.
# Saves ~300 MB of image size and several minutes of build time on Railway,
# which is the common case (RAG_ENABLED defaults to false).
RUN if [ "$INCLUDE_RAG_MODEL" = "true" ]; then \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" ; \
    else \
      echo "Skipping sentence-transformers download (INCLUDE_RAG_MODEL=$INCLUDE_RAG_MODEL)" ; \
    fi

COPY . .

RUN mkdir -p /data/brain/chroma /data/brain/exports

EXPOSE 9000

# Honour $PORT (Railway sets this dynamically); fall back to 9000 elsewhere.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:${PORT:-9000}/health || exit 1

# Single worker keeps SQLite and the in-memory rate-limiter happy on a
# single-instance Railway deployment. Multi-worker users should switch to
# DB_BACKEND=supabase and bump --workers explicitly.
CMD uvicorn brain.main:app --host 0.0.0.0 --port ${PORT:-9000} --workers 1


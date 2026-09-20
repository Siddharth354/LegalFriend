FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim@sha256:fb576a1ff0c6b967e8b466695af934e34161c4a99c2fbfb859261d4a24d4a8d3 AS build

ARG DENSE_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
ARG DENSE_MODEL_DTYPE=float32

ENV DENSE_MODEL_DTYPE=$DENSE_MODEL_DTYPE \
    DENSE_MODEL_NAME=$DENSE_MODEL_NAME \
    HF_HOME=/app/model-cache/huggingface \
    TMPDIR=/app/model-cache \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
RUN mkdir -p /app/model-cache /app/data /app/legal-corpus/qdrant_data
RUN uv run --no-sync python -c "import os, torch; from fastembed import SparseTextEmbedding; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['DENSE_MODEL_NAME'], model_kwargs={'torch_dtype': getattr(torch, os.environ['DENSE_MODEL_DTYPE'])}); SparseTextEmbedding(model_name='Qdrant/bm25')"

COPY backend/src ./src
COPY legal-corpus/chunks /app/legal-corpus/chunks

ENV CHUNKS_DIR=/app/legal-corpus/chunks \
    QDRANT_PATH=/app/legal-corpus/qdrant_data \
    SQLITE_PATH=/app/data/legalfriend.db

RUN uv run --no-sync python -c "from src.modules.legal_notice.implementations.retrieval_adapter import RetrievalAdapter; RetrievalAdapter().build_index()"
RUN touch /app/data/.volume

FROM gcr.io/distroless/python3-debian13:nonroot@sha256:0e52dfee02b1aba142e77b004f6ea11210b79456b51f10d70e9bd631cbc21d98

ARG DENSE_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
ARG DENSE_MODEL_DTYPE=float32

ENV DENSE_MODEL_DTYPE=$DENSE_MODEL_DTYPE \
    DENSE_MODEL_NAME=$DENSE_MODEL_NAME \
    ENV=dev \
    HF_HOME=/app/model-cache/huggingface \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TMPDIR=/app/model-cache \
    PYTHONPATH=/app/backend/.venv/lib/python3.13/site-packages \
    PYTHONUNBUFFERED=1 \
    CHUNKS_DIR=/app/legal-corpus/chunks \
    QDRANT_PATH=/app/legal-corpus/qdrant_data \
    SQLITE_PATH=/app/data/legalfriend.db

WORKDIR /app/backend

COPY --chown=65532:65532 --from=build /app/backend/.venv/lib/python3.13/site-packages /app/backend/.venv/lib/python3.13/site-packages
COPY --chown=65532:65532 --from=build /app/backend/src ./src
COPY --chown=65532:65532 --from=build /app/legal-corpus /app/legal-corpus
COPY --chown=65532:65532 --from=build /app/model-cache /app/model-cache
COPY --chown=65532:65532 --from=build /app/data /app/data

EXPOSE 8000

CMD ["-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

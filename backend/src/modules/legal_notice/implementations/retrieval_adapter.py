import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import torch
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


class RetrievalAdapter:
    def __init__(self) -> None:
        self.client = QdrantClient(path=str(settings.qdrant_path))
        dense_model_dtype: torch.dtype = getattr(torch, settings.dense_model_dtype)
        self.dense_model = SentenceTransformer(
            settings.dense_model_name,
            trust_remote_code=True,
            model_kwargs={"torch_dtype": dense_model_dtype},
        )
        self.sparse_model = SparseTextEmbedding(model_name=settings.sparse_model_name)

    def build_index(self, force: bool = False) -> int:
        if self.client.collection_exists(settings.collection_name):
            if not force:
                logger.info(
                    "qdrant_index",
                    status="already_built",
                    collection=settings.collection_name,
                )
                return self.client.count(settings.collection_name).count
            self.client.delete_collection(settings.collection_name)

        chunks: list[dict] = []
        for chunk_file in sorted(settings.chunks_dir.glob("*_chunks.json")):
            chunks.extend(json.loads(Path(chunk_file).read_text(encoding="utf-8")))

        contents = [c["content"] for c in chunks]
        dense_vectors = self.dense_model.encode_document(contents)
        sparse_vectors = list(self.sparse_model.embed(contents))

        self.client.create_collection(
            collection_name=settings.collection_name,
            vectors_config={
                "dense": models.VectorParams(
                    size=dense_vectors.shape[1], distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )

        points = [
            models.PointStruct(
                id=i,
                vector={
                    "dense": dense_vectors[i].tolist(),
                    "sparse": models.SparseVector(
                        indices=sparse_vectors[i].indices.tolist(),
                        values=sparse_vectors[i].values.tolist(),
                    ),
                },
                payload=chunks[i],
            )
            for i in range(len(chunks))
        ]
        self.client.upsert(collection_name=settings.collection_name, points=points)
        logger.info("qdrant_index", status="built", chunk_count=len(points))
        return len(points)

    def retrieve(self, english_query: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or settings.retrieval_top_k
        dense_q = self.dense_model.encode_query(english_query)
        sparse_q = next(iter(self.sparse_model.embed([english_query])))

        results = self.client.query_points(
            collection_name=settings.collection_name,
            prefetch=[
                models.Prefetch(query=dense_q.tolist(), using="dense", limit=top_k * 2),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_q.indices.tolist(),
                        values=sparse_q.values.tolist(),
                    ),
                    using="sparse",
                    limit=top_k * 2,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        ).points
        return [{"score": r.score, **(r.payload or {})} for r in results]

    def retrieve_many(
        self,
        english_queries: list[str],
        top_k: int | None = None,
    ) -> list[list[dict[str, object]]]:
        resolved_top_k: int = top_k or settings.retrieval_top_k
        dense_queries = self.dense_model.encode_query(english_queries)
        sparse_queries = list(self.sparse_model.embed(english_queries))

        def query_one(index: int) -> list[dict[str, object]]:
            results = self.client.query_points(
                collection_name=settings.collection_name,
                prefetch=[
                    models.Prefetch(
                        query=dense_queries[index].tolist(),
                        using="dense",
                        limit=resolved_top_k * 2,
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                            indices=sparse_queries[index].indices.tolist(),
                            values=sparse_queries[index].values.tolist(),
                        ),
                        using="sparse",
                        limit=resolved_top_k * 2,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=resolved_top_k,
            ).points
            return [
                {"score": result.score, **(result.payload or {})} for result in results
            ]

        worker_count: int = min(len(english_queries), 5)
        if worker_count == 0:
            return []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            return list(executor.map(query_one, range(len(english_queries))))

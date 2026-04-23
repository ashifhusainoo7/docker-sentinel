import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from config.settings import settings

logger = logging.getLogger("sentinel.services.crash_memory")

_RESERVED_PAYLOAD_KEYS = frozenset({"tenant_id", "analysis", "created_at"})


class CrashMemory:
    """Qdrant-backed semantic dedup for crash events.

    Multi-tenant via payload filtering on tenant_id. Single shared collection,
    384-dim cosine vectors, bge-small-en-v1.5 embeddings (via fastembed).
    All failures degrade silently so the LLM path is always reachable.
    """

    COLLECTION = "crash_history"
    VECTOR_SIZE = 384
    MODEL_NAME = "BAAI/bge-small-en-v1.5"

    def __init__(self):
        self._client: QdrantClient | None = None
        self._embedder: TextEmbedding | None = None
        self._ready: bool = False
        self._init_lock = threading.Lock()

    def _init(self) -> None:
        """Lazy-init: connect, load embedder, ensure collection exists.

        Thread-safe — concurrent callers inside asyncio.to_thread serialize on
        _init_lock so the Qdrant client and fastembed model are built once.
        """
        if self._ready:
            return
        with self._init_lock:
            if self._ready:
                return
            self._client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
            )
            self._embedder = TextEmbedding(model_name=self.MODEL_NAME)
            self._ensure_collection()
            self._ready = True

    def _ensure_collection(self) -> None:
        """Create the collection if it doesn't exist. Idempotent."""
        existing = {c.name for c in self._client.get_collections().collections}
        if self.COLLECTION in existing:
            return
        self._client.create_collection(
            collection_name=self.COLLECTION,
            vectors_config=VectorParams(
                size=self.VECTOR_SIZE, distance=Distance.COSINE
            ),
        )

    def _embed(self, text: str) -> list[float]:
        vec = next(self._embedder.embed([text]))
        return vec.tolist()

    async def find_similar(
        self,
        text: str,
        tenant_id: str,
        threshold: float = 0.92,
    ) -> dict | None:
        try:
            await asyncio.to_thread(self._init)
            vector = await asyncio.to_thread(self._embed, text)
            results = await asyncio.to_thread(
                self._client.search,
                collection_name=self.COLLECTION,
                query_vector=vector,
                query_filter=Filter(
                    must=[FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id),
                    )]
                ),
                limit=1,
                score_threshold=threshold,
            )
        except Exception:
            logger.exception("Qdrant find_similar failed; treating as cache miss")
            return None

        if not results:
            return None
        return results[0].payload.get("analysis")

    async def store(
        self,
        text: str,
        analysis: dict,
        tenant_id: str,
        metadata: dict | None = None,
    ) -> None:
        try:
            await asyncio.to_thread(self._init)
            vector = await asyncio.to_thread(self._embed, text)
            payload = {
                "tenant_id": tenant_id,
                "analysis": analysis,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if metadata:
                # Drop reserved keys so metadata can never overwrite tenant
                # isolation / analysis / created_at fields.
                safe = {
                    k: v for k, v in metadata.items()
                    if k not in _RESERVED_PAYLOAD_KEYS
                }
                if len(safe) < len(metadata):
                    dropped = set(metadata) & _RESERVED_PAYLOAD_KEYS
                    logger.warning(
                        "CrashMemory.store: dropped reserved metadata keys: %s",
                        sorted(dropped),
                    )
                payload.update(safe)
            await asyncio.to_thread(
                self._client.upsert,
                collection_name=self.COLLECTION,
                points=[PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload=payload,
                )],
            )
        except Exception:
            logger.exception("Qdrant store failed; analysis remains uncached")

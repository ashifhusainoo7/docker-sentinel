class CrashMemory:
    """Qdrant vector cache for crash similarity matching.

    Phase 2: stubs — find_similar always returns None (cache miss),
    store is a no-op. Phase 3 replaces the bodies with QdrantClient +
    OpenAIEmbeddings.
    """

    async def find_similar(
        self, logs: str, threshold: float = 0.92
    ) -> dict | None:
        return None

    async def store(self, logs: str, analysis: dict) -> None:
        return None

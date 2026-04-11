class CrashMemory:
    """Qdrant vector cache for crash similarity matching.

    Placeholder — the user will implement:
    - Embedding crash logs with text-embedding-3-small
    - Storing in Qdrant collection 'crash_history'
    - Similarity search with threshold 0.92
    - Returning cached CrashAnalysis for matches
    """

    def __init__(self):
        pass

    async def find_similar(self, logs: str, threshold: float = 0.92) -> dict | None:
        """Search Qdrant for similar past crashes.

        Returns cached analysis dict if similarity > threshold, else None.
        """
        raise NotImplementedError(
            "Qdrant similarity search not yet implemented. "
            "Will use QdrantClient + OpenAIEmbeddings to find similar crash logs."
        )

    async def store(self, logs: str, analysis: dict) -> None:
        """Store crash logs + analysis in Qdrant for future matching."""
        raise NotImplementedError(
            "Qdrant storage not yet implemented. "
            "Will embed logs and store with analysis metadata."
        )

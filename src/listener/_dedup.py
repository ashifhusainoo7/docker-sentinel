import time


class DedupCache:
    """In-memory dedup for (host_id, container_id) within a time window.

    Entries older than the window are lazily removed on each write.
    """

    def __init__(self, window_seconds: float = 60.0):
        self.window = window_seconds
        self._cache: dict[tuple[str, str], float] = {}

    def is_duplicate(self, host_id: str, container_id: str) -> bool:
        now = time.monotonic()
        key = (host_id, container_id)
        last = self._cache.get(key)
        if last is not None and (now - last) < self.window:
            return True
        self._cache[key] = now
        self._cleanup(now)
        return False

    def _cleanup(self, now: float) -> None:
        cutoff = now - self.window
        self._cache = {k: v for k, v in self._cache.items() if v >= cutoff}

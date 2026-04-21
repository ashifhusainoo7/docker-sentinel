import time

from src.listener._dedup import DedupCache


def test_first_event_for_container_is_not_duplicate():
    cache = DedupCache(window_seconds=60)
    assert cache.is_duplicate("host-1", "container-abc") is False


def test_second_event_within_window_is_duplicate():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-1", "container-abc") is True


def test_different_containers_do_not_collide():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-1", "container-xyz") is False


def test_different_hosts_do_not_collide():
    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    assert cache.is_duplicate("host-2", "container-abc") is False


def test_event_outside_window_is_not_duplicate(monkeypatch):
    current = [1000.0]

    def fake_monotonic():
        return current[0]

    monkeypatch.setattr("src.listener._dedup.time.monotonic", fake_monotonic)

    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-abc")
    current[0] = 1061.0  # 61 seconds later
    assert cache.is_duplicate("host-1", "container-abc") is False


def test_lazy_cleanup_drops_stale_entries(monkeypatch):
    current = [1000.0]
    monkeypatch.setattr("src.listener._dedup.time.monotonic", lambda: current[0])

    cache = DedupCache(window_seconds=60)
    cache.is_duplicate("host-1", "container-old")
    current[0] = 1200.0  # well past window
    cache.is_duplicate("host-1", "container-new")

    assert ("host-1", "container-old") not in cache._cache
    assert ("host-1", "container-new") in cache._cache

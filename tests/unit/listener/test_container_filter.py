from src.listener._filter import should_monitor


def test_monitor_all_always_returns_true():
    assert should_monitor("anything", monitor_all=True, whitelist=[]) is True
    assert should_monitor("anything", monitor_all=True, whitelist=["x"]) is True


def test_monitor_none_with_empty_whitelist_returns_false():
    assert should_monitor("anything", monitor_all=False, whitelist=[]) is False


def test_whitelist_exact_match_returns_true():
    assert should_monitor("web-1", monitor_all=False, whitelist=["web-1", "api"]) is True


def test_whitelist_non_match_returns_false():
    assert should_monitor("db-1", monitor_all=False, whitelist=["web-1", "api"]) is False


def test_empty_container_name_returns_false_when_filtered():
    assert should_monitor("", monitor_all=False, whitelist=["web-1"]) is False

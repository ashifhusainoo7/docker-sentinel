import pytest

from src.orchestrator.nodes import should_restart, check_multi_crash, check_restart_result


def test_should_restart_true():
    state = {"analysis": {"restart_likely_fixes": True}}
    assert should_restart(state) == "attempt_restart"


def test_should_restart_false():
    state = {"analysis": {"restart_likely_fixes": False}}
    assert should_restart(state) == "notify_slack"


def test_should_restart_no_analysis():
    state = {"analysis": None}
    assert should_restart(state) == "notify_slack"


def test_check_restart_success():
    state = {"restart_success": True}
    assert check_restart_result(state) == "log"


def test_check_restart_failure():
    state = {"restart_success": False}
    assert check_restart_result(state) == "notify_slack"


def test_check_multi_crash_above_threshold():
    state = {"recent_crash_count": 3}
    assert check_multi_crash(state) == "make_call"


def test_check_multi_crash_below_threshold():
    state = {"recent_crash_count": 1}
    assert check_multi_crash(state) == "log"

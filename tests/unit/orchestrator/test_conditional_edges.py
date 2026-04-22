from src.orchestrator.nodes import check_restart_result, should_restart


def test_check_restart_result_true_goes_to_log():
    assert check_restart_result({"restart_success": True}) == "log"


def test_check_restart_result_false_goes_to_log_in_phase_1():
    """Phase 1: notify_slack is NotImplementedError, so failed restarts
    must still reach log_event. Revisit when Phase 2 implements notifications.
    """
    assert check_restart_result({"restart_success": False}) == "log"


def test_check_restart_result_none_goes_to_log_in_phase_1():
    assert check_restart_result({"restart_success": None}) == "log"


def test_check_restart_result_missing_key_goes_to_log_in_phase_1():
    assert check_restart_result({}) == "log"


def test_should_restart_true_goes_to_attempt_restart():
    state = {"analysis": {"restart_likely_fixes": True}}
    assert should_restart(state) == "attempt_restart"


def test_should_restart_false_goes_to_log_in_phase_2():
    """Phase 2: notify_slack is NotImplementedError, so non-restart analyses
    must still reach log_event. Phase 2.5 (notifications) restores the
    False → notify_slack edge.
    """
    state = {"analysis": {"restart_likely_fixes": False}}
    assert should_restart(state) == "log"


def test_should_restart_missing_analysis_goes_to_log():
    assert should_restart({"analysis": None}) == "log"
    assert should_restart({}) == "log"

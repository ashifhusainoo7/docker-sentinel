from src.orchestrator.nodes import check_restart_result


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

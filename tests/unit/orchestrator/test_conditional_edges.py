from src.orchestrator.nodes import check_restart_result, should_restart


# --- check_restart_result ---

def test_check_restart_result_true_goes_to_log():
    assert check_restart_result({"restart_success": True}) == "log"


def test_check_restart_result_false_goes_to_notify_slack():
    assert check_restart_result({"restart_success": False}) == "notify_slack"


def test_check_restart_result_none_goes_to_notify_slack():
    """Defensive: when restart wasn't attempted (host missing, non-TCP), also notify."""
    assert check_restart_result({"restart_success": None}) == "notify_slack"


def test_check_restart_result_missing_key_goes_to_notify_slack():
    assert check_restart_result({}) == "notify_slack"


# --- should_restart ---

def test_should_restart_true_goes_to_attempt_restart():
    state = {"analysis": {"restart_likely_fixes": True}}
    assert should_restart(state) == "attempt_restart"


def test_should_restart_false_goes_to_notify_slack():
    state = {"analysis": {"restart_likely_fixes": False}}
    assert should_restart(state) == "notify_slack"


def test_should_restart_missing_analysis_goes_to_notify_slack():
    assert should_restart({"analysis": None}) == "notify_slack"
    assert should_restart({}) == "notify_slack"

from src.agents._prompts import build_analysis_prompt


def _event(**overrides):
    base = {
        "container_name": "web-1",
        "image": "nginx:1.25",
        "exit_code": 137,
        "event_type": "die",
        "logs": "out of memory\nkilled process 42",
    }
    base.update(overrides)
    return base


def test_prompt_returns_system_and_user_messages():
    messages = build_analysis_prompt(_event())
    assert isinstance(messages, list)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_prompt_contains_container_and_exit_code():
    messages = build_analysis_prompt(_event(container_name="api-3", exit_code=1))
    user_content = messages[1]["content"]
    assert "api-3" in user_content
    assert "1" in user_content


def test_prompt_truncates_logs_to_last_200_lines():
    long_logs = "\n".join(f"line {i}" for i in range(500))
    messages = build_analysis_prompt(_event(logs=long_logs))
    user_content = messages[1]["content"]
    assert "line 300" in user_content  # within last 200
    assert "line 499" in user_content
    assert "line 0" not in user_content  # truncated


def test_prompt_handles_missing_logs():
    messages = build_analysis_prompt(_event(logs=None))
    user_content = messages[1]["content"]
    assert "<no logs captured>" in user_content


def test_prompt_handles_missing_container_name_and_image():
    messages = build_analysis_prompt(_event(container_name=None, image=None))
    user_content = messages[1]["content"]
    assert "<unknown>" in user_content

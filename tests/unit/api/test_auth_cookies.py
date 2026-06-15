from unittest.mock import MagicMock, patch

from src.services.auth_cookies import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    REFRESH_PATH,
    clear_auth_cookies,
    set_auth_cookies,
)


def _capture_set_cookie_calls():
    """Returns a MagicMock Response and a way to inspect set_cookie calls."""
    response = MagicMock()
    return response


def test_set_auth_cookies_writes_access_and_refresh():
    response = _capture_set_cookie_calls()
    set_auth_cookies(response, "access.jwt", "refresh.jwt")

    assert response.set_cookie.call_count == 2
    first = response.set_cookie.call_args_list[0].kwargs
    second = response.set_cookie.call_args_list[1].kwargs

    assert first["key"] == ACCESS_COOKIE
    assert first["value"] == "access.jwt"
    assert first["httponly"] is True
    assert first["samesite"] == "lax"
    assert first["path"] == "/"
    assert first["max_age"] == 30 * 60  # 30 minutes default

    assert second["key"] == REFRESH_COOKIE
    assert second["value"] == "refresh.jwt"
    assert second["httponly"] is True
    assert second["samesite"] == "lax"
    assert second["path"] == REFRESH_PATH
    assert second["max_age"] == 7 * 86400  # 7 days default


def test_set_auth_cookies_secure_in_production():
    response = _capture_set_cookie_calls()
    with patch("src.services.auth_cookies.settings") as s:
        s.environment = "production"
        s.jwt_access_token_expire_minutes = 30
        s.jwt_refresh_token_expire_days = 7
        set_auth_cookies(response, "a", "r")

    for call in response.set_cookie.call_args_list:
        assert call.kwargs["secure"] is True


def test_set_auth_cookies_insecure_in_development():
    response = _capture_set_cookie_calls()
    with patch("src.services.auth_cookies.settings") as s:
        s.environment = "development"
        s.jwt_access_token_expire_minutes = 30
        s.jwt_refresh_token_expire_days = 7
        set_auth_cookies(response, "a", "r")

    for call in response.set_cookie.call_args_list:
        assert call.kwargs["secure"] is False


def test_clear_auth_cookies_deletes_both():
    response = _capture_set_cookie_calls()
    clear_auth_cookies(response)

    assert response.delete_cookie.call_count == 2
    first = response.delete_cookie.call_args_list[0]
    second = response.delete_cookie.call_args_list[1]

    # delete_cookie's first positional arg is the key; path kwarg identifies scope
    args_first = first.args + tuple(first.kwargs.values())
    args_second = second.args + tuple(second.kwargs.values())
    assert ACCESS_COOKIE in args_first
    assert REFRESH_COOKIE in args_second
    assert "/" in args_first or first.kwargs.get("path") == "/"
    assert REFRESH_PATH in args_second or second.kwargs.get("path") == REFRESH_PATH

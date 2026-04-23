import uuid

import pytest

from src.services import auth_service


def test_create_ws_token_has_ws_type_and_60s_expiry():
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    token = auth_service.create_ws_token(user_id, tenant_id)
    payload = auth_service.decode_token(token)

    assert payload["type"] == "ws"
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    # exp - iat must be exactly 60 seconds
    assert payload["exp"] - payload["iat"] == 60

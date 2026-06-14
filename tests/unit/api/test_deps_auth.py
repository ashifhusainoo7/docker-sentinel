import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.api.deps import get_current_user
from src.services import auth_service


@pytest.fixture
def user_id():
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def tenant_id():
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def valid_access_token(user_id, tenant_id):
    return auth_service.create_access_token(user_id, tenant_id)


@pytest.fixture
def fake_user(user_id, tenant_id):
    u = MagicMock()
    u.id = user_id
    u.tenant_id = tenant_id
    u.is_active = True
    return u


def _request_with_cookies(cookies: dict):
    req = MagicMock()
    req.cookies = cookies
    return req


def _db_returning(user):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_get_current_user_reads_cookie(valid_access_token, fake_user):
    request = _request_with_cookies({"access_token": valid_access_token})
    db = _db_returning(fake_user)

    result = await get_current_user(request, db, authorization=None)
    assert result is fake_user


@pytest.mark.asyncio
async def test_get_current_user_falls_back_to_authorization_header(
    valid_access_token, fake_user
):
    request = _request_with_cookies({})
    db = _db_returning(fake_user)

    result = await get_current_user(
        request, db, authorization=f"Bearer {valid_access_token}"
    )
    assert result is fake_user


@pytest.mark.asyncio
async def test_get_current_user_prefers_cookie_over_header(
    valid_access_token, fake_user, user_id, tenant_id
):
    cookie_token = valid_access_token
    header_token = auth_service.create_access_token(uuid.uuid4(), uuid.uuid4())

    request = _request_with_cookies({"access_token": cookie_token})
    db = _db_returning(fake_user)

    await get_current_user(
        request, db, authorization=f"Bearer {header_token}"
    )
    # Assert the cookie token's user_id was used for the DB lookup
    stmt = db.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    assert str(user_id) in compiled or user_id.hex in compiled


@pytest.mark.asyncio
async def test_get_current_user_401_when_no_token():
    request = _request_with_cookies({})
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(request, db, authorization=None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_401_when_token_expired(user_id, tenant_id, fake_user):
    import jwt

    from config.settings import settings

    # Build an expired token
    expired = jwt.encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "type": "access", "exp": 0},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    request = _request_with_cookies({"access_token": expired})
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await get_current_user(request, db, authorization=None)
    assert exc.value.status_code == 401

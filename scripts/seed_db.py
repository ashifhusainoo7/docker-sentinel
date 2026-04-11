"""Seed the database with test data for development.

Usage: python scripts/seed_db.py
"""

import asyncio
import uuid

from sqlalchemy import text

from src.models.tenant import Tenant
from src.models.user import User
from src.models.docker_host import DockerHost
from src.services.database import async_session_factory


async def seed():
    async with async_session_factory() as db:
        # Create test tenant
        tenant = Tenant(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="Test Workspace",
            slug="test-workspace",
        )
        db.add(tenant)

        # Create test user
        user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            tenant_id=tenant.id,
            email="test@example.com",
            name="Test User",
            role="owner",
            oauth_provider="github",
            oauth_provider_id="12345",
        )
        db.add(user)

        # Create test Docker host (TCP mode)
        host = DockerHost(
            id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            tenant_id=tenant.id,
            name="Dev Server",
            connection_mode="tcp",
            tcp_url="tcp://localhost:2375",
            status="connected",
        )
        db.add(host)

        await db.commit()
        print("Database seeded successfully!")
        print(f"  Tenant: {tenant.name} ({tenant.id})")
        print(f"  User: {user.email} ({user.id})")
        print(f"  Host: {host.name} ({host.id})")


if __name__ == "__main__":
    asyncio.run(seed())

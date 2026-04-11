"""Generate an API key for a tenant.

Usage: python scripts/generate_api_key.py --tenant-id <uuid> --name "My Agent Key"
"""

import argparse
import asyncio
import uuid

from src.services.api_key_service import create_api_key
from src.schemas.api_key import ApiKeyCreate
from src.services.database import async_session_factory


async def generate(tenant_id: str, name: str):
    async with async_session_factory() as db:
        data = ApiKeyCreate(name=name, scopes=["agent"])
        api_key, full_key = await create_api_key(
            db, uuid.UUID(tenant_id), None, data
        )
        await db.commit()

        print(f"API Key created successfully!")
        print(f"  Name: {api_key.name}")
        print(f"  Key: {full_key}")
        print(f"  Prefix: {api_key.key_prefix}")
        print(f"\n  Save this key — it cannot be retrieved again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an API key")
    parser.add_argument("--tenant-id", required=True, help="Tenant UUID")
    parser.add_argument("--name", required=True, help="Key name/description")
    args = parser.parse_args()
    asyncio.run(generate(args.tenant_id, args.name))

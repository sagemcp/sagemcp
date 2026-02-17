"""Bootstrap admin API key on first startup with auth enabled."""

import logging

from sqlalchemy import select, func

from ..config import get_settings
from ..database.connection import get_db_context
from ..models.api_key import APIKey, APIKeyScope
from .auth import generate_api_key, hash_api_key

logger = logging.getLogger(__name__)


async def bootstrap_admin_key() -> None:
    """Create a platform_admin key if none exist and bootstrap config is set.

    Called from lifespan after table creation. Idempotent — skips if any
    active API key already exists.
    """
    settings = get_settings()
    if not settings.enable_auth:
        return

    async with get_db_context() as session:
        # Check if any API keys exist
        result = await session.execute(
            select(func.count()).select_from(APIKey).where(APIKey.is_active.is_(True))
        )
        count = result.scalar()
        if count and count > 0:
            logger.debug("API keys already exist, skipping bootstrap")
            return

        # Use explicit bootstrap key from env if provided
        bootstrap_key = settings.bootstrap_admin_key
        if bootstrap_key:
            raw_key = bootstrap_key
        else:
            raw_key = generate_api_key(APIKeyScope.PLATFORM_ADMIN)

        key_hash = hash_api_key(raw_key)
        api_key = APIKey(
            name="Bootstrap Admin Key",
            key_prefix=raw_key[:8],
            key_hash=key_hash,
            scope=APIKeyScope.PLATFORM_ADMIN,
            tenant_id=None,
            is_active=True,
        )
        session.add(api_key)
        await session.commit()

        if not bootstrap_key:
            # Only print when auto-generated — the user needs to save it
            logger.warning(
                "No API keys found. Auto-generated platform admin key:\n"
                "  %s\n"
                "Save this key — it cannot be retrieved later.",
                raw_key,
            )
        else:
            logger.info("Bootstrapped platform admin key from SAGEMCP_BOOTSTRAP_ADMIN_KEY")

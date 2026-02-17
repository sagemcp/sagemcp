"""Admin API for server pool introspection and management."""

import time
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from ..models.api_key import APIKeyScope
from ..security.auth import require_scope

router = APIRouter()


@router.get("/pool", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def list_pool_entries(request: Request, tenant_slug: Optional[str] = Query(None)):
    """List all entries in the server pool."""
    pool = getattr(request.app.state, "server_pool", None)
    if pool is None:
        return []

    now = time.monotonic()
    entries = []
    for key, entry in pool._pool.items():
        parts = key.split(":", 1)
        t_slug = parts[0] if len(parts) > 0 else ""
        c_id = parts[1] if len(parts) > 1 else ""

        if tenant_slug and t_slug != tenant_slug:
            continue

        ttl_remaining = max(0, pool.ttl_seconds - (now - entry.created_at))
        entries.append({
            "key": key,
            "tenant_slug": t_slug,
            "connector_id": c_id,
            "created_at": round(now - entry.created_at, 1),
            "last_access": round(now - entry.last_access, 1),
            "hit_count": entry.hit_count,
            "ttl_remaining": round(ttl_remaining, 1),
            "status": "healthy" if ttl_remaining > 300 else "expiring" if ttl_remaining > 0 else "expired",
        })

    return entries


@router.get("/pool/summary", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def pool_summary(request: Request):
    """Get aggregated pool statistics."""
    pool = getattr(request.app.state, "server_pool", None)
    if pool is None:
        return {
            "total": 0,
            "max_size": 0,
            "ttl_seconds": 0,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0,
            "by_tenant": {},
            "by_status": {"healthy": 0, "expiring": 0, "expired": 0},
            "memory_estimate_kb": 0,
        }

    now = time.monotonic()
    by_tenant: dict[str, int] = {}
    by_status = {"healthy": 0, "expiring": 0, "expired": 0}

    for key, entry in pool._pool.items():
        t_slug = key.split(":", 1)[0]
        by_tenant[t_slug] = by_tenant.get(t_slug, 0) + 1

        ttl_remaining = pool.ttl_seconds - (now - entry.created_at)
        if ttl_remaining > 300:
            by_status["healthy"] += 1
        elif ttl_remaining > 0:
            by_status["expiring"] += 1
        else:
            by_status["expired"] += 1

    total_requests = pool.hits + pool.misses
    return {
        "total": pool.size,
        "max_size": pool.max_size,
        "ttl_seconds": pool.ttl_seconds,
        "hits": pool.hits,
        "misses": pool.misses,
        "hit_rate": round(pool.hits / total_requests * 100, 1) if total_requests > 0 else 0,
        "by_tenant": by_tenant,
        "by_status": by_status,
        "memory_estimate_kb": round(pool.size * 5, 1),
    }


@router.delete("/pool/{tenant_slug}/{connector_id}", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def evict_pool_entry(request: Request, tenant_slug: str, connector_id: str):
    """Evict a specific entry from the pool."""
    pool = getattr(request.app.state, "server_pool", None)
    if pool is None:
        return {"evicted": False, "message": "Pool not available"}

    pool.invalidate(tenant_slug, connector_id)
    return {"evicted": True, "pool_size": pool.size}


@router.post("/pool/evict-idle", dependencies=[Depends(require_scope(APIKeyScope.PLATFORM_ADMIN))])
async def evict_idle(request: Request, idle_seconds: float = Query(default=600)):
    """Evict entries idle longer than the given threshold."""
    pool = getattr(request.app.state, "server_pool", None)
    if pool is None:
        return {"evicted_count": 0, "pool_size": 0}

    now = time.monotonic()
    idle_keys = [
        key for key, entry in pool._pool.items()
        if (now - entry.last_access) >= idle_seconds
    ]
    for key in idle_keys:
        del pool._pool[key]

    return {"evicted_count": len(idle_keys), "pool_size": pool.size}

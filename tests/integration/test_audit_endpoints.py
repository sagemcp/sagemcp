"""Integration tests for audit log query endpoints."""

import asyncio
import threading
import uuid
from datetime import datetime, timezone, timedelta

import pytest

from sage_mcp.models.audit_log import AuditLog
from sage_mcp.models.tenant import Tenant
from tests.conftest import TestingAsyncSessionLocal


# ---------------------------------------------------------------------------
# Async DB helper — runs coroutine on a background thread so it works
# inside synchronous TestClient tests.
# ---------------------------------------------------------------------------

def _run_async(coro_fn):
    """Run an async function on a background thread (new event loop)."""
    result_box = [None, None]  # [result, exception]

    def _target():
        try:
            result_box[0] = asyncio.run(coro_fn())
        except Exception as e:
            result_box[1] = e

    t = threading.Thread(target=_target)
    t.start()
    t.join()
    if result_box[1]:
        raise result_box[1]
    return result_box[0]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_audit_logs():
    """Delete all audit_logs and test tenants from the async DB between tests."""
    yield

    async def _cleanup():
        async with TestingAsyncSessionLocal() as session:
            from sqlalchemy import delete
            await session.execute(delete(AuditLog))
            # Clean up tenants created by _seed_tenant_async
            await session.execute(
                delete(Tenant).where(Tenant.slug.like("audit-%"))
            )
            await session.commit()

    _run_async(_cleanup)


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_audit_rows(count=5, tenant_id=None, action="tenant.create"):
    """Insert audit rows via the async test DB."""

    async def _insert():
        async with TestingAsyncSessionLocal() as session:
            for i in range(count):
                row = AuditLog(
                    id=uuid.uuid4(),
                    timestamp=datetime.now(timezone.utc) - timedelta(seconds=count - i),
                    actor_id=f"actor-{i}",
                    actor_type="api_key",
                    action=action,
                    resource_type="tenant",
                    resource_id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    ip_address="127.0.0.1",
                    user_agent="test",
                )
                session.add(row)
            await session.commit()

    _run_async(_insert)


def _seed_tenant(slug="audit-test-tenant", name="Audit Test Tenant"):
    """Insert a tenant via the async test DB and return {id, slug}."""

    async def _insert():
        async with TestingAsyncSessionLocal() as session:
            tenant = Tenant(slug=slug, name=name, is_active=True)
            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)
            return {"id": tenant.id, "slug": tenant.slug}

    return _run_async(_insert)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/audit (platform admin)
# ---------------------------------------------------------------------------

class TestPlatformAuditEndpoint:

    def test_list_audit_logs_returns_items(self, client):
        _seed_audit_rows(count=3)
        resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_list_audit_logs_pagination(self, client):
        _seed_audit_rows(count=5)
        resp = client.get("/api/v1/admin/audit?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

        resp2 = client.get("/api/v1/admin/audit?limit=2&offset=2")
        body2 = resp2.json()
        assert len(body2["items"]) == 2
        page1_ids = {item["id"] for item in body["items"]}
        page2_ids = {item["id"] for item in body2["items"]}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_audit_logs_filter_by_action(self, client):
        _seed_audit_rows(count=3, action="tenant.create")
        _seed_audit_rows(count=2, action="connector.delete")
        resp = client.get("/api/v1/admin/audit?action=connector.delete")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert all(item["action"] == "connector.delete" for item in body["items"])

    def test_list_audit_logs_filter_by_actor_id(self, client):
        _seed_audit_rows(count=3)
        resp = client.get("/api/v1/admin/audit?actor_id=actor-0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["actor_id"] == "actor-0"

    def test_list_audit_logs_empty_result(self, client):
        resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_audit_logs_ordered_by_timestamp_desc(self, client):
        _seed_audit_rows(count=3)
        resp = client.get("/api/v1/admin/audit")
        body = resp.json()
        timestamps = [item["timestamp"] for item in body["items"]]
        assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# GET /api/v1/admin/tenants/{slug}/audit (tenant scoped)
# ---------------------------------------------------------------------------

class TestTenantAuditEndpoint:

    def test_tenant_audit_scoped_to_tenant(self, client):
        tenant = _seed_tenant(slug="audit-scope-t")
        tid = tenant["id"]
        _seed_audit_rows(tenant_id=tid, count=3, action="connector.create")
        _seed_audit_rows(tenant_id=None, count=2, action="system.startup")

        resp = client.get(f"/api/v1/admin/tenants/{tenant['slug']}/audit")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert all(item["tenant_id"] == str(tid) for item in body["items"])

    def test_tenant_audit_filter_by_action(self, client):
        tenant = _seed_tenant(slug="audit-filter-t")
        tid = tenant["id"]
        _seed_audit_rows(tenant_id=tid, count=2, action="connector.create")
        _seed_audit_rows(tenant_id=tid, count=1, action="tool.toggle")

        resp = client.get(f"/api/v1/admin/tenants/{tenant['slug']}/audit?action=tool.toggle")
        body = resp.json()
        assert body["total"] == 1

    def test_tenant_audit_pagination(self, client):
        tenant = _seed_tenant(slug="audit-page-t")
        tid = tenant["id"]
        _seed_audit_rows(tenant_id=tid, count=5)

        resp = client.get(f"/api/v1/admin/tenants/{tenant['slug']}/audit?limit=2&offset=0")
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 5

    def test_tenant_audit_404_for_unknown_tenant(self, client):
        resp = client.get("/api/v1/admin/tenants/nonexistent/audit")
        assert resp.status_code == 404

    def test_tenant_audit_time_range_filter(self, client):
        tenant = _seed_tenant(slug="audit-time-t")
        tid = tenant["id"]
        now = datetime.now(timezone.utc)

        async def _insert_timed():
            async with TestingAsyncSessionLocal() as session:
                session.add(AuditLog(
                    id=uuid.uuid4(),
                    timestamp=now - timedelta(hours=1),
                    actor_id="actor-old",
                    actor_type="api_key",
                    action="old.action",
                    tenant_id=tid,
                ))
                session.add(AuditLog(
                    id=uuid.uuid4(),
                    timestamp=now,
                    actor_id="actor-new",
                    actor_type="api_key",
                    action="new.action",
                    tenant_id=tid,
                ))
                await session.commit()

        _run_async(_insert_timed)

        start_ts = now - timedelta(minutes=5)
        resp = client.get(
            f"/api/v1/admin/tenants/{tenant['slug']}/audit",
            params={"start": start_ts.isoformat()},
        )
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["action"] == "new.action"

"""Integration tests for global tool policy admin endpoints.

Tests the full CRUD lifecycle via the FastAPI test client.
Uses the conftest ``client`` fixture (auth disabled, SQLite in-memory).
"""

import uuid

import pytest

from sage_mcp.security.tool_policy import invalidate_policy_cache


@pytest.fixture(autouse=True)
def _clean_policy_cache():
    """Ensure policy cache is clean between tests."""
    invalidate_policy_cache()
    yield
    invalidate_policy_cache()


class TestToolPolicyCRUD:
    """Full CRUD lifecycle for /admin/policies/tools."""

    def test_list_empty(self, client):
        resp = client.get("/api/v1/admin/policies/tools")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_policy(self, client):
        payload = {
            "tool_name_pattern": "github_delete_*",
            "action": "block",
            "reason": "Destructive action",
            "connector_type": "github",
        }
        resp = client.post("/api/v1/admin/policies/tools", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["tool_name_pattern"] == "github_delete_*"
        assert data["action"] == "block"
        assert data["reason"] == "Destructive action"
        assert data["connector_type"] == "github"
        assert data["is_active"] is True
        assert "id" in data

    def test_create_and_list(self, client):
        payload = {
            "tool_name_pattern": "slack_send_*",
            "action": "warn",
            "reason": "Review messages",
        }
        create_resp = client.post("/api/v1/admin/policies/tools", json=payload)
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        list_resp = client.get("/api/v1/admin/policies/tools")
        assert list_resp.status_code == 200
        policies = list_resp.json()
        assert any(p["id"] == policy_id for p in policies)

    def test_update_policy(self, client):
        # Create
        create_resp = client.post("/api/v1/admin/policies/tools", json={
            "tool_name_pattern": "jira_delete_*",
            "action": "warn",
            "reason": "Be careful",
        })
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        # Update
        update_resp = client.put(f"/api/v1/admin/policies/tools/{policy_id}", json={
            "action": "block",
            "reason": "Now blocked",
        })
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["action"] == "block"
        assert data["reason"] == "Now blocked"
        assert data["tool_name_pattern"] == "jira_delete_*"

    def test_delete_policy(self, client):
        # Create
        create_resp = client.post("/api/v1/admin/policies/tools", json={
            "tool_name_pattern": "temp_policy",
            "action": "block",
            "reason": "Temporary",
        })
        assert create_resp.status_code == 201
        policy_id = create_resp.json()["id"]

        # Delete
        del_resp = client.delete(f"/api/v1/admin/policies/tools/{policy_id}")
        assert del_resp.status_code == 200
        assert "deleted" in del_resp.json()["message"].lower()

        # Verify gone
        list_resp = client.get("/api/v1/admin/policies/tools")
        assert all(p["id"] != policy_id for p in list_resp.json())

    def test_update_nonexistent_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.put(f"/api/v1/admin/policies/tools/{fake_id}", json={
            "action": "block",
        })
        assert resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = client.delete(f"/api/v1/admin/policies/tools/{fake_id}")
        assert resp.status_code == 404

    def test_create_with_defaults(self, client):
        """Create policy with minimal fields — defaults apply."""
        resp = client.post("/api/v1/admin/policies/tools", json={
            "tool_name_pattern": "notion_*",
            "action": "warn",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is True
        assert data["reason"] is None
        assert data["connector_type"] is None

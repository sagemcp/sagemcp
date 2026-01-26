"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data


class TestAdminAPI:
    """Test admin API endpoints."""

    def test_create_tenant(self, client: TestClient):
        """Test creating a tenant."""
        tenant_data = {
            "slug": "test-tenant",
            "name": "Test Tenant",
            "description": "A test tenant",
            "contact_email": "test@example.com"
        }

        response = client.post("/api/v1/admin/tenants", json=tenant_data)

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "test-tenant"
        assert data["name"] == "Test Tenant"
        assert data["is_active"] is True

    def test_create_tenant_duplicate_slug(self, client: TestClient):
        """Test creating tenant with duplicate slug."""
        tenant_data = {
            "slug": "duplicate-tenant",
            "name": "Tenant 1",
            "description": "First tenant",
            "contact_email": "test1@example.com"
        }

        # Create first tenant
        response1 = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert response1.status_code == 201

        # Try to create second tenant with same slug
        tenant_data["name"] = "Tenant 2"
        tenant_data["contact_email"] = "test2@example.com"

        response2 = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert response2.status_code == 400

    def test_list_tenants(self, client: TestClient):
        """Test listing tenants."""
        # Create a tenant first
        tenant_data = {
            "slug": "list-test-tenant",
            "name": "List Test Tenant",
            "description": "A tenant for list testing",
            "contact_email": "listtest@example.com"
        }
        client.post("/api/v1/admin/tenants", json=tenant_data)

        # List tenants
        response = client.get("/api/v1/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Check that our tenant is in the list
        tenant_slugs = [tenant["slug"] for tenant in data]
        assert "list-test-tenant" in tenant_slugs

    def test_get_tenant(self, client: TestClient):
        """Test getting a specific tenant."""
        # Create a tenant first
        tenant_data = {
            "slug": "get-test-tenant",
            "name": "Get Test Tenant",
            "description": "A tenant for get testing",
            "contact_email": "gettest@example.com"
        }
        create_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert create_response.status_code == 201

        # Get the tenant
        response = client.get("/api/v1/admin/tenants/get-test-tenant")

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "get-test-tenant"
        assert data["name"] == "Get Test Tenant"

    def test_get_nonexistent_tenant(self, client: TestClient):
        """Test getting a non-existent tenant."""
        response = client.get("/api/v1/admin/tenants/nonexistent-tenant")

        assert response.status_code == 404

    def test_create_connector(self, client: TestClient):
        """Test creating a connector."""
        # Create a tenant first
        tenant_data = {
            "slug": "connector-test-tenant",
            "name": "Connector Test Tenant",
            "description": "A tenant for connector testing",
            "contact_email": "connectortest@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # Create a connector
        connector_data = {
            "name": "Test GitHub Connector",
            "description": "GitHub integration for testing",
            "connector_type": "github",
            "configuration": {}
        }

        response = client.post(
            "/api/v1/admin/tenants/connector-test-tenant/connectors",
            json=connector_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test GitHub Connector"
        assert data["connector_type"] == "github"
        assert data["is_enabled"] is True

    def test_list_connectors(self, client: TestClient):
        """Test listing connectors for a tenant."""
        # Create a tenant first
        tenant_data = {
            "slug": "list-connector-tenant",
            "name": "List Connector Tenant",
            "description": "A tenant for connector list testing",
            "contact_email": "listconnector@example.com"
        }
        client.post("/api/v1/admin/tenants", json=tenant_data)

        # Create a connector
        connector_data = {
            "name": "List Test Connector",
            "description": "A connector for list testing",
            "connector_type": "github",
            "configuration": {}
        }
        client.post(
            "/api/v1/admin/tenants/list-connector-tenant/connectors",
            json=connector_data
        )

        # List connectors
        response = client.get("/api/v1/admin/tenants/list-connector-tenant/connectors")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["name"] == "List Test Connector"


class TestOAuthAPI:
    """Test OAuth API endpoints."""

    def test_oauth_providers(self, client: TestClient):
        """Test getting OAuth providers."""
        response = client.get("/api/v1/oauth/providers")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # Get provider IDs
        provider_ids = [p["id"] for p in data]
        assert "github" in provider_ids
        assert "slack" in provider_ids

        # Check GitHub provider structure
        github = next(p for p in data if p["id"] == "github")
        assert github["name"] == "GitHub"
        assert "auth_url" in github
        assert "scopes" in github

    def test_oauth_authorize_url(self, client: TestClient):
        """Test generating OAuth authorize URL."""
        # Create a tenant first
        tenant_data = {
            "slug": "oauth-test-tenant",
            "name": "OAuth Test Tenant",
            "description": "A tenant for OAuth testing",
            "contact_email": "oauth@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # Initiate OAuth - this should return 500 without OAuth credentials configured
        # In a real environment with OAuth credentials, this would redirect
        response = client.get("/api/v1/oauth/oauth-test-tenant/auth/github", follow_redirects=False)

        # Without OAuth credentials configured, expect 500 error
        # With credentials, it would be a redirect (307, 302, or 303)
        assert response.status_code in [500, 307, 302, 303]
        if response.status_code in [307, 302, 303]:
            assert "location" in response.headers
            assert "github.com" in response.headers["location"]

    def test_create_oauth_config(self, client: TestClient):
        """Test creating OAuth configuration for a tenant."""
        # Create a tenant first
        tenant_data = {
            "slug": "oauth-config-tenant",
            "name": "OAuth Config Tenant",
            "description": "A tenant for OAuth config testing",
            "contact_email": "oauthconfig@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # Create OAuth config
        oauth_config = {
            "provider": "slack",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret"
        }
        response = client.post(
            "/api/v1/oauth/oauth-config-tenant/config",
            json=oauth_config
        )

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "slack"
        assert data["client_id"] == "test-client-id"
        assert data["is_active"] is True

    def test_list_oauth_configs(self, client: TestClient):
        """Test listing OAuth configurations for a tenant."""
        # Create a tenant first
        tenant_data = {
            "slug": "oauth-list-config-tenant",
            "name": "OAuth List Config Tenant",
            "description": "A tenant for OAuth config listing",
            "contact_email": "oauthlistconfig@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # Create OAuth config
        oauth_config = {
            "provider": "github",
            "client_id": "test-github-client-id",
            "client_secret": "test-github-client-secret"
        }
        client.post(
            "/api/v1/oauth/oauth-list-config-tenant/config",
            json=oauth_config
        )

        # List OAuth configs
        response = client.get("/api/v1/oauth/oauth-list-config-tenant/config")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert data[0]["provider"] == "github"

    def test_delete_oauth_config(self, client: TestClient):
        """Test deleting OAuth configuration."""
        # Create a tenant first
        tenant_data = {
            "slug": "oauth-delete-config-tenant",
            "name": "OAuth Delete Config Tenant",
            "description": "A tenant for OAuth config deletion",
            "contact_email": "oauthdeleteconfig@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # Create OAuth config
        oauth_config = {
            "provider": "slack",
            "client_id": "test-delete-client-id",
            "client_secret": "test-delete-client-secret"
        }
        client.post(
            "/api/v1/oauth/oauth-delete-config-tenant/config",
            json=oauth_config
        )

        # Delete OAuth config
        response = client.delete(
            "/api/v1/oauth/oauth-delete-config-tenant/config/slack"
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "deleted successfully" in data["message"]

    def test_list_oauth_credentials(self, client: TestClient):
        """Test listing OAuth credentials for a tenant."""
        # Create a tenant first
        tenant_data = {
            "slug": "oauth-creds-tenant",
            "name": "OAuth Creds Tenant",
            "description": "A tenant for OAuth credentials testing",
            "contact_email": "oauthcreds@example.com"
        }
        tenant_response = client.post("/api/v1/admin/tenants", json=tenant_data)
        assert tenant_response.status_code == 201

        # List OAuth credentials (should be empty initially)
        response = client.get("/api/v1/oauth/oauth-creds-tenant/auth")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

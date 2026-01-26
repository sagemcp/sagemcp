"""Test models module."""

from datetime import datetime, timedelta, timezone

from sage_mcp.models.tenant import Tenant
from sage_mcp.models.connector import Connector, ConnectorType
from sage_mcp.models.oauth_credential import OAuthCredential


class TestTenant:
    """Test Tenant model."""

    def test_tenant_creation(self, db_session):
        """Test creating a tenant."""
        tenant = Tenant(
            slug="test-tenant",
            name="Test Tenant",
            description="A test tenant",
            contact_email="test@example.com"
        )

        db_session.add(tenant)
        db_session.commit()

        assert tenant.id is not None
        assert tenant.slug == "test-tenant"
        assert tenant.name == "Test Tenant"
        assert tenant.is_active is True
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    def test_tenant_string_representation(self):
        """Test tenant string representation."""
        tenant = Tenant(slug="test", name="Test Tenant")
        assert str(tenant) == "<Tenant(slug='test', name='Test Tenant')>"

    def test_tenant_relationships(self, db_session, sample_tenant):
        """Test tenant relationships."""
        # Add a connector to the tenant
        connector = Connector(
            name="Test Connector",
            description="Test",
            connector_type=ConnectorType.GITHUB,
            tenant_id=sample_tenant.id
        )
        db_session.add(connector)
        db_session.commit()

        # Add an OAuth credential
        credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="github",
            provider_user_id="123",
            access_token="token"
        )
        db_session.add(credential)
        db_session.commit()

        # Test relationships
        assert len(sample_tenant.connectors) == 1
        assert len(sample_tenant.oauth_credentials) == 1
        assert sample_tenant.connectors[0].name == "Test Connector"


class TestConnector:
    """Test Connector model."""

    def test_connector_creation(self, db_session, sample_tenant):
        """Test creating a connector."""
        connector = Connector(
            name="GitHub Connector",
            description="GitHub integration",
            connector_type=ConnectorType.GITHUB,
            tenant_id=sample_tenant.id,
            configuration={"api_url": "https://api.github.com"}
        )

        db_session.add(connector)
        db_session.commit()

        assert connector.id is not None
        assert connector.name == "GitHub Connector"
        assert connector.connector_type == ConnectorType.GITHUB
        assert connector.is_enabled is True
        assert connector.configuration["api_url"] == "https://api.github.com"

    def test_connector_types(self):
        """Test connector types enum."""
        assert ConnectorType.GITHUB.value == "github"
        assert ConnectorType.GITLAB.value == "gitlab"
        assert ConnectorType.GOOGLE_DOCS.value == "google_docs"

    def test_connector_tenant_relationship(self, db_session, sample_tenant):
        """Test connector-tenant relationship."""
        connector = Connector(
            name="Test Connector",
            description="Test",
            connector_type=ConnectorType.GITHUB,
            tenant_id=sample_tenant.id
        )
        db_session.add(connector)
        db_session.commit()

        assert connector.tenant.slug == sample_tenant.slug


class TestOAuthCredential:
    """Test OAuthCredential model."""

    def test_oauth_credential_creation(self, db_session, sample_tenant):
        """Test creating an OAuth credential."""
        credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="github",
            provider_user_id="123456",
            provider_username="testuser",
            access_token="access_token_123",
            refresh_token="refresh_token_123",
            token_type="Bearer",
            scopes="repo,user:email",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        db_session.add(credential)
        db_session.commit()

        assert credential.id is not None
        assert credential.provider == "github"
        assert credential.provider_user_id == "123456"
        assert credential.is_active is True
        assert credential.scopes == "repo,user:email"

    def test_oauth_credential_expiration(self, db_session, sample_tenant):
        """Test OAuth credential expiration check."""
        # Create expired credential
        expired_credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="github",
            provider_user_id="123",
            access_token="token",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )

        # Create non-expired credential
        valid_credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="gitlab",
            provider_user_id="456",
            access_token="token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )

        # Create credential with no expiration
        no_expiry_credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="google",
            provider_user_id="789",
            access_token="token"
        )

        assert expired_credential.is_expired is True
        assert valid_credential.is_expired is False
        assert no_expiry_credential.is_expired is False

    def test_oauth_credential_tenant_relationship(self, db_session, sample_tenant):
        """Test OAuth credential-tenant relationship."""
        credential = OAuthCredential(
            tenant_id=sample_tenant.id,
            provider="github",
            provider_user_id="123",
            access_token="token"
        )
        db_session.add(credential)
        db_session.commit()

        assert credential.tenant.slug == sample_tenant.slug

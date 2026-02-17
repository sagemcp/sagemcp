"""Test configuration and fixtures."""

import pytest
import asyncio
import os
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set test environment variables BEFORE importing the app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_PROVIDER"] = "postgresql"  # Use postgresql for tests (even with SQLite)
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from sage_mcp.main import app
from sage_mcp.database.connection import get_db_session, db_manager
from sage_mcp.models.base import Base
from sage_mcp.models.tenant import Tenant
from sage_mcp.models.connector import Connector, ConnectorType
from sage_mcp.models.oauth_credential import OAuthCredential
from sage_mcp.models.api_key import APIKey


# Always use SQLite for tests to avoid PostgreSQL driver dependencies
TEST_DATABASE_URL = "sqlite:///:memory:"
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine with SQLite-specific configuration (synchronous for unit tests)
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create async test engine for integration tests
test_async_engine = create_async_engine(
    TEST_ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestingAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(event_loop):
    """Create tables before tests and drop them after."""
    # Create all tables for sync engine
    Base.metadata.create_all(bind=test_engine)

    # Create all tables for async engine
    async def create_async_tables():
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(create_async_tables())

    yield

    # Drop all tables after all tests
    async def drop_async_tables():
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_async_engine.dispose()

    Base.metadata.drop_all(bind=test_engine)
    event_loop.run_until_complete(drop_async_tables())


@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean up database between tests."""
    yield
    # Clean up all data after each test
    session = TestingSessionLocal()
    try:
        # Delete in correct order to avoid foreign key constraints
        session.query(OAuthCredential).delete()
        session.query(Connector).delete()
        try:
            session.query(APIKey).delete()
        except Exception:
            session.rollback()
        session.query(Tenant).delete()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def db_session():
    """Create a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client with database override."""
    async def override_get_db_session():
        async with TestingAsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_tenant(db_session) -> Tenant:
    """Create a sample tenant for testing."""
    tenant = Tenant(
        slug="test-tenant",
        name="Test Tenant",
        description="A test tenant",
        contact_email="test@example.com",
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def sample_connector(db_session, sample_tenant) -> Connector:
    """Create a sample connector for testing."""
    connector = Connector(
        name="Test GitHub Connector",
        description="GitHub integration for testing",
        connector_type=ConnectorType.GITHUB,
        tenant_id=sample_tenant.id,
        is_enabled=True,
        configuration={}
    )
    db_session.add(connector)
    db_session.commit()
    db_session.refresh(connector)
    return connector


@pytest.fixture
def sample_oauth_credential(db_session, sample_tenant) -> OAuthCredential:
    """Create a sample OAuth credential for testing."""
    credential = OAuthCredential(
        tenant_id=sample_tenant.id,
        provider="github",
        provider_user_id="123456",
        provider_username="testuser",
        access_token="test_access_token",
        token_type="Bearer",
        scopes="repo,user:email,read:org",
        is_active=True
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential


@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses."""
    mock = Mock()
    mock.json.return_value = {
        "login": "testuser",
        "id": 123456,
        "type": "User",
        "name": "Test User",
        "public_repos": 5,
        "total_private_repos": 2
    }
    mock.headers = {
        "X-OAuth-Scopes": "repo, user:email, read:org",
        "X-Accepted-OAuth-Scopes": ""
    }
    return mock


@pytest.fixture
def mock_mcp_server():
    """Mock MCP server for testing."""
    mock = AsyncMock()
    mock.initialize.return_value = True
    mock.connectors = []
    return mock

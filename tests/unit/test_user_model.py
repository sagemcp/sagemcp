"""Tests for User and UserTenantMembership models."""

import os
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")

from sage_mcp.models.user import AuthProvider, TenantRole, User, UserTenantMembership


class TestUserModel:
    """User table CRUD and constraints."""

    def test_create_local_user(self, db_session):
        user = User(
            email="alice@example.com",
            display_name="Alice",
            password_hash="hashed_pw",
            auth_provider=AuthProvider.LOCAL,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.id is not None
        assert user.email == "alice@example.com"
        assert user.display_name == "Alice"
        assert user.auth_provider == AuthProvider.LOCAL
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_github_user(self, db_session):
        user = User(
            email="bob@example.com",
            auth_provider=AuthProvider.GITHUB,
            provider_user_id="gh-12345",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert user.auth_provider == AuthProvider.GITHUB
        assert user.provider_user_id == "gh-12345"
        assert user.password_hash is None

    def test_create_google_user(self, db_session):
        user = User(
            email="carol@example.com",
            auth_provider=AuthProvider.GOOGLE,
            provider_user_id="google-99",
        )
        db_session.add(user)
        db_session.commit()

        assert user.auth_provider == AuthProvider.GOOGLE

    def test_email_unique_constraint(self, db_session):
        u1 = User(email="dup@example.com", auth_provider=AuthProvider.LOCAL)
        db_session.add(u1)
        db_session.commit()

        u2 = User(email="dup@example.com", auth_provider=AuthProvider.LOCAL)
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_is_active_default(self, db_session):
        user = User(email="active@example.com", auth_provider=AuthProvider.LOCAL)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.is_active is True

    def test_nullable_password_hash(self, db_session):
        user = User(email="nopw@example.com", auth_provider=AuthProvider.GITHUB)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        assert user.password_hash is None

    def test_repr(self, db_session):
        user = User(email="repr@example.com", auth_provider=AuthProvider.LOCAL)
        db_session.add(user)
        db_session.commit()
        assert "repr@example.com" in repr(user)
        assert "local" in repr(user)

    def test_to_dict(self, db_session):
        user = User(
            email="dict@example.com",
            display_name="Dict",
            auth_provider=AuthProvider.LOCAL,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        d = user.to_dict()
        assert d["email"] == "dict@example.com"
        assert d["display_name"] == "Dict"
        assert "id" in d
        assert "created_at" in d


class TestUserTenantMembership:
    """Membership join table CRUD and constraints."""

    def _make_user(self, db_session, email):
        user = User(email=email, auth_provider=AuthProvider.LOCAL)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    def _make_tenant(self, db_session, slug):
        from sage_mcp.models.tenant import Tenant

        tenant = Tenant(slug=slug, name=slug.title(), is_active=True)
        db_session.add(tenant)
        db_session.commit()
        db_session.refresh(tenant)
        return tenant

    def test_create_membership(self, db_session):
        user = self._make_user(db_session, "member@example.com")
        tenant = self._make_tenant(db_session, "acme")

        m = UserTenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantRole.TENANT_MEMBER
        )
        db_session.add(m)
        db_session.commit()
        db_session.refresh(m)

        assert m.id is not None
        assert m.user_id == user.id
        assert m.tenant_id == tenant.id
        assert m.role == TenantRole.TENANT_MEMBER

    def test_all_roles(self, db_session):
        user = self._make_user(db_session, "roles@example.com")
        for i, role in enumerate(TenantRole):
            tenant = self._make_tenant(db_session, f"role-tenant-{i}")
            m = UserTenantMembership(
                user_id=user.id, tenant_id=tenant.id, role=role
            )
            db_session.add(m)
        db_session.commit()

    def test_unique_user_tenant_constraint(self, db_session):
        user = self._make_user(db_session, "unique@example.com")
        tenant = self._make_tenant(db_session, "unique-tenant")

        m1 = UserTenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantRole.TENANT_MEMBER
        )
        db_session.add(m1)
        db_session.commit()

        m2 = UserTenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantRole.TENANT_ADMIN
        )
        db_session.add(m2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_repr(self, db_session):
        user = self._make_user(db_session, "repr-m@example.com")
        tenant = self._make_tenant(db_session, "repr-tenant")
        m = UserTenantMembership(
            user_id=user.id, tenant_id=tenant.id, role=TenantRole.TENANT_VIEWER
        )
        db_session.add(m)
        db_session.commit()
        assert "tenant_viewer" in repr(m)


class TestAuthProviderEnum:
    """AuthProvider enum values."""

    def test_values(self):
        assert AuthProvider.LOCAL.value == "local"
        assert AuthProvider.GOOGLE.value == "google"
        assert AuthProvider.GITHUB.value == "github"

    def test_is_str_enum(self):
        assert isinstance(AuthProvider.LOCAL, str)


class TestTenantRoleEnum:
    """TenantRole enum values."""

    def test_values(self):
        assert TenantRole.PLATFORM_ADMIN.value == "platform_admin"
        assert TenantRole.TENANT_ADMIN.value == "tenant_admin"
        assert TenantRole.TENANT_MEMBER.value == "tenant_member"
        assert TenantRole.TENANT_VIEWER.value == "tenant_viewer"

    def test_is_str_enum(self):
        assert isinstance(TenantRole.PLATFORM_ADMIN, str)

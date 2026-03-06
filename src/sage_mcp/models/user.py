"""User identity, tenant membership, and refresh token models."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuthProvider(str, enum.Enum):
    """Supported authentication providers."""

    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"


class TenantRole(str, enum.Enum):
    """Role within a tenant."""

    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    TENANT_MEMBER = "tenant_member"
    TENANT_VIEWER = "tenant_viewer"


class User(Base):
    """User identity for authentication and RBAC."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    auth_provider: Mapped[AuthProvider] = mapped_column(
        Enum(
            AuthProvider,
            name="authprovider",
            create_constraint=False,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AuthProvider.LOCAL,
    )

    provider_user_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<User(email='{self.email}', provider='{self.auth_provider.value}')>"


class UserTenantMembership(Base):
    """Maps users to tenants with a specific role."""

    __tablename__ = "user_tenant_memberships"

    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[TenantRole] = mapped_column(
        Enum(
            TenantRole,
            name="tenantrole",
            create_constraint=False,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UserTenantMembership(user={self.user_id}, tenant={self.tenant_id}, role='{self.role.value}')>"


class RefreshToken(Base):
    """Stores hashed refresh tokens for token rotation.

    Raw tokens are never persisted. We store a SHA-256 hash so we can
    look up and revoke tokens without exposing the secret.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<RefreshToken(user={self.user_id}, revoked={self.revoked})>"

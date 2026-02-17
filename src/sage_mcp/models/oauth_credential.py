"""OAuth credential model for storing tenant-specific OAuth tokens."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from ..security.types import EncryptedText

if TYPE_CHECKING:
    from .tenant import Tenant


class OAuthCredential(Base):
    """OAuth credentials for tenant-specific service access."""

    __tablename__ = "oauth_credentials"

    # Foreign key to tenant
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Service provider (github, gitlab, google, etc.)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # User identifier from the provider
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # User display name from provider
    provider_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # OAuth tokens
    access_token: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(EncryptedText, nullable=True)
    token_type: Mapped[str] = mapped_column(String(50), default="bearer", nullable=False)

    # Token expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # OAuth scopes granted
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Additional provider-specific data (JSON)
    provider_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="oauth_credentials")

    def __repr__(self) -> str:
        return f"<OAuthCredential(provider='{self.provider}', tenant_id='{self.tenant_id}')>"

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) >= self.expires_at

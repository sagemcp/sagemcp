from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from .base import Base
from ..security.types import EncryptedText


class OAuthConfig(Base):
    """OAuth application configuration for each tenant and provider."""
    __tablename__ = "oauth_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # github, slack
    client_id = Column(String(255), nullable=False)
    client_secret = Column(EncryptedText, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tenant = relationship("Tenant", back_populates="oauth_configs")

    def __repr__(self):
        return f"<OAuthConfig {self.tenant_id}:{self.provider}>"

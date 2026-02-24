"""Global tool policy model for platform-wide governance."""

import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PolicyAction(str, enum.Enum):
    """Action to take when a tool matches a policy."""

    BLOCK = "block"
    WARN = "warn"


class GlobalToolPolicy(Base):
    """Platform-wide tool governance policy.

    Policies match tool names using exact strings or glob patterns (fnmatch).
    Optionally scoped to a specific connector type.
    Evaluated on the hot path — all active policies are cached in memory.
    """

    __tablename__ = "global_tool_policies"

    tool_name_pattern: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )

    action: Mapped[PolicyAction] = mapped_column(
        Enum(
            PolicyAction,
            name="policyaction",
            create_constraint=False,
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    connector_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<GlobalToolPolicy(pattern='{self.tool_name_pattern}', "
            f"action='{self.action.value}', connector_type={self.connector_type})>"
        )

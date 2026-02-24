"""Daily tool usage counter model."""

from datetime import date

from sqlalchemy import Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ToolUsageDaily(Base):
    """Persistent daily counter for tool calls."""

    __tablename__ = "tool_usage_daily"
    __table_args__ = (
        UniqueConstraint("day", name="uq_tool_usage_daily_day"),
    )

    day: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tool_calls_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

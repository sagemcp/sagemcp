"""Standardized metrics schema for AI coding tool connectors.

Every AI coding tool connector implements a `get_normalized_metrics` tool
that returns a CodingToolMetrics dataclass. Fields not available from the
API return None with the field name listed in metadata["unavailable_fields"].
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class CodingToolMetrics:
    """Normalized metrics for cross-tool comparison of AI coding tools."""

    # Identity
    tool_name: str
    period: str  # e.g. "2024-01-01/2024-01-31"

    # Seat / license metrics
    total_seats: Optional[int] = None
    active_seats: Optional[int] = None
    seat_utilization_pct: Optional[float] = None
    inactive_seats: Optional[int] = None

    # Usage metrics
    total_suggestions: Optional[int] = None
    total_acceptances: Optional[int] = None
    acceptance_rate_pct: Optional[float] = None
    total_lines_suggested: Optional[int] = None
    total_lines_accepted: Optional[int] = None
    total_chat_interactions: Optional[int] = None
    daily_active_users: Optional[int] = None

    # Cost metrics
    total_cost_usd: Optional[float] = None
    cost_per_user_usd: Optional[float] = None
    cost_per_accepted_suggestion_usd: Optional[float] = None

    # Breakdown data
    usage_by_language: Optional[Dict[str, Any]] = None
    usage_by_editor: Optional[Dict[str, Any]] = None
    usage_by_model: Optional[Dict[str, Any]] = None

    # Metadata — always includes "unavailable_fields" list
    metadata: Dict[str, Any] = field(default_factory=lambda: {"unavailable_fields": []})

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary, suitable for JSON output."""
        return asdict(self)

    @staticmethod
    def unavailable(tool_name: str, period: str, fields: List[str]) -> "CodingToolMetrics":
        """Helper to create a metrics object with all specified fields marked unavailable."""
        metrics = CodingToolMetrics(
            tool_name=tool_name,
            period=period,
            metadata={"unavailable_fields": fields},
        )
        return metrics

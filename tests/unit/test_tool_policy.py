"""Unit tests for global tool policy enforcement.

Tests the hot-path ``check_tool_policy()`` pure function and the
in-memory policy cache lifecycle.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sage_mcp.security.tool_policy import (
    PolicyResult,
    _CachedPolicy,
    _RESULT_ALLOWED,
    check_tool_policy,
    invalidate_policy_cache,
    is_cache_stale,
    load_policies,
)
import sage_mcp.security.tool_policy as tp_module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_cache(policies, loaded_at=None):
    """Directly inject policies into the module-level cache for testing."""
    tp_module._cached_policies = policies
    tp_module._cache_loaded_at = loaded_at if loaded_at is not None else time.monotonic()


def _clear_cache():
    """Reset to empty cache."""
    tp_module._cached_policies = []
    tp_module._cache_loaded_at = 0.0


@pytest.fixture(autouse=True)
def clean_cache():
    """Ensure each test starts with a clean cache."""
    _clear_cache()
    yield
    _clear_cache()


# ---------------------------------------------------------------------------
# check_tool_policy — pure function tests
# ---------------------------------------------------------------------------


class TestCheckToolPolicy:
    """Tests for the hot-path check_tool_policy() pure function."""

    def test_no_policies_allows_all(self):
        """No policies loaded → everything is allowed."""
        _set_cache([])
        result = check_tool_policy("github_delete_repo")
        assert result.allowed is True
        assert result.action == "allow"

    def test_exact_match_block(self):
        """Exact tool name match with block action."""
        _set_cache([
            _CachedPolicy(
                pattern="github_delete_repo",
                action="block",
                reason="Destructive action",
                connector_type=None,
            ),
        ])
        result = check_tool_policy("github_delete_repo")
        assert result.allowed is False
        assert result.action == "block"
        assert result.reason == "Destructive action"

    def test_exact_match_no_match(self):
        """Tool name that doesn't match any policy."""
        _set_cache([
            _CachedPolicy(
                pattern="github_delete_repo",
                action="block",
                reason="Destructive",
                connector_type=None,
            ),
        ])
        result = check_tool_policy("github_list_repos")
        assert result.allowed is True
        assert result.action == "allow"

    def test_glob_pattern_star(self):
        """Glob pattern with trailing * matches tool prefix."""
        _set_cache([
            _CachedPolicy(
                pattern="github_delete_*",
                action="block",
                reason="No delete tools",
                connector_type=None,
            ),
        ])
        assert check_tool_policy("github_delete_repo").allowed is False
        assert check_tool_policy("github_delete_branch").allowed is False
        assert check_tool_policy("github_list_repos").allowed is True

    def test_glob_pattern_question_mark(self):
        """Glob pattern with ? matches single character."""
        _set_cache([
            _CachedPolicy(
                pattern="jira_delete_?ssue",
                action="block",
                reason="Typo catch",
                connector_type=None,
            ),
        ])
        assert check_tool_policy("jira_delete_issue").allowed is False
        assert check_tool_policy("jira_delete_issues").allowed is True

    def test_warn_action_allows(self):
        """Warn action returns allowed=True with action=warn."""
        _set_cache([
            _CachedPolicy(
                pattern="slack_send_message",
                action="warn",
                reason="Review before sending",
                connector_type=None,
            ),
        ])
        result = check_tool_policy("slack_send_message")
        assert result.allowed is True
        assert result.action == "warn"
        assert result.reason == "Review before sending"

    def test_block_takes_precedence_over_warn(self):
        """Block wins over warn when both match."""
        _set_cache([
            _CachedPolicy(
                pattern="github_delete_*",
                action="warn",
                reason="Be careful",
                connector_type=None,
            ),
            _CachedPolicy(
                pattern="github_delete_repo",
                action="block",
                reason="Never delete repos",
                connector_type=None,
            ),
        ])
        result = check_tool_policy("github_delete_repo")
        assert result.allowed is False
        assert result.action == "block"

    def test_connector_scoped_policy_matches(self):
        """Policy scoped to a connector type only matches that type."""
        _set_cache([
            _CachedPolicy(
                pattern="*_delete_*",
                action="block",
                reason="No deletes on github",
                connector_type="github",
            ),
        ])
        # Matches github
        assert check_tool_policy("github_delete_repo", connector_type="github").allowed is False
        # Doesn't match jira (different connector type)
        assert check_tool_policy("jira_delete_issue", connector_type="jira").allowed is True

    def test_connector_scoped_case_insensitive(self):
        """Connector type matching is case-insensitive."""
        _set_cache([
            _CachedPolicy(
                pattern="*_admin_*",
                action="block",
                reason="No admin tools",
                connector_type="GitHub",
            ),
        ])
        assert check_tool_policy("github_admin_settings", connector_type="github").allowed is False

    def test_unscoped_policy_matches_all_connectors(self):
        """Policy with connector_type=None matches any connector."""
        _set_cache([
            _CachedPolicy(
                pattern="*_delete_*",
                action="block",
                reason="Global no-delete",
                connector_type=None,
            ),
        ])
        assert check_tool_policy("github_delete_repo", connector_type="github").allowed is False
        assert check_tool_policy("jira_delete_issue", connector_type="jira").allowed is False
        assert check_tool_policy("slack_delete_message", connector_type="slack").allowed is False

    def test_no_connector_type_provided(self):
        """When no connector_type is provided, scoped policies still match."""
        _set_cache([
            _CachedPolicy(
                pattern="github_delete_*",
                action="block",
                reason="Block deletes",
                connector_type="github",
            ),
        ])
        # connector_type=None means we don't filter by connector
        result = check_tool_policy("github_delete_repo", connector_type=None)
        assert result.allowed is False

    def test_returns_singleton_on_allow(self):
        """Happy path returns the module-level singleton (zero allocation)."""
        _set_cache([])
        result = check_tool_policy("anything")
        assert result is _RESULT_ALLOWED


# ---------------------------------------------------------------------------
# Cache lifecycle tests
# ---------------------------------------------------------------------------


class TestPolicyCacheLifecycle:
    """Tests for cache TTL, staleness, and invalidation."""

    def test_cache_stale_when_never_loaded(self):
        """Cache is stale when _cache_loaded_at is 0."""
        assert is_cache_stale() is True

    def test_cache_fresh_after_load(self):
        """Cache is fresh right after setting loaded_at to now."""
        _set_cache([], loaded_at=time.monotonic())
        assert is_cache_stale() is False

    def test_cache_stale_after_ttl(self):
        """Cache becomes stale after TTL expires."""
        _set_cache([], loaded_at=time.monotonic() - tp_module._CACHE_TTL - 1)
        assert is_cache_stale() is True

    def test_invalidate_makes_stale(self):
        """invalidate_policy_cache() forces staleness."""
        _set_cache([], loaded_at=time.monotonic())
        assert is_cache_stale() is False
        invalidate_policy_cache()
        assert is_cache_stale() is True

    @pytest.mark.asyncio
    async def test_load_policies_populates_cache(self):
        """load_policies() fetches from DB and populates module cache."""
        # Mock the DB session
        mock_session = AsyncMock()

        # Create mock policy objects
        mock_policy = MagicMock()
        mock_policy.tool_name_pattern = "github_delete_*"
        mock_policy.action = MagicMock()
        mock_policy.action.value = "block"
        mock_policy.reason = "No deletes"
        mock_policy.connector_type = None
        mock_policy.is_active = True

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_policy]
        mock_session.execute.return_value = mock_result

        await load_policies(mock_session)

        assert len(tp_module._cached_policies) == 1
        assert tp_module._cached_policies[0].pattern == "github_delete_*"
        assert tp_module._cached_policies[0].action == "block"
        assert is_cache_stale() is False

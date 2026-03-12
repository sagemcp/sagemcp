"""Unit tests for local MCP catalog helpers."""

from sage_mcp.mcp.local_catalog import (
    OVERRIDABLE_METHODS,
    compose_virtual_arguments,
    extract_template_variables,
    match_uri_template,
    merge_unique_by_key,
    normalize_prompt_arguments_metadata,
    resolve_prompt_arguments_metadata,
)


def test_merge_unique_by_key_prefers_upstream_item_on_collision():
    upstream = [{"name": "shared"}, {"name": "upstream_only"}]
    local = [{"name": "shared"}, {"name": "local_only"}]

    merged = merge_unique_by_key(upstream, local, key_func=lambda item: item["name"])

    assert merged == [
        {"name": "shared"},
        {"name": "upstream_only"},
        {"name": "local_only"},
    ]


def test_match_uri_template_extracts_named_variables():
    matched = match_uri_template(
        "sagemcp://github/issues/{owner}/{repo}/{issue_number}",
        "sagemcp://github/issues/openai/codex/97",
    )

    assert matched == {
        "owner": "openai",
        "repo": "codex",
        "issue_number": "97",
    }


def test_compose_virtual_arguments_applies_mapping_then_fixed_overrides():
    composed = compose_virtual_arguments(
        provided={"owner": "openai", "repo": "sagemcp", "timeout": 60},
        fixed_arguments={"timeout": 10, "format": "json"},
        argument_mapping={"repository": "repo"},
        passthrough_unmapped=True,
    )

    assert composed == {
        "owner": "openai",
        "repo": "sagemcp",
        "timeout": 10,
        "repository": "sagemcp",
        "format": "json",
    }


def test_override_whitelist_exposes_only_supported_target_kinds():
    assert OVERRIDABLE_METHODS["tools/call"] == {"tool"}
    assert OVERRIDABLE_METHODS["resources/read"] == {"resource", "resource_template"}
    assert OVERRIDABLE_METHODS["prompts/get"] == {"prompt"}


def test_normalize_prompt_arguments_metadata_validates_shape():
    normalized = normalize_prompt_arguments_metadata(
        [
            {"name": "issue_number", "required": True, "description": "Issue to inspect"},
            {"name": "repo"},
        ]
    )

    assert normalized == [
        {"name": "issue_number", "required": True, "description": "Issue to inspect"},
        {"name": "repo"},
    ]


def test_normalize_prompt_arguments_metadata_rejects_invalid_entries():
    try:
        normalize_prompt_arguments_metadata([{"required": True}])
    except ValueError as exc:
        assert "name must be a non-empty string" in str(exc)
    else:
        raise AssertionError("Expected invalid prompt metadata to raise ValueError")


def test_extract_template_variables_returns_unique_placeholder_names():
    assert extract_template_variables("Prompt {id} for {repo[name]} and {id}") == ["id", "repo"]


def test_resolve_prompt_arguments_metadata_infers_required_arguments_from_payload():
    resolved = resolve_prompt_arguments_metadata(
        "Prompt for {id} in {repo}",
        [{"name": "repo", "description": "Repository"}],
    )

    assert resolved == [
        {"name": "repo", "description": "Repository", "required": True},
        {"name": "id", "required": True},
    ]

"""Generic local MCP override registry and helpers."""

from __future__ import annotations

import json
import re
import string
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple, TypeVar

from mcp import types
from sqlalchemy import select

from ..database.connection import get_db_context
from ..models.connector_mcp_override import ConnectorMCPOverride

T = TypeVar("T")

TARGET_TOOL = "tool"
TARGET_RESOURCE = "resource"
TARGET_RESOURCE_TEMPLATE = "resource_template"
TARGET_PROMPT = "prompt"

OVERRIDABLE_METHODS = {
    "tools/list": {TARGET_TOOL},
    "tools/call": {TARGET_TOOL},
    "resources/list": {TARGET_RESOURCE},
    "resources/read": {TARGET_RESOURCE, TARGET_RESOURCE_TEMPLATE},
    "resources/templates/list": {TARGET_RESOURCE_TEMPLATE},
    "prompts/list": {TARGET_PROMPT},
    "prompts/get": {TARGET_PROMPT},
}


@dataclass
class LocalToolExecution:
    handled: bool
    result: Optional[str] = None


@dataclass
class LocalResourceRead:
    handled: bool
    content: Optional[types.TextResourceContents] = None


@dataclass
class LocalPromptResolution:
    handled: bool
    result: Optional[types.GetPromptResult] = None


@dataclass
class ResolvedOverride:
    """Generic resolved local override."""

    record: ConnectorMCPOverride
    rendered_payload: str
    context: Dict[str, Any]


def merge_unique_by_key(
    upstream: Sequence[T],
    local: Sequence[T],
    key_func: Callable[[T], str],
) -> List[T]:
    """Merge upstream and local items without duplicating collision keys."""
    merged = list(upstream)
    seen = {key_func(item) for item in upstream}
    for item in local:
        item_key = key_func(item)
        if item_key in seen:
            continue
        merged.append(item)
        seen.add(item_key)
    return merged


def parse_uri_template(uri_template: str) -> Tuple[re.Pattern[str], List[str]]:
    """Compile a URI template with ``{var}`` placeholders into a regex."""
    pattern_parts: List[str] = []
    variable_names: List[str] = []
    formatter = string.Formatter()

    for literal_text, field_name, _format_spec, _conversion in formatter.parse(uri_template):
        pattern_parts.append(re.escape(literal_text))
        if field_name is None:
            continue
        variable_names.append(field_name)
        pattern_parts.append(f"(?P<{field_name}>[^/?#]+)")

    return re.compile("^" + "".join(pattern_parts) + "$"), variable_names


def match_uri_template(uri_template: str, uri: str) -> Optional[Dict[str, str]]:
    """Match a real URI against a stored URI template."""
    pattern, _variable_names = parse_uri_template(uri_template)
    match = pattern.match(uri)
    if not match:
        return None
    return match.groupdict()


def validate_input_schema(input_schema: Optional[Dict[str, Any]], provided: Dict[str, Any]) -> None:
    """Apply light validation for object-style JSON Schema payloads."""
    if not input_schema:
        return
    if input_schema.get("type") not in (None, "object"):
        raise ValueError("Only object input schemas are supported for local virtual tools")

    required = input_schema.get("required") or []
    missing = [key for key in required if key not in provided]
    if missing:
        raise ValueError(f"Missing required arguments: {', '.join(sorted(missing))}")


def compose_virtual_arguments(
    provided: Dict[str, Any],
    fixed_arguments: Optional[Dict[str, Any]],
    argument_mapping: Optional[Dict[str, Any]],
    passthrough_unmapped: bool,
) -> Dict[str, Any]:
    """Compose upstream tool arguments from caller inputs and local mappings."""
    composed: Dict[str, Any] = {}

    if passthrough_unmapped:
        composed.update(provided)

    if argument_mapping:
        for target_name, source_name in argument_mapping.items():
            if source_name in provided:
                composed[target_name] = provided[source_name]

    if fixed_arguments:
        composed.update(fixed_arguments)

    return composed


def normalize_prompt_arguments_metadata(arguments: Any) -> List[Dict[str, Any]]:
    """Validate stored prompt argument metadata before exposing it to MCP."""
    if arguments in (None, []):
        return []
    if not isinstance(arguments, list):
        raise ValueError("Prompt metadata arguments must be a list")

    normalized_arguments: List[Dict[str, Any]] = []
    for index, argument in enumerate(arguments):
        if not isinstance(argument, dict):
            raise ValueError(f"Prompt metadata arguments[{index}] must be an object")

        name = argument.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Prompt metadata arguments[{index}].name must be a non-empty string")

        normalized_argument: Dict[str, Any] = {"name": name.strip()}

        description = argument.get("description")
        if description is not None:
            if not isinstance(description, str):
                raise ValueError(f"Prompt metadata arguments[{index}].description must be a string")
            normalized_argument["description"] = description

        required = argument.get("required")
        if required is not None:
            if not isinstance(required, bool):
                raise ValueError(f"Prompt metadata arguments[{index}].required must be a boolean")
            normalized_argument["required"] = required

        normalized_arguments.append(normalized_argument)

    return normalized_arguments


def extract_template_variables(payload_text: str) -> List[str]:
    """Extract unique format placeholder names from a template string."""
    variables: List[str] = []
    formatter = string.Formatter()

    for _literal_text, field_name, _format_spec, _conversion in formatter.parse(payload_text):
        if not field_name:
            continue

        variable_name = field_name.split(".", 1)[0].split("[", 1)[0].strip()
        if not variable_name or variable_name in variables:
            continue
        variables.append(variable_name)

    return variables


def resolve_prompt_arguments_metadata(
    payload_text: str,
    arguments: Any,
) -> List[Dict[str, Any]]:
    """Combine explicit prompt metadata with variables inferred from the template body."""
    normalized_arguments = normalize_prompt_arguments_metadata(arguments)
    arguments_by_name = {argument["name"]: dict(argument) for argument in normalized_arguments}

    for variable_name in extract_template_variables(payload_text):
        inferred_argument = arguments_by_name.setdefault(variable_name, {"name": variable_name})
        inferred_argument["required"] = True

    return list(arguments_by_name.values())


class LocalOverrideRegistry:
    """Generic registry for connector-managed MCP overrides."""

    def __init__(self, connector_id: Any):
        self.connector_id = connector_id

    async def _list_overrides(self, target_kind: str) -> List[ConnectorMCPOverride]:
        if target_kind not in {TARGET_TOOL, TARGET_RESOURCE, TARGET_RESOURCE_TEMPLATE, TARGET_PROMPT}:
            raise ValueError(f"Unsupported override target kind: {target_kind}")

        async with get_db_context() as session:
            result = await session.execute(
                select(ConnectorMCPOverride).where(
                    ConnectorMCPOverride.connector_id == self.connector_id,
                    ConnectorMCPOverride.target_kind == target_kind,
                    ConnectorMCPOverride.is_enabled.is_(True),
                )
            )
            return list(result.scalars().all())

    async def _get_override(self, target_kind: str, identifier: str) -> Optional[ConnectorMCPOverride]:
        async with get_db_context() as session:
            result = await session.execute(
                select(ConnectorMCPOverride).where(
                    ConnectorMCPOverride.connector_id == self.connector_id,
                    ConnectorMCPOverride.target_kind == target_kind,
                    ConnectorMCPOverride.identifier == identifier,
                    ConnectorMCPOverride.is_enabled.is_(True),
                )
            )
            return result.scalar_one_or_none()

    def _render_payload(self, payload_text: str, context: Dict[str, Any]) -> str:
        """Render templated payload text, short-circuiting plain text."""
        if "{" not in payload_text:
            return payload_text
        try:
            return payload_text.format(**context)
        except KeyError as exc:
            missing_key = exc.args[0]
            raise ValueError(f"Missing template variable: {missing_key}") from exc

    def _build_context(
        self,
        record: ConnectorMCPOverride,
        provided: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build substitution context from metadata and provided values."""
        metadata = record.metadata_json or {}
        context = dict(provided or {})
        context.setdefault("identifier", record.identifier)
        context.setdefault("metadata", metadata)
        return context

    async def resolve_override(
        self,
        target_kind: str,
        identifier: str,
        provided: Optional[Dict[str, Any]] = None,
    ) -> Optional[ResolvedOverride]:
        """Resolve and render a single local override."""
        record = await self._get_override(target_kind, identifier)
        if record is None:
            return None

        context = self._build_context(record, provided)
        return ResolvedOverride(
            record=record,
            rendered_payload=self._render_payload(record.payload_text, context),
            context=context,
        )

    async def list_virtual_tools(self) -> List[types.Tool]:
        records = await self._list_overrides(TARGET_TOOL)
        tools: List[types.Tool] = []
        for record in records:
            metadata = record.metadata_json or {}
            tools.append(
                types.Tool(
                    name=record.identifier,
                    title=metadata.get("title"),
                    description=metadata.get("description"),
                    inputSchema=metadata.get("inputSchema") or {"type": "object", "properties": {}},
                    _meta=metadata.get("_meta"),
                )
            )
        return tools

    async def execute_virtual_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        call_upstream_tool: Callable[[str, Dict[str, Any]], Awaitable[str]],
    ) -> LocalToolExecution:
        resolved = await self.resolve_override(TARGET_TOOL, name, arguments)
        if resolved is None:
            return LocalToolExecution(handled=False)

        metadata = resolved.record.metadata_json or {}
        validate_input_schema(metadata.get("inputSchema"), arguments)

        if resolved.rendered_payload.strip():
            try:
                upstream_args = json.loads(resolved.rendered_payload)
                if not isinstance(upstream_args, dict):
                    raise ValueError("Rendered tool payload must decode to an object")
            except json.JSONDecodeError as exc:
                raise ValueError(f"Rendered tool payload is not valid JSON: {exc}") from exc
        else:
            upstream_args = compose_virtual_arguments(
                provided=arguments,
                fixed_arguments=metadata.get("fixedArguments"),
                argument_mapping=metadata.get("argumentMapping"),
                passthrough_unmapped=metadata.get("passthroughUnmapped", True),
            )

        return LocalToolExecution(
            handled=True,
            result=await call_upstream_tool(metadata["targetToolName"], upstream_args),
        )

    async def list_static_resources(self) -> List[types.Resource]:
        records = await self._list_overrides(TARGET_RESOURCE)
        resources: List[types.Resource] = []
        for record in records:
            metadata = record.metadata_json or {}
            resources.append(
                types.Resource(
                    name=metadata.get("name") or record.identifier,
                    title=metadata.get("title"),
                    uri=record.identifier,
                    description=metadata.get("description"),
                    mimeType=metadata.get("mimeType"),
                    size=len(record.payload_text.encode("utf-8")),
                    _meta=metadata.get("_meta"),
                )
            )
        return resources

    async def read_local_resource(
        self,
        uri: str,
        call_upstream_tool: Callable[[str, Dict[str, Any]], Awaitable[str]],
    ) -> LocalResourceRead:
        static_resolved = await self.resolve_override(TARGET_RESOURCE, uri)
        if static_resolved is not None:
            metadata = static_resolved.record.metadata_json or {}
            return LocalResourceRead(
                handled=True,
                content=types.TextResourceContents(
                    uri=uri,
                    mimeType=metadata.get("mimeType"),
                    text=static_resolved.rendered_payload,
                    _meta=metadata.get("_meta"),
                ),
            )

        virtual_records = await self._list_overrides(TARGET_RESOURCE_TEMPLATE)
        for record in virtual_records:
            template_variables = match_uri_template(record.identifier, uri)
            if template_variables is None:
                continue

            metadata = record.metadata_json or {}
            upstream_args = compose_virtual_arguments(
                provided=template_variables,
                fixed_arguments=metadata.get("fixedArguments"),
                argument_mapping=metadata.get("argumentMapping"),
                passthrough_unmapped=metadata.get("passthroughUnmapped", True),
            )
            tool_result = await call_upstream_tool(metadata["targetToolName"], upstream_args)

            context = dict(template_variables)
            context.setdefault("tool_result", tool_result)
            rendered_payload = self._render_payload(record.payload_text, context)

            return LocalResourceRead(
                handled=True,
                content=types.TextResourceContents(
                    uri=uri,
                    mimeType=metadata.get("mimeType"),
                    text=rendered_payload if rendered_payload else tool_result,
                    _meta=metadata.get("_meta"),
                ),
            )

        return LocalResourceRead(handled=False)

    async def list_virtual_resource_templates(self) -> List[types.ResourceTemplate]:
        records = await self._list_overrides(TARGET_RESOURCE_TEMPLATE)
        templates: List[types.ResourceTemplate] = []
        for record in records:
            metadata = record.metadata_json or {}
            templates.append(
                types.ResourceTemplate(
                    name=metadata.get("name") or record.identifier,
                    title=metadata.get("title"),
                    uriTemplate=record.identifier,
                    description=metadata.get("description"),
                    mimeType=metadata.get("mimeType"),
                    _meta=metadata.get("_meta"),
                )
            )
        return templates

    async def list_prompts(self) -> List[types.Prompt]:
        records = await self._list_overrides(TARGET_PROMPT)
        prompts: List[types.Prompt] = []
        for record in records:
            metadata = record.metadata_json or {}
            prompt_arguments = resolve_prompt_arguments_metadata(
                record.payload_text,
                metadata.get("arguments"),
            )
            prompts.append(
                types.Prompt(
                    name=record.identifier,
                    title=metadata.get("title"),
                    description=metadata.get("description"),
                    arguments=[types.PromptArgument(**argument) for argument in prompt_arguments],
                    _meta=metadata.get("_meta"),
                )
            )
        return prompts

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, str]],
    ) -> LocalPromptResolution:
        record = await self._get_override(TARGET_PROMPT, name)
        if record is None:
            return LocalPromptResolution(handled=False)

        metadata = record.metadata_json or {}
        provided = arguments or {}
        declared_arguments = resolve_prompt_arguments_metadata(
            record.payload_text,
            metadata.get("arguments"),
        )
        missing = [
            arg["name"]
            for arg in declared_arguments
            if arg.get("required") and arg.get("name") not in provided
        ]
        if missing:
            raise ValueError(f"Missing required prompt arguments: {', '.join(sorted(missing))}")

        context = self._build_context(record, provided)
        rendered_payload = self._render_payload(record.payload_text, context)

        return LocalPromptResolution(
            handled=True,
            result=types.GetPromptResult(
                description=metadata.get("description"),
                messages=[
                    types.PromptMessage(
                        role=metadata.get("role", "user"),
                        content=types.TextContent(type="text", text=rendered_payload),
                    )
                ],
                _meta=metadata.get("_meta"),
            ),
        )

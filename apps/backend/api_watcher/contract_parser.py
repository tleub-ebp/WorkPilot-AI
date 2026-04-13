"""
Contract Parser — Parse OpenAPI, GraphQL, and Protobuf specifications.

Produces a normalised internal representation for semantic diff.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ContractFormat(str, Enum):
    OPENAPI = "openapi"
    GRAPHQL = "graphql"
    PROTOBUF = "protobuf"
    UNKNOWN = "unknown"


@dataclass
class ApiField:
    """A single field in an API schema."""

    name: str
    type: str
    required: bool = False
    description: str = ""
    deprecated: bool = False
    children: list[ApiField] = field(default_factory=list)


@dataclass
class ApiEndpoint:
    """A single API endpoint / operation."""

    path: str
    method: str = ""
    operation_id: str = ""
    parameters: list[ApiField] = field(default_factory=list)
    request_body: list[ApiField] = field(default_factory=list)
    responses: dict[str, list[ApiField]] = field(default_factory=dict)
    deprecated: bool = False


@dataclass
class ApiContract:
    """Normalised representation of an API contract."""

    title: str = ""
    version: str = ""
    format: ContractFormat = ContractFormat.UNKNOWN
    endpoints: list[ApiEndpoint] = field(default_factory=list)
    types: dict[str, list[ApiField]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class ContractParser:
    """Parse API specification files into normalised ApiContract objects.

    Usage::

        parser = ContractParser()
        contract = parser.parse_file(Path("openapi.yaml"))
    """

    def parse_file(self, path: Path) -> ApiContract:
        """Parse a spec file, auto-detecting the format."""
        content = path.read_text(encoding="utf-8")
        fmt = self.detect_format(path, content)

        if fmt == ContractFormat.OPENAPI:
            return self._parse_openapi(content)
        if fmt == ContractFormat.GRAPHQL:
            return self._parse_graphql(content)
        if fmt == ContractFormat.PROTOBUF:
            return self._parse_protobuf(content)

        return ApiContract(format=ContractFormat.UNKNOWN)

    def parse_string(self, content: str, fmt: ContractFormat) -> ApiContract:
        """Parse a spec string with an explicit format."""
        if fmt == ContractFormat.OPENAPI:
            return self._parse_openapi(content)
        if fmt == ContractFormat.GRAPHQL:
            return self._parse_graphql(content)
        if fmt == ContractFormat.PROTOBUF:
            return self._parse_protobuf(content)
        return ApiContract(format=ContractFormat.UNKNOWN)

    @staticmethod
    def detect_format(path: Path, content: str = "") -> ContractFormat:
        """Auto-detect the contract format from file extension and content."""
        suffix = path.suffix.lower()
        name = path.name.lower()

        if suffix in (".graphql", ".gql") or "schema.graphql" in name:
            return ContractFormat.GRAPHQL
        if suffix == ".proto":
            return ContractFormat.PROTOBUF
        if suffix in (".yaml", ".yml", ".json"):
            if "openapi" in content[:500].lower() or "swagger" in content[:500].lower():
                return ContractFormat.OPENAPI
        return ContractFormat.UNKNOWN

    def _parse_openapi(self, content: str) -> ApiContract:
        """Parse an OpenAPI/Swagger spec."""
        try:
            import yaml
            data = yaml.safe_load(content)
        except Exception:
            try:
                data = json.loads(content)
            except Exception:
                return ApiContract(format=ContractFormat.OPENAPI)

        if not isinstance(data, dict):
            return ApiContract(format=ContractFormat.OPENAPI)

        contract = ApiContract(
            title=data.get("info", {}).get("title", ""),
            version=data.get("info", {}).get("version", ""),
            format=ContractFormat.OPENAPI,
            raw=data,
        )

        paths = data.get("paths", {})
        for path_str, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, op in methods.items():
                if method.startswith("x-") or not isinstance(op, dict):
                    continue
                endpoint = ApiEndpoint(
                    path=path_str,
                    method=method.upper(),
                    operation_id=op.get("operationId", ""),
                    deprecated=op.get("deprecated", False),
                )
                for param in op.get("parameters", []):
                    if isinstance(param, dict):
                        endpoint.parameters.append(ApiField(
                            name=param.get("name", ""),
                            type=param.get("schema", {}).get("type", "string") if isinstance(param.get("schema"), dict) else "string",
                            required=param.get("required", False),
                        ))
                contract.endpoints.append(endpoint)

        # Extract schemas/components
        schemas = data.get("components", {}).get("schemas", data.get("definitions", {}))
        for name, schema in schemas.items():
            if isinstance(schema, dict):
                fields = []
                required_fields = set(schema.get("required", []))
                for prop_name, prop in schema.get("properties", {}).items():
                    if isinstance(prop, dict):
                        fields.append(ApiField(
                            name=prop_name,
                            type=prop.get("type", "object"),
                            required=prop_name in required_fields,
                            deprecated=prop.get("deprecated", False),
                        ))
                contract.types[name] = fields

        return contract

    def _parse_graphql(self, content: str) -> ApiContract:
        """Parse a GraphQL schema (simplified parser)."""
        import re
        contract = ApiContract(format=ContractFormat.GRAPHQL)

        type_pattern = re.compile(r'type\s+(\w+)\s*\{([^}]+)\}', re.MULTILINE)
        field_pattern = re.compile(r'(\w+)(?:\([^)]*\))?\s*:\s*([^\n!]+!?)')

        for tmatch in type_pattern.finditer(content):
            type_name = tmatch.group(1)
            body = tmatch.group(2)
            fields: list[ApiField] = []
            for fmatch in field_pattern.finditer(body):
                ftype = fmatch.group(2).strip()
                fields.append(ApiField(
                    name=fmatch.group(1),
                    type=ftype,
                    required=ftype.endswith("!"),
                ))
            contract.types[type_name] = fields

            if type_name in ("Query", "Mutation", "Subscription"):
                for f in fields:
                    contract.endpoints.append(ApiEndpoint(
                        path=f.name,
                        method=type_name.upper(),
                        parameters=[],
                    ))

        return contract

    def _parse_protobuf(self, content: str) -> ApiContract:
        """Parse a protobuf schema (simplified parser)."""
        import re
        contract = ApiContract(format=ContractFormat.PROTOBUF)

        msg_pattern = re.compile(r'message\s+(\w+)\s*\{([^}]+)\}', re.MULTILINE)
        field_pattern = re.compile(r'(repeated|optional|required)?\s*(\w+)\s+(\w+)\s*=\s*(\d+)')

        for mmatch in msg_pattern.finditer(content):
            msg_name = mmatch.group(1)
            body = mmatch.group(2)
            fields: list[ApiField] = []
            for fmatch in field_pattern.finditer(body):
                fields.append(ApiField(
                    name=fmatch.group(3),
                    type=fmatch.group(2),
                    required=fmatch.group(1) == "required",
                ))
            contract.types[msg_name] = fields

        svc_pattern = re.compile(r'service\s+(\w+)\s*\{([^}]+)\}', re.MULTILINE)
        rpc_pattern = re.compile(r'rpc\s+(\w+)\s*\((\w+)\)\s*returns\s*\((\w+)\)')
        for smatch in svc_pattern.finditer(content):
            body = smatch.group(2)
            for rmatch in rpc_pattern.finditer(body):
                contract.endpoints.append(ApiEndpoint(
                    path=f"{smatch.group(1)}/{rmatch.group(1)}",
                    method="RPC",
                    operation_id=rmatch.group(1),
                ))

        return contract

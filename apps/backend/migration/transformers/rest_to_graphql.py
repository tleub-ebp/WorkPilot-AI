"""
REST to GraphQL Transformer
Transforms REST API endpoints into a GraphQL schema scaffold.

Strategy
--------
We don't try to fully migrate handlers — that needs human review on
business semantics. Instead we generate a *scaffold* that's much more
useful than the previous TODO-only template:

* parse REST routes (FastAPI, Flask, Express, NestJS) with regex
* GET → Query field
* POST/PUT/PATCH → Mutation field
* DELETE → Mutation field returning Boolean
* infer GraphQL types from route paths (`/users/{id}` → `User`,
  `/orders` → `Order`)
* emit a stub resolver per route, with a clear `TODO(<handler>)`
  pointing back at the original handler so the developer can wire it up

The output is opinionated but compiles in any GraphQL server (the
schema text is valid SDL).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..models import TransformationResult


@dataclass(frozen=True)
class _RestRoute:
    """One detected REST route."""

    method: str  # GET / POST / PUT / DELETE / PATCH
    path: str  # /users/{id}
    handler: str  # detected handler / function name (best-effort)
    framework: str  # fastapi | flask | express | nestjs | unknown


# ---------------------------------------------------------------------------
# Detection patterns


_FASTAPI_ROUTE_RE = re.compile(
    r"@(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_FLASK_ROUTE_RE = re.compile(
    r"@(?:app|bp|blueprint)\.route\(\s*[\"']([^\"']+)[\"']\s*,\s*methods\s*=\s*\[([^\]]*)\]",
    re.IGNORECASE,
)
_EXPRESS_ROUTE_RE = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch)\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
_NESTJS_DECORATOR_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch)\(\s*[\"']?([^\"')]*)[\"']?\s*\)",
)
# Best-effort handler-name capture: the function or method right after
# the route declaration.
_DEF_AFTER_ROUTE_RE = re.compile(
    r"(?:def|async\s+def|function|public|private|protected)\s+(\w+)",
)


# ---------------------------------------------------------------------------
# Helpers


def _singularise(word: str) -> str:
    """Crude singulariser for resource names: users → User, queries → Query."""
    if word.endswith("ies"):
        return word[:-3].capitalize() + "y"
    if word.endswith("ses") or word.endswith("xes"):
        return word[:-2].capitalize()
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1].capitalize()
    return word.capitalize()


def _resource_from_path(path: str) -> str:
    """`/users/{id}/posts` → `Post` (last meaningful segment)."""
    segments = [s for s in path.strip("/").split("/") if s and not s.startswith("{")]
    if not segments:
        return "Resource"
    return _singularise(segments[-1].replace("-", "_").replace(".", "_"))


def _path_args(path: str) -> list[str]:
    """Extract `{id}`-style path parameters."""
    # Both `{id}` and `:id` syntaxes.
    curly = re.findall(r"\{(\w+)\}", path)
    colon = re.findall(r":(\w+)", path)
    return curly + colon


def _field_name(method: str, path: str, handler: str | None) -> str:
    """Best-guess GraphQL field name."""
    if handler:
        return handler
    res = _resource_from_path(path).lower()
    if method == "GET":
        # /users → users (list), /users/{id} → user (single)
        return f"{res}_by_id" if _path_args(path) else f"{res}s"
    if method == "POST":
        return f"create_{res}"
    if method in ("PUT", "PATCH"):
        return f"update_{res}"
    if method == "DELETE":
        return f"delete_{res}"
    return res


# ---------------------------------------------------------------------------
# Transformer


class RestToGraphQLTransformer:
    """Transform REST API to GraphQL."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform REST endpoints to GraphQL."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                content = full_path.read_text()

                if self._is_rest_route_file(content):
                    transformed = self._transform_routes_to_graphql(content, file_path)
                    routes = self._extract_routes(content)
                    result = TransformationResult(
                        file_path=file_path,
                        transformation_type="rest_to_graphql",
                        before=content,
                        after=transformed,
                        changes_count=self._count_changes(content, transformed),
                        # Confidence reflects "we generated a sane scaffold,
                        # not a fully migrated codebase". Higher when we
                        # actually found routes.
                        confidence=0.75 if routes else 0.4,
                        validation_passed=False,
                    )
                    results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="rest_to_graphql",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"REST to GraphQL transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _is_rest_route_file(self, content: str) -> bool:
        """Check if file contains REST routes."""
        return bool(
            re.search(r"router\.(get|post|put|delete|patch)\(", content)
            or re.search(r"app\.(get|post|put|delete|patch)\(", content)
            or re.search(r"@(Get|Post|Put|Delete|Patch)\(", content)
            or _FASTAPI_ROUTE_RE.search(content)
            or _FLASK_ROUTE_RE.search(content)
        )

    # ------------------------------------------------------------------
    # Route extraction

    def _extract_routes(self, content: str) -> list[_RestRoute]:
        """Detect REST routes across known frameworks."""
        routes: list[_RestRoute] = []

        # FastAPI: @app.get("/users/{id}")  +  def list_users(...)
        for m in _FASTAPI_ROUTE_RE.finditer(content):
            method = m.group(1).upper()
            path = m.group(2)
            handler = self._handler_after(content, m.end())
            routes.append(_RestRoute(method, path, handler, "fastapi"))

        # Flask: @app.route("/x", methods=["GET","POST"])
        for m in _FLASK_ROUTE_RE.finditer(content):
            path = m.group(1)
            for method in re.findall(r"[\"'](\w+)[\"']", m.group(2)):
                handler = self._handler_after(content, m.end())
                routes.append(_RestRoute(method.upper(), path, handler, "flask"))

        # Express / NestJS share the .get(/post/...) syntax — but NestJS
        # uses decorators. We try the decorator first (more specific).
        for m in _NESTJS_DECORATOR_RE.finditer(content):
            method = m.group(1).upper()
            path = m.group(2) or "/"
            handler = self._handler_after(content, m.end())
            routes.append(_RestRoute(method, path, handler, "nestjs"))

        # Express call-style — but skip lines we already matched as FastAPI
        # (the regexes share `app.get(...)`). Best-effort dedup on (method, path).
        seen: set[tuple[str, str]] = {(r.method, r.path) for r in routes}
        for m in _EXPRESS_ROUTE_RE.finditer(content):
            method = m.group(1).upper()
            path = m.group(2)
            if (method, path) in seen:
                continue
            handler = self._handler_after(content, m.end())
            routes.append(_RestRoute(method, path, handler, "express"))
            seen.add((method, path))

        return routes

    @staticmethod
    def _handler_after(content: str, offset: int) -> str:
        """Best-effort handler-name capture in the next 200 chars."""
        snippet = content[offset : offset + 200]
        m = _DEF_AFTER_ROUTE_RE.search(snippet)
        return m.group(1) if m else ""

    # ------------------------------------------------------------------
    # SDL generation

    def _transform_routes_to_graphql(self, content: str, file_path: str) -> str:
        routes = self._extract_routes(content)

        if not routes:
            # Old behaviour: no routes detected → emit a clear notice rather
            # than a TODO-laden template that gets committed.
            return (
                f"# GraphQL scaffold for {file_path}\n"
                "# No REST routes detected — nothing to generate.\n"
            )

        types = self._infer_types(routes)
        queries = [r for r in routes if r.method == "GET"]
        mutations = [r for r in routes if r.method != "GET"]

        out: list[str] = []
        out.append(f"# GraphQL schema generated from {file_path}\n")
        out.append("# Resolvers below are stubs — wire them to the original")
        out.append("# REST handlers (named in the TODO comments).\n")

        # Type definitions
        for type_name in sorted(types):
            out.append(f"type {type_name} {{")
            out.append("  id: ID!")
            out.append("  # TODO: add fields based on the original response shape")
            out.append("}\n")

        # Query type
        out.append("type Query {")
        if queries:
            for r in queries:
                out.append(self._field_for(r))
        else:
            out.append("  _empty: Boolean")
        out.append("}\n")

        # Mutation type
        out.append("type Mutation {")
        if mutations:
            for r in mutations:
                out.append(self._field_for(r))
        else:
            out.append("  _empty: Boolean")
        out.append("}\n")

        # Stub resolvers (JSON-style sketch — language-agnostic)
        out.append("# --- Stub resolvers ---")
        out.append("# const resolvers = {")
        if queries:
            out.append("#   Query: {")
            for r in queries:
                out.append(self._resolver_for(r))
            out.append("#   },")
        if mutations:
            out.append("#   Mutation: {")
            for r in mutations:
                out.append(self._resolver_for(r))
            out.append("#   },")
        out.append("# };")
        return "\n".join(out) + "\n"

    @staticmethod
    def _infer_types(routes: list[_RestRoute]) -> set[str]:
        return {_resource_from_path(r.path) for r in routes}

    @staticmethod
    def _field_for(r: _RestRoute) -> str:
        """Single SDL field line for a route."""
        name = _field_name(r.method, r.path, r.handler)
        type_name = _resource_from_path(r.path)
        args = _path_args(r.path)
        arg_sig = ""
        if args:
            arg_sig = "(" + ", ".join(f"{a}: ID!" for a in args) + ")"
        if r.method == "GET":
            return_type = type_name if args else f"[{type_name}!]!"
        elif r.method == "DELETE":
            return_type = "Boolean!"
        else:
            return_type = type_name
        return f"  {name}{arg_sig}: {return_type}"

    @staticmethod
    def _resolver_for(r: _RestRoute) -> str:
        name = _field_name(r.method, r.path, r.handler)
        handler_hint = (
            r.handler or f"{r.method.lower()}_{_resource_from_path(r.path).lower()}"
        )
        return (
            f"#     {name}: async (parent, args, ctx) => {{ /* TODO({handler_hint}) — "
            f"port the {r.method} {r.path} handler */ }},"
        )

    # ------------------------------------------------------------------
    # Diff metric

    def _count_changes(self, before: str, after: str) -> int:
        before_lines = before.split("\n")
        after_lines = after.split("\n")
        changes = abs(len(before_lines) - len(after_lines))
        for b, a in zip(before_lines, after_lines):
            if b != a:
                changes += 1
        return changes

    def get_transformations(self) -> list[TransformationResult]:
        return self.transformations

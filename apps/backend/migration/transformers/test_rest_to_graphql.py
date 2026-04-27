"""Tests for the upgraded REST→GraphQL transformer.

Confirms the new behaviour: real route extraction → SDL with Query /
Mutation / type definitions, instead of the old TODO-only template.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from migration.transformers.rest_to_graphql import (
    RestToGraphQLTransformer,
    _field_name,
    _path_args,
    _resource_from_path,
    _RestRoute,
    _singularise,
)

# ----------------------------------------------------------------------
# Pure helpers


class TestHelpers:
    def test_singularise_basic(self) -> None:
        assert _singularise("users") == "User"
        assert _singularise("orders") == "Order"
        assert _singularise("queries") == "Query"
        assert _singularise("boxes") == "Box"
        # `classes` ends in -ses → strips 2 chars
        assert _singularise("classes") == "Class"
        # `class` ends in -ss (don't strip the trailing s)
        assert _singularise("class") == "Class"

    def test_resource_from_path(self) -> None:
        assert _resource_from_path("/users") == "User"
        assert _resource_from_path("/users/{id}") == "User"
        assert _resource_from_path("/users/{id}/posts") == "Post"
        assert _resource_from_path("/") == "Resource"

    def test_path_args_curly(self) -> None:
        assert _path_args("/users/{id}/posts/{postId}") == ["id", "postId"]

    def test_path_args_colon(self) -> None:
        assert _path_args("/users/:id") == ["id"]

    def test_field_name_handler_wins(self) -> None:
        assert _field_name("GET", "/x", handler="my_handler") == "my_handler"

    def test_field_name_falls_back_to_path(self) -> None:
        assert _field_name("GET", "/users", handler=None) == "users"  # list
        assert _field_name("GET", "/users/{id}", handler=None) == "user_by_id"
        assert _field_name("POST", "/users", handler=None) == "create_user"
        assert _field_name("PATCH", "/users/{id}", handler=None) == "update_user"
        assert _field_name("DELETE", "/users/{id}", handler=None) == "delete_user"


# ----------------------------------------------------------------------
# Route extraction


class TestRouteExtraction:
    def _xfm(self, tmp_path: Path) -> RestToGraphQLTransformer:
        return RestToGraphQLTransformer(str(tmp_path))

    def test_fastapi_routes_extracted(self, tmp_path: Path) -> None:
        content = (
            "from fastapi import APIRouter\n"
            "router = APIRouter()\n"
            "@router.get('/users')\n"
            "def list_users(): pass\n"
            "@router.post('/users')\n"
            "def create_user(): pass\n"
        )
        routes = self._xfm(tmp_path)._extract_routes(content)
        methods = {r.method for r in routes}
        assert methods == {"GET", "POST"}
        # Handlers picked up from the def line.
        names = {r.handler for r in routes}
        assert names == {"list_users", "create_user"}

    def test_flask_route_with_methods_array(self, tmp_path: Path) -> None:
        content = (
            "@app.route('/users', methods=['GET','POST'])\ndef users_handler(): pass\n"
        )
        routes = self._xfm(tmp_path)._extract_routes(content)
        assert {r.method for r in routes} == {"GET", "POST"}

    def test_express_routes(self, tmp_path: Path) -> None:
        content = (
            "router.get('/orders', listOrders)\nrouter.post('/orders', createOrder)\n"
        )
        routes = self._xfm(tmp_path)._extract_routes(content)
        assert {r.method for r in routes} == {"GET", "POST"}

    def test_nestjs_decorator(self, tmp_path: Path) -> None:
        content = "@Get('/health')\npublic healthCheck() { return {ok: true}; }\n"
        routes = self._xfm(tmp_path)._extract_routes(content)
        assert routes and routes[0].method == "GET"

    def test_no_routes_returns_empty(self, tmp_path: Path) -> None:
        assert self._xfm(tmp_path)._extract_routes("nothing to see here") == []


# ----------------------------------------------------------------------
# SDL generation


class TestSdlGeneration:
    def test_emits_query_for_get(self, tmp_path: Path) -> None:
        content = "@app.get('/users')\ndef list_users(): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        results = RestToGraphQLTransformer(str(tmp_path)).transform_files(["routes.py"])
        sdl = results[0].after
        assert "type Query" in sdl
        assert "type Mutation" in sdl
        # Real field, not a TODO.
        assert "list_users:" in sdl or "users:" in sdl
        assert "TODO: Auto-generate" not in sdl  # old behaviour gone

    def test_emits_mutation_for_post(self, tmp_path: Path) -> None:
        content = "@app.post('/orders')\ndef create_order(): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        results = RestToGraphQLTransformer(str(tmp_path)).transform_files(["routes.py"])
        sdl = results[0].after
        assert "create_order:" in sdl
        # Mutation block has the field, Query is empty placeholder.
        assert "type Mutation" in sdl
        assert "_empty: Boolean" in sdl  # placeholder Query

    def test_emits_type_per_resource(self, tmp_path: Path) -> None:
        content = (
            "@app.get('/users')\ndef list_users(): pass\n"
            "@app.get('/orders')\ndef list_orders(): pass\n"
        )
        f = tmp_path / "routes.py"
        f.write_text(content)
        results = RestToGraphQLTransformer(str(tmp_path)).transform_files(["routes.py"])
        sdl = results[0].after
        assert "type User" in sdl
        assert "type Order" in sdl

    def test_path_args_become_field_args(self, tmp_path: Path) -> None:
        content = "@app.get('/users/{id}')\ndef get_user(id): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        sdl = (
            RestToGraphQLTransformer(str(tmp_path))
            .transform_files(["routes.py"])[0]
            .after
        )
        # Argument list with id: ID!
        assert "id: ID!" in sdl
        # Single-item return type
        assert ": User" in sdl

    def test_get_collection_returns_list(self, tmp_path: Path) -> None:
        content = "@app.get('/users')\ndef list_users(): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        sdl = (
            RestToGraphQLTransformer(str(tmp_path))
            .transform_files(["routes.py"])[0]
            .after
        )
        # List notation present
        assert "[User!]!" in sdl

    def test_delete_returns_boolean(self, tmp_path: Path) -> None:
        content = "@app.delete('/users/{id}')\ndef delete_user(id): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        sdl = (
            RestToGraphQLTransformer(str(tmp_path))
            .transform_files(["routes.py"])[0]
            .after
        )
        assert "Boolean!" in sdl

    def test_resolver_stub_mentions_handler(self, tmp_path: Path) -> None:
        content = "@app.post('/payments')\ndef charge_card(): pass\n"
        f = tmp_path / "routes.py"
        f.write_text(content)
        sdl = (
            RestToGraphQLTransformer(str(tmp_path))
            .transform_files(["routes.py"])[0]
            .after
        )
        # The original handler name appears in the resolver TODO.
        assert "charge_card" in sdl

    def test_no_routes_emits_clear_notice(self, tmp_path: Path) -> None:
        content = "# no routes here\nprint('hello')\n"
        f = tmp_path / "boring.py"
        f.write_text(content)
        # _is_rest_route_file returns False → no transformation result emitted.
        results = RestToGraphQLTransformer(str(tmp_path)).transform_files(["boring.py"])
        assert results == []


# ----------------------------------------------------------------------
# Confidence


class TestConfidence:
    def test_routes_found_gives_higher_confidence(self, tmp_path: Path) -> None:
        good = tmp_path / "good.py"
        good.write_text("@app.get('/users')\ndef list_users(): pass\n")
        result = RestToGraphQLTransformer(str(tmp_path)).transform_files(["good.py"])[0]
        assert result.confidence == pytest.approx(0.75)

    def test_naming_only_files_skipped(self, tmp_path: Path) -> None:
        # `def get_X` alone (no decorator, no .get(...) call) is not a route
        # file. The detector intentionally avoids false positives here.
        f = tmp_path / "naming.py"
        f.write_text("def get_things(): pass\ndef post_stuff(): pass\n")
        result = RestToGraphQLTransformer(str(tmp_path)).transform_files(["naming.py"])
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

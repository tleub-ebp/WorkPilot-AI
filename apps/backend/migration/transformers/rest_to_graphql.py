"""
REST to GraphQL Transformer
Transforms REST API endpoints to GraphQL schema and resolvers
"""

import re
from typing import List
from pathlib import Path

from ..models import TransformationResult


class RestToGraphQLTransformer:
    """Transform REST API to GraphQL."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: List[TransformationResult] = []

    def transform_files(self, file_paths: List[str]) -> List[TransformationResult]:
        """Transform REST endpoints to GraphQL."""
        results = []
        
        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue
                
                content = full_path.read_text()
                
                # Transform REST routes to GraphQL
                if self._is_rest_route_file(content):
                    transformed = self._transform_routes_to_graphql(content, file_path)
                    result = TransformationResult(
                        file_path=file_path,
                        transformation_type="rest_to_graphql",
                        before=content,
                        after=transformed,
                        changes_count=self._count_changes(content, transformed),
                        confidence=0.75,  # Lower confidence for complex transformations
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
            re.search(r'router\.(get|post|put|delete|patch)\(', content) or
            re.search(r'app\.(get|post|put|delete|patch)\(', content) or
            re.search(r'@(Get|Post|Put|Delete|Patch)\(', content) or
            re.search(r'def\s+(get|post|put|delete|patch)_', content, re.IGNORECASE)
        )

    def _transform_routes_to_graphql(self, content: str, file_path: str) -> str:
        """Transform REST routes to GraphQL schema and resolvers."""
        # Stub implementation - REST to GraphQL is complex
        # Would need to:
        # 1. Parse all routes and methods
        # 2. Generate GraphQL types from route responses
        # 3. Generate resolvers from route handlers
        # 4. Handle authentication and middleware
        
        graphql_template = '''# GraphQL Schema
type Query {
  # TODO: Auto-generate queries from REST endpoints
}

type Mutation {
  # TODO: Auto-generate mutations from REST endpoints
}

# TODO: Auto-generate types from REST responses
'''
        
        return graphql_template

    def _count_changes(self, before: str, after: str) -> int:
        """Count lines changed."""
        before_lines = before.split('\n')
        after_lines = after.split('\n')
        
        changes = abs(len(before_lines) - len(after_lines))
        
        for b, a in zip(before_lines, after_lines):
            if b != a:
                changes += 1
        
        return changes

    def get_transformations(self) -> List[TransformationResult]:
        """Get all transformations."""
        return self.transformations

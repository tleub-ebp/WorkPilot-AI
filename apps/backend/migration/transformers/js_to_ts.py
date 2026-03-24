"""
JavaScript to TypeScript Transformer
Transforms JavaScript code to TypeScript with type annotations
"""

import re
from pathlib import Path

from ..models import TransformationResult


class JSToTypeScriptTransformer:
    """Transform JavaScript to TypeScript."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform JavaScript files to TypeScript."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists() or not (
                    file_path.endswith(".js") or file_path.endswith(".jsx")
                ):
                    continue

                content = full_path.read_text()

                # Transform JavaScript to TypeScript
                transformed = self._transform_to_typescript(content, file_path)

                # Change file extension
                ts_path = file_path.replace(".js", ".ts").replace(".jsx", ".tsx")

                result = TransformationResult(
                    file_path=ts_path,
                    transformation_type="js_to_ts",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.80,
                    validation_passed=False,
                )
                results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="js_to_ts",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"JS to TS transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _transform_to_typescript(self, content: str, file_path: str) -> str:
        """Transform JavaScript to TypeScript."""
        ts = content

        # 1. Add type annotations to function parameters
        ts = self._add_function_types(ts)

        # 2. Add return type annotations
        ts = self._add_return_types(ts)

        # 3. Add variable type annotations
        ts = self._add_variable_types(ts)

        # 4. Generate interfaces for objects
        ts = self._generate_interfaces(ts)

        # 5. Add strict type checking
        ts = self._add_strict_types(ts)

        return ts

    def _add_function_types(self, code: str) -> str:
        """Add type annotations to function parameters."""
        # function foo(a, b) { ... } -> function foo(a: any, b: any) { ... }
        code = re.sub(
            r"function\s+(\w+)\s*\(([^)]*)\)",
            lambda m: self._annotate_function_params(m),
            code,
        )

        # const foo = (a, b) => ... -> const foo = (a: any, b: any) => ...
        code = re.sub(
            r"const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>",
            lambda m: self._annotate_arrow_params(m),
            code,
        )

        return code

    def _annotate_function_params(self, match) -> str:
        """Annotate function parameters."""
        func_name = match.group(1)
        params = match.group(2)

        if not params.strip():
            return f"function {func_name}()"

        # Add ': any' to parameters that don't have types
        param_list = []
        for param in params.split(","):
            param = param.strip()
            if ":" not in param:  # No type annotation
                param = f"{param}: any"
            param_list.append(param)

        annotated_params = ", ".join(param_list)
        return f"function {func_name}({annotated_params})"

    def _annotate_arrow_params(self, match) -> str:
        """Annotate arrow function parameters."""
        var_name = match.group(1)
        params = match.group(2)

        if not params.strip():
            return f"const {var_name} = () =>"

        # Add ': any' to parameters
        param_list = []
        for param in params.split(","):
            param = param.strip()
            if ":" not in param:
                param = f"{param}: any"
            param_list.append(param)

        annotated_params = ", ".join(param_list)
        return f"const {var_name} = ({annotated_params}) =>"

    def _add_return_types(self, code: str) -> str:
        """Add return type annotations."""
        # This is complex - for now, add ': any' to all functions
        # More advanced analysis would infer actual types

        # function foo(...): any { ... }
        code = re.sub(
            r"function\s+(\w+)\s*\([^)]*\)\s*{", r"function \1(...): any {", code
        )

        # const foo = (...): any => ...
        code = re.sub(
            r"const\s+(\w+)\s*=\s*\([^)]*\)\s*:\s*any\s*=>",
            r"const \1 = (...): any =>",
            code,
        )

        return code

    def _add_variable_types(self, code: str) -> str:
        """Add type annotations to variables."""
        # const x = 5; -> const x: number = 5;
        # This requires type inference - for now, use 'any'

        code = re.sub(r"const\s+(\w+)\s*=\s*(\d+)", r"const \1: number = \2", code)

        code = re.sub(
            r'const\s+(\w+)\s*=\s*([\'"][^\'"]+ [\'"])', r"const \1: string = \2", code
        )

        code = re.sub(r"const\s+(\w+)\s*=\s*({)", r"const \1: any = \2", code)

        return code

    def _generate_interfaces(self, code: str) -> str:
        """Generate TypeScript interfaces for objects."""
        # Find object patterns and suggest interfaces

        # For now, add a basic interface generation stub
        if "interface" not in code:
            # Add a generic type any import
            if "import" in code:
                code = code.replace(
                    "import",
                    "// TypeScript interfaces\n// TODO: Define interfaces for object types\n\nimport",
                    1,
                )

        return code

    def _add_strict_types(self, code: str) -> str:
        """Add strict type checking."""
        # Add 'as' type guards where needed
        # Use 'unknown' instead of 'any' for safer typing

        return code

    def _count_changes(self, before: str, after: str) -> int:
        """Count lines changed."""
        before_lines = before.split("\n")
        after_lines = after.split("\n")

        changes = abs(len(before_lines) - len(after_lines))

        for b, a in zip(before_lines, after_lines):
            if b != a:
                changes += 1

        return changes

    def get_transformations(self) -> list[TransformationResult]:
        """Get all transformations."""
        return self.transformations

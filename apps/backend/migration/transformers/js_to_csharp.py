"""
JavaScript/TypeScript to C# (.NET) Transformer
Transforms JavaScript/TypeScript code to C# for .NET applications
"""

import re
from pathlib import Path

from ..models import TransformationResult


class JSToCSharpTransformer:
    """Transform JavaScript/TypeScript to C#."""

    # Type mappings from JavaScript to C#
    TYPE_MAPPINGS = {
        "string": "string",
        "number": "double",
        "int": "int",
        "boolean": "bool",
        "object": "object",
        "any": "dynamic",
        "void": "void",
        "array": "List",
        "Array": "List",
        "Date": "DateTime",
        "Promise": "Task",
        "null": "null",
        "undefined": "null",
    }

    # Keyword mappings
    KEYWORD_MAPPINGS = {
        "const": "const",
        "let": "var",
        "var": "var",
        "function": "public void",
        "class": "public class",
        "interface": "public interface",
        "enum": "public enum",
        "import": "using",
        "export": "public",
        "async": "async",
        "await": "await",
        "try": "try",
        "catch": "catch",
        "finally": "finally",
        "throw": "throw",
        "return": "return",
        "if": "if",
        "else": "else",
        "for": "for",
        "while": "while",
        "do": "do",
        "switch": "switch",
        "case": "case",
        "default": "default",
        "break": "break",
        "continue": "continue",
        "true": "true",
        "false": "false",
    }

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform JavaScript/TypeScript files to C#."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                if not (file_path.endswith(".js") or file_path.endswith(".ts")):
                    continue

                content = full_path.read_text()

                # Transform to C#
                transformed = self._transform_to_csharp(content, file_path)

                # Change file extension to .cs
                cs_path = file_path.replace(".js", ".cs").replace(".ts", ".cs")

                result = TransformationResult(
                    file_path=cs_path,
                    transformation_type="js_to_csharp",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.78,
                    validation_passed=False,
                )
                results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="js_to_csharp",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"C# transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _transform_to_csharp(self, content: str, file_path: str) -> str:
        """Transform JavaScript to C#."""
        csharp = content

        # 1. Transform imports to using statements
        csharp = self._transform_imports(csharp)

        # 2. Transform function declarations
        csharp = self._transform_functions(csharp)

        # 3. Transform async/await (after function transformation)
        csharp = self._transform_async_await(csharp)

        # 4. Transform class declarations
        csharp = self._transform_classes(csharp)

        # 5. Transform variable declarations
        csharp = self._transform_variables(csharp)

        # 6. Transform type annotations
        csharp = self._transform_types(csharp)

        # 7. Transform object literals to C# objects
        csharp = self._transform_objects(csharp)

        # 8. Transform array methods
        csharp = self._transform_arrays(csharp)

        # 9. Transform string methods
        csharp = self._transform_strings(csharp)

        # 10. Transform template literals
        csharp = self._transform_template_literals(csharp)

        # 11. Wrap in namespace
        csharp = self._wrap_in_namespace(csharp, file_path)

        return csharp

    def _transform_imports(self, content: str) -> str:
        """Transform ES6 imports to C# using statements."""
        # import { x, y } from 'module' -> using Module;
        pattern = r'import\s+{([^}]+)}\s+from\s+[\'"]([^\'"]+)[\'"]'

        def replace_import(match):
            module = match.group(2)

            # Convert module name to PascalCase for C#
            module_parts = module.replace("-", "_").split("_")
            module_name = "".join(word.capitalize() for word in module_parts)

            return f"using {module_name};"

        content = re.sub(pattern, replace_import, content)

        # import * as name from 'module'
        pattern = r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        content = re.sub(pattern, r"using \2;", content)

        # import defaultExport from 'module'
        pattern = r'import\s+(\w+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        content = re.sub(pattern, r"using \2;", content)

        return content

    def _transform_functions(self, content: str) -> str:
        """Transform function declarations."""
        # function name(param: Type) => { ... }
        pattern = r"function\s+(\w+)\s*\(([^)]*)\)\s*:\s*(\w+)\s*{"

        def replace_func(match):
            func_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3)

            csharp_type = self.TYPE_MAPPINGS.get(return_type, return_type)
            csharp_params = self._convert_params_to_csharp(params)

            return f"public {csharp_type} {func_name}({csharp_params}) {{"

        content = re.sub(pattern, replace_func, content)

        # Arrow functions: const name = (param: Type): Type => { ... }
        pattern = r"const\s+(\w+)\s*=\s*\(([^)]*)\)\s*:\s*(\w+)\s*=>\s*{"
        content = re.sub(pattern, lambda m: self._convert_arrow_to_csharp(m), content)

        # Arrow functions without types: const name = (param) => { ... }
        pattern = r"const\s+(\w+)\s*=\s*async\s*\(([^)]*)\)\s*=>\s*{"
        content = re.sub(
            pattern, lambda m: self._convert_arrow_to_csharp_simple(m), content
        )

        pattern = r"const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>\s*{"
        content = re.sub(
            pattern, lambda m: self._convert_arrow_to_csharp_simple(m), content
        )

        return content

    def _convert_params_to_csharp(self, params: str) -> str:
        """Convert function parameters to C# syntax."""
        if not params.strip():
            return ""

        csharp_params = []
        for param in params.split(","):
            param = param.strip()
            if ":" in param:
                # Has type annotation
                name, ptype = param.split("=")
                name = name.strip()
                ptype = ptype.strip()
                csharp_type = self.TYPE_MAPPINGS.get(ptype, ptype)
                csharp_params.append(f"{csharp_type} {name}")
            else:
                # No type, default to dynamic
                csharp_params.append(f"dynamic {param}")

        return ", ".join(csharp_params)

    def _convert_arrow_to_csharp(self, match) -> str:
        """Convert arrow function to C# method."""
        func_name = match.group(1)
        params = match.group(2)
        return_type = match.group(3)

        csharp_type = self.TYPE_MAPPINGS.get(return_type, return_type)
        csharp_params = self._convert_params_to_csharp(params)

        return f"public {csharp_type} {func_name}({csharp_params}) {{"

    def _convert_arrow_to_csharp_simple(self, match) -> str:
        """Convert arrow function without types to C# method."""
        func_name = match.group(1)
        params = match.group(2)
        csharp_params = self._convert_params_to_csharp(params)

        # Check if the original match was for an async function
        original_text = match.group(0)
        if "async" in original_text:
            return f"public async Task {func_name}({csharp_params}) {{"
        else:
            return f"public void {func_name}({csharp_params}) {{"

    def _transform_classes(self, content: str) -> str:
        """Transform class declarations."""
        # class ClassName { ... } or class ClassName extends ParentClass { ... }
        pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{"

        def replace_class(match):
            class_name = match.group(1)
            parent = match.group(2)

            if parent:
                return f"public class {class_name} : {parent} {{"
            else:
                return f"public class {class_name} {{"

        content = re.sub(pattern, replace_class, content)

        return content

    def _transform_variables(self, content: str) -> str:
        """Transform variable declarations."""
        # const name: Type = value -> Type name = value;
        pattern = r"(?:const|let|var)\s+(\w+)\s*:\s*(\w+)\s*="

        def replace_var(match):
            var_name = match.group(1)
            var_type = match.group(2)

            csharp_type = self.TYPE_MAPPINGS.get(var_type, var_type)
            return f"{csharp_type} {var_name} ="

        content = re.sub(pattern, replace_var, content)

        # const/let/var name = value -> var name = value;
        pattern = r"(?:const|let|var)\s+(\w+)\s*="
        content = re.sub(pattern, r"var \1 =", content)

        return content

    def _transform_types(self, content: str) -> str:
        """Transform TypeScript type annotations."""
        for ts_type, csharp_type in self.TYPE_MAPPINGS.items():
            content = re.sub(f":\\s*{ts_type}\\b", f": {csharp_type}", content)

        return content

    def _transform_async_await(self, content: str) -> str:
        """Transform async/await patterns."""
        # async function name() => async Task name()
        content = re.sub(r"async\s+function\s+(\w+)", r"async Task \1", content)

        # async const name = (params) => ... => async Task name(params)
        content = re.sub(
            r"async\s+const\s+(\w+)\s*=\s*\(([^)]*)\)\s*=>",
            r"async Task \1(\2)",
            content,
        )

        # () => { } becomes () => { }
        # Already handled by function transformation

        return content

    def _transform_objects(self, content: str) -> str:
        """Transform object literals to C# objects."""
        # { key: value } -> new Dictionary { { "key", value } }
        # Could be complex, simplified version

        return content

    def _transform_arrays(self, content: str) -> str:
        """Transform array methods."""
        # .map() -> .Select()
        content = content.replace(".map(", ".Select(")

        # .filter() -> .Where()
        content = content.replace(".filter(", ".Where(")

        # .reduce() -> .Aggregate()
        content = content.replace(".reduce(", ".Aggregate(")

        # .forEach() -> .ForEach()
        content = content.replace(".forEach(", ".ForEach(")

        # .find() -> .FirstOrDefault()
        content = content.replace(".find(", ".FirstOrDefault(")

        # .includes() -> .Contains()
        content = content.replace(".includes(", ".Contains(")

        # .push() -> .Add()
        content = content.replace(".push(", ".Add(")

        # .pop() -> RemoveAt()
        content = content.replace(".pop(", ".RemoveAt(Count - 1)")

        return content

    def _transform_strings(self, content: str) -> str:
        """Transform string methods."""
        # .substring() -> .Substring()
        content = content.replace(".substring(", ".Substring(")

        # .charAt() -> .Char.At() or [index]
        content = re.sub(r"\.charAt\((\w+)\)", r"[\1]", content)

        # .toUpperCase() -> .ToUpper()
        content = content.replace(".toUpperCase(", ".ToUpper(")

        # .toLowerCase() -> .ToLower()
        content = content.replace(r"\.toLowerCase\(", ".ToLower(", content)

        # .trim() -> .Trim()
        content = content.replace(r"\.trim\(", ".Trim(", content)

        # .split() -> .Split()
        content = content.replace(r"\.split\(", ".Split(", content)

        # .replace() -> .Replace()
        content = content.replace(r"\.replace\(", ".Replace(", content)

        # .includes() -> .Contains()
        content = content.replace(r"\.includes\(", ".Contains(", content)

        return content

    def _transform_template_literals(self, content: str) -> str:
        """Transform template literals to string interpolation."""
        # `text ${variable}` -> $"text {variable}"
        pattern = r"`([^`]*)\$\{([^}]+)\}([^`]*)`"

        def replace_template(match):
            before = match.group(1)
            variable = match.group(2)
            after = match.group(3)

            return f'$"{before}{{{variable}}}{after}"'

        content = re.sub(pattern, replace_template, content)

        # Simple template literals without variables
        content = re.sub(r"`([^`]*)`", r'"\1"', content)

        return content

    def _wrap_in_namespace(self, content: str, file_path: str) -> str:
        """Wrap code in C# namespace."""
        # Extract namespace from file path
        namespace = "MyApplication"

        if "services" in file_path:
            namespace = "MyApplication.Services"
        elif "models" in file_path:
            namespace = "MyApplication.Models"
        elif "controllers" in file_path:
            namespace = "MyApplication.Controllers"
        elif "utils" in file_path:
            namespace = "MyApplication.Utils"

        csharp_code = f"""using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace {namespace}
{{
{self._indent_code(content)}
}}
"""

        return csharp_code

    def _indent_code(self, content: str, spaces: int = 4) -> str:
        """Indent code with specified number of spaces."""
        indent = " " * spaces
        lines = content.split("\n")
        indented = [indent + line if line.strip() else line for line in lines]
        return "\n".join(indented)

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

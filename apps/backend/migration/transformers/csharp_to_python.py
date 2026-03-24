"""
C# to Python Transformer
Transforms C# code to Python
"""

import re
from pathlib import Path

from ..models import TransformationResult


class CSharpToPythonTransformer:
    """Transform C# code to Python."""

    # Type mappings from C# to Python
    TYPE_MAPPINGS = {
        "string": "str",
        "int": "int",
        "double": "float",
        "float": "float",
        "bool": "bool",
        "object": "object",
        "dynamic": "Any",
        "void": "None",
        "List": "list",
        "Dictionary": "dict",
        "Task": "asyncio.Task",
        "DateTime": "datetime",
        "Guid": "uuid.UUID",
        "decimal": "Decimal",
        "byte": "bytes",
        "char": "str",
        "long": "int",
    }

    # Keyword mappings
    KEYWORD_MAPPINGS = {
        "public": "",  # Python doesn't use public
        "private": "",  # Python uses _
        "protected": "",  # Python uses _
        "static": "@staticmethod",
        "abstract": "",  # Use ABC instead
        "virtual": "",  # Python doesn't need this
        "override": "",  # Python uses super()
        "class": "class",
        "interface": "class",  # Use ABC for interface
        "namespace": "",  # Use packages instead
        "using": "import",
        "async": "async",
        "await": "await",
        "try": "try",
        "catch": "except",
        "finally": "finally",
        "throw": "raise",
        "return": "return",
        "if": "if",
        "else": "else",
        "else if": "elif",
        "for": "for",
        "foreach": "for",
        "while": "while",
        "do": "while",  # Convert to while True
        "switch": "if/elif",  # Use if/elif in Python
        "case": "",  # Not needed in Python
        "break": "break",
        "continue": "continue",
        "true": "True",
        "false": "False",
        "null": "None",
        "var": "",  # Python has dynamic typing
        "const": "",  # No const in Python
        "readonly": "",  # No readonly in Python
        "new": "",  # Python doesn't need new
    }

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform C# files to Python."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists() or not file_path.endswith(".cs"):
                    continue

                content = full_path.read_text()

                # Transform to Python
                transformed = self._transform_to_python(content, file_path)

                # Change file extension to .py
                py_path = file_path.replace(".cs", ".py")

                result = TransformationResult(
                    file_path=py_path,
                    transformation_type="csharp_to_python",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.75,
                    validation_passed=False,
                )
                results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="csharp_to_python",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"C# to Python transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _transform_to_python(self, content: str, file_path: str) -> str:
        """Transform C# code to Python."""
        python = content

        # 1. Transform using statements to imports
        python = self._transform_using_statements(python)

        # 2. Transform namespace to package structure
        python = self._transform_namespace(python)

        # 3. Transform class definitions
        python = self._transform_classes(python)

        # 4. Transform properties to methods
        python = self._transform_properties(python)

        # 5. Transform method signatures
        python = self._transform_methods(python)

        # 6. Transform types
        python = self._transform_types(python)

        # 7. Transform control flow
        python = self._transform_control_flow(python)

        # 8. Transform LINQ to comprehensions
        python = self._transform_linq(python)

        # 9. Transform access modifiers
        python = self._transform_access_modifiers(python)

        # 10. Add Python imports
        python = self._add_python_imports(python)

        return python

    def _transform_using_statements(self, content: str) -> str:
        """Transform using statements to imports."""
        # using System; -> import sys
        # using System.Collections.Generic; -> from collections import defaultdict

        mappings = {
            r"using System;": "import sys",
            r"using System\.Collections\.Generic;": "from collections import defaultdict, OrderedDict",
            r"using System\.Linq;": "from functools import reduce",
            r"using System\.Threading\.Tasks;": "import asyncio",
            r"using System\.Text;": "import string",
            r"using System\.IO;": "import os, io",
            r"using System\.Net;": "import socket, urllib",
            r"using System\.Json;": "import json",
        }

        for csharp, python in mappings.items():
            content = re.sub(csharp, python, content)

        return content

    def _transform_namespace(self, content: str) -> str:
        """Transform namespace to Python package."""
        # Remove namespace declarations (Python uses directory structure)
        pattern = r"namespace\s+[\w\.]+\s*{"
        content = re.sub(pattern, "", content)

        # Remove closing brace for namespace
        # This is tricky - for now, just note it

        return content

    def _transform_classes(self, content: str) -> str:
        """Transform class definitions."""
        # public class MyClass : IInterface -> class MyClass:
        pattern = (
            r"(?:public\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s*:\s*([^\{]+))?\s*\{"
        )

        def replace_class(match):
            class_name = match.group(1)
            bases = match.group(2)

            if bases:
                bases = bases.strip()
                # Remove interface markers
                bases = bases.replace("I", "", 1) if bases.startswith("I") else bases
                return f"class {class_name}({bases}):"
            else:
                return f"class {class_name}:"

        content = re.sub(pattern, replace_class, content)

        return content

    def _transform_properties(self, content: str) -> str:
        """Transform C# properties to Python methods."""
        # public string Name { get; set; } ->
        # def name(self, value=None):

        pattern = r"public\s+(\w+)\s+(\w+)\s*\{\s*get;\s*set;\s*\}"

        def replace_property(match):
            prop_type = match.group(1)
            prop_name = match.group(2)

            python_type = self.TYPE_MAPPINGS.get(prop_type, prop_type)

            return f"""@property
    def {prop_name.lower()}(self) -> {python_type}:
        return self._{prop_name.lower()}
    
    @{prop_name.lower()}.setter
    def {prop_name.lower()}(self, value: {python_type}) -> None:
        self._{prop_name.lower()} = value"""

        content = re.sub(pattern, replace_property, content)

        return content

    def _transform_methods(self, content: str) -> str:
        """Transform method signatures."""
        # public void MyMethod(string param) ->
        # def my_method(self, param: str) -> None:

        pattern = r"(?:public|private|protected)?\s*(?:static\s+)?(?:async\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)\s*"

        def replace_method(match):
            return_type = match.group(1)
            method_name = match.group(2)
            params = match.group(3)

            # Convert return type
            python_return = self.TYPE_MAPPINGS.get(return_type, return_type)

            # Convert parameters
            param_list = []
            if params.strip():
                for param in params.split(","):
                    param = param.strip()
                    if " " in param:
                        ptype, pname = param.rsplit(" ", 1)
                        python_ptype = self.TYPE_MAPPINGS.get(ptype, ptype)
                        param_list.append(f"{pname}: {python_ptype}")
                    else:
                        param_list.append(f"{param}: Any")

            params_str = ", ".join(param_list)
            if params_str:
                params_str = "self, " + params_str
            else:
                params_str = "self"

            method_name_python = self._to_snake_case(method_name)

            return f"def {method_name_python}({params_str}) -> {python_return}:"

        content = re.sub(pattern, replace_method, content, flags=re.MULTILINE)

        return content

    def _transform_types(self, content: str) -> str:
        """Transform type annotations."""
        for csharp_type, python_type in self.TYPE_MAPPINGS.items():
            pattern = f"\\b{csharp_type}\\b(?!\\w)"
            content = re.sub(pattern, python_type, content)

        return content

    def _transform_control_flow(self, content: str) -> str:
        """Transform control flow."""
        # else if -> elif
        content = re.sub(r"else\s+if\s*\(", "elif (", content)

        # Remove semicolons
        content = re.sub(r";$", "", content, flags=re.MULTILINE)

        # Transform for/foreach
        content = re.sub(
            r"foreach\s*\(\s*var\s+(\w+)\s+in\s+(\w+)\s*\)", r"for \1 in \2:", content
        )

        return content

    def _transform_linq(self, content: str) -> str:
        """Transform LINQ to Python comprehensions."""
        # .Where(x => x.IsActive).Select(x => x.Name) ->
        # [item.name for item in items if item.is_active]

        # This is complex - for now, just note it in comments
        content = re.sub(
            r"\.Where\s*\(\s*(\w+)\s*=>\s*([^)]+)\)",
            lambda m: f" if {m.group(2).replace(m.group(1) + '.', '')}",
            content,
        )

        return content

    def _transform_access_modifiers(self, content: str) -> str:
        """Transform access modifiers."""
        # public -> (removed, default in Python)
        content = re.sub(r"\bpublic\s+", "", content)

        # private -> _ prefix
        content = re.sub(r"\bprivate\s+", "self._", content)

        # protected -> _ prefix
        content = re.sub(r"\bprotected\s+", "self._", content)

        return content

    def _add_python_imports(self, content: str) -> str:
        """Add necessary Python imports."""
        imports = []

        if "async" in content:
            imports.append("import asyncio")
        if "datetime" in content.lower():
            imports.append("from datetime import datetime")
        if "uuid" in content.lower():
            imports.append("import uuid")
        if "Decimal" in content:
            imports.append("from decimal import Decimal")

        if imports:
            import_str = "\n".join(imports)
            content = import_str + "\n\n" + content

        return content

    def _to_snake_case(self, name: str) -> str:
        """Convert PascalCase to snake_case."""
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

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

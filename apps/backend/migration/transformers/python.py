"""
Python 2 to Python 3 Transformer
Transforms Python 2 code to Python 3 compatible code
"""

import re
from pathlib import Path

from ..models import TransformationResult


class PythonTransformer:
    """Transform Python 2 to Python 3."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform Python 2 files to Python 3."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists() or not file_path.endswith(".py"):
                    continue

                content = full_path.read_text()

                if not self._is_python2_code(content):
                    continue

                # Transform the content
                transformed = self._transform_to_python3(content)

                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="python2_to_3",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.88,
                    validation_passed=False,
                )
                results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="python2_to_3",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"Python transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _is_python2_code(self, content: str) -> bool:
        """Check if file is Python 2 code."""
        # Check for Python 2 specific patterns
        indicators = [
            r'print\s+[\'"]',  # print statement without parens
            r"print\s+\w",  # print statement
            r"xrange\(",  # xrange
            r"raw_input\(",  # raw_input
            r"unicode\(",  # unicode type
            r"basestring",  # basestring type
            r"<type \'",  # Old-style type representation
            r"\.iteritems\(",  # iteritems
            r"\.itervalues\(",  # itervalues
            r"\.iterkeys\(",  # iterkeys
            r"\/\/ ",  # Comment style
        ]

        return any(re.search(indicator, content) for indicator in indicators)

    def _transform_to_python3(self, content: str) -> str:
        """Transform Python 2 code to Python 3."""
        code = content

        # 1. Transform print statements to print functions
        code = self._transform_print_statements(code)

        # 2. Transform imports
        code = self._transform_imports(code)

        # 3. Transform string types and unicode
        code = self._transform_string_handling(code)

        # 4. Transform division operator
        code = self._transform_division(code)

        # 5. Transform iterator methods
        code = self._transform_iterators(code)

        # 6. Transform xrange to range
        code = self._transform_range(code)

        # 7. Transform exception syntax
        code = self._transform_exceptions(code)

        # 8. Transform dict methods
        code = self._transform_dict_methods(code)

        # 9. Transform comparisons
        code = self._transform_comparisons(code)

        # 10. Add future imports for compatibility
        code = self._add_future_imports(code)

        return code

    def _transform_print_statements(self, code: str) -> str:
        """Transform print statements to print functions."""
        lines = code.split("\n")
        result = []

        for line in lines:
            # Skip if already a print function
            if re.match(r"\s*print\s*\(", line):
                result.append(line)
                continue

            # Transform print statement
            # print "text" -> print("text")
            match = re.match(r"^(\s*)print\s+(.+)$", line)
            if match:
                indent = match.group(1)
                content = match.group(2)
                # Handle print with >> redirection
                if ">>" in content:
                    parts = content.split(">>", 1)
                    result.append(
                        f"{indent}print({parts[1].strip()}, file={parts[0].strip()})"
                    )
                else:
                    result.append(f"{indent}print({content})")
            else:
                result.append(line)

        return "\n".join(result)

    def _transform_imports(self, code: str) -> str:
        """Transform Python 2 imports to Python 3."""
        import_mappings = {
            "import StringIO": "from io import StringIO",
            "from StringIO import": "from io import",
            "import ConfigParser": "import configparser",
            "import Queue": "import queue",
            "import SocketServer": "import socketserver",
            "import xmlrpclib": "import xmlrpc.client",
            "import urllib2": "import urllib.request",
            "import urllib": "import urllib.parse",
            "import httplib": "import http.client",
            "import cookielib": "import http.cookiejar",
            "import htmllib": "import html.parser",
        }

        for py2, py3 in import_mappings.items():
            code = re.sub(
                f"^{re.escape(py2)}", py3, code, flags=re.MULTILINE | re.IGNORECASE
            )

        return code

    def _transform_string_handling(self, code: str) -> str:
        """Transform string and unicode handling."""
        # unicode() -> str()
        code = re.sub(r"\bunicode\s*\(", "str(", code)

        # basestring -> str
        code = re.sub(r"\bbasestring\b", "str", code)

        # isinstance(..., unicode) -> isinstance(..., str)
        code = re.sub(
            r"isinstance\s*\(\s*([^,]+)\s*,\s*unicode\s*\)",
            r"isinstance(\1, str)",
            code,
        )

        # isinstance(..., basestring) -> isinstance(..., str)
        code = re.sub(
            r"isinstance\s*\(\s*([^,]+)\s*,\s*basestring\s*\)",
            r"isinstance(\1, str)",
            code,
        )

        # Add coding declaration for non-ASCII
        if re.search(r"[^\x00-\x7F]", code):
            if not code.startswith("# -*- coding:"):
                code = "# -*- coding: utf-8 -*-\n" + code

        return code

    def _transform_division(self, code: str) -> str:
        """Transform division operator."""
        # This is tricky - need to add from __future__ import division
        # and convert / to // where integer division is needed

        # For now, add future import (user will need to review)
        if "/" in code and "from __future__ import division" not in code:
            # Simple heuristic: look for int division patterns
            code = re.sub(
                r"(\d+)\s*\/\s*(\d+)",
                r"\1 // \2",  # Convert literal divisions to floor division
                code,
            )

        return code

    def _transform_iterators(self, code: str) -> str:
        """Transform iterator methods."""
        # .iteritems() -> .items()
        code = re.sub(r"\.iteritems\(\)", ".items()", code)

        # .itervalues() -> .values()
        code = re.sub(r"\.itervalues\(\)", ".values()", code)

        # .iterkeys() -> .keys()
        code = re.sub(r"\.iterkeys\(\)", ".keys()", code)

        return code

    def _transform_range(self, code: str) -> str:
        """Transform xrange to range."""
        code = re.sub(r"\bxrange\b", "range", code)

        return code

    def _transform_exceptions(self, code: str) -> str:
        """Transform exception syntax."""
        # except Exception, e: -> except Exception as e:
        code = re.sub(r"except\s+(\w+)\s*,\s*(\w+)\s*:", r"except \1 as \2:", code)

        # raise Exception, "message" -> raise Exception("message")
        code = re.sub(r'raise\s+(\w+)\s*,\s*([\'"][^\'"]*[\'"])', r"raise \1(\2)", code)

        return code

    def _transform_dict_methods(self, code: str) -> str:
        """Transform dict methods."""
        # dict.has_key(key) -> key in dict
        code = re.sub(r"(\w+)\.has_key\(([^)]+)\)", r"\2 in \1", code)

        # dict.keys() in conditional
        code = re.sub(r"(\w+)\s+in\s+(\w+)\.keys\(\)", r"\1 in \2", code)

        return code

    def _transform_comparisons(self, code: str) -> str:
        """Transform comparisons."""
        # <> -> !=
        code = re.sub(r"<>", "!=", code)

        return code

    def _add_future_imports(self, code: str) -> str:
        """Add Python 3 future imports if not present."""
        lines = code.split("\n")

        # Check if future imports are needed
        needs_division = "/" in code and "from __future__ import division" not in code
        needs_print = "print " in code or "print\t" in code

        # Find position to add imports (after module docstring and encoding)
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith('"""') or line.startswith("'''"):
                # Skip docstring
                insert_pos = i + 1
            elif line.startswith("#"):
                # Skip comments and encoding declarations
                insert_pos = i + 1
            elif line.strip() and not line.startswith("from __future__"):
                break

        # Add future imports
        future_imports = []
        if needs_division or needs_print:
            future_imports.append("from __future__ import print_function")
        if needs_division:
            future_imports.append("from __future__ import division")

        if future_imports:
            for imp in future_imports:
                if imp not in code:
                    lines.insert(insert_pos, imp)
                    insert_pos += 1

        return "\n".join(lines)

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

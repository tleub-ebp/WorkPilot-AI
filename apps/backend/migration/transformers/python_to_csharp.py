"""
Python to C# Transformer
Transforms Python code to C# for .NET applications
"""

import re
from typing import List
from pathlib import Path

from ..models import TransformationResult


class PythonToCSharpTransformer:
    """Transform Python code to C#."""

    # Type mappings from Python to C#
    TYPE_MAPPINGS = {
        'str': 'string',
        'int': 'int',
        'float': 'double',
        'bool': 'bool',
        'list': 'List',
        'dict': 'Dictionary',
        'tuple': 'Tuple',
        'set': 'HashSet',
        'None': 'void',
        'Any': 'dynamic',
        'Optional': 'nullable',
        'datetime': 'DateTime',
        'Decimal': 'decimal',
        'bytes': 'byte[]',
        'object': 'object',
    }

    # Keyword mappings
    KEYWORD_MAPPINGS = {
        'def': '',  # Will be replaced with method signature
        'class': 'public class',
        'import': 'using',
        'from': 'using',
        'async': 'async',
        'await': 'await',
        'try': 'try',
        'except': 'catch',
        'finally': 'finally',
        'raise': 'throw',
        'return': 'return',
        'if': 'if',
        'elif': 'else if',
        'else': 'else',
        'for': 'for',
        'while': 'while',
        'break': 'break',
        'continue': 'continue',
        'pass': '{}',
        'True': 'true',
        'False': 'false',
        'None': 'null',
        'in': 'in',
        'not': '!',
        'and': '&&',
        'or': '||',
        'is': '==',
        'lambda': '=>',
    }

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: List[TransformationResult] = []

    def transform_files(self, file_paths: List[str]) -> List[TransformationResult]:
        """Transform Python files to C#."""
        results = []
        
        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists() or not file_path.endswith('.py'):
                    continue
                
                content = full_path.read_text()
                
                # Transform to C#
                transformed = self._transform_to_csharp(content, file_path)
                
                # Change file extension to .cs
                cs_path = file_path.replace('.py', '.cs')
                
                result = TransformationResult(
                    file_path=cs_path,
                    transformation_type="python_to_csharp",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.77,
                    validation_passed=False,
                )
                results.append(result)
                
            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="python_to_csharp",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"Python to C# transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)
        
        self.transformations = results
        return results

    def _transform_to_csharp(self, content: str, file_path: str) -> str:
        """Transform Python code to C#."""
        csharp = content
        
        # 1. Transform imports to using statements
        csharp = self._transform_imports(csharp)
        
        # 2. Transform class definitions
        csharp = self._transform_classes(csharp)
        
        # 3. Transform method definitions
        csharp = self._transform_methods(csharp)
        
        # 4. Transform decorators
        csharp = self._transform_decorators(csharp)
        
        # 5. Transform type annotations
        csharp = self._transform_type_annotations(csharp)
        
        # 6. Transform control flow
        csharp = self._transform_control_flow(csharp)
        
        # 7. Transform string formatting
        csharp = self._transform_strings(csharp)
        
        # 8. Transform list/dict comprehensions
        csharp = self._transform_comprehensions(csharp)
        
        # 9. Transform access modifiers
        csharp = self._transform_access_modifiers(csharp)
        
        # 10. Transform indentation to braces
        csharp = self._transform_indentation(csharp)
        
        # 11. Add C# using statements
        csharp = self._add_csharp_using(csharp)
        
        # 12. Wrap in namespace
        csharp = self._wrap_in_namespace(csharp, file_path)
        
        return csharp

    def _transform_imports(self, content: str) -> str:
        """Transform Python imports to C# using statements."""
        mappings = {
            r'import sys': 'using System;',
            r'import os': 'using System.IO;',
            r'import json': 'using Newtonsoft.Json;',
            r'import asyncio': 'using System.Threading.Tasks;',
            r'from datetime import datetime': 'using System;',
            r'from collections import': 'using System.Collections.Generic;',
            r'import math': 'using System;',
            r'import random': 'using System;',
            r'import uuid': 'using System;',
            r'import decimal': 'using System;',
        }
        
        for python, csharp in mappings.items():
            content = re.sub(python, csharp, content)
        
        # Generic import transformation
        pattern = r'from\s+(\w+)\s+import\s+(\w+)'
        content = re.sub(pattern, r'using \1;  // import \2', content)
        
        pattern = r'import\s+(\w+)'
        content = re.sub(pattern, r'using \1;', content)
        
        return content

    def _transform_classes(self, content: str) -> str:
        """Transform class definitions."""
        # class MyClass: -> public class MyClass {
        pattern = r'class\s+(\w+)(?:\(([^\)]*)\))?:'
        
        def replace_class(match):
            class_name = match.group(1)
            bases = match.group(2)
            
            if bases and bases.strip():
                return f'public class {class_name} : {bases} {{'
            else:
                return f'public class {class_name} {{'
        
        content = re.sub(pattern, replace_class, content)
        
        return content

    def _transform_methods(self, content: str) -> str:
        """Transform method definitions."""
        # def method_name(self, param: str) -> int: -> 
        # public int MethodName(string param) {
        
        pattern = r'def\s+(\w+)\s*\((?:self,?\s*)?([^)]*)\)(?:\s*->\s*(\w+))?:'
        
        def replace_method(match):
            method_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3)
            
            # Convert return type
            csharp_return = self.TYPE_MAPPINGS.get(return_type, return_type) if return_type else 'void'
            
            # Convert method name to PascalCase
            csharp_method_name = self._to_pascal_case(method_name)
            
            # Convert parameters
            param_list = self._convert_params_to_csharp(params)
            
            return f'public {csharp_return} {csharp_method_name}({param_list}) {{'
        
        content = re.sub(pattern, replace_method, content, flags=re.MULTILINE)
        
        return content

    def _convert_params_to_csharp(self, params: str) -> str:
        """Convert Python parameters to C#."""
        if not params.strip():
            return ''
        
        param_list = []
        for param in params.split(','):
            param = param.strip()
            if not param:
                continue
            
            # Handle type annotations
            if ':' in param:
                name, ptype = param.split(':', 1)
                name = name.strip()
                ptype = ptype.strip()
                
                # Remove default values
                if '=' in name:
                    name = name.split('=')[0].strip()
                
                csharp_type = self.TYPE_MAPPINGS.get(ptype, ptype)
                param_list.append(f'{csharp_type} {name}')
            else:
                # No type annotation
                name = param.split('=')[0].strip()
                param_list.append(f'dynamic {name}')
        
        return ', '.join(param_list)

    def _transform_decorators(self, content: str) -> str:
        """Transform Python decorators to C# attributes."""
        # @property -> [property]
        content = re.sub(r'@property', '[property]', content)
        
        # @staticmethod -> [static]
        content = re.sub(r'@staticmethod', '[static]', content)
        
        # @classmethod -> [static]
        content = re.sub(r'@classmethod', '[static]', content)
        
        return content

    def _transform_type_annotations(self, content: str) -> str:
        """Transform Python type annotations to C#."""
        for python_type, csharp_type in self.TYPE_MAPPINGS.items():
            pattern = f'\\b{python_type}\\b'
            content = re.sub(pattern, csharp_type, content)
        
        return content

    def _transform_control_flow(self, content: str) -> str:
        """Transform control flow statements."""
        # elif -> else if
        content = re.sub(r'\belif\b', 'else if', content)
        
        # Remove colons
        content = re.sub(r':\s*$', ' {', content, flags=re.MULTILINE)
        
        return content

    def _transform_strings(self, content: str) -> str:
        """Transform string formatting."""
        # f-string -> $-string in C#
        pattern = r'f["\']([^"\']*)\{([^}]*)\}([^"\']*)["\']'
        
        def replace_fstring(match):
            before = match.group(1)
            var = match.group(2)
            after = match.group(3)
            return f'$"{before}{{{var}}}{after}"'
        
        content = re.sub(pattern, replace_fstring, content)
        
        return content

    def _transform_comprehensions(self, content: str) -> str:
        """Transform list comprehensions to LINQ."""
        # [x for x in items] -> items.Select(x => x)
        pattern = r'\[(\w+)\s+for\s+(\w+)\s+in\s+(\w+)\]'
        content = re.sub(pattern, r'\3.Select(\2 => \1).ToList()', content)
        
        # [x for x in items if condition] -> items.Where(x => condition).Select(x => x)
        pattern = r'\[(\w+)\s+for\s+(\w+)\s+in\s+(\w+)\s+if\s+([^\]]+)\]'
        content = re.sub(pattern, r'\3.Where(\2 => \4).Select(\2 => \1).ToList()', content)
        
        return content

    def _transform_access_modifiers(self, content: str) -> str:
        """Transform Python access modifiers to C#."""
        # _private -> private
        content = re.sub(r'\b_([a-zA-Z])', r'private \1', content)
        
        # __private -> private
        content = re.sub(r'\b__([a-zA-Z])', r'private \1', content)
        
        return content

    def _transform_indentation(self, content: str) -> str:
        """Transform Python indentation to C# braces."""
        lines = content.split('\n')
        result = []
        indent_stack = [0]
        brace_count = 0
        
        for line in lines:
            if not line.strip():
                result.append(line)
                continue
            
            # Count indentation
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            
            # Close braces if dedenting
            while indent < indent_stack[-1]:
                indent_stack.pop()
                result.append('    ' * (len(indent_stack) - 1) + '}')
                brace_count -= 1
            
            # Add line
            result.append(line)
            
            # Open braces for blocks
            if stripped.endswith('{'):
                indent_stack.append(indent + 4)
                brace_count += 1
        
        # Close remaining braces
        while len(indent_stack) > 1:
            indent_stack.pop()
            result.append('    ' * (len(indent_stack) - 1) + '}')
        
        return '\n'.join(result)

    def _add_csharp_using(self, content: str) -> str:
        """Add necessary C# using statements."""
        using_statements = set()
        
        if 'List' in content or 'list' in content:
            using_statements.add('using System.Collections.Generic;')
        if 'Dictionary' in content or 'dict' in content:
            using_statements.add('using System.Collections.Generic;')
        if 'async' in content or 'await' in content:
            using_statements.add('using System.Threading.Tasks;')
        if 'DateTime' in content or 'datetime' in content:
            using_statements.add('using System;')
        if 'LINQ' in content or '.Select(' in content or '.Where(' in content:
            using_statements.add('using System.Linq;')
        
        if using_statements:
            using_str = '\n'.join(sorted(using_statements))
            content = using_str + '\n\n' + content
        
        return content

    def _wrap_in_namespace(self, content: str, file_path: str) -> str:
        """Wrap code in C# namespace."""
        # Determine namespace from file path
        namespace = 'MyApplication'
        
        if 'models' in file_path.lower():
            namespace = 'MyApplication.Models'
        elif 'services' in file_path.lower():
            namespace = 'MyApplication.Services'
        elif 'controllers' in file_path.lower():
            namespace = 'MyApplication.Controllers'
        elif 'utils' in file_path.lower():
            namespace = 'MyApplication.Utils'
        elif 'helpers' in file_path.lower():
            namespace = 'MyApplication.Helpers'
        
        csharp_code = f"""namespace {namespace}
{{
{self._indent_code(content, 1)}
}}
"""
        
        return csharp_code

    def _indent_code(self, content: str, level: int = 1) -> str:
        """Indent code with specified level."""
        indent = '    ' * level
        lines = content.split('\n')
        indented = [indent + line if line.strip() else line for line in lines]
        return '\n'.join(indented)

    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case to PascalCase."""
        words = name.split('_')
        return ''.join(word.capitalize() for word in words if word)

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

"""
React to Angular Transformer
Transforms React components to Angular components with TypeScript
"""

import re
from pathlib import Path

from ..models import TransformationResult


class ReactToAngularTransformer:
    """Transform React components to Angular components."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: list[TransformationResult] = []

    def transform_files(self, file_paths: list[str]) -> list[TransformationResult]:
        """Transform React JSX files to Angular components."""
        results = []

        for file_path in file_paths:
            try:
                full_path = self.project_dir / file_path
                if not full_path.exists():
                    continue

                content = full_path.read_text()

                # Skip if not a React component
                if not self._is_react_component(content):
                    continue

                # Transform the content
                transformed = self._transform_react_to_angular(content, file_path)

                result = TransformationResult(
                    file_path=file_path.replace(".jsx", ".component.ts").replace(
                        ".tsx", ".component.ts"
                    ),
                    transformation_type="react_to_angular",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.82,
                    validation_passed=False,
                )
                results.append(result)

            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="react_to_angular",
                    before="",
                    after="",
                    changes_count=0,
                    confidence=0.0,
                    errors=[f"Transformation error: {str(e)}"],
                    validation_passed=False,
                )
                results.append(result)

        self.transformations = results
        return results

    def _is_react_component(self, content: str) -> bool:
        """Check if file is a React component."""
        return bool(
            re.search(r'import.*from\s+[\'"]react[\'"]', content)
            or re.search(r"from react import", content)
            or re.search(r"React\.", content)
        )

    def _transform_react_to_angular(self, content: str, file_path: str) -> str:
        """Transform React component to Angular component."""
        angular_ts = content

        # 1. Remove React imports
        angular_ts = re.sub(
            r'import\s+(?:React|{\s*React\s*})\s+from\s+[\'"]react[\'"];?\n?',
            "",
            angular_ts,
        )

        # 2. Extract component name from file path
        comp_name = Path(file_path).stem
        comp_class_name = "".join(
            word.capitalize() for word in comp_name.split("_") if word
        )

        # 3. Convert function component to Angular class component
        angular_ts = self._convert_to_class_component(angular_ts)

        # 4. Transform props to @Input decorators
        angular_ts = self._transform_props_to_inputs(angular_ts)

        # 5. Transform state to properties
        angular_ts = self._transform_state_to_properties(angular_ts)

        # 6. Transform hooks to lifecycle hooks
        angular_ts = self._transform_hooks_to_lifecycle(angular_ts)

        # 7. Transform JSX to template
        template = self._extract_and_transform_template(angular_ts)

        # 8. Wrap in Angular component with decorator
        angular_ts = self._create_angular_component(
            angular_ts, comp_class_name, comp_name, template
        )

        return angular_ts

    def _is_react_component(self, content: str) -> bool:
        """Check if content is React component."""
        return bool(
            re.search(r"import.*react", content, re.IGNORECASE)
            or re.search(r"function\s+\w+\s*\(", content)
            or re.search(r"const\s+\w+\s*=\s*\(", content)
        )

    def _convert_to_class_component(self, content: str) -> str:
        """Convert function component to Angular class component."""
        # Extract function body
        func_pattern = (
            r"(?:function|const)\s+\w+\s*\(([^)]*)\)\s*(?:=>)?\s*{([\s\S]*?)^}"
        )

        match = re.search(func_pattern, content, re.MULTILINE)
        if match:
            body = match.group(2)
            return body

        return content

    def _transform_props_to_inputs(self, content: str) -> str:
        """Transform props to @Input decorators."""
        # Detect prop access patterns
        prop_pattern = r"props\.(\w+)"

        # Also detect destructured props in function parameters
        destructured_pattern = r"function\s+\w+\s*\(\s*\{([^}]+)\}\s*\)"

        props = set()

        # Find props.propName patterns
        for match in re.finditer(prop_pattern, content):
            props.add(match.group(1))

        # Find destructured props
        for match in re.finditer(destructured_pattern, content):
            props_str = match.group(1)
            # Split by comma and clean up
            for prop in props_str.split(","):
                prop = prop.strip()
                # Handle default values like "prop = defaultValue"
                if "=" in prop:
                    prop = prop.split("=")[0].strip()
                if prop:
                    props.add(prop)

        # Add @Input decorators for each prop
        if props:
            imports = "import { Component, Input } from '@angular/core'\n\n"

            input_declarations = []
            for prop in sorted(props):
                input_declarations.append(f"  @Input() {prop}: any")

            inputs_str = "\n".join(input_declarations)
            return f"{imports}{inputs_str}\n\n{content}"

        return content

    def _transform_state_to_properties(self, content: str) -> str:
        """Transform useState to class properties."""
        # useState(value) -> property: type = value
        pattern = r"const\s+\[(\w+),\s*set(\w+)\]\s*=\s*useState\(([^)]*)\)"

        def replace_state(match):
            var_name = match.group(1)
            initial_value = match.group(3)

            return f"{var_name}: any = {initial_value}"

        content = re.sub(pattern, replace_state, content)

        # Replace setState calls with direct assignment
        content = re.sub(r"set(\w+)\(([^)]*)\)", r"this.\1 = \2", content)

        return content

    def _transform_hooks_to_lifecycle(self, content: str) -> str:
        """Transform React hooks to Angular lifecycle hooks."""
        # useEffect -> ngOnInit or ngOnChanges
        pattern = r"useEffect\(\s*\(\)\s*=>\s*{([\s\S]*?)},\s*\[\]\s*\)"
        content = re.sub(pattern, r"ngOnInit() {\1}", content)

        # useEffect with deps -> ngOnChanges
        pattern = r"useEffect\(\s*\(\)\s*=>\s*{([\s\S]*?)},\s*\[([^\]]+)\]\s*\)"
        content = re.sub(pattern, r"ngOnChanges(changes: SimpleChanges) {\1}", content)

        return content

    def _extract_and_transform_template(self, content: str) -> str:
        """Extract JSX and convert to Angular template."""
        # Find return statement with JSX
        jsx_pattern = r"return\s*\(([\s\S]*?)\)"
        match = re.search(jsx_pattern, content)

        if not match:
            return "<div><!-- TODO: Add template --></div>"

        jsx = match.group(1)

        # Convert JSX to template
        template = self._convert_jsx_to_template(jsx)

        return template

    def _convert_jsx_to_template(self, jsx: str) -> str:
        """Convert JSX syntax to Angular template."""
        template = jsx

        # className -> class
        template = template.replace("className=", "[class]=")
        template = template.replace("class=", "class=")

        # onClick -> (click)
        template = template.replace("onClick=", "(click)=")
        template = template.replace("onChange=", "(change)=")

        # {variable} -> {{ variable }}
        template = re.sub(r"{(\w+)}", r"{{ \1 }}", template)

        # condition && <JSX> -> *ngIf
        template = re.sub(
            r"{(\w+)\s*&&\s*<(\w+)([^>]*)>", r'<\2 *ngIf="\1"\3>', template
        )

        # .map() -> *ngFor
        template = re.sub(
            r"{(\w+)\.map\(\((\w+)\)\s*=>\s*<(\w+)([^>]*)>",
            r'<\3 *ngFor="let \2 of \1"\4>',
            template,
        )

        return template

    def _create_angular_component(
        self, script: str, class_name: str, selector_name: str, template: str
    ) -> str:
        """Create Angular component with decorator."""
        component_decorator = f"""
import {{ Component, Input, OnInit }} from '@angular/core'

@Component({{
  selector: '{selector_name}',
  template: `
    {template}
  `,
  styleUrls: ['./{selector_name}.component.css']
}})
export class {class_name}Component implements OnInit {{
  {self._extract_properties(script)}
  
  constructor() {{}}
  
  ngOnInit(): void {{
    // Component initialization
  }}
  
  {self._extract_methods(script)}
}}
"""
        return component_decorator

    def _extract_properties(self, content: str) -> str:
        """Extract properties from component."""
        lines = []
        for line in content.split("\n"):
            if "=" in line and "function" not in line and "const" not in line:
                lines.append("  " + line.strip())
        return "\n".join(lines) if lines else ""

    def _extract_methods(self, content: str) -> str:
        """Extract methods from component."""
        methods = []

        # Find arrow functions and regular functions
        pattern = r"const\s+(\w+)\s*=\s*(?:\([^)]*\)\s*)?=>\s*{([\s\S]*?)(?=\n\s*(?:const|function|return)|\Z)}"

        for match in re.finditer(pattern, content):
            method_name = match.group(1)
            method_body = match.group(2)
            methods.append(f"  {method_name}(): void {{\n{method_body}\n  }}")

        return "\n\n".join(methods) if methods else ""

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

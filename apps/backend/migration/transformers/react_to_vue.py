"""
React to Vue Transformer
Transforms React JSX components to Vue Single File Components (.vue)
"""

import re
from typing import Dict, List, Tuple
from pathlib import Path

from ..models import TransformationResult


class ReactToVueTransformer:
    """Transform React components to Vue 3."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
        self.transformations: List[TransformationResult] = []

    def transform_files(self, file_paths: List[str]) -> List[TransformationResult]:
        """Transform React JSX files to Vue .vue files."""
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
                transformed = self._transform_jsx_to_vue(content, file_path)
                
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="jsx_to_vue_sfc",
                    before=content,
                    after=transformed,
                    changes_count=self._count_changes(content, transformed),
                    confidence=0.85,  # High confidence for standard patterns
                    validation_passed=False,
                )
                results.append(result)
                
            except Exception as e:
                result = TransformationResult(
                    file_path=file_path,
                    transformation_type="jsx_to_vue_sfc",
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
            re.search(r'import.*from\s+[\'"]react[\'"]', content) or
            re.search(r'from react import', content) or
            re.search(r'React\.', content) or
            re.search(r'function\s+\w+\s*\(.*\)\s*{.*return.*jsx', content, re.DOTALL)
        )

    def _transform_jsx_to_vue(self, content: str, file_path: str) -> str:
        """Transform JSX to Vue SFC."""
        vue_content = content
        
        # 1. Remove React import
        vue_content = re.sub(
            r'import\s+(?:React|{\s*React\s*})\s+from\s+[\'"]react[\'"];?\n?',
            '',
            vue_content
        )
        
        # 2. Remove useCallback, useMemo, useEffect, useState imports (will add composables)
        vue_content = re.sub(
            r'import\s*{\s*([^}]*?)(useCallback|useMemo|useEffect|useState)([^}]*?)\s*}\s*from\s+[\'"]react[\'"];?',
            lambda m: self._transform_hooks_import(m, vue_content),
            vue_content
        )
        
        # 3. Transform function component to setup function
        vue_content = self._transform_component_function(vue_content)
        
        # 4. Transform JSX to Vue template
        vue_content = self._transform_jsx_to_template(vue_content)
        
        # 5. Transform hooks to composition API
        vue_content = self._transform_hooks_to_composition_api(vue_content)
        
        # 6. Transform event handlers
        vue_content = self._transform_event_handlers(vue_content)
        
        # 7. Transform conditional rendering
        vue_content = self._transform_conditionals(vue_content)
        
        # 8. Transform lists/loops
        vue_content = self._transform_loops(vue_content)
        
        # 9. Wrap in Vue SFC template
        vue_content = self._wrap_in_sfc(vue_content, file_path)
        
        return vue_content

    def _transform_hooks_import(self, match, content: str) -> str:
        """Transform React hooks imports to Vue composables."""
        return ""

    def _transform_component_function(self, content: str) -> str:
        """Transform React function component to Vue setup function."""
        # Pattern: function MyComponent({ prop1, prop2 }) { ... }
        pattern = r'function\s+(\w+)\s*\(\s*{\s*([^}]*?)\s*}\s*\)\s*{'
        
        def replace_func(match):
            comp_name = match.group(1)
            props_str = match.group(2)
            props = [p.strip() for p in props_str.split(',') if p.strip()]
            
            props_def = ', '.join(props) if props else ''
            return f'function {comp_name}(props) {{'
        
        content = re.sub(pattern, replace_func, content)
        
        # Also handle arrow functions: const MyComponent = ({ prop1, prop2 }) => { ... }
        arrow_pattern = r'const\s+(\w+)\s*=\s*\(\s*{\s*([^}]*?)\s*}\s*\)\s*=>\s*{'
        
        def replace_arrow(match):
            comp_name = match.group(1)
            props_str = match.group(2)
            props = [p.strip() for p in props_str.split(',') if p.strip()]
            
            props_def = ', '.join(props) if props else ''
            return f'const {comp_name} = (props) => {{'
        
        content = re.sub(arrow_pattern, replace_arrow, content)
        
        return content

    def _transform_jsx_to_template(self, content: str) -> str:
        """Transform JSX to Vue template syntax."""
        # Transform className to class
        content = re.sub(r'className=', 'class=', content)
        
        # Transform onClick, onChange, etc. to @click, @change
        content = re.sub(r'onClick=', '@click=', content)
        content = re.sub(r'onChange=', '@change=', content)
        content = re.sub(r'onSubmit=', '@submit=', content)
        content = re.sub(r'onFocus=', '@focus=', content)
        content = re.sub(r'onBlur=', '@blur=', content)
        content = re.sub(r'onHover=', '@hover=', content)
        content = re.sub(r'onKeyDown=', '@keydown=', content)
        content = re.sub(r'onKeyUp=', '@keyup=', content)
        content = re.sub(r'onMouseEnter=', '@mouseenter=', content)
        content = re.sub(r'onMouseLeave=', '@mouseleave=', content)
        
        # Transform props access: props.name → {{ name }}
        content = re.sub(r'{props\.(\w+)}', r'{{ \1 }}', content)
        
        # Transform {variable} to {{ variable }} (already mostly done above)
        content = re.sub(r'{(\w+)}(?![}])', r'{{ \1 }}', content)
        
        # Transform htmlFor to for
        content = re.sub(r'htmlFor=', 'for=', content)
        
        # Transform dangerouslySetInnerHTML to v-html
        content = re.sub(
            r'dangerouslySetInnerHTML=\{\{__html:\s*([^}]+)\}\}',
            r'v-html="\1"',
            content
        )
        
        return content

    def _transform_hooks_to_composition_api(self, content: str) -> str:
        """Transform React hooks to Vue composition API."""
        
        # useState -> ref or reactive
        content = re.sub(
            r'const\s+\[(\w+),\s*set(\w+)\]\s*=\s*useState\(([^)]*)\)',
            lambda m: self._transform_use_state(m.group(1), m.group(2), m.group(3)),
            content
        )
        
        # useEffect -> onMounted, onUpdated, watch
        content = re.sub(
            r'useEffect\(\s*\(\)\s*=>\s*{([^}]*)}(?:\s*,\s*\[([^\]]*)\])?',
            lambda m: self._transform_use_effect(m.group(1), m.group(2)),
            content
        )
        
        # useCallback
        content = re.sub(
            r'const\s+(\w+)\s*=\s*useCallback\(\s*([^,]+),\s*\[([^\]]*)\]\s*\)',
            lambda m: self._transform_use_callback(m.group(1), m.group(2)),
            content
        )
        
        # useMemo
        content = re.sub(
            r'const\s+(\w+)\s*=\s*useMemo\(\s*\(\)\s*=>\s*({[^}]*}),\s*\[([^\]]*)\]\s*\)',
            lambda m: self._transform_use_memo(m.group(1), m.group(2)),
            content
        )
        
        # useContext -> inject
        content = re.sub(
            r'const\s+(\w+)\s*=\s*useContext\((\w+)\)',
            r'const \1 = inject("\2")',
            content
        )
        
        return content

    def _transform_use_state(self, var_name: str, setter_name: str, initial_value: str) -> str:
        """Transform useState hook."""
        # Convert to ref for simple values, reactive for objects
        if initial_value.strip().startswith('{'):
            return f'const {var_name} = reactive({initial_value})'
        else:
            return f'const {var_name} = ref({initial_value})'

    def _transform_use_effect(self, body: str, deps: str) -> str:
        """Transform useEffect hook."""
        if not deps or deps.strip() == '':
            # No dependencies - runs on every render
            return f'onUpdated(() => {{{body}}})'
        elif deps.strip() == '[]':
            # Empty deps - runs once on mount
            return f'onMounted(() => {{{body}}})'
        else:
            # Has dependencies - use watch
            deps_list = [d.strip() for d in deps.split(',')]
            deps_str = ', '.join(deps_list)
            return f'watch([{deps_str}], () => {{{body}}})'

    def _transform_use_callback(self, name: str, func: str) -> str:
        """Transform useCallback hook."""
        # In Vue 3 composition API, functions are naturally memoized
        return f'const {name} = {func}'

    def _transform_use_memo(self, name: str, compute_func: str, deps: str) -> str:
        """Transform useMemo hook."""
        deps_list = [d.strip() for d in deps.split(',')]
        deps_str = ', '.join(deps_list)
        return f'const {name} = computed(() => {compute_func})'

    def _transform_event_handlers(self, content: str) -> str:
        """Transform event handler syntax."""
        # Transform @click="handleClick" with parentheses
        content = re.sub(
            r'@click=\{(\w+)\}',
            r'@click="\1"',
            content
        )
        
        # Transform inline handlers
        content = re.sub(
            r'@click=\{.*?\s*=>\s*([^}]*)\}',
            r'@click="\1"',
            content
        )
        
        return content

    def _transform_conditionals(self, content: str) -> str:
        """Transform conditional rendering."""
        # Transform condition && <JSXElement> to v-if
        content = re.sub(
            r'{(\w+)\s*&&\s*<(\w+)([^>]*)>([^<]*)</\2>}',
            r'<\2 v-if="\1"\3>\4</\2>',
            content
        )
        
        # Transform ternary operator
        content = re.sub(
            r'{condition\s*\?\s*<(\w+)([^>]*)>([^<]*)</\1>\s*:\s*<(\w+)([^>]*)>([^<]*)</\4>}',
            lambda m: self._transform_ternary(m),
            content
        )
        
        return content

    def _transform_ternary(self, match) -> str:
        """Transform ternary conditional."""
        true_tag = match.group(1)
        true_attrs = match.group(2)
        true_content = match.group(3)
        false_tag = match.group(4)
        false_attrs = match.group(5)
        false_content = match.group(6)
        
        # Vue doesn't have else for v-if easily, use template
        return (
            f'<template v-if="condition">'
            f'<{true_tag}{true_attrs}>{true_content}</{true_tag}>'
            f'</template>'
            f'<template v-else>'
            f'<{false_tag}{false_attrs}>{false_content}</{false_tag}>'
            f'</template>'
        )

    def _transform_loops(self, content: str) -> str:
        """Transform list rendering."""
        # Transform map function to v-for
        pattern = r'{(\w+)\.map\(\((\w+)\)\s*=>\s*<(\w+)([^>]*?)key=\{[^}]*\}([^>]*)>([^<]*)</\3>\s*\)}'
        
        def replace_loop(match):
            array_name = match.group(1)
            item_name = match.group(2)
            tag_name = match.group(3)
            attrs1 = match.group(4)
            attrs2 = match.group(5)
            content_text = match.group(6)
            
            return (
                f'<{tag_name} v-for="{item_name} in {array_name}" '
                f':{item_name.lower()}_key="{item_name}.id"{attrs1}{attrs2}>'
                f'{content_text}</{tag_name}>'
            )
        
        content = re.sub(pattern, replace_loop, content)
        
        return content

    def _wrap_in_sfc(self, script_content: str, file_path: str) -> str:
        """Wrap content in Vue Single File Component format."""
        file_name = Path(file_path).stem
        
        # Extract component name from file path
        comp_name = ''.join(word.capitalize() for word in file_name.split('_') if word)
        
        vue_sfc = f'''<template>
  <div>
    <!-- Component template goes here -->
    <!-- TODO: Extract template from component return -->
  </div>
</template>

<script setup lang="ts">
import {{ ref, reactive, computed, onMounted, watch, inject }} from 'vue'

// Component logic
{script_content}
</script>

<style scoped>
/* Styles go here */
</style>
'''
        
        return vue_sfc

    def _count_changes(self, before: str, after: str) -> int:
        """Count lines changed."""
        before_lines = before.split('\n')
        after_lines = after.split('\n')
        
        changes = abs(len(before_lines) - len(after_lines))
        
        # Count different lines
        for b, a in zip(before_lines, after_lines):
            if b != a:
                changes += 1
        
        return changes

    def get_transformations(self) -> List[TransformationResult]:
        """Get all transformations."""
        return self.transformations

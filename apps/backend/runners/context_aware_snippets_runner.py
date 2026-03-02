#!/usr/bin/env python3
"""
Context-Aware Snippets Runner

Generates code snippets that adapt to the project's style, conventions,
and existing patterns. Uses project context and memory to create
snippets that feel like they were written by someone who knows the project.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from core.context_manager import ContextManager
from core.model_info import get_model_info_for_logs
from memory.bmad_memory import BMadMemory
from services.project_analyzer import ProjectAnalyzer


class ContextAwareSnippetResult:
    """Result structure for context-aware snippet generation"""
    
    def __init__(self, snippet: str, language: str, description: str, 
                 context_used: List[str], adaptations: List[str], 
                 reasoning: str):
        self.snippet = snippet
        self.language = language
        self.description = description
        self.context_used = context_used
        self.adaptations = adaptations
        self.reasoning = reasoning
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'snippet': self.snippet,
            'language': self.language,
            'description': self.description,
            'context_used': self.context_used,
            'adaptations': self.adaptations,
            'reasoning': self.reasoning
        }


class ContextAwareSnippetsRunner:
    """Generates context-aware code snippets"""
    
    def __init__(self, project_dir: str, model: Optional[str] = None, 
                 thinking_level: Optional[str] = None):
        self.project_dir = Path(project_dir)
        self.model = model
        self.thinking_level = thinking_level
        self.context_manager = ContextManager()
        self.memory = BMadMemory()
        self.project_analyzer = ProjectAnalyzer(project_dir)
        
    def generate_snippet(self, snippet_type: str, description: str, 
                        target_language: Optional[str] = None) -> ContextAwareSnippetResult:
        """Generate a context-aware code snippet"""
        
        print(f"Analyzing project context for {snippet_type} snippet...")
        
        # Analyze project structure and conventions
        project_context = self._analyze_project_context()
        
        # Detect language if not specified
        if not target_language:
            target_language = self._detect_primary_language(project_context)
        
        # Get relevant patterns and conventions
        patterns = self._get_relevant_patterns(snippet_type, target_language, project_context)
        
        # Build context-aware prompt
        context_prompt = self._build_context_prompt(
            snippet_type, description, target_language, project_context, patterns
        )
        
        print(f"Generating {target_language} snippet with project context...")
        
        # Generate the snippet using Claude
        snippet_content = self._generate_with_claude(context_prompt)
        
        # Extract and structure the result
        result = self._parse_snippet_result(
            snippet_content, target_language, description, patterns
        )
        
        return result
    
    def _analyze_project_context(self) -> Dict[str, Any]:
        """Analyze the project to extract context information"""
        
        context = {
            'languages': self.project_analyzer.detect_languages(),
            'frameworks': self.project_analyzer.detect_frameworks(),
            'conventions': self._analyze_conventions(),
            'imports': self._get_common_imports(),
            'patterns': self._detect_code_patterns(),
            'style_guide': self._infer_style_guide()
        }
        
        return context
    
    def _detect_primary_language(self, context: Dict[str, Any]) -> str:
        """Detect the primary programming language of the project"""
        
        languages = context.get('languages', [])
        if not languages:
            return 'javascript'  # Default fallback
        
        # Return the most common language
        return max(languages, key=languages.count)
    
    def _analyze_conventions(self) -> Dict[str, Any]:
        """Analyze coding conventions used in the project"""
        
        conventions = {
            'naming': self._detect_naming_conventions(),
            'formatting': self._detect_formatting_conventions(),
            'imports': self._detect_import_conventions(),
            'comments': self._detect_comment_style()
        }
        
        return conventions
    
    def _get_common_imports(self) -> List[str]:
        """Get commonly used imports in the project"""
        
        try:
            # This would scan source files to find common imports
            # For now, return a basic list
            return [
                'react', 'lodash', 'axios', 'moment', 
                'uuid', 'classnames', 'prop-types'
            ]
        except Exception:
            return []
    
    def _detect_code_patterns(self) -> List[str]:
        """Detect common code patterns in the project"""
        
        patterns = []
        
        # Look for common patterns like function components, class components, etc.
        try:
            # This would involve more sophisticated analysis
            patterns = [
                'functional-components',
                'hooks-usage',
                'async-await',
                'error-boundaries'
            ]
        except Exception:
            pass
        
        return patterns
    
    def _infer_style_guide(self) -> Dict[str, Any]:
        """Infer the style guide being used"""
        
        # Check for common style guide files
        style_files = [
            '.eslintrc.js', '.eslintrc.json', '.prettierrc', 
            'pyproject.toml', 'setup.cfg'
        ]
        
        detected_rules = {}
        
        for style_file in style_files:
            file_path = self.project_dir / style_file
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        detected_rules[style_file] = content
                except Exception:
                    pass
        
        return detected_rules
    
    def _detect_naming_conventions(self) -> Dict[str, str]:
        """Detect naming conventions used"""
        
        # Basic detection - would be more sophisticated in practice
        return {
            'variables': 'camelCase',
            'functions': 'camelCase', 
            'classes': 'PascalCase',
            'constants': 'UPPER_SNAKE_CASE',
            'files': 'kebab-case'
        }
    
    def _detect_formatting_conventions(self) -> Dict[str, Any]:
        """Detect formatting conventions"""
        
        return {
            'indentation': '2 spaces',  # Would detect from actual files
            'quotes': 'single',
            'semicolons': True,
            'trailing_commas': 'es5'
        }
    
    def _detect_import_conventions(self) -> Dict[str, Any]:
        """Detect import organization conventions"""
        
        return {
            'style': 'es6-imports',
            'order': ['react', 'third-party', 'relative'],
            'grouping': True
        }
    
    def _detect_comment_style(self) -> str:
        """Detect comment style preferences"""
        
        return 'jsdoc'  # Would detect from actual code
    
    def _get_relevant_patterns(self, snippet_type: str, language: str, 
                              context: Dict[str, Any]) -> List[str]:
        """Get patterns relevant to the snippet type and language"""
        
        patterns = []
        
        # Map snippet types to relevant patterns
        pattern_map = {
            'component': ['functional-components', 'hooks-usage', 'props-destructuring'],
            'function': ['arrow-functions', 'async-await', 'error-handling'],
            'class': ['class-syntax', 'constructor-patterns', 'method-binding'],
            'hook': ['custom-hooks', 'state-management', 'effect-usage'],
            'utility': ['pure-functions', 'type-hints', 'error-handling'],
            'api': ['async-functions', 'error-handling', 'response-parsing'],
            'test': ['test-patterns', 'mocking', 'assertions']
        }
        
        relevant = pattern_map.get(snippet_type, [])
        
        # Filter by what's actually found in the project
        project_patterns = context.get('patterns', [])
        patterns = [p for p in relevant if p in project_patterns]
        
        return patterns
    
    def _build_context_prompt(self, snippet_type: str, description: str, 
                             language: str, project_context: Dict[str, Any], 
                             patterns: List[str]) -> str:
        """Build a context-aware prompt for snippet generation"""
        
        # Extract relevant context information
        conventions = project_context.get('conventions', {})
        frameworks = project_context.get('frameworks', [])
        imports = project_context.get('imports', [])
        
        prompt = f"""Generate a {language} code snippet for: {description}

PROJECT CONTEXT:
- Primary Language: {language}
- Frameworks: {', '.join(frameworks) if frameworks else 'None detected'}
- Common Imports: {', '.join(imports[:5]) if imports else 'None detected'}

CODING CONVENTIONS:
- Naming: {conventions.get('naming', {})}
- Formatting: {conventions.get('formatting', {})}
- Import Style: {conventions.get('imports', {})}

RELEVANT PATTERNS:
{', '.join(patterns) if patterns else 'No specific patterns detected'}

REQUIREMENTS:
1. Generate a complete, ready-to-use code snippet
2. Follow the detected coding conventions exactly
3. Use imports and patterns that match the project style
4. Include appropriate error handling if applicable
5. Add brief comments explaining key parts
6. Make it feel like it was written by someone who knows this project

RESPONSE FORMAT:
Provide the response in this exact JSON format:
{{
  "snippet": "the actual code snippet",
  "language": "{language}",
  "description": "brief description of what the snippet does",
  "context_used": ["list", "of", "context", "elements", "used"],
  "adaptations": ["list", "of", "adaptations", "made", "for", "project"],
  "reasoning": "explanation of why the snippet was designed this way"
}}

Generate the snippet now:"""

        return prompt
    
    def _generate_with_claude(self, prompt: str) -> str:
        """Generate content using Claude"""
        
        try:
            from agents.claude_agent_sdk import ClaudeAgent
            
            # Configure the agent
            agent_config = {
                'model': self.model or 'claude-3-sonnet-20240229',
                'thinking_level': self.thinking_level or 'medium'
            }
            
            agent = ClaudeAgent(config=agent_config)
            
            # Generate the response
            response = agent.run(prompt)
            
            return response
            
        except Exception as e:
            print(f"Error using Claude: {e}")
            # Fallback to a basic response
            return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when Claude is unavailable"""
        
        # Extract basic information from the prompt
        language = "javascript"  # Default
        if "python" in prompt.lower():
            language = "python"
        elif "typescript" in prompt.lower():
            language = "typescript"
        
        fallback_json = f"""{{
  "snippet": "# Generated snippet (Claude unavailable)\\n# TODO: Implement based on your requirements",
  "language": "{language}",
  "description": "Fallback snippet - please implement manually",
  "context_used": ["fallback-mode"],
  "adaptations": ["basic-structure"],
  "reasoning": "Claude was unavailable, so this is a basic placeholder"
}}"""
        
        return fallback_json
    
    def _parse_snippet_result(self, content: str, language: str, 
                             description: str, patterns: List[str]) -> ContextAwareSnippetResult:
        """Parse the generated content into a structured result"""
        
        try:
            # Try to parse as JSON
            if content.strip().startswith('{'):
                data = json.loads(content)
                
                return ContextAwareSnippetResult(
                    snippet=data.get('snippet', content),
                    language=data.get('language', language),
                    description=data.get('description', description),
                    context_used=data.get('context_used', []),
                    adaptations=data.get('adaptations', []),
                    reasoning=data.get('reasoning', 'Generated based on project context')
                )
        
        except json.JSONDecodeError:
            # Fallback: treat the entire content as the snippet
            pass
        
        # Fallback result
        return ContextAwareSnippetResult(
            snippet=content,
            language=language,
            description=description,
            context_used=patterns,
            adaptations=['basic-formatting'],
            reasoning='Generated with basic context analysis'
        )


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description='Generate context-aware code snippets')
    parser.add_argument('--project-dir', required=True, help='Project directory path')
    parser.add_argument('--snippet-type', required=True, 
                       choices=['component', 'function', 'class', 'hook', 'utility', 'api', 'test'],
                       help='Type of snippet to generate')
    parser.add_argument('--description', required=True, help='Description of the snippet')
    parser.add_argument('--language', help='Target programming language')
    parser.add_argument('--model', help='Claude model to use')
    parser.add_argument('--thinking-level', help='Thinking level for Claude')
    
    args = parser.parse_args()
    
    try:
        # Validate project directory
        project_path = Path(args.project_dir)
        if not project_path.exists():
            print(f"Error: Project directory {args.project_dir} does not exist")
            sys.exit(1)
        
        # Create runner
        runner = ContextAwareSnippetsRunner(
            project_dir=args.project_dir,
            model=args.model,
            thinking_level=args.thinking_level
        )
        
        # Generate snippet
        result = runner.generate_snippet(
            snippet_type=args.snippet_type,
            description=args.description,
            target_language=args.language
        )
        
        # Output the result
        print(f"__CONTEXT_AWARE_SNIPPET__:{json.dumps(result.to_dict())}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

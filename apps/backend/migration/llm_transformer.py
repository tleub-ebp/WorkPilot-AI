"""
LLM-Enhanced Transformer
Uses Claude to improve code transformation quality with context-aware refactoring
"""

import asyncio
import os
from pathlib import Path
from typing import Optional

import anthropic

from .models import TransformationResult


class LLMTransformer:
    """Enhance transformations with LLM intelligence."""

    def __init__(self, project_dir: str, api_key: Optional[str] = None):
        self.project_dir = Path(project_dir)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = (
            anthropic.Anthropic(api_key=self.api_key) if self.api_key else None
        )

    async def enhance_transformation(
        self,
        result: TransformationResult,
        source_framework: str,
        target_framework: str,
        prompt_template: str,
    ) -> TransformationResult:
        """
        Enhance a transformation result using Claude.

        Args:
            result: Base transformation result from rule-based transformer
            source_framework: Source framework/language
            target_framework: Target framework/language
            prompt_template: Template for the LLM prompt

        Returns:
            Enhanced TransformationResult with improved code quality
        """
        if not self.client:
            return result

        try:
            # Load the prompt template
            prompt = self._build_prompt(
                result.before,
                result.after,
                source_framework,
                target_framework,
                prompt_template,
            )

            # Call Claude
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            enhanced_code = response.content[0].text

            # Update the result
            result.after = enhanced_code
            result.confidence = min(result.confidence + 0.1, 0.99)
            result.llm_enhanced = True

            return result

        except Exception as e:
            result.errors.append(f"LLM enhancement error: {str(e)}")
            return result

    async def enhance_transformations_batch(
        self,
        results: list[TransformationResult],
        source_framework: str,
        target_framework: str,
        prompt_template: str,
        max_concurrent: int = 3,
    ) -> list[TransformationResult]:
        """
        Enhance multiple transformations in parallel.

        Args:
            results: List of transformation results
            source_framework: Source framework
            target_framework: Target framework
            prompt_template: Template for prompts
            max_concurrent: Max concurrent LLM calls

        Returns:
            List of enhanced results
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enhance_with_limit(result: TransformationResult):
            async with semaphore:
                return await self.enhance_transformation(
                    result, source_framework, target_framework, prompt_template
                )

        tasks = [enhance_with_limit(r) for r in results]
        return await asyncio.gather(*tasks)

    def _build_prompt(
        self,
        original_code: str,
        transformed_code: str,
        source_framework: str,
        target_framework: str,
        template: str,
    ) -> str:
        """Build the LLM prompt from template."""
        # Load prompt template
        prompt_file = self.project_dir.parent / "prompts" / template

        if prompt_file.exists():
            base_prompt = prompt_file.read_text()
        else:
            # Fallback generic prompt
            base_prompt = self._get_generic_prompt()

        # Fill in the template
        prompt = (
            base_prompt
            + f"""

## Original Code ({source_framework}):
```
{original_code}
```

## Initial Transformation ({target_framework}):
```
{transformed_code}
```

## Task
Review and enhance the transformation above. Make sure:
1. All logic is correctly preserved
2. Best practices for {target_framework} are followed
3. Edge cases are handled properly
4. Code is idiomatic and clean
5. Comments explain complex transformations

Return ONLY the enhanced {target_framework} code without any markdown formatting or explanations.
"""
        )
        return prompt

    def _get_generic_prompt(self) -> str:
        """Generic fallback prompt."""
        return """You are an expert software engineer specializing in code migration and refactoring.

Your task is to review and enhance code transformations between different frameworks/languages.
Ensure the transformation:
- Preserves all original functionality
- Follows target framework best practices
- Handles edge cases
- Is idiomatic and maintainable
"""

    async def validate_transformation(
        self, result: TransformationResult, test_files: Optional[list[str]] = None
    ) -> bool:
        """
        Use LLM to validate if transformation is correct.

        Args:
            result: Transformation result to validate
            test_files: Optional related test files for context

        Returns:
            True if validation passes
        """
        if not self.client:
            return False

        try:
            prompt = f"""Review this code transformation and determine if it's correct.

Original Code:
```
{result.before}
```

Transformed Code:
```
{result.after}
```

Analyze:
1. Is the logic preserved?
2. Are there any bugs introduced?
3. Does it follow best practices?
4. Are edge cases handled?

Respond with JSON:
{{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["list of issues if any"],
    "suggestions": ["list of improvement suggestions"]
}}
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            import json

            validation = json.loads(response.content[0].text)

            result.validation_passed = validation.get("valid", False)
            result.confidence = validation.get("confidence", result.confidence)

            if validation.get("issues"):
                result.errors.extend(validation["issues"])

            return validation.get("valid", False)

        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
            return False

    async def suggest_manual_changes(
        self, result: TransformationResult
    ) -> list[dict[str, str]]:
        """
        Generate suggestions for manual review.

        Returns:
            List of suggestions with line numbers and descriptions
        """
        if not self.client:
            return []

        try:
            prompt = f"""Analyze this code transformation and identify parts that need manual review.

Original:
```
{result.before}
```

Transformed:
```
{result.after}
```

Identify areas that:
1. Might need manual verification
2. Have complex logic that's hard to auto-migrate
3. Could have multiple valid approaches
4. Require domain knowledge

Return JSON array:
[
    {{
        "line_number": 10,
        "description": "Complex async logic - verify behavior",
        "severity": "high|medium|low"
    }}
]
"""

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )

            import json

            suggestions = json.loads(response.content[0].text)
            return suggestions

        except Exception as e:
            return [
                {
                    "line_number": 0,
                    "description": f"Error: {str(e)}",
                    "severity": "high",
                }
            ]

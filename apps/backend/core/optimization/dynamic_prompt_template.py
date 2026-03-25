"""
Dynamic Prompt Template
======================

Implements dynamic prompt generation with context optimization.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ContextLevel(Enum):
    """Context optimization levels"""

    MINIMAL = "minimal"
    STANDARD = "standard"
    DETAILED = "detailed"


@dataclass
class ContextInfo:
    """Information about task context"""

    files: Optional[list[str]] = field(default=None)
    recent_history: Optional[list[str]] = field(default=None)
    dependencies: Optional[list[str]] = field(default=None)
    constraints: Optional[dict[str, Any]] = field(default=None)
    examples: Optional[list[str]] = field(default=None)


class DynamicPromptTemplate:
    """
    Dynamic prompt template that adapts to context and constraints.

    Features:
    - Context-aware prompt generation
    - Token optimization based on constraints
    - Dynamic example selection
    - Adaptive level selection
    """

    def __init__(self):
        self.base_template = """
# Task Analysis
Task: {task_description}
Complexity: {complexity}
Priority: {priority}

# Context Information
{context_section}

# Requirements and Constraints
{constraints_section}

# Examples and References
{examples_section}

# Expected Output Format
{output_format}

# Validation Criteria
{validation_section}
"""

        # Context builders
        self.context_builders = {
            ContextLevel.MINIMAL: self._build_minimal_context,
            ContextLevel.STANDARD: self._build_standard_context,
            ContextLevel.DETAILED: self._build_detailed_context,
        }

        # Example selectors
        self.example_selectors = {
            "relevance": self._select_relevant_examples,
            "similarity": self._select_similar_examples,
            "random": self._select_random_examples,
        }

        # Output formatters
        self.output_formatters = {
            "code": self._format_code_output,
            "text": self._format_text_output,
            "json": self._format_json_output,
            "list": self._format_list_output,
        }

    def generate(
        self,
        task_description: str,
        context_info: ContextInfo | None = None,
        constraints: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        output_format: str = "text",
    ) -> str:
        """
        Generate a dynamic prompt optimized for the given parameters.

        Args:
            task_description: Main task description
            context_info: Context information
            constraints: Task constraints
            max_tokens: Maximum tokens allowed
            output_format: Expected output format

        Returns:
            Optimized prompt string
        """
        # Determine optimal context level
        context_level = self._determine_context_level(
            task_description, context_info, max_tokens
        )

        # Build prompt components
        complexity = self._assess_task_complexity(task_description)
        priority = constraints.get("priority", "normal") if constraints else "normal"

        context_section = self._build_context_section(context_info, context_level)
        constraints_section = self._build_constraints_section(constraints)
        examples_section = self._build_examples_section(context_info, task_description)
        output_format_section = self._build_output_format_section(output_format)
        validation_section = self._build_validation_section(constraints)

        # Generate prompt
        prompt = self.base_template.format(
            task_description=task_description,
            complexity=complexity,
            priority=priority,
            context_section=context_section,
            constraints_section=constraints_section,
            examples_section=examples_section,
            output_format=output_format_section,
            validation_section=validation_section,
        )

        # Optimize for token budget if specified
        if max_tokens:
            prompt = self._optimize_for_token_budget(prompt, max_tokens)

        logger.debug(
            f"Generated dynamic prompt with context level {context_level.value}"
        )
        return prompt

    def _determine_context_level(
        self,
        task_description: str,
        _context_info: Optional["ContextInfo"],
        max_tokens: int | None,
    ) -> ContextLevel:
        """Determine optimal context level based on task and constraints"""

        if max_tokens and max_tokens < 500:
            return ContextLevel.MINIMAL

        # Assess task complexity
        complexity = self._assess_task_complexity(task_description)

        if complexity in ["simple", "low"]:
            return ContextLevel.MINIMAL
        elif complexity in ["medium", "moderate"]:
            return ContextLevel.STANDARD
        else:
            return ContextLevel.DETAILED

    def _assess_task_complexity(self, task_description: str) -> str:
        """Assess task complexity from description"""
        description_lower = task_description.lower()

        # Complexity indicators
        complexity_indicators = {
            "simple": ["simple", "basic", "straightforward", "easy"],
            "medium": ["moderate", "standard", "regular", "typical"],
            "complex": ["complex", "advanced", "sophisticated", "intricate"],
            "very_complex": [
                "very complex",
                "highly complex",
                "extensive",
                "comprehensive",
            ],
        }

        for level, indicators in complexity_indicators.items():
            if any(indicator in description_lower for indicator in indicators):
                return level

        # Default assessment based on length
        if len(task_description) < 100:
            return "simple"
        elif len(task_description) < 300:
            return "medium"
        elif len(task_description) < 600:
            return "complex"
        else:
            return "very_complex"

    def _build_context_section(
        self, context_info: ContextInfo | None, level: ContextLevel
    ) -> str:
        """Build context section based on level and available info"""
        if not context_info:
            return "No additional context provided."

        builder = self.context_builders[level]
        return builder(context_info)

    def _build_minimal_context(self, context_info: ContextInfo) -> str:
        """Build minimal context"""
        context_parts = []

        if context_info.files and len(context_info.files) <= 3:
            context_parts.append(f"Relevant files: {', '.join(context_info.files[:3])}")

        if context_info.constraints:
            key_constraints = list(context_info.constraints.items())[:3]
            constraints_str = ", ".join(f"{k}: {v}" for k, v in key_constraints)
            context_parts.append(f"Key constraints: {constraints_str}")

        return (
            "\n".join(context_parts) if context_parts else "Minimal context available."
        )

    def _build_standard_context(self, context_info: ContextInfo) -> str:
        """Build standard context"""
        context_parts = []

        if context_info.files:
            context_parts.append(f"Files: {', '.join(context_info.files)}")

        if context_info.dependencies:
            context_parts.append(
                f"Dependencies: {', '.join(context_info.dependencies)}"
            )

        if context_info.recent_history:
            recent = context_info.recent_history[:5]
            context_parts.append("Recent actions:")
            for i, action in enumerate(recent, 1):
                context_parts.append(f"  {i}. {action}")

        return (
            "\n".join(context_parts) if context_parts else "Standard context available."
        )

    def _build_detailed_context(self, context_info: ContextInfo) -> str:
        """Build detailed context"""
        context_parts = []

        if context_info.files:
            context_parts.append("Files involved:")
            for file in context_info.files:
                context_parts.append(f"  - {file}")

        if context_info.dependencies:
            context_parts.append("Dependencies:")
            for dep in context_info.dependencies:
                context_parts.append(f"  - {dep}")

        if context_info.recent_history:
            context_parts.append("Recent history:")
            for i, action in enumerate(context_info.recent_history, 1):
                context_parts.append(f"  {i}. {action}")

        if context_info.constraints:
            context_parts.append("Current constraints:")
            for key, value in context_info.constraints.items():
                context_parts.append(f"  - {key}: {value}")

        return (
            "\n".join(context_parts) if context_parts else "Detailed context available."
        )

    def _build_constraints_section(self, constraints: dict[str, Any] | None) -> str:
        """Build constraints section"""
        if not constraints:
            return "No specific constraints."

        constraint_parts = []
        for key, value in constraints.items():
            constraint_parts.append(f"- {key}: {value}")

        return "\n".join(constraint_parts)

    def _build_examples_section(
        self, context_info: ContextInfo | None, task_description: str
    ) -> str:
        """Build examples section"""
        if not context_info or not context_info.examples:
            return "No specific examples provided."

        # Use relevance-based selection
        examples = self._select_relevant_examples(
            context_info.examples, task_description
        )

        if not examples:
            return "No relevant examples available."

        example_parts = ["Examples:"]
        for i, example in enumerate(examples[:3], 1):  # Limit to 3 examples
            example_parts.append(f"{i}. {example}")

        return "\n".join(example_parts)

    def _select_relevant_examples(
        self, examples: list[str], task_description: str
    ) -> list[str]:
        """Select examples most relevant to the task"""
        task_keywords = set(task_description.lower().split())

        scored_examples = []
        for example in examples:
            example_keywords = set(example.lower().split())
            # Calculate relevance score based on keyword overlap
            common_keywords = task_keywords.intersection(example_keywords)
            score = len(common_keywords) / max(len(task_keywords), 1)
            scored_examples.append((example, score))

        # Sort by relevance and return top examples
        scored_examples.sort(key=lambda x: x[1], reverse=True)
        return [example for example, _ in scored_examples]

    def _select_similar_examples(
        self, examples: list[str], task_description: str
    ) -> list[str]:
        """Select examples based on similarity"""
        # Simple implementation - could be enhanced with NLP
        return examples[:3]

    def _select_random_examples(
        self, examples: list[str], task_description: str
    ) -> list[str]:
        """Select random examples"""
        import random

        return random.sample(examples, min(3, len(examples)))

    def _build_output_format_section(self, output_format: str) -> str:
        """Build output format section"""
        formatter = self.output_formatters.get(output_format, self._format_text_output)
        return formatter()

    def _format_code_output(self) -> str:
        """Format for code output"""
        return """Provide code in the appropriate language with:
- Clear comments explaining the approach
- Proper error handling
- Following language-specific best practices
- Include necessary imports and dependencies"""

    def _format_text_output(self) -> str:
        """Format for text output"""
        return """Provide a clear, well-structured response with:
- Direct answer to the question
- Supporting details and explanations
- Logical organization with headings
- Concise and professional language"""

    def _format_json_output(self) -> str:
        """Format for JSON output"""
        return """Provide response in valid JSON format with:
- Properly structured data
- All required fields included
- Valid data types
- No syntax errors"""

    def _format_list_output(self) -> str:
        """Format for list output"""
        return """Provide response as a numbered or bulleted list with:
- Clear, concise items
- Logical ordering
- Complete coverage of the topic
- Consistent formatting"""

    def _build_validation_section(self, constraints: dict[str, Any] | None) -> str:
        """Build validation section"""
        validation_criteria = [
            "Solution addresses all requirements",
            "Follows best practices and conventions",
            "Is efficient and maintainable",
            "Handles edge cases appropriately",
        ]

        if constraints:
            validation_criteria.append("Meets all specified constraints")

        return "Validation:\n" + "\n".join(
            f"- {criteria}" for criteria in validation_criteria
        )

    def _optimize_for_token_budget(self, prompt: str, max_tokens: int) -> str:
        """Optimize prompt to fit within token budget"""
        # Rough token estimation
        current_tokens = len(prompt) // 4

        if current_tokens <= max_tokens:
            return prompt

        # Calculate reduction needed
        reduction_ratio = max_tokens / current_tokens

        # Reduce sections proportionally
        lines = prompt.split("\n")
        target_lines = int(len(lines) * reduction_ratio)

        # Keep most important lines (headers and key content)
        important_lines = []
        for line in lines:
            if line.strip().startswith("#") or len(important_lines) < target_lines:
                important_lines.append(line)

        optimized_prompt = "\n".join(important_lines[:target_lines])

        logger.warning(
            f"Reduced prompt from {current_tokens} to ~{len(optimized_prompt) // 4} tokens"
        )
        return optimized_prompt

    def add_context_builder(
        self, level: ContextLevel, builder: Callable[[ContextInfo], str]
    ):
        """Add a custom context builder"""
        self.context_builders[level] = builder
        logger.info(f"Added custom context builder for {level.value}")

    def add_example_selector(
        self, name: str, selector: Callable[[list[str], str], list[str]]
    ):
        """Add a custom example selector"""
        self.example_selectors[name] = selector
        logger.info(f"Added custom example selector '{name}'")

    def add_output_formatter(self, format_name: str, formatter: Callable[[], str]):
        """Add a custom output formatter"""
        self.output_formatters[format_name] = formatter
        logger.info(f"Added custom output formatter '{format_name}'")

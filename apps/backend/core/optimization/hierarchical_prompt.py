"""
Hierarchical Prompt
==================

Implements hierarchical prompt structure for optimal token usage.
Based on GitHub Copilot best practices: start general, then get specific.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PromptLevel(Enum):
    """Prompt complexity levels"""
    MINIMAL = "minimal"
    STANDARD = "standard"
    COMPREHENSENSIVE = "comprehensive"


@dataclass
class PromptTemplate:
    """Template for prompt components"""
    name: str
    content: str
    token_estimate: int
    priority: int = 1  # Lower number = higher priority


class HierarchicalPrompt:
    """
    Hierarchical prompt system for optimal token usage.
    
    Implements GitHub Copilot best practices:
    1. Start general, then get specific
    2. Give examples when needed
    3. Break complex tasks into simpler tasks
    4. Avoid ambiguity
    """
    
    def __init__(self):
        self.templates = {
            'general': PromptTemplate(
                name='general',
                content=self._get_general_template(),
                token_estimate=150,
                priority=1
            ),
            'specific': PromptTemplate(
                name='specific',
                content=self._get_specific_template(),
                token_estimate=200,
                priority=2
            ),
            'examples': PromptTemplate(
                name='examples',
                content=self._get_examples_template(),
                token_estimate=300,
                priority=3
            ),
            'validation': PromptTemplate(
                name='validation',
                content=self._get_validation_template(),
                token_estimate=100,
                priority=4
            ),
            'context': PromptTemplate(
                name='context',
                content=self._get_context_template(),
                token_estimate=250,
                priority=2
            )
        }
        
        # Pre-built prompt combinations for different levels
        self.level_combinations = {
            PromptLevel.MINIMAL: ['general', 'specific'],
            PromptLevel.STANDARD: ['general', 'specific', 'context'],
            PromptLevel.COMPREHENSIVE: ['general', 'specific', 'context', 'examples', 'validation']
        }
    
    def build_prompt(self, 
                     task_description: str,
                     level: PromptLevel = PromptLevel.STANDARD,
                     context: Optional[Dict[str, Any]] = None,
                     examples: Optional[List[str]] = None,
                     constraints: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a hierarchical prompt based on the specified level.
        
        Args:
            task_description: Main task description
            level: Prompt complexity level
            context: Additional context information
            examples: Specific examples for the task
            constraints: Task constraints and requirements
            
        Returns:
            Optimized prompt string
        """
        selected_templates = self.level_combinations[level]
        
        # Build prompt components
        components = []
        
        for template_name in selected_templates:
            template = self.templates[template_name]
            
            if template_name == 'general':
                component = template.content.format(task_description=task_description)
            elif template_name == 'specific':
                component = template.content.format(constraints=constraints or {})
            elif template_name == 'context':
                component = template.content.format(context=context or {})
            elif template_name == 'examples':
                component = template.content.format(examples=examples or [])
            elif template_name == 'validation':
                component = template.content.format(constraints=constraints or {})
            
            components.append(component)
        
        # Combine components
        prompt = "\n\n".join(components)
        
        # Log token estimate
        estimated_tokens = self.estimate_tokens(prompt)
        logger.debug(f"Built {level.value} prompt with ~{estimated_tokens} tokens")
        
        return prompt
    
    def estimate_tokens(self, prompt: str) -> int:
        """Estimate token count for a prompt"""
        # Rough estimation: ~1 token per 4 characters
        return len(prompt) // 4
    
    def optimize_for_budget(self, 
                           task_description: str,
                           max_tokens: int,
                           context: Optional[Dict[str, Any]] = None,
                           examples: Optional[List[str]] = None,
                           constraints: Optional[Dict[str, Any]] = None) -> str:
        """
        Build a prompt that fits within a specific token budget.
        
        Args:
            task_description: Main task description
            max_tokens: Maximum tokens allowed
            context: Additional context information
            examples: Specific examples for the task
            constraints: Task constraints and requirements
            
        Returns:
            Optimized prompt within budget
        """
        # Try different levels starting from minimal
        for level in [PromptLevel.MINIMAL, PromptLevel.STANDARD, PromptLevel.COMPREHENSIVE]:
            prompt = self.build_prompt(
                task_description=task_description,
                level=level,
                context=context,
                examples=examples,
                constraints=constraints
            )
            
            if self.estimate_tokens(prompt) <= max_tokens:
                return prompt
        
        # If even minimal is too large, create ultra-minimal
        return self._create_ultra_minimal_prompt(task_description, constraints)
    
    def _create_ultra_minimal_prompt(self, task_description: str, constraints: Optional[Dict[str, Any]]) -> str:
        """Create an ultra-minimal prompt for very tight budgets"""
        prompt = f"Task: {task_description}\n"
        
        if constraints:
            prompt += f"Requirements: {constraints}\n"
        
        prompt += "Provide a concise solution."
        
        return prompt
    
    def _get_general_template(self) -> str:
        """General context template"""
        return """You are an AI assistant helping with the following task:

{task_description}

Focus on providing a clear, efficient solution that follows best practices."""
    
    def _get_specific_template(self) -> str:
        """Specific requirements template"""
        return """Specific requirements:
{constraints}

Ensure your solution meets all these requirements exactly."""
    
    def _get_context_template(self) -> str:
        """Context information template"""
        return """Additional context:
{context}

Use this context to inform your solution."""
    
    def _get_examples_template(self) -> str:
        """Examples template"""
        return """Examples to follow:
{examples}

Use these examples as guidance for your solution format and approach."""
    
    def _get_validation_template(self) -> str:
        """Validation criteria template"""
        return """Validation criteria:
- Solution meets all requirements
- Code follows best practices
- Solution is efficient and maintainable
{constraints}

Ensure your solution passes all validation criteria."""
    
    def add_custom_template(self, 
                           name: str,
                           content: str,
                           token_estimate: int,
                           priority: int = 5):
        """Add a custom prompt template"""
        self.templates[name] = PromptTemplate(
            name=name,
            content=content,
            token_estimate=token_estimate,
            priority=priority
        )
        logger.info(f"Added custom template '{name}' with {token_estimate} tokens")
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a specific template"""
        if template_name not in self.templates:
            return {}
        
        template = self.templates[template_name]
        return {
            'name': template.name,
            'token_estimate': template.token_estimate,
            'priority': template.priority,
            'content_length': len(template.content)
        }
    
    def analyze_prompt_efficiency(self, prompt: str) -> Dict[str, Any]:
        """Analyze a prompt for efficiency and provide recommendations"""
        tokens = self.estimate_tokens(prompt)
        
        # Basic efficiency analysis
        recommendations = []
        
        if tokens > 1000:
            recommendations.append("Consider using a more concise prompt structure")
        
        if "example" not in prompt.lower() and tokens > 500:
            recommendations.append("Add examples to improve clarity and reduce ambiguity")
        
        if prompt.count('\n\n') > 5:
            recommendations.append("Consider reducing the number of paragraphs")
        
        # Calculate efficiency score (0-1, higher is better)
        efficiency_score = max(0, 1 - (tokens - 300) / 1000)
        efficiency_score = min(1, efficiency_score)
        
        return {
            'token_estimate': tokens,
            'efficiency_score': round(efficiency_score, 3),
            'recommendations': recommendations,
            'complexity_level': self._assess_complexity(prompt)
        }
    
    def _assess_complexity(self, prompt: str) -> str:
        """Assess the complexity level of a prompt"""
        tokens = self.estimate_tokens(prompt)
        
        if tokens < 200:
            return "simple"
        elif tokens < 500:
            return "medium"
        elif tokens < 800:
            return "complex"
        else:
            return "very_complex"

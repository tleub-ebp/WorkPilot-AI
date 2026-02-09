"""
Learning Mode - Explains everything Claude does in real-time

This module provides detailed explanations of AI actions, decisions,
and code generation to help developers learn and understand.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ExplanationLevel(str, Enum):
    """Level of detail for explanations"""

    BEGINNER = "beginner"  # Very detailed, assumes no prior knowledge
    INTERMEDIATE = "intermediate"  # Moderate detail, assumes basic knowledge
    ADVANCED = "advanced"  # Concise, focuses on "why" not "what"
    EXPERT = "expert"  # Minimal, only key insights


@dataclass
class LearningModeConfig:
    """Configuration for Learning Mode"""

    enabled: bool = True
    explanation_level: ExplanationLevel = ExplanationLevel.INTERMEDIATE
    explain_tools: bool = True  # Explain tool usage (Read, Glob, Grep)
    explain_decisions: bool = True  # Explain the decision-making process
    explain_code: bool = True  # Explain code being generated
    explain_patterns: bool = True  # Explain design patterns used
    explain_best_practices: bool = True  # Explain best practices applied
    generate_inline_comments: bool = True  # Add educational comments in code
    generate_summary: bool = True  # Generate session summary
    interactive_questions: bool = False  # Pause for user questions (interactive mode)
    save_learnings: bool = True  # Save explanations for later review

    # Learning preferences
    prefer_visual_diagrams: bool = False  # Generate mermaid diagrams when helpful
    prefer_examples: bool = True  # Include code examples in explanations
    prefer_comparisons: bool = True  # Compare with alternative approaches


@dataclass
class LearningExplanation:
    """A single explanation in Learning Mode"""

    timestamp: datetime
    category: str  # "tool_use", "decision", "code", "pattern", "best_practice"
    title: str
    explanation: str
    code_snippet: str | None = None
    diagram: str | None = None  # Mermaid diagram
    alternative_approaches: list[dict[str, str]] = field(default_factory=list)
    references: list[str] = field(default_factory=list)  # URLs to learn more
    difficulty: ExplanationLevel = ExplanationLevel.INTERMEDIATE

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "title": self.title,
            "explanation": self.explanation,
            "code_snippet": self.code_snippet,
            "diagram": self.diagram,
            "alternative_approaches": self.alternative_approaches,
            "references": self.references,
            "difficulty": self.difficulty.value,
        }


class LearningMode:
    """Learning Mode - Educational explanations of AI actions"""

    def __init__(self, config: LearningModeConfig | None = None):
        self.config = config or LearningModeConfig()
        self.explanations: list[LearningExplanation] = []
        self.session_start = datetime.now()

    def explain_tool_use(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        reason: str,
        expected_outcome: str
    ) -> LearningExplanation | None:
        """Explain why a tool is being used"""
        if not self.config.enabled or not self.config.explain_tools:
            return None
        
        explanations_by_level = {
            ExplanationLevel.BEGINNER: self._explain_tool_beginner,
            ExplanationLevel.INTERMEDIATE: self._explain_tool_intermediate,
            ExplanationLevel.ADVANCED: self._explain_tool_advanced,
            ExplanationLevel.EXPERT: self._explain_tool_expert,
        }
        
        explanation = explanations_by_level[self.config.explanation_level](
            tool_name, tool_input, reason, expected_outcome
        )
        
        if explanation:
            self.explanations.append(explanation)
        
        return explanation
    
    def _explain_tool_beginner(
        self, tool_name: str, tool_input: Dict[str, Any], reason: str, expected_outcome: str
    ) -> LearningExplanation:
        """Beginner-level tool explanation"""
        tool_descriptions = {
            "Read": "The Read tool allows me to read the contents of a specific file. This is like opening a file in your text editor to see what's inside.",
            "Glob": "The Glob tool helps me search for files using patterns. For example, '*.py' finds all Python files. It's like using the search function in your file explorer.",
            "Grep": "The Grep tool searches for specific text within files. It's like using Ctrl+F (Find) across multiple files at once.",
        }
        
        base_desc = tool_descriptions.get(tool_name, f"The {tool_name} tool")
        
        explanation_text = f"""{base_desc}

**Why I'm using it now:**
{reason}

**What I'm looking for:**
{expected_outcome}

**The specific command:**
```json
{json.dumps(tool_input, indent=2)}
```

**Learning tip:** This tool helps me understand your codebase better. The more I explore, the better I can help you!
"""
        
        return LearningExplanation(
            timestamp=datetime.now(),
            category="tool_use",
            title=f"Using {tool_name} Tool",
            explanation=explanation_text,
            difficulty=ExplanationLevel.BEGINNER,
            references=[
                "https://en.wikipedia.org/wiki/Grep" if tool_name == "Grep" else None,
                "https://en.wikipedia.org/wiki/Glob_(programming)" if tool_name == "Glob" else None,
            ]
        )
    
    def _explain_tool_intermediate(
        self, tool_name: str, tool_input: Dict[str, Any], reason: str, expected_outcome: str
    ) -> LearningExplanation:
        """Intermediate-level tool explanation"""
        explanation_text = f"""I'm using the **{tool_name}** tool to gather information from your codebase.

**Purpose:** {reason}

**Expected result:** {expected_outcome}

**Parameters:** `{json.dumps(tool_input, indent=2)}`
"""
        
        return LearningExplanation(
            timestamp=datetime.now(),
            category="tool_use",
            title=f"{tool_name}: {reason[:50]}...",
            explanation=explanation_text,
            difficulty=ExplanationLevel.INTERMEDIATE,
        )
    
    def _explain_tool_advanced(
        self, tool_name: str, tool_input: Dict[str, Any], reason: str, expected_outcome: str
    ) -> LearningExplanation:
        """Advanced-level tool explanation"""
        explanation_text = f"""**{tool_name}** → {reason}

Target: `{tool_input}`
"""
        
        return LearningExplanation(
            timestamp=datetime.now(),
            category="tool_use",
            title=f"{tool_name}",
            explanation=explanation_text,
            difficulty=ExplanationLevel.ADVANCED,
        )
    
    def _explain_tool_expert(
        self, tool_name: str, tool_input: Dict[str, Any], reason: str, expected_outcome: str
    ) -> LearningExplanation:
        """Expert-level tool explanation (minimal)"""
        return LearningExplanation(
            timestamp=datetime.now(),
            category="tool_use",
            title=f"{tool_name}",
            explanation=reason,
            difficulty=ExplanationLevel.EXPERT,
        )
    
    def explain_decision(
        self,
        decision: str,
        reasoning: str,
        alternatives_considered: Optional[List[Dict[str, str]]] = None
    ) -> Optional[LearningExplanation]:
        """Explain a decision made during code generation"""
        if not self.config.enabled or not self.config.explain_decisions:
            return None
        
        explanation_text = f"""**Decision:** {decision}

**Reasoning:**
{reasoning}
"""
        
        if alternatives_considered and self.config.prefer_comparisons:
            explanation_text += "\n**Alternatives considered:**\n"
            for i, alt in enumerate(alternatives_considered, 1):
                explanation_text += f"\n{i}. **{alt['name']}**\n"
                explanation_text += f"   - Pros: {alt.get('pros', 'N/A')}\n"
                explanation_text += f"   - Cons: {alt.get('cons', 'N/A')}\n"
                explanation_text += f"   - Why not chosen: {alt.get('reason_rejected', 'N/A')}\n"
        
        explanation = LearningExplanation(
            timestamp=datetime.now(),
            category="decision",
            title=decision,
            explanation=explanation_text,
            alternative_approaches=alternatives_considered or [],
            difficulty=self.config.explanation_level,
        )
        
        self.explanations.append(explanation)
        return explanation
    
    def explain_code(
        self,
        code: str,
        purpose: str,
        key_concepts: List[str],
        pattern: Optional[str] = None,
        best_practices: Optional[List[str]] = None
    ) -> Optional[LearningExplanation]:
        """Explain code being generated"""
        if not self.config.enabled or not self.config.explain_code:
            return None
        
        explanation_text = f"""**Purpose:** {purpose}

**Key concepts used:**
"""
        for concept in key_concepts:
            explanation_text += f"- {concept}\n"
        
        if pattern and self.config.explain_patterns:
            explanation_text += f"\n**Design pattern:** {pattern}\n"
        
        if best_practices and self.config.explain_best_practices:
            explanation_text += "\n**Best practices applied:**\n"
            for practice in best_practices:
                explanation_text += f"- {practice}\n"
        
        explanation = LearningExplanation(
            timestamp=datetime.now(),
            category="code",
            title=f"Code: {purpose[:50]}...",
            explanation=explanation_text,
            code_snippet=code,
            difficulty=self.config.explanation_level,
        )
        
        self.explanations.append(explanation)
        return explanation
    
    def explain_pattern(
        self,
        pattern_name: str,
        description: str,
        when_to_use: str,
        example_code: Optional[str] = None,
        diagram: Optional[str] = None
    ) -> Optional[LearningExplanation]:
        """Explain a design pattern being used"""
        if not self.config.enabled or not self.config.explain_patterns:
            return None
        
        explanation_text = f"""**Pattern: {pattern_name}**

{description}

**When to use:**
{when_to_use}
"""
        
        explanation = LearningExplanation(
            timestamp=datetime.now(),
            category="pattern",
            title=pattern_name,
            explanation=explanation_text,
            code_snippet=example_code,
            diagram=diagram,
            difficulty=self.config.explanation_level,
        )
        
        self.explanations.append(explanation)
        return explanation
    
    def generate_session_summary(self) -> Dict[str, Any]:
        """Generate a summary of the learning session"""
        if not self.config.enabled or not self.config.generate_summary:
            return {}
        
        session_duration = (datetime.now() - self.session_start).total_seconds()
        
        # Group explanations by category
        by_category = {}
        for exp in self.explanations:
            if exp.category not in by_category:
                by_category[exp.category] = []
            by_category[exp.category].append(exp)
        
        # Extract key learnings
        key_concepts = []
        patterns_used = []
        tools_used = set()
        
        for exp in self.explanations:
            if exp.category == "pattern":
                patterns_used.append(exp.title)
            elif exp.category == "tool_use":
                tools_used.add(exp.title.split()[0])
        
        summary = {
            "session_duration_seconds": session_duration,
            "total_explanations": len(self.explanations),
            "explanations_by_category": {
                cat: len(exps) for cat, exps in by_category.items()
            },
            "tools_used": list(tools_used),
            "patterns_used": patterns_used,
            "key_concepts": key_concepts,
            "explanation_level": self.config.explanation_level.value,
            "timestamp": datetime.now().isoformat(),
        }
        
        return summary
    
    def save_session(self, output_dir: Path) -> Path:
        """Save the learning session to a file"""
        if not self.config.enabled or not self.config.save_learnings:
            return None
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        session_file = output_dir / f"learning_session_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        
        session_data = {
            "config": {
                "explanation_level": self.config.explanation_level.value,
                "enabled_features": {
                    "tools": self.config.explain_tools,
                    "decisions": self.config.explain_decisions,
                    "code": self.config.explain_code,
                    "patterns": self.config.explain_patterns,
                    "best_practices": self.config.explain_best_practices,
                }
            },
            "summary": self.generate_session_summary(),
            "explanations": [exp.to_dict() for exp in self.explanations],
        }
        
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return session_file
    
    def generate_markdown_report(self) -> str:
        """Generate a markdown report of the learning session"""
        md = f"""# Learning Session Report

**Date:** {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}
**Duration:** {(datetime.now() - self.session_start).total_seconds():.1f}s
**Explanation Level:** {self.config.explanation_level.value}
**Total Explanations:** {len(self.explanations)}

---

"""
        
        # Group by category
        by_category = {}
        for exp in self.explanations:
            if exp.category not in by_category:
                by_category[exp.category] = []
            by_category[exp.category].append(exp)
        
        # Write each category
        category_names = {
            "tool_use": "🔧 Tool Usage",
            "decision": "🤔 Decision Making",
            "code": "💻 Code Explanations",
            "pattern": "🎨 Design Patterns",
            "best_practice": "✨ Best Practices",
        }
        
        for category, exps in by_category.items():
            md += f"## {category_names.get(category, category.title())}\n\n"
            
            for exp in exps:
                md += f"### {exp.title}\n\n"
                md += f"*{exp.timestamp.strftime('%H:%M:%S')}*\n\n"
                md += f"{exp.explanation}\n\n"
                
                if exp.code_snippet:
                    md += "```python\n"
                    md += exp.code_snippet
                    md += "\n```\n\n"
                
                if exp.diagram:
                    md += "```mermaid\n"
                    md += exp.diagram
                    md += "\n```\n\n"
                
                if exp.alternative_approaches:
                    md += "**Alternative Approaches:**\n\n"
                    for alt in exp.alternative_approaches:
                        md += f"- **{alt.get('name', 'Unknown')}**: {alt.get('description', '')}\n"
                    md += "\n"
                
                if exp.references:
                    md += "**References:**\n\n"
                    for ref in exp.references:
                        if ref:
                            md += f"- {ref}\n"
                    md += "\n"
                
                md += "---\n\n"
        
        # Add summary
        summary = self.generate_session_summary()
        md += "## 📊 Session Summary\n\n"
        md += f"- **Duration:** {summary['session_duration_seconds']:.1f}s\n"
        md += f"- **Total Explanations:** {summary['total_explanations']}\n"
        md += f"- **Tools Used:** {', '.join(summary['tools_used'])}\n"
        if summary['patterns_used']:
            md += f"- **Design Patterns:** {', '.join(summary['patterns_used'])}\n"
        
        return md


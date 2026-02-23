#!/usr/bin/env python3
"""
Prompt Optimizer Runner - AI-powered prompt enhancement using Claude SDK

This script analyzes a user's prompt and enriches it with project context
(stack, conventions, patterns) to produce an optimized prompt for each
agent type (analysis, coding, verification, general).

It leverages past build results and QA reports to learn which formulations
yield the best outcomes.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.utils import import_dotenv
from core.auth import ensure_claude_code_oauth_token, get_auth_token
from core.dependency_validator import validate_platform_dependencies
from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_section,
    debug_success,
)
from phase_config import get_thinking_budget, resolve_model_id

try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ClaudeAgentOptions = None
    ClaudeSDKClient = None

validate_platform_dependencies()

# Load .env file with centralized error handling
load_dotenv = import_dotenv()

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)


def load_project_context(project_dir: str) -> str:
    """Load comprehensive project context for prompt optimization."""
    context_parts = []

    # Load project index
    index_path = Path(project_dir) / ".auto-claude" / "project_index.json"
    if index_path.exists():
        try:
            with open(index_path, encoding="utf-8") as f:
                index = json.load(f)
            summary = {
                "project_root": index.get("project_root", ""),
                "project_type": index.get("project_type", "unknown"),
                "languages": index.get("languages", []),
                "frameworks": index.get("frameworks", []),
                "services": list(index.get("services", {}).keys()),
                "infrastructure": index.get("infrastructure", {}),
                "conventions": index.get("conventions", {}),
            }
            context_parts.append(
                f"## Project Structure\n```json\n{json.dumps(summary, indent=2)}\n```"
            )
        except Exception:
            pass

    # Load roadmap for strategic context
    roadmap_path = Path(project_dir) / ".auto-claude" / "roadmap" / "roadmap.json"
    if roadmap_path.exists():
        try:
            with open(roadmap_path, encoding="utf-8") as f:
                roadmap = json.load(f)
            features = roadmap.get("features", [])
            feature_summary = [
                {"title": f.get("title", ""), "status": f.get("status", "")}
                for f in features[:10]
            ]
            context_parts.append(
                f"## Roadmap Features\n```json\n{json.dumps(feature_summary, indent=2)}\n```"
            )
        except Exception:
            pass

    # Load existing specs/tasks and their outcomes
    specs_path = Path(project_dir) / ".auto-claude" / "specs"
    if specs_path.exists():
        try:
            task_dirs = sorted(
                [d for d in specs_path.iterdir() if d.is_dir()],
                key=lambda d: d.name,
                reverse=True,
            )

            # Collect task names
            task_names = [d.name for d in task_dirs[:15]]
            if task_names:
                context_parts.append(
                    "## Existing Tasks/Specs\n- " + "\n- ".join(task_names)
                )

            # Analyze recent build outcomes for learning
            build_insights = _analyze_build_history(task_dirs[:10])
            if build_insights:
                context_parts.append(f"## Build History Insights\n{build_insights}")

        except Exception:
            pass

    return (
        "\n\n".join(context_parts)
        if context_parts
        else "No project context available yet."
    )


def _analyze_build_history(task_dirs: list) -> str:
    """Analyze recent build outcomes to extract patterns for prompt optimization."""
    insights = []
    success_count = 0
    failure_patterns = []

    for task_dir in task_dirs:
        # Check QA reports for outcomes
        qa_report = task_dir / "qa_report.md"
        qa_fix = task_dir / "QA_FIX_REQUEST.md"
        spec_file = task_dir / "spec.md"
        requirements_file = task_dir / "requirements.json"

        task_name = task_dir.name

        if qa_report.exists():
            try:
                content = qa_report.read_text(encoding="utf-8")
                if "PASS" in content.upper() or "APPROVED" in content.upper():
                    success_count += 1
                elif qa_fix.exists():
                    # Extract failure reason summary
                    fix_content = qa_fix.read_text(encoding="utf-8")[:500]
                    failure_patterns.append(
                        f"- Task `{task_name}`: required QA fixes"
                    )
            except Exception:
                pass

        # Extract complexity and category from requirements
        if requirements_file.exists():
            try:
                with open(requirements_file, encoding="utf-8") as f:
                    reqs = json.load(f)
                complexity = reqs.get("complexity", "unknown")
                category = reqs.get("category", "unknown")
                insights.append(f"- `{task_name}`: complexity={complexity}, category={category}")
            except Exception:
                pass

    parts = []
    total = len(task_dirs)
    if total > 0:
        parts.append(
            f"Recent build success rate: {success_count}/{total} passed QA on first attempt."
        )

    if failure_patterns:
        parts.append("Common issues:\n" + "\n".join(failure_patterns[:5]))

    if insights:
        parts.append("Task profiles:\n" + "\n".join(insights[:8]))

    return "\n".join(parts)


def build_system_prompt(project_dir: str, agent_type: str) -> str:
    """Build the system prompt for the prompt optimizer agent."""
    context = load_project_context(project_dir)

    agent_guidelines = _get_agent_guidelines(agent_type)

    return f"""You are a **Prompt Optimizer** — an AI assistant specialized in improving and enriching user prompts to maximize the quality of AI-generated outputs.

Your goal is to take the user's original prompt and transform it into an optimized version that:
1. Incorporates relevant project context (stack, conventions, patterns)
2. Is structured for the target agent type ({agent_type})
3. Includes specific, actionable details
4. References relevant existing code patterns and conventions
5. Anticipates edge cases and requirements

## Project Context

{context}

## Agent-Specific Guidelines ({agent_type})

{agent_guidelines}

## Output Format

You MUST output your optimized prompt using this exact marker format on a SINGLE LINE:

__OPTIMIZED_PROMPT__:{{"optimized": "The full optimized prompt text here", "changes": ["List of changes made"], "reasoning": "Brief explanation of why these changes improve the prompt"}}

## Rules
- Preserve the user's original intent — never change what they want, only improve HOW they ask for it
- Add project-specific details (languages, frameworks, conventions) from the context
- Structure the prompt with clear sections if the task is complex
- Include acceptance criteria when appropriate
- Reference similar past tasks if relevant
- Keep the optimized prompt concise but comprehensive
- If the prompt is already excellent, return it with minimal changes and explain why
- Always output exactly ONE __OPTIMIZED_PROMPT__ marker"""


def _get_agent_guidelines(agent_type: str) -> str:
    """Return agent-specific guidelines for prompt optimization."""
    guidelines = {
        "analysis": """For analysis/spec creation agents:
- Include clear scope boundaries (what IS and IS NOT in scope)
- Specify which parts of the codebase to focus on
- Mention relevant existing patterns to follow
- Ask for structured output (acceptance criteria, edge cases, dependencies)
- Reference existing specs as examples if available""",

        "coding": """For coding/implementation agents:
- Specify the exact files and modules that need changes
- Reference existing code patterns and conventions to follow
- Include testing requirements explicitly
- Mention error handling expectations
- Specify any performance constraints
- Reference related implementations in the codebase""",

        "verification": """For QA/verification agents:
- Define clear pass/fail criteria
- Specify which test types to run (unit, integration, e2e)
- Include edge cases to verify
- Mention security considerations
- Reference the project's testing conventions
- Specify acceptance criteria thresholds""",

        "general": """For general-purpose prompts:
- Balance detail with conciseness
- Include context about the project stack and conventions
- Structure with clear objectives
- Add relevant constraints and requirements
- Reference existing patterns when applicable"""
    }
    return guidelines.get(agent_type, guidelines["general"])


async def run_with_sdk(
    project_dir: str,
    prompt: str,
    agent_type: str = "general",
    model: str = "sonnet",
    thinking_level: str = "medium",
) -> None:
    """Run the prompt optimizer using Claude SDK with streaming."""
    if not SDK_AVAILABLE:
        print("Claude SDK not available, falling back to simple mode", file=sys.stderr)
        run_simple(project_dir, prompt, agent_type)
        return

    if not get_auth_token():
        print(
            "No authentication token found, falling back to simple mode",
            file=sys.stderr,
        )
        run_simple(project_dir, prompt, agent_type)
        return

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    system_prompt = build_system_prompt(project_dir, agent_type)
    project_path = Path(project_dir).resolve()

    user_prompt = f"""Please optimize the following prompt for a {agent_type} agent:

---
{prompt}
---

Analyze it, enrich it with relevant project context, and output the optimized version using the __OPTIMIZED_PROMPT__ marker."""

    max_thinking_tokens = get_thinking_budget(thinking_level)

    debug(
        "prompt_optimizer",
        "Using model configuration",
        model=model,
        thinking_level=thinking_level,
        max_thinking_tokens=max_thinking_tokens,
        agent_type=agent_type,
    )

    try:
        options_kwargs = {
            "model": resolve_model_id(model),
            "system_prompt": system_prompt,
            "allowed_tools": ["Read", "Glob", "Grep"],
            "max_turns": 15,
            "cwd": str(project_path),
        }

        if max_thinking_tokens is not None:
            options_kwargs["max_thinking_tokens"] = max_thinking_tokens

        client = ClaudeSDKClient(options=ClaudeAgentOptions(**options_kwargs))

        async with client:
            await client.query(user_prompt)

            response_text = ""
            current_tool = None

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                debug_detailed("prompt_optimizer", "Received message", msg_type=msg_type)

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            text = block.text
                            print(text, flush=True)
                            response_text += text
                        elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                            tool_name = block.name
                            tool_input = ""

                            if hasattr(block, "input") and block.input:
                                inp = block.input
                                if isinstance(inp, dict):
                                    if "pattern" in inp:
                                        tool_input = f"pattern: {inp['pattern']}"
                                    elif "file_path" in inp:
                                        fp = inp["file_path"]
                                        if len(fp) > 50:
                                            fp = "..." + fp[-47:]
                                        tool_input = fp
                                    elif "path" in inp:
                                        tool_input = inp["path"]

                            current_tool = tool_name
                            print(
                                f"__TOOL_START__:{json.dumps({'name': tool_name, 'input': tool_input})}",
                                flush=True,
                            )

                elif msg_type == "ToolResult":
                    if current_tool:
                        print(
                            f"__TOOL_END__:{json.dumps({'name': current_tool})}",
                            flush=True,
                        )
                        current_tool = None

            if response_text and not response_text.endswith("\n"):
                print()

            debug(
                "prompt_optimizer",
                "Response complete",
                response_length=len(response_text),
            )

    except Exception as e:
        print(f"Error using Claude SDK: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        run_simple(project_dir, prompt, agent_type)


def run_simple(project_dir: str, prompt: str, agent_type: str = "general") -> None:
    """Simple fallback mode without SDK - uses subprocess to call claude CLI."""
    import subprocess

    system_prompt = build_system_prompt(project_dir, agent_type)

    full_prompt = f"""{system_prompt}

User prompt to optimize:
{prompt}

Please output the optimized version using the __OPTIMIZED_PROMPT__ marker."""

    try:
        result = subprocess.run(
            ["claude", "--print", "-p", full_prompt],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=120,
        )

        if result.returncode == 0:
            print(result.stdout)
        else:
            # Return original prompt as fallback
            fallback = json.dumps({
                "optimized": prompt,
                "changes": [],
                "reasoning": "Could not optimize - returning original prompt"
            })
            print(f"__OPTIMIZED_PROMPT__:{fallback}")

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        print(f"Error: {e}", file=sys.stderr)
        fallback = json.dumps({
            "optimized": prompt,
            "changes": [],
            "reasoning": f"Optimization failed ({type(e).__name__}) - returning original prompt"
        })
        print(f"__OPTIMIZED_PROMPT__:{fallback}")


def main():
    parser = argparse.ArgumentParser(description="AI Prompt Optimizer Runner")
    parser.add_argument("--project-dir", required=True, help="Project directory path")
    parser.add_argument("--prompt", required=True, help="User prompt to optimize")
    parser.add_argument(
        "--agent-type",
        default="general",
        choices=["analysis", "coding", "verification", "general"],
        help="Target agent type for optimization (default: general)",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        help="Model to use (haiku, sonnet, opus, or full model ID)",
    )
    parser.add_argument(
        "--thinking-level",
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
        help="Thinking level for extended reasoning (default: medium)",
    )
    args = parser.parse_args()

    debug_section("prompt_optimizer", "Starting Prompt Optimization")

    debug(
        "prompt_optimizer",
        "Arguments",
        project_dir=args.project_dir,
        prompt_length=len(args.prompt),
        agent_type=args.agent_type,
        model=args.model,
        thinking_level=args.thinking_level,
    )

    asyncio.run(
        run_with_sdk(
            args.project_dir,
            args.prompt,
            args.agent_type,
            args.model,
            args.thinking_level,
        )
    )
    debug_success("prompt_optimizer", "Optimization completed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Code Playground Runner - AI-powered code playground generation using Claude SDK

This script provides an AI-powered playground for prototyping code ideas
with live preview and integration capabilities.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Validate platform-specific dependencies BEFORE any imports that might
# trigger graphiti_core -> real_ladybug -> pywintypes import chain (ACS-253)
from cli.utils import import_dotenv
from core.dependency_validator import validate_platform_dependencies
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

env_file = Path(__file__).parent.parent.parent.parent / ".env-files" / ".env"
if env_file.exists():
    load_dotenv(env_file)


class CodePlaygroundRunner:
    """AI-powered code playground generator"""

    # Configuration constants to reduce cognitive complexity
    TYPE_INSTRUCTIONS = {
        "html": """
For HTML playgrounds:
- Use semantic HTML5
- Include modern CSS with animations and transitions
- Add vanilla JavaScript for interactivity
- Ensure responsive design
- Use CSS Grid and Flexbox where appropriate""",
        "react": """
For React playgrounds:
- Use modern React with hooks
- Include TypeScript types
- Use functional components
- Add proper state management
- Include CSS modules or styled-components""",
        "vanilla-js": """
For vanilla JavaScript playgrounds:
- Use modern ES6+ syntax
- Include proper error handling
- Add event listeners and DOM manipulation
- Use modern APIs and patterns
- Ensure cross-browser compatibility""",
        "python": """
For Python playgrounds:
- Use standard library modules
- Include clear documentation
- Add error handling and validation
- Use modern Python features
- Consider performance and readability""",
        "node": """
For Node.js playgrounds:
- Use CommonJS or ES modules as appropriate
- Include package.json dependencies
- Add proper error handling
- Use async/await patterns
- Include example usage""",
    }

    SANDBOX_INSTRUCTIONS = {
        "iframe": "The code will run in an iframe sandbox with limited permissions.",
        "docker": "The code will run in a Docker container with full system access.",
        "webworker": "The code will run in a Web Worker with no DOM access.",
    }

    def __init__(
        self,
        project_dir: str,
        idea: str,
        playground_type: str,
        sandbox_type: str,
        model: str = None,
        thinking_level: str = None,
    ):
        self.project_dir = Path(project_dir)
        self.idea = idea
        self.playground_type = playground_type
        self.sandbox_type = sandbox_type
        self.model = resolve_model_id(model) if model else "claude-3-5-sonnet-20241022"
        self.thinking_level = thinking_level or "medium"

        if not SDK_AVAILABLE:
            print(
                "❌ Claude SDK not available. Please install the claude-agent-sdk package.",
                file=sys.stderr,
            )
            sys.exit(1)

    async def generate_playground(self) -> dict:
        """Generate a code playground based on the idea and configuration"""
        self._print_generation_info()

        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt()

        client = self._create_claude_client(system_prompt)

        try:
            response_text = await self._execute_claude_query(client, user_prompt)
            print("✅ Playground generated successfully!")
            return self._parse_response(response_text)
        except Exception as e:
            print(f"❌ Error generating playground: {e}", file=sys.stderr)
            raise

    def _build_system_prompt(self) -> str:
        """Build system prompt based on playground type and sandbox"""
        base_prompt = self._get_base_prompt()
        type_instructions = self.TYPE_INSTRUCTIONS.get(self.playground_type, "")
        sandbox_instructions = self.SANDBOX_INSTRUCTIONS.get(self.sandbox_type, "")

        return f"{base_prompt}\n\n{type_instructions}\n\n{sandbox_instructions}"

    def _print_generation_info(self):
        """Print information about the playground generation"""
        print(
            f"🚀 Generating {self.playground_type} playground with {self.sandbox_type} sandbox..."
        )
        print(f"📝 Idea: {self.idea}")

    def _build_user_prompt(self) -> str:
        """Build the user prompt for playground generation"""
        return f"""Create a code playground based on this idea: {self.idea}

Generate a complete, working implementation with:
1. HTML structure (if applicable)
2. CSS styling for modern appearance
3. JavaScript functionality
4. File structure for integration
5. Integration notes

The playground should be:
- Interactive and engaging
- Well-documented
- Ready for live preview
- Easy to integrate into a project

Respond with a structured JSON object containing:
- html: HTML content
- css: CSS content
- javascript: JavaScript content
- files: Array of file objects with path, content, and size
- integrationNotes: Instructions for integration
"""

    def _create_claude_client(self, system_prompt: str) -> ClaudeSDKClient:
        """Create and configure Claude SDK client"""
        max_thinking_tokens = get_thinking_budget(self.thinking_level)

        options_kwargs: dict = {
            "model": self.model,
            "system_prompt": system_prompt,
            "max_turns": 5,
            "cwd": str(self.project_dir),
        }
        if max_thinking_tokens is not None:
            options_kwargs["max_thinking_tokens"] = max_thinking_tokens

        return ClaudeSDKClient(options=ClaudeAgentOptions(**options_kwargs))

    async def _execute_claude_query(
        self, client: ClaudeSDKClient, user_prompt: str
    ) -> str:
        """Execute Claude query and collect response text"""
        response_text = ""

        async with client:
            print("🤖 Generating playground with Claude...")
            await client.query(user_prompt)

            async for msg in client.receive_response():
                response_text += self._process_message(msg)

        return response_text

    def _process_message(self, msg) -> str:
        """Process a single message from Claude and return text content"""
        msg_type = type(msg).__name__

        if msg_type == "AssistantMessage" and hasattr(msg, "content"):
            return self._process_assistant_message(msg)

        return ""

    def _process_assistant_message(self, msg) -> str:
        """Process assistant message content and return text"""
        text_content = ""

        for block in msg.content:
            block_type = type(block).__name__

            if block_type == "TextBlock" and hasattr(block, "text"):
                text_content += block.text
                print(block.text, flush=True)
            elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                self._handle_tool_use_block(block)

        return text_content

    def _handle_tool_use_block(self, block):
        """Handle tool use block by printing tool start marker"""
        try:
            print(f"__TOOL_START__:{json.dumps({'tool': block.name})}", flush=True)
        except Exception:
            pass

    def _get_base_prompt(self) -> str:
        """Get the base system prompt"""
        return """You are an expert frontend developer and creative coder specializing in building interactive code playgrounds and prototypes.

Your task is to create engaging, interactive playgrounds that demonstrate programming concepts, UI components, or creative coding ideas.

Guidelines:
- Write clean, modern, well-structured code
- Use best practices for the chosen framework/technology
- Include comments and documentation
- Make it visually appealing with modern CSS
- Ensure interactivity and engagement
- Consider performance and accessibility
- Provide clear integration instructions"""

    def _parse_response(self, response: str) -> dict:
        """Parse Claude's response and extract structured data"""

        try:
            json_str = self._extract_json_from_response(response)
            if json_str is None:
                return self._create_fallback_result(
                    response, "No JSON found in response"
                )

            result = json.loads(json_str)
            return self._normalize_result(result)

        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse JSON from response: {e}", file=sys.stderr)
            return self._create_fallback_result(response, "JSON parsing failed")

    def _extract_json_from_response(self, response: str) -> str | None:
        """Extract JSON string from response, return None if not found"""

        # Try to extract JSON from code block
        if "```json" in response:
            return self._extract_json_from_code_block(response)

        # Try to find JSON object in the response
        if "{" in response and "}" in response:
            return self._extract_json_from_text(response)

        return None

    def _extract_json_from_code_block(self, response: str) -> str:
        """Extract JSON from markdown code block"""
        start = response.find("```json") + 7
        end = response.find("```", start)
        return response[start:end].strip()

    def _extract_json_from_text(self, response: str) -> str:
        """Extract JSON object from plain text"""
        start = response.find("{")
        brace_count = 0

        for i, char in enumerate(response[start:]):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = start + i + 1
                    break

        return response[start:end]

    def _normalize_result(self, result: dict) -> dict:
        """Normalize and validate the parsed result"""
        # Ensure required fields
        result.setdefault("html", "")
        result.setdefault("css", "")
        result.setdefault("javascript", "")
        result.setdefault("files", [])
        result.setdefault("integrationNotes", "")
        result["playgroundType"] = self.playground_type
        result["sandboxType"] = self.sandbox_type

        # Calculate file sizes
        for file in result.get("files", []):
            if "content" in file and "size" not in file:
                file["size"] = len(file["content"])

        return result

    def _create_fallback_result(self, response: str, reason: str) -> dict:
        """Create fallback result when parsing fails"""
        return {
            "html": response,
            "css": "",
            "javascript": "",
            "files": [
                {"path": "index.html", "content": response, "size": len(response)}
            ],
            "integrationNotes": f"Basic HTML playground generated from response ({reason}).",
            "playgroundType": self.playground_type,
            "sandboxType": self.sandbox_type,
        }

    def _output_result(self, result: dict):
        """Output the result in the expected format"""

        # Output the structured result marker
        print(f"__PLAYGROUND_RESULT__:{json.dumps(result)}")


async def main():
    """Main entry point"""

    parser = argparse.ArgumentParser(description="Generate AI-powered code playgrounds")
    parser.add_argument("--project-dir", required=True, help="Project directory")
    parser.add_argument("--idea", required=True, help="Playground idea/description")
    parser.add_argument(
        "--playground-type",
        required=True,
        choices=["html", "react", "vanilla-js", "python", "node"],
        help="Type of playground to generate",
    )
    parser.add_argument(
        "--sandbox-type",
        required=True,
        choices=["iframe", "docker", "webworker"],
        help="Type of sandbox to use",
    )
    parser.add_argument("--model", help="Model to use")
    parser.add_argument("--thinking-level", help="Thinking level")

    args = parser.parse_args()

    # Validate project directory
    project_dir = Path(args.project_dir)
    if not project_dir.exists():
        print(f"❌ Project directory does not exist: {project_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        # Create runner
        runner = CodePlaygroundRunner(
            project_dir=str(project_dir),
            idea=args.idea,
            playground_type=args.playground_type,
            sandbox_type=args.sandbox_type,
            model=args.model,
            thinking_level=args.thinking_level,
        )

        # Generate playground
        result = await runner.generate_playground()

        # Output result
        runner._output_result(result)

    except KeyboardInterrupt:
        print("\n🛑 Playground generation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Voice Control Runner - AI-powered voice command processing using Claude SDK

This script provides voice control functionality with speech-to-text
processing and AI-powered command interpretation.
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add auto-claude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Validate platform-specific dependencies BEFORE any imports that might
# trigger graphiti_core -> real_ladybug -> pywintypes import chain (ACS-253)
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


class VoiceControlProcessor:
    """Voice control processor with speech-to-text and command interpretation"""

    def __init__(self, model_id: str, thinking_budget: int, project_dir: Optional[str] = None):
        self.model_id = model_id
        self.thinking_budget = thinking_budget
        self.project_dir = project_dir
        self.client = None
        self.setup_client()

    def setup_client(self):
        """Setup Claude SDK client"""
        if not SDK_AVAILABLE:
            debug_error("Claude SDK not available")
            return

        try:
            token = get_auth_token()
            if not token:
                debug_error("No authentication token available")
                return

            options = ClaudeAgentOptions(
                model_id=self.model_id,
                thinking_budget=self.thinking_budget,
            )
            self.client = ClaudeSDKClient(options)
            debug_success("Claude SDK client initialized")
        except Exception as e:
            debug_error(f"Failed to setup Claude client: {e}")

    async def record_and_process(self, language: str = "en") -> Dict[str, Any]:
        """Record audio and process voice command"""
        try:
            # Simulate audio recording with progress
            debug("Starting voice recording...")
            
            # Simulate recording duration and audio levels
            duration = 0.0
            for i in range(30):  # 3 seconds of recording
                duration += 0.1
                # Emit audio level (simulate varying levels)
                audio_level = 0.3 + 0.4 * abs(time.time() % 1.0 - 0.5)
                print(f"__AUDIO_LEVEL__:{audio_level}")
                print(f"__DURATION__:{duration}")
                await asyncio.sleep(0.1)
            
            debug("Recording completed, processing speech...")
            
            # Simulate speech-to-text processing
            transcript = await self.speech_to_text(language)
            debug(f"Transcript: {transcript}")
            
            # Process command with AI
            result = await self.process_command(transcript)
            return result
            
        except Exception as e:
            debug_error(f"Error in voice recording: {e}")
            return {
                "transcript": "",
                "command": "",
                "action": "error",
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }

    async def speech_to_text(self, language: str) -> str:
        """Convert speech to text (simulated)"""
        # In a real implementation, this would use Whisper or Deepgram
        # For now, we'll simulate with a sample command
        await asyncio.sleep(1.0)  # Simulate processing time
        
        # Sample commands for demonstration
        sample_commands = [
            "Show me the kanban board",
            "Create a new task for user authentication",
            "Open the project settings",
            "Start a build on spec 42",
            "Show me the analytics dashboard",
            "Navigate to the code review",
            "Open the terminal view"
        ]
        
        import random
        return random.choice(sample_commands)

    async def process_command(self, transcript: str) -> Dict[str, Any]:
        """Process voice command with AI"""
        if not self.client:
            debug_error("No client available for command processing")
            return {
                "transcript": transcript,
                "command": transcript,
                "action": "error",
                "parameters": {},
                "confidence": 0.0
            }

        try:
            # Build system prompt for command interpretation
            system_prompt = self._build_system_prompt()
            
            # Build user prompt with transcript
            user_prompt = f"""Interpret this voice command and extract the action and parameters:

Voice command: "{transcript}"

Respond with a JSON object containing:
- "command": The exact command text
- "action": The main action (e.g., "navigate", "create", "show", "start")
- "parameters": Object with relevant parameters
- "confidence": Confidence score (0-1)

Example response:
{{
  "command": "Show me the kanban board",
  "action": "navigate",
  "parameters": {{
    "destination": "kanban"
  }},
  "confidence": 0.95
}}"""

            debug("Processing command with AI...")
            print(f"__TOOL_START__:{{\"tool\":\"claude_sdk\",\"action\":\"process_command\"}}")
            
            # Process with Claude SDK
            response = await self.client.process_message_async(
                system_prompt=system_prompt,
                user_message=user_prompt
            )
            
            print(f"__TOOL_END__:{{\"tool\":\"claude_sdk\"}}")
            
            # Parse the response
            result = self._parse_ai_response(response.content, transcript)
            debug_success(f"Command processed: {result['action']}")
            
            return result
            
        except Exception as e:
            debug_error(f"Error processing command: {e}")
            return {
                "transcript": transcript,
                "command": transcript,
                "action": "error",
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }

    def _build_system_prompt(self) -> str:
        """Build system prompt for command interpretation"""
        base_prompt = """You are a voice command interpreter for WorkPilot AI, a development management tool.

Your task is to interpret voice commands and extract structured information about the user's intent.

Available actions:
- "navigate": Navigate to a specific view/section
- "create": Create something (task, project, etc.)
- "show": Display information
- "start": Initiate an action (build, process, etc.)
- "open": Open a dialog or view
- "help": Show help or information

Common destinations:
- "kanban": Kanban board view
- "terminals": Terminal view
- "analytics": Analytics dashboard
- "settings": Settings dialog
- "insights": Insights view
- "roadmap": Roadmap view
- "context": Project context
- "code-review": Code review view
- "documentation": Documentation view

Always respond with valid JSON. If you cannot understand the command, set action to "unknown" and confidence low."""

        if self.project_dir:
            base_prompt += f"\n\nCurrent project context: {self.project_dir}"

        return base_prompt

    def _parse_ai_response(self, response: str, transcript: str) -> Dict[str, Any]:
        """Parse AI response and ensure valid structure"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            
            if json_match:
                parsed = json.loads(json_match.group())
                
                # Ensure required fields
                result = {
                    "transcript": transcript,
                    "command": parsed.get("command", transcript),
                    "action": parsed.get("action", "unknown"),
                    "parameters": parsed.get("parameters", {}),
                    "confidence": float(parsed.get("confidence", 0.5))
                }
                
                # Validate confidence range
                result["confidence"] = max(0.0, min(1.0, result["confidence"]))
                
                return result
            else:
                debug_error("No JSON found in AI response")
                raise ValueError("Invalid response format")
                
        except Exception as e:
            debug_error(f"Error parsing AI response: {e}")
            # Fallback response
            return {
                "transcript": transcript,
                "command": transcript,
                "action": "unknown",
                "parameters": {},
                "confidence": 0.3
            }


async def main():
    """Main voice control function"""
    parser = argparse.ArgumentParser(description="Voice Control Runner")
    parser.add_argument("command", choices=["record"], help="Command to execute")
    parser.add_argument("--project-dir", help="Project directory path")
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--model", help="Model ID to use")
    parser.add_argument("--thinking-level", default="medium", help="Thinking level")
    
    args = parser.parse_args()
    
    # Validate authentication
    token = ensure_claude_code_oauth_token()
    if not token:
        debug_error("Authentication required. Please run: claude-code auth")
        sys.exit(1)
    
    # Resolve model configuration
    model_id = resolve_model_id(args.model)
    thinking_budget = get_thinking_budget(args.thinking_level)
    
    debug_section("Voice Control")
    debug(f"Model: {model_id}")
    debug(f"Thinking budget: {thinking_budget}")
    debug(f"Language: {args.language}")
    if args.project_dir:
        debug(f"Project: {args.project_dir}")
    
    # Initialize processor
    processor = VoiceControlProcessor(
        model_id=model_id,
        thinking_budget=thinking_budget,
        project_dir=args.project_dir
    )
    
    if not processor.client:
        debug_error("Failed to initialize voice processor")
        sys.exit(1)
    
    # Execute command
    if args.command == "record":
        try:
            result = await processor.record_and_process(args.language)
            
            # Output structured result
            print(f"__VOICE_RESULT__:{json.dumps(result)}")
            debug_success("Voice control completed")
            
        except KeyboardInterrupt:
            debug("Voice control interrupted")
            sys.exit(0)
        except Exception as e:
            debug_error(f"Voice control failed: {e}")
            sys.exit(1)
    else:
        debug_error(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

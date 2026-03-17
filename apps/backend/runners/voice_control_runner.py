#!/usr/bin/env python3
"""
Voice Control Runner - AI-powered voice command processing using Claude SDK

This script provides voice control functionality with speech-to-text
processing and AI-powered command interpretation.
"""

import argparse
import asyncio
import json
import os
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
            debug_error("VoiceControl", "Claude SDK not available")
            return

        try:
            token = get_auth_token()
            if not token:
                debug_error("VoiceControl", "No authentication token available")
                return

            options = ClaudeAgentOptions(
                model=self.model_id,
                max_thinking_tokens=self.thinking_budget,
            )
            self.client = ClaudeSDKClient(options)
            debug_success("VoiceControl", "Claude SDK client initialized")
        except Exception as e:
            debug_error("VoiceControl", f"Failed to setup Claude client: {e}")

    async def record_and_process(self) -> Dict[str, Any]:
        """Record audio and process voice command"""
        try:
            # Simulate audio recording with progress
            debug("VoiceControl", "Starting voice recording...")
            
            # Simulate recording duration and audio levels
            duration = 0.0
            for _ in range(30):  # 3 seconds of recording
                duration += 0.1
                # Emit audio level (simulate varying levels)
                audio_level = 0.3 + 0.4 * abs(time.time() % 1.0 - 0.5)
                print(f"__AUDIO_LEVEL__:{audio_level}")
                print(f"__DURATION__:{duration}")
                await asyncio.sleep(0.1)
            
            debug("VoiceControl", "Recording completed, processing speech...")
            
            # Simulate speech-to-text processing
            transcript = await self.speech_to_text()
            debug("VoiceControl", f"Transcript: {transcript}")
            
            # Process command with AI
            result = self.process_command(transcript)
            return result
            
        except Exception as e:
            debug_error("VoiceControl", f"Error in voice recording: {e}")
            return {
                "transcript": "",
                "command": "",
                "action": "error",
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }

    async def speech_to_text(self) -> str:
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

    def process_command(self, transcript: str) -> Dict[str, Any]:
        """Process voice command using keyword matching"""
        result = self._classify_command(transcript)
        debug_success("VoiceControl", f"Command classified: {result['action']} -> {result['parameters']}")
        return result

    def _classify_command(self, transcript: str) -> Dict[str, Any]:
        """Classify voice command using keyword matching"""
        text = transcript.lower()

        # Destination keyword map
        destinations = {
            "kanban": ["kanban", "tableau", "tâche", "task board"],
            "terminals": ["terminal", "console", "shell"],
            "analytics": ["analytics", "statistique", "stat"],
            "settings": ["setting", "paramètre", "configuration", "préférence", "preference"],
            "insights": ["insight", "chat", "exploration"],
            "roadmap": ["roadmap", "feuille de route", "planning"],
            "context": ["context", "mémoire", "memory"],
            "code-review": ["code review", "review", "relecture"],
            "documentation": ["doc", "documentation"],
            "dashboard": ["dashboard", "accueil", "home", "overview"],
            "ideation": ["idéation", "ideation", "idée", "idea", "brainstorm"],
            "changelog": ["changelog", "release", "notes de version"],
            "cost-estimator": ["cost", "coût", "estimat", "billing", "facturation"],
            "pair-programming": ["pair", "paire", "pair programming"],
            "learning-loop": ["learning", "apprentissage"],
            "self-healing": ["self.healing", "healing", "auto-répar"],
            "mission-control": ["mission control", "mission"],
        }

        navigate_verbs = ["go", "open", "show", "navigate", "display", "switch", "va", "ouvre",
                          "montre", "affiche", "navigue", "voir", "see"]

        is_navigation = any(v in text for v in navigate_verbs)

        for destination, keywords in destinations.items():
            if any(kw in text for kw in keywords):
                return {
                    "transcript": transcript,
                    "command": transcript,
                    "action": "navigate",
                    "parameters": {"destination": destination},
                    "confidence": 0.9 if is_navigation else 0.75,
                }

        return {
            "transcript": transcript,
            "command": transcript,
            "action": "unknown",
            "parameters": {},
            "confidence": 0.3,
        }

    def _create_error_result(self, transcript: str, message: str, error: str = None) -> Dict[str, Any]:
        """Create standardized error result"""
        debug_error("VoiceControl", message)
        result = {
            "transcript": transcript,
            "command": transcript,
            "action": "error",
            "parameters": {},
            "confidence": 0.0
        }
        if error:
            result["error"] = error
        return result

    def _build_user_prompt(self, transcript: str) -> str:
        """Build user prompt with transcript"""
        return f"""Classify this voice command into a JSON object. Reply with ONLY the JSON, nothing else.

Voice command: "{transcript}"

Use action "navigate" for any command about going to, showing, or opening a view.
Destinations: kanban, terminals, analytics, settings, insights, roadmap, context, code-review, documentation, dashboard, ideation, changelog, cost-estimator.

Required JSON format:
{{
  "command": "{transcript}",
  "action": "navigate",
  "parameters": {{
    "destination": "<matching destination>"
  }},
  "confidence": 0.95
}}"""

    async def _process_with_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Process command with Claude SDK"""
        debug("VoiceControl", "Processing command with AI...")
        print("__TOOL_START__:{\"tool\":\"claude_sdk\",\"action\":\"process_command\"}")

        # Create client and process
        client = self._create_ai_client(system_prompt)
        response_text = await self._get_ai_response(client, user_prompt)
        
        debug("VoiceControl", f"AI raw response: {response_text[:200]}")
        print("__TOOL_END__:{\"tool\":\"claude_sdk\"}")
        return response_text

    def _create_ai_client(self, system_prompt: str) -> ClaudeSDKClient:
        """Create and configure AI client for command classification (no thinking needed)"""
        options = ClaudeAgentOptions(
            model=self.model_id,
            system_prompt=system_prompt,
        )
        return ClaudeSDKClient(options)

    async def _get_ai_response(self, client: ClaudeSDKClient, user_prompt: str) -> str:
        """Get response from AI client"""
        response_text = ""
        async with client:
            await client.query(user_prompt)
            async for msg in client.receive_response():
                response_text += self._process_message(msg)
        return response_text

    def _process_message(self, msg) -> str:
        """Process individual message from AI"""
        msg_type = type(msg).__name__
        
        if msg_type == "AssistantMessage" and hasattr(msg, 'content'):
            return self._process_assistant_message(msg)
        elif msg_type == "ResultMessage" and hasattr(msg, 'result'):
            return self._process_result_message(msg)
        
        return ""

    def _process_assistant_message(self, msg) -> str:
        """Process AssistantMessage content"""
        text = ""
        for block in msg.content:
            if type(block).__name__ == "TextBlock" and hasattr(block, 'text'):
                text += block.text
        return text

    def _process_result_message(self, msg) -> str:
        """Process ResultMessage content"""
        if isinstance(msg.result, str):
            return msg.result
        return ""

    def _build_system_prompt(self) -> str:
        """Build system prompt for command interpretation"""
        base_prompt = "You are a voice command classifier for WorkPilot AI. Respond only with a JSON object, no explanation or markdown."

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
                debug_error("VoiceControl", "No JSON found in AI response")
                raise ValueError("Invalid response format")
                
        except Exception as e:
            debug_error("VoiceControl", f"Error parsing AI response: {e}")
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
    
    # Validate authentication (ensure_claude_code_oauth_token sets env as a side effect)
    ensure_claude_code_oauth_token()
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") and not get_auth_token():
        debug_error("VoiceControl", "Authentication required. Please run: claude-code auth")
        sys.exit(1)
    
    # Resolve model configuration
    model_id = resolve_model_id(args.model)
    thinking_budget = get_thinking_budget(args.thinking_level)
    
    debug_section("VoiceControl", "Voice Control")
    debug("VoiceControl", f"Model: {model_id}")
    debug("VoiceControl", f"Thinking budget: {thinking_budget}")
    debug("VoiceControl", f"Language: {args.language}")
    if args.project_dir:
        debug("VoiceControl", f"Project: {args.project_dir}")
    
    # Initialize processor
    processor = VoiceControlProcessor(
        model_id=model_id,
        thinking_budget=thinking_budget,
        project_dir=args.project_dir
    )
    
    if not processor.client:
        debug_error("VoiceControl", "Failed to initialize voice processor")
        sys.exit(1)
    
    # Execute command
    if args.command == "record":
        try:
            result = await processor.record_and_process()
            
            # Output structured result
            print(f"__VOICE_RESULT__:{json.dumps(result)}")
            debug_success("VoiceControl", "Voice control completed")
            
        except KeyboardInterrupt:
            debug("VoiceControl", "Voice control interrupted")
            sys.exit(0)
        except Exception as e:
            debug_error("VoiceControl", f"Voice control failed: {e}")
            sys.exit(1)
    else:
        debug_error("VoiceControl", f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

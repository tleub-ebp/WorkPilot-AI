#!/usr/bin/env python3
"""
Natural Language Git Runner

Converts natural language commands into Git commands and executes them.
Uses AI to understand the user's intent and generate appropriate Git commands.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add the apps/backend directory to the Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from task_logger.logger import TaskLogger
from core.model_info import get_current_model_info


class NaturalLanguageGitRunner:
    """Handles natural language to Git command conversion and execution."""

    def __init__(self, project_path: str, command: str, model: Optional[str] = None, thinking_level: Optional[str] = None):
        self.project_path = Path(project_path)
        self.command = command
        self.model = model
        self.thinking_level = thinking_level
        self.logger = TaskLogger("natural-language-git")
        
        # Change to project directory
        os.chdir(self.project_path)

    def run(self) -> None:
        """Main execution method."""
        try:
            self._log_status("Analyzing natural language command...")

            # Generate Git command using AI
            git_command = self._generate_git_command()
            if not git_command:
                self._log_error("Failed to generate Git command")
                error_result = {
                    'generatedCommand': '',
                    'explanation': 'Could not generate a Git command. Please check your Claude configuration.',
                    'executionOutput': '',
                    'success': False,
                }
                print(f"__GIT_RESULT__:{json.dumps(error_result)}")
                return

            self._log_status(f"Generated command: {git_command}")

            # Execute the Git command
            result = self._execute_git_command(git_command)

            # Output the result
            self._output_result(git_command, result)

        except Exception as e:
            self._log_error(f"Unexpected error: {str(e)}")
            sys.exit(1)

    def _generate_git_command(self) -> Optional[str]:
        """Generate Git command from natural language using AI."""
        try:
            import asyncio
            from core.client import create_client
            from core.session import run_agent_session

            self._log_status("Understanding command intent...")

            git_status = self._get_git_status()
            current_branch = self._get_current_branch()
            system_prompt = self._build_system_prompt(git_status, current_branch)
            user_prompt = f"Convert this natural language command to a Git command: '{self.command}'"
            full_prompt = f"{system_prompt}\n\n{user_prompt}"

            async def _run_async() -> str:
                client = create_client(
                    project_dir=str(self.project_path),
                    model=self.model,
                    agent_type="coder",
                )
                async with client:
                    _, response = await run_agent_session(client, full_prompt, None)
                return response or ""

            response = asyncio.run(_run_async())
            command = self._extract_command_from_response(response)

            if command:
                self._log_status(f"Generated Git command: {command}")
                return command

            self._log_error("Could not extract Git command from AI response")
            return None

        except Exception as e:
            self._log_error(f"Failed to generate Git command: {str(e)}")
            return None

    def _build_system_prompt(self, git_status: str, current_branch: str) -> str:
        """Build the system prompt for Git command generation."""
        model_info = get_current_model_info()
        model_string = f" [{model_info['provider']}:{model_info['model_label']}]" if model_info else ""
        
        return f"""You are a Git expert assistant{model_string}. Your task is to convert natural language commands into precise Git commands.

Current Git context:
- Current branch: {current_branch}
- Git status: {git_status}
- Working directory: {self.project_path}

Rules:
1. Generate ONLY the Git command, no explanations
2. Use safe Git commands (avoid destructive operations unless explicitly requested)
3. Include flags and arguments as needed
4. Use absolute paths when necessary
5. For complex operations, prefer multiple simple commands over one complex one
6. If the command is ambiguous, choose the most common interpretation

Common command patterns:
- "show changes" -> git status, git diff, git log --oneline
- "undo last commit" -> git reset --soft HEAD~1
- "create branch" -> git branch <name>, git checkout <name>
- "switch to branch" -> git checkout <branch>
- "merge branch" -> git merge <branch>
- "show history" -> git log --oneline -10
- "stage files" -> git add <files>
- "commit changes" -> git commit -m "message"
- "push changes" -> git push origin <branch>
- "pull changes" -> git pull origin <branch>

Respond with ONLY the Git command, nothing else."""

    def _get_git_status(self) -> str:
        """Get current Git status."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() or "clean"
        except Exception:
            return "unknown"

    def _get_current_branch(self) -> str:
        """Get current Git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def _extract_command_from_response(self, response: str) -> Optional[str]:
        """Extract the Git command from AI response."""
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lines that start with 'git '
            if line.startswith('git '):
                return line
            # Look for command patterns in backticks
            if line.startswith('`') and line.endswith('`'):
                cmd = line.strip('`')
                if cmd.startswith('git '):
                    return cmd
        
        # If no explicit git command found, try to find any command
        for line in lines:
            line = line.strip()
            if 'git ' in line:
                # Extract the git command part
                parts = line.split('git ')
                if len(parts) > 1:
                    return 'git ' + parts[1].split()[0]
        
        return None

    def _execute_git_command(self, command: str) -> Dict[str, Any]:
        """Execute the Git command and return results."""
        try:
            self._log_status(f"Executing: {command}")

            parts = command.split()
            if not parts or parts[0] != 'git':
                raise ValueError("Invalid Git command")

            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_path
            )

            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out after 30 seconds',
                'returncode': -1
            }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }

    def _output_result(self, command: str, result: Dict[str, Any]) -> None:
        """Output the execution result in the expected format."""
        explanation = self._generate_explanation(command, result)
        
        output_result = {
            'generatedCommand': command,
            'explanation': explanation,
            'executionOutput': result['stdout'] + (result['stderr'] if result['stderr'] else ''),
            'success': result['success']
        }
        
        # Output the structured result
        print(f"__GIT_RESULT__:{json.dumps(output_result)}")

    def _generate_explanation(self, command: str, result: Dict[str, Any]) -> str:
        """Generate an explanation of what the command does."""
        cmd_parts = command.split()[1:]  # Skip 'git'
        
        explanations = {
            'status': 'Shows the working tree status',
            'log': 'Shows commit history',
            'diff': 'Shows changes between commits',
            'add': 'Stages files for commit',
            'commit': 'Creates a new commit',
            'push': 'Pushes commits to remote repository',
            'pull': 'Pulls changes from remote repository',
            'branch': 'Lists, creates, or deletes branches',
            'checkout': 'Switches branches or restores files',
            'merge': 'Merges branches',
            'reset': 'Resets current HEAD to specified state',
            'stash': 'Stashes away changes',
        }
        
        if cmd_parts and cmd_parts[0] in explanations:
            return explanations[cmd_parts[0]]
        else:
            return f"Executes Git command: {command}"

    def _log_status(self, message: str) -> None:
        """Log status message."""
        print(f"__STATUS__:{message}")
        self.logger.log(message)

    def _log_error(self, message: str) -> None:
        """Log error message."""
        print(f"__ERROR__:{message}")
        self.logger.log(f"ERROR: {message}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Natural Language Git Runner")
    parser.add_argument("--project-dir", required=True, help="Project directory")
    parser.add_argument("--command", required=True, help="Natural language command")
    parser.add_argument("--model", help="AI model to use")
    parser.add_argument("--thinking-level", help="Thinking level for AI")
    
    args = parser.parse_args()
    
    # Validate project directory
    if not os.path.isdir(args.project_dir):
        print(f"__ERROR__:Project directory not found: {args.project_dir}")
        sys.exit(1)
    
    # Check if it's a Git repository
    git_dir = os.path.join(args.project_dir, ".git")
    if not os.path.exists(git_dir):
        print(f"__ERROR__:Not a Git repository: {args.project_dir}")
        sys.exit(1)
    
    # Create and run the runner
    runner = NaturalLanguageGitRunner(
        project_path=args.project_dir,
        command=args.command,
        model=args.model,
        thinking_level=args.thinking_level
    )
    
    runner.run()


if __name__ == "__main__":
    main()

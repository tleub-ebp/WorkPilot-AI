"""
Tool Executor for Agent Runtime
==============================

Handles execution of tools during agent sessions.
"""

from typing import Any, Dict, List, Optional
import asyncio
import json
import subprocess
from pathlib import Path


class ToolExecutor:
    """Executes tools for agent sessions."""
    
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)
    
    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool
            
        Returns:
            Result of the tool execution
        """
        # Basic tool execution - can be extended with specific tool implementations
        if tool_name == "read_file":
            return await self._read_file(arguments.get("path"))
        elif tool_name == "write_file":
            return await self._write_file(arguments.get("path"), arguments.get("content"))
        elif tool_name == "list_files":
            return await self._list_files(arguments.get("directory", "."))
        elif tool_name == "run_command":
            return await self._run_command(arguments.get("command"), arguments.get("cwd"))
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _read_file(self, path: Optional[str]) -> str:
        """Read a file and return its contents."""
        if not path:
            raise ValueError("Path is required for read_file")
        
        file_path = self.project_dir / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Error reading file {path}: {e}")
    
    async def _write_file(self, path: Optional[str], content: Optional[str]) -> str:
        """Write content to a file."""
        if not path:
            raise ValueError("Path is required for write_file")
        if content is None:
            raise ValueError("Content is required for write_file")
        
        file_path = self.project_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            raise RuntimeError(f"Error writing file {path}: {e}")
    
    async def _list_files(self, directory: str) -> List[str]:
        """List files in a directory."""
        dir_path = self.project_dir / directory
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        try:
            files = []
            for item in dir_path.iterdir():
                if item.is_file():
                    files.append(item.name)
                elif item.is_dir():
                    files.append(item.name + "/")
            return sorted(files)
        except Exception as e:
            raise RuntimeError(f"Error listing files in {directory}: {e}")
    
    async def _run_command(self, command: Optional[str], cwd: Optional[str] = None) -> str:
        """Run a shell command."""
        if not command:
            raise ValueError("Command is required for run_command")
        
        work_dir = self.project_dir / cwd if cwd else self.project_dir
        
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=work_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Command failed with code {process.returncode}: {stderr}")
            
            return stdout
        except Exception as e:
            raise RuntimeError(f"Error running command {command}: {e}")


def get_tool_definitions(agent_type: str) -> List[Dict[str, Any]]:
    """
    Get tool definitions for a specific agent type.
    
    Args:
        agent_type: Type of agent (e.g., 'coder', 'planner')
        
    Returns:
        List of tool definitions
    """
    # Basic tool definitions - can be extended based on agent type
    base_tools = [
        {
            "name": "read_file",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write content to a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["path", "content"]
            }
        },
        {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list files from",
                        "default": "."
                    }
                }
            }
        },
        {
            "name": "run_command",
            "description": "Run a shell command",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to run"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for the command"
                    }
                },
                "required": ["command"]
            }
        }
    ]
    
    # Add agent-specific tools
    if agent_type == "coder":
        base_tools.extend([
            {
                "name": "create_directory",
                "description": "Create a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the directory to create"
                        }
                    },
                    "required": ["path"]
                }
            }
        ])
    elif agent_type == "planner":
        base_tools.extend([
            {
                "name": "analyze_project",
                "description": "Analyze the project structure",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ])
    
    return base_tools

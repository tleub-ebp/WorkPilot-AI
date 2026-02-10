"""
Agent Wrapper for Streaming Mode.

Wraps the agent execution to emit streaming events in real-time.
"""

import logging
from typing import Any, Optional

from .session_recorder import SessionRecorder
from .streaming_manager import get_streaming_manager

logger = logging.getLogger(__name__)


class StreamingAgentWrapper:
    """
    Wraps agent execution to broadcast events for streaming mode.
    
    This wrapper intercepts agent operations and emits real-time events
    that can be consumed by the frontend streaming UI.
    """
    
    def __init__(self, session_id: str, enable_recording: bool = True):
        self.session_id = session_id
        self.streaming_manager = get_streaming_manager()
        self.enable_recording = enable_recording
        self.recorder = SessionRecorder() if enable_recording else None
        self._is_active = False
        
    async def start_session(self, metadata: dict[str, Any]):
        """Start a streaming session."""
        self._is_active = True
        await self.streaming_manager.start_session(self.session_id, metadata)
        
        if self.recorder:
            self.recorder.start_recording(self.session_id, metadata)
            
        logger.info(f"Started streaming session {self.session_id}")
        
    async def end_session(self):
        """End a streaming session."""
        self._is_active = False
        await self.streaming_manager.end_session(self.session_id)
        
        if self.recorder:
            recording = self.recorder.stop_recording(self.session_id)
            if recording:
                logger.info(f"Session recording saved: {recording.session_id}")
                
        logger.info(f"Ended streaming session {self.session_id}")
        
    async def emit_file_change(
        self,
        file_path: str,
        operation: str = "update",
        content: Optional[str] = None,
    ):
        """Emit a file change event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_file_operation(
            session_id=self.session_id,
            operation=operation,
            file_path=file_path,
            content=content,
        )
        
    async def emit_command(self, command: str, cwd: Optional[str] = None):
        """Emit a command execution event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_command(
            session_id=self.session_id,
            command=command,
            cwd=cwd,
        )
        
    async def emit_command_output(self, output: str, is_error: bool = False):
        """Emit command output event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_command_output(
            session_id=self.session_id,
            output=output,
            is_error=is_error,
        )
        
    async def emit_agent_thinking(self, thinking: str):
        """Emit agent thinking/reasoning event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_agent_thinking(
            session_id=self.session_id,
            thinking=thinking,
        )
        
    async def emit_agent_response(self, response: str, tokens_used: Optional[int] = None):
        """Emit agent response event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_agent_response(
            session_id=self.session_id,
            response=response,
            tokens_used=tokens_used,
        )
        
    async def emit_test_run(self, test_command: str):
        """Emit test run event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_test_run(
            session_id=self.session_id,
            test_command=test_command,
        )
        
    async def emit_test_result(self, success: bool, details: Optional[str] = None):
        """Emit test result event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_test_result(
            session_id=self.session_id,
            success=success,
            details=details,
        )
        
    async def emit_progress(
        self,
        progress: float,
        status: str,
        current_step: Optional[str] = None,
    ):
        """Emit progress update event."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_progress(
            session_id=self.session_id,
            progress=progress,
            status=status,
            current_step=current_step,
        )
        
    async def emit_chat_message(
        self,
        message: str,
        author: str = "Agent",
        author_type: str = "agent",
    ):
        """Emit a chat message from the agent."""
        if not self._is_active:
            return
            
        await self.streaming_manager.emit_chat_message(
            session_id=self.session_id,
            message=message,
            author=author,
            author_type=author_type,
        )


# Convenience function to create a wrapper
def create_streaming_wrapper(session_id: str, enable_recording: bool = True) -> StreamingAgentWrapper:
    """Create a streaming agent wrapper."""
    return StreamingAgentWrapper(session_id, enable_recording)
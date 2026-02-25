#!/usr/bin/env python3
"""
Workflow Logger System
======================

Centralized logging system to track all AI agents, skills, hooks and workflows
execution with structured, readable logs for debugging and monitoring.

Usage:
    from core.workflow_logger import workflow_logger
    
    # Log agent execution
    workflow_logger.log_agent_start("Claude Code", "refactor_task", {"file": "app.py"})
    workflow_logger.log_agent_end("Claude Code", "success", {"changes": 5})
    
    # Log skill execution  
    workflow_logger.log_skill_start("framework-migration", "analyze", {"framework": "react"})
    workflow_logger.log_skill_end("framework-migration", "success", {"migrations_found": 3})
    
    # Log hook execution
    workflow_logger.log_hook_start("pre-commit", "validate_syntax")
    workflow_logger.log_hook_end("pre-commit", "success")
"""

import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict


class WorkflowType(Enum):
    """Types of workflow components."""
    AGENT = "agent"
    SKILL = "skill" 
    HOOK = "hook"
    ORCHESTRATOR = "orchestrator"
    STREAMING = "streaming"
    PHASE = "phase"
    TASK = "task"


class WorkflowStatus(Enum):
    """Status of workflow execution."""
    START = "start"
    END = "end"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class WorkflowEvent:
    """Structured workflow event."""
    timestamp: str
    workflow_type: WorkflowType
    component_name: str
    action: str
    status: WorkflowStatus
    duration_ms: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    trace_id: Optional[str] = None


class WorkflowLogger:
    """Centralized workflow logging system."""
    
    def __init__(self, log_file: Optional[str] = None, enable_console: bool = True):
        self.log_file = Path(log_file) if log_file else Path("logs/workflow.log")
        self.enable_console = enable_console
        self.active_traces: Dict[str, float] = {}
        
        # Create logs directory
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure file logger
        self.logger = logging.getLogger("workflow_logger")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        if enable_console:
            console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _generate_trace_id(self, component_name: str, action: str) -> str:
        """Generate unique trace ID for workflow tracking."""
        return f"{component_name}-{action}-{int(time.time() * 1000)}"
    
    def _format_log_message(self, event: WorkflowEvent) -> str:
        """Format workflow event for readable logging."""
        # Create visual indicators
        type_icons = {
            WorkflowType.AGENT: "🤖",
            WorkflowType.SKILL: "⚡", 
            WorkflowType.HOOK: "🪝",
            WorkflowType.ORCHESTRATOR: "🎼",
            WorkflowType.STREAMING: "📡",
            WorkflowType.PHASE: "🔄",
            WorkflowType.TASK: "📋"
        }
        
        status_icons = {
            WorkflowStatus.START: "▶️",
            WorkflowStatus.END: "✅",
            WorkflowStatus.ERROR: "❌",
            WorkflowStatus.TIMEOUT: "⏰",
            WorkflowStatus.CANCELLED: "🛑"
        }
        
        icon = type_icons.get(event.workflow_type, "📝")
        status_icon = status_icons.get(event.status, "❓")
        
        # Build base message
        msg = f"{icon} [{event.workflow_type.value.upper()}] {status_icon} {event.component_name}"
        
        # Add action
        if event.action:
            msg += f" - {event.action}"
        
        # Add duration for end events
        if event.duration_ms is not None:
            if event.duration_ms < 1000:
                msg += f" ({event.duration_ms}ms)"
            else:
                msg += f" ({event.duration_ms/1000:.2f}s)"
        
        # Add metadata highlights
        if event.metadata:
            highlights = []
            for key, value in event.metadata.items():
                if key in ["files", "changes", "errors", "migrations_found", "tokens_used"]:
                    highlights.append(f"{key}={value}")
            if highlights:
                msg += f" [{', '.join(highlights)}]"
        
        # Add error for error events
        if event.error:
            msg += f" - ERROR: {event.error}"
        
        # Add trace ID
        if event.trace_id:
            msg += f" (trace: {event.trace_id})"
        
        return msg
    
    def _log_event(self, event: WorkflowEvent):
        """Log workflow event to all outputs."""
        # Format readable message
        formatted_msg = self._format_log_message(event)
        
        # Log to console
        if self.enable_console:
            print(formatted_msg)
        
        # Log to file with structured data
        self.logger.info(formatted_msg)
        self.logger.info(f"STRUCTURED: {json.dumps(asdict(event), default=str)}")
    
    def log_agent_start(self, agent_name: str, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Log agent execution start."""
        trace_id = self._generate_trace_id(agent_name, action)
        self.active_traces[trace_id] = time.time()
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.AGENT,
            component_name=agent_name,
            action=action,
            status=WorkflowStatus.START,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
        return trace_id
    
    def log_agent_end(self, agent_name: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """Log agent execution end."""
        duration_ms = None
        if trace_id and trace_id in self.active_traces:
            duration_ms = int((time.time() - self.active_traces[trace_id]) * 1000)
            del self.active_traces[trace_id]
        
        workflow_status = WorkflowStatus.END if status == "success" else WorkflowStatus.ERROR
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.AGENT,
            component_name=agent_name,
            action=action,
            status=workflow_status,
            duration_ms=duration_ms,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
    
    def log_skill_start(self, skill_name: str, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Log skill execution start."""
        trace_id = self._generate_trace_id(skill_name, action)
        self.active_traces[trace_id] = time.time()
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.SKILL,
            component_name=skill_name,
            action=action,
            status=WorkflowStatus.START,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
        return trace_id
    
    def log_skill_end(self, skill_name: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """Log skill execution end."""
        duration_ms = None
        if trace_id and trace_id in self.active_traces:
            duration_ms = int((time.time() - self.active_traces[trace_id]) * 1000)
            del self.active_traces[trace_id]
        
        workflow_status = WorkflowStatus.END if status == "success" else WorkflowStatus.ERROR
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.SKILL,
            component_name=skill_name,
            action=action,
            status=workflow_status,
            duration_ms=duration_ms,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
    
    def log_hook_start(self, hook_name: str, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Log hook execution start."""
        trace_id = self._generate_trace_id(hook_name, action)
        self.active_traces[trace_id] = time.time()
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.HOOK,
            component_name=hook_name,
            action=action,
            status=WorkflowStatus.START,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
        return trace_id
    
    def log_hook_end(self, hook_name: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """Log hook execution end."""
        duration_ms = None
        if trace_id and trace_id in self.active_traces:
            duration_ms = int((time.time() - self.active_traces[trace_id]) * 1000)
            del self.active_traces[trace_id]
        
        workflow_status = WorkflowStatus.END if status == "success" else WorkflowStatus.ERROR
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.HOOK,
            component_name=hook_name,
            action=action,
            status=workflow_status,
            duration_ms=duration_ms,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
    
    def log_orchestrator_start(self, component_name: str, action: str, metadata: Optional[Dict[str, Any]] = None):
        """Log orchestrator execution start."""
        trace_id = self._generate_trace_id(component_name, action)
        self.active_traces[trace_id] = time.time()
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.ORCHESTRATOR,
            component_name=component_name,
            action=action,
            status=WorkflowStatus.START,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
        return trace_id
    
    def log_orchestrator_end(self, component_name: str, action: str, status: str, metadata: Optional[Dict[str, Any]] = None, trace_id: Optional[str] = None):
        """Log orchestrator execution end."""
        duration_ms = None
        if trace_id and trace_id in self.active_traces:
            duration_ms = int((time.time() - self.active_traces[trace_id]) * 1000)
            del self.active_traces[trace_id]
        
        workflow_status = WorkflowStatus.END if status == "success" else WorkflowStatus.ERROR
        
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.ORCHESTRATOR,
            component_name=component_name,
            action=action,
            status=workflow_status,
            duration_ms=duration_ms,
            metadata=metadata,
            trace_id=trace_id
        )
        self._log_event(event)
    
    def log_error(self, component_name: str, action: str, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Log error event."""
        event = WorkflowEvent(
            timestamp=datetime.now().isoformat(),
            workflow_type=WorkflowType.AGENT,  # Default to agent for errors
            component_name=component_name,
            action=action,
            status=WorkflowStatus.ERROR,
            error=error,
            metadata=metadata
        )
        self._log_event(event)
    
    def get_active_traces(self) -> Dict[str, float]:
        """Get all active trace IDs and their start times."""
        return self.active_traces.copy()


# Global instance
workflow_logger = WorkflowLogger()

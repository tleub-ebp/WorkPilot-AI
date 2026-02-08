"""
Inter-Agent Communication Bus
==============================

Enables agents to communicate, challenge each other, and build consensus.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class MessageType(str, Enum):
    """Type of message in agent communication."""

    PROPOSAL = "proposal"  # Initial proposal for a solution
    CHALLENGE = "challenge"  # Challenge/question another agent's idea
    SUPPORT = "support"  # Support another agent's proposal
    ALTERNATIVE = "alternative"  # Propose alternative approach
    CONCERN = "concern"  # Raise a concern without blocking
    VETO = "veto"  # Block a decision (if role has veto rights)
    VOTE = "vote"  # Cast a vote
    CONSENSUS = "consensus"  # Declare consensus reached
    QUESTION = "question"  # Ask clarifying question
    ANSWER = "answer"  # Answer a question


@dataclass
class AgentMessage:
    """A message from an agent in the debate."""

    message_id: str
    agent_role: str
    agent_name: str
    message_type: MessageType
    content: str
    timestamp: float
    references: list[str] = field(default_factory=list)  # IDs of messages this responds to
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Create from dictionary."""
        data["message_type"] = MessageType(data["message_type"])
        return cls(**data)


@dataclass
class DebateThread:
    """A thread of discussion on a specific topic."""

    thread_id: str
    topic: str
    messages: list[AgentMessage] = field(default_factory=list)
    status: str = "active"  # active, resolved, deadlock
    resolution: str | None = None
    started_at: float = field(default_factory=time.time)
    resolved_at: float | None = None

    def add_message(self, message: AgentMessage):
        """Add a message to the thread."""
        self.messages.append(message)

    def get_participants(self) -> set[str]:
        """Get set of participating agent roles."""
        return {msg.agent_role for msg in self.messages}

    def get_latest_messages(self, n: int = 5) -> list[AgentMessage]:
        """Get the n most recent messages."""
        return self.messages[-n:]

    def has_veto(self) -> bool:
        """Check if any message is a veto."""
        return any(msg.message_type == MessageType.VETO for msg in self.messages)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "messages": [msg.to_dict() for msg in self.messages],
            "status": self.status,
            "resolution": self.resolution,
            "started_at": self.started_at,
            "resolved_at": self.resolved_at,
        }


class CommunicationBus:
    """Manages inter-agent communication."""

    def __init__(self, spec_dir: Path):
        self.spec_dir = Path(spec_dir)
        self.threads: dict[str, DebateThread] = {}
        self.message_counter = 0

        # Create debate log directory
        self.debate_dir = self.spec_dir / "debates"
        self.debate_dir.mkdir(exist_ok=True)

    def create_thread(self, topic: str) -> DebateThread:
        """Create a new debate thread."""
        thread_id = f"thread_{len(self.threads) + 1}"
        thread = DebateThread(thread_id=thread_id, topic=topic)
        self.threads[thread_id] = thread
        return thread

    def post_message(
        self,
        thread_id: str,
        agent_role: str,
        agent_name: str,
        message_type: MessageType,
        content: str,
        references: list[str] | None = None,
        metadata: dict | None = None,
    ) -> AgentMessage:
        """Post a message to a thread."""
        self.message_counter += 1
        message = AgentMessage(
            message_id=f"msg_{self.message_counter}",
            agent_role=agent_role,
            agent_name=agent_name,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            references=references or [],
            metadata=metadata or {},
        )

        if thread_id in self.threads:
            self.threads[thread_id].add_message(message)
            self._save_thread(thread_id)

        return message

    def get_thread(self, thread_id: str) -> DebateThread | None:
        """Get a debate thread by ID."""
        return self.threads.get(thread_id)

    def get_thread_history(self, thread_id: str) -> str:
        """Get formatted history of a thread for agent context."""
        thread = self.threads.get(thread_id)
        if not thread:
            return ""

        lines = [f"## Debate Thread: {thread.topic}", ""]
        for msg in thread.messages:
            timestamp = time.strftime("%H:%M:%S", time.localtime(msg.timestamp))
            lines.append(
                f"**[{timestamp}] {msg.agent_name} ({msg.message_type.value}):**"
            )
            lines.append(msg.content)
            lines.append("")

        return "\n".join(lines)

    def detect_consensus(self, thread_id: str) -> bool:
        """
        Detect if consensus has been reached in a thread.

        Consensus indicators:
        - Multiple SUPPORT messages
        - No recent CHALLENGE or CONCERN messages
        - No VETO messages
        """
        thread = self.threads.get(thread_id)
        if not thread or len(thread.messages) < 3:
            return False

        # Check for vetos
        if thread.has_veto():
            return False

        # Count recent message types (last 5 messages)
        recent = thread.get_latest_messages(5)
        support_count = sum(1 for msg in recent if msg.message_type == MessageType.SUPPORT)
        challenge_count = sum(
            1 for msg in recent if msg.message_type in [MessageType.CHALLENGE, MessageType.CONCERN]
        )

        # Simple heuristic: 3+ supports and no challenges
        return support_count >= 3 and challenge_count == 0

    def _save_thread(self, thread_id: str):
        """Save thread to disk for debugging/auditing."""
        thread = self.threads.get(thread_id)
        if not thread:
            return

        file_path = self.debate_dir / f"{thread_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(thread.to_dict(), f, indent=2)

    def save_all_threads(self):
        """Save all threads to disk."""
        for thread_id in self.threads:
            self._save_thread(thread_id)

        # Save summary
        summary_path = self.debate_dir / "summary.json"
        summary = {
            "total_threads": len(self.threads),
            "total_messages": self.message_counter,
            "threads": [
                {
                    "id": t.thread_id,
                    "topic": t.topic,
                    "status": t.status,
                    "messages": len(t.messages),
                    "participants": list(t.get_participants()),
                }
                for t in self.threads.values()
            ],
        }
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)


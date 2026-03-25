"""
Claude Teams - Communication Bus
==================================

Message bus, debate threads, and consensus detection for multi-agent teams.
"""

import json
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class MessageType(str, Enum):
    PROPOSAL = "proposal"
    CHALLENGE = "challenge"
    SUPPORT = "support"
    VETO = "veto"
    INFO = "info"


@dataclass
class AgentMessage:
    message_id: str
    agent_role: str
    agent_name: str
    message_type: MessageType
    content: str
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "agent_role": self.agent_role,
            "agent_name": self.agent_name,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
        }


class DebateThread:
    def __init__(self, thread_id: str, topic: str):
        self.thread_id = thread_id
        self.topic = topic
        self.status = "active"
        self.messages: list[AgentMessage] = []
        self.created_at = time.time()

    def add_message(self, message: AgentMessage) -> None:
        self.messages.append(message)

    def get_participants(self) -> list[str]:
        return list({msg.agent_role for msg in self.messages})

    def has_veto(self) -> bool:
        return any(msg.message_type == MessageType.VETO for msg in self.messages)

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "topic": self.topic,
            "status": self.status,
            "created_at": self.created_at,
            "messages": [m.to_dict() for m in self.messages],
        }


class CommunicationBus:
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.debates_dir = self.base_path / "debates"
        self.debates_dir.mkdir(parents=True, exist_ok=True)
        self._threads: dict[str, DebateThread] = {}
        self._thread_counter = 0

    def create_thread(self, topic: str) -> DebateThread:
        self._thread_counter += 1
        thread_id = f"thread_{self._thread_counter}"
        thread = DebateThread(thread_id, topic)
        self._threads[thread_id] = thread
        return thread

    def post_message(
        self,
        thread_id: str,
        agent_role: str,
        agent_name: str,
        message_type: MessageType,
        content: str,
    ) -> AgentMessage:
        thread = self._threads[thread_id]
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            agent_role=agent_role,
            agent_name=agent_name,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
        )
        thread.add_message(message)
        self._save_thread(thread)
        return message

    def get_thread_history(self, thread_id: str) -> str:
        thread = self._threads[thread_id]
        lines = [f"Debate Thread: {thread.topic}", "=" * 40]
        for msg in thread.messages:
            lines.append(
                f"[{msg.message_type.value}] {msg.agent_name} ({msg.agent_role}): {msg.content}"
            )
        return "\n".join(lines)

    def detect_consensus(self, thread_id: str) -> bool:
        thread = self._threads[thread_id]
        messages = thread.messages

        if len(messages) < 3:
            return False

        if thread.has_veto():
            return False

        # Recent challenge (last 3 messages) prevents consensus
        recent = messages[-3:]
        if any(m.message_type == MessageType.CHALLENGE for m in recent):
            return False

        support_count = sum(
            1 for m in messages if m.message_type == MessageType.SUPPORT
        )
        return support_count >= 3

    def save_all_threads(self) -> None:
        total_messages = sum(len(t.messages) for t in self._threads.values())
        summary = {
            "total_threads": len(self._threads),
            "total_messages": total_messages,
            "threads": [
                {
                    "thread_id": t.thread_id,
                    "topic": t.topic,
                    "message_count": len(t.messages),
                }
                for t in self._threads.values()
            ],
        }
        summary_file = self.debates_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

    def _save_thread(self, thread: DebateThread) -> None:
        thread_file = self.debates_dir / f"{thread.thread_id}.json"
        with open(thread_file, "w") as f:
            json.dump(thread.to_dict(), f, indent=2)

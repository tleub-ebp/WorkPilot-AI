"""
Tests for Claude Teams - Communication Bus
===========================================

Tests the message bus, debate threads, and consensus detection.
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import time

# Add backend to path BEFORE any imports
backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Mock dependencies before importing
from unittest.mock import MagicMock
sys.modules['claude_agent_sdk'] = MagicMock()
sys.modules['core.client'] = MagicMock()
sys.modules['debug'] = MagicMock()

from teams.communication import AgentMessage, CommunicationBus, DebateThread, MessageType


class TestCommunicationBus:
    """Test suite for communication bus."""

    def test_create_thread(self):
        """Can create a debate thread."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            
            thread = bus.create_thread("Test topic")
            
            assert thread.thread_id == "thread_1"
            assert thread.topic == "Test topic"
            assert thread.status == "active"
            assert len(thread.messages) == 0

    def test_post_message_to_thread(self):
        """Can post messages to a thread."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            thread = bus.create_thread("Test topic")
            
            message = bus.post_message(
                thread_id=thread.thread_id,
                agent_role="architect",
                agent_name="System Architect",
                message_type=MessageType.PROPOSAL,
                content="I propose using REST API",
            )
            
            assert message.agent_role == "architect"
            assert message.message_type == MessageType.PROPOSAL
            assert "REST API" in message.content
            assert thread.messages[0] == message

    def test_get_thread_history(self):
        """Thread history formats messages properly."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            thread = bus.create_thread("Test")
            
            bus.post_message(
                thread.thread_id, "architect", "Architect", 
                MessageType.PROPOSAL, "Use REST"
            )
            bus.post_message(
                thread.thread_id, "security", "Security", 
                MessageType.CHALLENGE, "What about auth?"
            )
            
            history = bus.get_thread_history(thread.thread_id)
            
            assert "Debate Thread: Test" in history
            assert "Architect" in history
            assert "Security" in history
            assert "proposal" in history
            assert "challenge" in history

    def test_detect_consensus_with_supports(self):
        """Consensus detected with 3+ supports."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            thread = bus.create_thread("Test")
            
            # Not enough messages
            assert bus.detect_consensus(thread.thread_id) is False
            
            # Add supports
            for i in range(4):
                bus.post_message(
                    thread.thread_id, f"agent{i}", f"Agent {i}",
                    MessageType.SUPPORT, "I support this"
                )
            
            # Should detect consensus
            assert bus.detect_consensus(thread.thread_id) is True

    def test_no_consensus_with_veto(self):
        """Veto prevents consensus."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            thread = bus.create_thread("Test")
            
            # Add supports
            for i in range(4):
                bus.post_message(
                    thread.thread_id, f"agent{i}", f"Agent {i}",
                    MessageType.SUPPORT, "Support"
                )
            
            # Add veto
            bus.post_message(
                thread.thread_id, "security", "Security",
                MessageType.VETO, "Security risk!"
            )
            
            # No consensus with veto
            assert bus.detect_consensus(thread.thread_id) is False

    def test_no_consensus_with_challenges(self):
        """Recent challenges prevent consensus."""
        with TemporaryDirectory() as tmpdir:
            bus = CommunicationBus(Path(tmpdir))
            thread = bus.create_thread("Test")
            
            # Add supports
            for i in range(3):
                bus.post_message(
                    thread.thread_id, f"agent{i}", f"Agent {i}",
                    MessageType.SUPPORT, "Support"
                )
            
            # Add recent challenge
            bus.post_message(
                thread.thread_id, "qa", "QA",
                MessageType.CHALLENGE, "What about edge cases?"
            )
            
            # No consensus with recent challenge
            assert bus.detect_consensus(thread.thread_id) is False

    def test_thread_saves_to_disk(self):
        """Threads are saved to JSON."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            bus = CommunicationBus(tmppath)
            thread = bus.create_thread("Test")
            
            bus.post_message(
                thread.thread_id, "architect", "Architect",
                MessageType.PROPOSAL, "Proposal"
            )
            
            # Check file exists
            thread_file = tmppath / "debates" / f"{thread.thread_id}.json"
            assert thread_file.exists()
            
            # Check content
            import json
            with open(thread_file) as f:
                saved = json.load(f)
            
            assert saved["thread_id"] == thread.thread_id
            assert saved["topic"] == "Test"
            assert len(saved["messages"]) == 1

    def test_save_all_threads_creates_summary(self):
        """save_all_threads creates summary file."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            bus = CommunicationBus(tmppath)
            
            # Create multiple threads
            thread1 = bus.create_thread("Topic 1")
            thread2 = bus.create_thread("Topic 2")
            
            bus.post_message(thread1.thread_id, "a", "A", MessageType.PROPOSAL, "P1")
            bus.post_message(thread2.thread_id, "b", "B", MessageType.PROPOSAL, "P2")
            
            bus.save_all_threads()
            
            # Check summary exists
            summary_file = tmppath / "debates" / "summary.json"
            assert summary_file.exists()
            
            import json
            with open(summary_file) as f:
                summary = json.load(f)
            
            assert summary["total_threads"] == 2
            assert summary["total_messages"] == 2


class TestDebateThread:
    """Test suite for debate thread."""

    def test_get_participants(self):
        """get_participants returns unique roles."""
        thread = DebateThread("t1", "Test")
        
        thread.add_message(AgentMessage(
            "m1", "architect", "Arch", MessageType.PROPOSAL, "P1", time.time()
        ))
        thread.add_message(AgentMessage(
            "m2", "security", "Sec", MessageType.CHALLENGE, "C1", time.time()
        ))
        thread.add_message(AgentMessage(
            "m3", "architect", "Arch", MessageType.SUPPORT, "S1", time.time()
        ))
        
        participants = thread.get_participants()
        assert len(participants) == 2
        assert "architect" in participants
        assert "security" in participants

    def test_has_veto(self):
        """has_veto detects veto messages."""
        thread = DebateThread("t1", "Test")
        
        assert thread.has_veto() is False
        
        thread.add_message(AgentMessage(
            "m1", "architect", "Arch", MessageType.PROPOSAL, "P1", time.time()
        ))
        
        assert thread.has_veto() is False
        
        thread.add_message(AgentMessage(
            "m2", "security", "Sec", MessageType.VETO, "VETO!", time.time()
        ))
        
        assert thread.has_veto() is True


if __name__ == "__main__":
    print("Running communication bus tests...\n")
    
    test_bus = TestCommunicationBus()
    test_thread = TestDebateThread()
    
    try:
        test_bus.test_create_thread()
        print("✅ Create thread test passed")
        
        test_bus.test_post_message_to_thread()
        print("✅ Post message test passed")
        
        test_bus.test_get_thread_history()
        print("✅ Thread history test passed")
        
        test_bus.test_detect_consensus_with_supports()
        print("✅ Consensus detection test passed")
        
        test_bus.test_no_consensus_with_veto()
        print("✅ Veto prevention test passed")
        
        test_bus.test_thread_saves_to_disk()
        print("✅ Persistence test passed")
        
        test_thread.test_get_participants()
        print("✅ Participants test passed")
        
        test_thread.test_has_veto()
        print("✅ Veto detection test passed")
        
        print("\n🎉 All communication tests passed!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


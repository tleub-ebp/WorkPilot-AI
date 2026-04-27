"""Tests for the Real-time Pair Programming session manager."""

from __future__ import annotations

import asyncio

import pytest
from pair_realtime import (
    Operation,
    OperationKind,
    PairRoom,
    PairSessionManager,
    Role,
)

# ----------------------------------------------------------------------
# Room basics


class TestRoomCreation:
    def test_invalid_room_id_rejected(self) -> None:
        for bad in ("", "../escape", "with space", "/abs", ".hidden"):
            with pytest.raises(ValueError):
                PairRoom(room_id=bad)

    def test_valid_room_id_accepted(self) -> None:
        for ok in ("session-1", "demo.v2", "abc_def"):
            PairRoom(room_id=ok)

    def test_new_room_has_no_participants(self) -> None:
        room = PairRoom(room_id="r1")
        snap = room.snapshot()
        assert snap.participants == []
        assert snap.op_count == 0
        assert snap.last_op_sequence == -1


class TestParticipants:
    def test_join_records_op(self) -> None:
        room = PairRoom(room_id="r1")
        op = room.join(user_id="u1", display_name="Alice", role=Role.DRIVER)
        assert op.kind == OperationKind.JOIN
        assert op.actor == "u1"
        assert {p.user_id for p in room.participants()} == {"u1"}

    def test_idempotent_join_does_not_duplicate(self) -> None:
        room = PairRoom(room_id="r1")
        room.join("u1", "Alice")
        room.join("u1", "Alice (again)")
        assert len(room.participants()) == 1

    def test_join_requires_user_id(self) -> None:
        room = PairRoom(room_id="r1")
        with pytest.raises(ValueError):
            room.join(user_id="", display_name="Anon")

    def test_leave_removes_participant(self) -> None:
        room = PairRoom(room_id="r1")
        room.join("u1", "Alice")
        op = room.leave("u1")
        assert op is not None and op.kind == OperationKind.LEAVE
        assert room.participants() == []

    def test_leave_unknown_returns_none(self) -> None:
        room = PairRoom(room_id="r1")
        assert room.leave("ghost") is None

    def test_set_role_changes_and_records(self) -> None:
        room = PairRoom(room_id="r1")
        room.join("u1", "Alice", role=Role.NAVIGATOR)
        op = room.set_role("u1", Role.DRIVER)
        assert op.kind == OperationKind.ROLE_CHANGE
        assert room.participants()[0].role == Role.DRIVER

    def test_set_role_unknown_user_raises(self) -> None:
        with pytest.raises(ValueError):
            PairRoom(room_id="r1").set_role("ghost", Role.DRIVER)


class TestOperations:
    def test_submit_edit(self) -> None:
        room = PairRoom(room_id="r1")
        room.join("u1", "Alice")
        op = room.submit_edit("u1", "main.py", 1, 5, "new code")
        assert op.kind == OperationKind.EDIT
        assert op.payload["file_path"] == "main.py"

    def test_submit_cursor(self) -> None:
        room = PairRoom(room_id="r1")
        op = room.submit_cursor("u1", "main.py", 10, 5)
        assert op.kind == OperationKind.CURSOR
        assert op.payload["line"] == 10

    def test_submit_chat(self) -> None:
        room = PairRoom(room_id="r1")
        op = room.submit_chat("u1", "looks good")
        assert op.kind == OperationKind.CHAT
        assert op.payload["text"] == "looks good"

    def test_chat_too_long_rejected(self) -> None:
        room = PairRoom(room_id="r1")
        with pytest.raises(ValueError):
            room.submit_chat("u1", "x" * 5_000)

    def test_empty_chat_rejected(self) -> None:
        room = PairRoom(room_id="r1")
        with pytest.raises(ValueError):
            room.submit_chat("u1", "")

    def test_sequences_are_monotonic(self) -> None:
        room = PairRoom(room_id="r1")
        ops = [room.submit_chat("u1", f"msg {i}") for i in range(5)]
        assert [o.sequence for o in ops] == [0, 1, 2, 3, 4]

    def test_recent_ops_filters_by_sequence(self) -> None:
        room = PairRoom(room_id="r1")
        for i in range(5):
            room.submit_chat("u1", f"msg {i}")
        # Get only ops with sequence ≥ 3
        recent = room.recent_ops(since_sequence=3)
        assert [o.sequence for o in recent] == [3, 4]

    def test_history_ring_buffer_caps(self) -> None:
        room = PairRoom(room_id="r1", history=3)
        for i in range(5):
            room.submit_chat("u1", f"msg {i}")
        # Only the last 3 are kept.
        kept = room.recent_ops()
        assert len(kept) == 3
        assert [o.payload["text"] for o in kept] == ["msg 2", "msg 3", "msg 4"]


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_receives_live_ops(self) -> None:
        room = PairRoom(room_id="r1")
        received: list[Operation] = []

        async def consumer() -> None:
            async for op in room.subscribe():
                received.append(op)
                if len(received) >= 3:
                    return

        task = asyncio.create_task(consumer())
        # Yield once so the subscriber actually registers.
        await asyncio.sleep(0)
        room.submit_chat("u1", "a")
        room.submit_chat("u1", "b")
        room.submit_chat("u1", "c")
        await asyncio.wait_for(task, timeout=2.0)
        assert [o.payload["text"] for o in received] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_subscribe_replays_history_first(self) -> None:
        room = PairRoom(room_id="r1")
        room.submit_chat("u1", "old1")
        room.submit_chat("u1", "old2")
        received: list[Operation] = []

        async def consumer() -> None:
            async for op in room.subscribe(since_sequence=0):
                received.append(op)
                if len(received) >= 3:
                    return

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0)
        room.submit_chat("u1", "new")
        await asyncio.wait_for(task, timeout=2.0)
        assert [o.payload["text"] for o in received] == ["old1", "old2", "new"]

    @pytest.mark.asyncio
    async def test_late_joiner_can_request_recent_only(self) -> None:
        room = PairRoom(room_id="r1")
        room.submit_chat("u1", "old")
        room.submit_chat("u1", "old2")
        # Late joiner asks for ops after sequence 2 only.
        received: list[Operation] = []

        async def consumer() -> None:
            async for op in room.subscribe(since_sequence=2):
                received.append(op)
                return

        task = asyncio.create_task(consumer())
        await asyncio.sleep(0)
        room.submit_chat("u1", "fresh")
        await asyncio.wait_for(task, timeout=2.0)
        assert [o.payload["text"] for o in received] == ["fresh"]


class TestLifecycle:
    def test_close_blocks_further_ops(self) -> None:
        room = PairRoom(room_id="r1")
        room.close()
        assert room.is_closed()
        with pytest.raises(ValueError):
            room.submit_chat("u1", "too late")

    def test_close_blocks_join(self) -> None:
        room = PairRoom(room_id="r1")
        room.close()
        with pytest.raises(ValueError):
            room.join("u1", "Alice")

    def test_snapshot_captures_state(self) -> None:
        room = PairRoom(room_id="r1")
        room.join("u1", "Alice", role=Role.DRIVER)
        room.submit_chat("u1", "hi")
        snap = room.snapshot()
        assert snap.room_id == "r1"
        assert len(snap.participants) == 1
        assert snap.op_count == 2  # join + chat
        assert snap.last_op_sequence == 1


# ----------------------------------------------------------------------
# Manager


class TestManager:
    def test_create_room_idempotent_via_get_or_create(self) -> None:
        mgr = PairSessionManager()
        a = mgr.get_or_create_room("r1")
        b = mgr.get_or_create_room("r1")
        assert a is b

    def test_create_room_rejects_duplicate(self) -> None:
        mgr = PairSessionManager()
        mgr.create_room("r1")
        with pytest.raises(ValueError):
            mgr.create_room("r1")

    def test_get_room_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            PairSessionManager().get_room("ghost")

    def test_close_room(self) -> None:
        mgr = PairSessionManager()
        room = mgr.create_room("r1")
        assert mgr.close_room("r1") is True
        assert room.is_closed()
        assert mgr.close_room("r1") is False  # already closed

    def test_list_rooms(self) -> None:
        mgr = PairSessionManager()
        mgr.create_room("a")
        mgr.create_room("b")
        assert mgr.list_rooms() == ["a", "b"]

    def test_reset_closes_everything(self) -> None:
        mgr = PairSessionManager()
        room = mgr.create_room("r1")
        mgr.reset()
        assert mgr.list_rooms() == []
        assert room.is_closed()


class TestSerialisation:
    def test_op_to_dict(self) -> None:
        room = PairRoom(room_id="r1")
        op = room.submit_chat("u1", "hi")
        d = op.to_dict()
        assert d["kind"] == "chat"
        assert d["payload"]["text"] == "hi"

    def test_snapshot_to_dict(self) -> None:
        import json

        room = PairRoom(room_id="r1")
        room.join("u1", "Alice")
        decoded = json.loads(json.dumps(room.snapshot().to_dict()))
        assert decoded["room_id"] == "r1"
        assert decoded["participants"][0]["user_id"] == "u1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

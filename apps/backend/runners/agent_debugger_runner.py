"""
Agent Debugger Runner
=====================

Thin JSON-over-stdout wrapper around :class:`DebuggerRegistry` so the
Electron main process can attach, list breakpoints, resume frames, etc.

Protocol (one line JSON responses)::

    python agent_debugger_runner.py --action <name> --session-id <id> [--payload JSON]

Actions:
  - ``attach``      create/get a session, returns {session_id}
  - ``detach``      remove a session
  - ``list_bp``     list breakpoints
  - ``add_bp``      payload: {id, tool, path_pattern?, content_pattern?,
                              command_pattern?} → adds a breakpoint
  - ``remove_bp``   payload: {id}
  - ``list_frames`` list paused frames awaiting resume
  - ``resume``      payload: {frame_id, action, tool_input?, reason?}
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from agents.debugger import Breakpoint, DebuggerRegistry  # noqa: E402


def _emit(payload: object) -> None:
    print(json.dumps(payload, default=str), flush=True)


def _action_attach(session_id: str, _payload: dict) -> dict:
    DebuggerRegistry.instance().attach(session_id)
    return {"session_id": session_id, "ok": True}


def _action_detach(session_id: str, _payload: dict) -> dict:
    ok = DebuggerRegistry.instance().detach(session_id)
    return {"session_id": session_id, "ok": ok}


def _action_list_bp(session_id: str, _payload: dict) -> dict:
    session = DebuggerRegistry.instance().get(session_id)
    if session is None:
        return {"breakpoints": []}
    return {
        "breakpoints": [
            {
                "id": bp.id,
                "tool": bp.tool,
                "path_pattern": bp.path_pattern,
                "content_pattern": bp.content_pattern,
                "command_pattern": bp.command_pattern,
                "enabled": bp.enabled,
            }
            for bp in session.list_breakpoints()
        ],
    }


def _action_add_bp(session_id: str, payload: dict) -> dict:
    session = DebuggerRegistry.instance().attach(session_id)
    bp = Breakpoint(
        id=str(payload.get("id") or "bp"),
        tool=str(payload.get("tool") or "*"),
        path_pattern=payload.get("path_pattern"),
        content_pattern=payload.get("content_pattern"),
        command_pattern=payload.get("command_pattern"),
        enabled=bool(payload.get("enabled", True)),
    )
    session.add_breakpoint(bp)
    return {"ok": True, "breakpoint_id": bp.id}


def _action_remove_bp(session_id: str, payload: dict) -> dict:
    session = DebuggerRegistry.instance().get(session_id)
    if session is None:
        return {"ok": False}
    ok = session.remove_breakpoint(str(payload.get("id") or ""))
    return {"ok": ok}


def _action_list_frames(session_id: str, _payload: dict) -> dict:
    session = DebuggerRegistry.instance().get(session_id)
    if session is None:
        return {"frames": []}
    return {"frames": [f.to_dict() for f in session.list_frames()]}


def _action_resume(session_id: str, payload: dict) -> dict:
    session = DebuggerRegistry.instance().get(session_id)
    if session is None:
        return {"ok": False, "reason": "unknown_session"}
    frame_id = str(payload.get("frame_id") or "")
    decision = {
        "action": payload.get("action", "continue"),
        "tool_input": payload.get("tool_input"),
        "reason": payload.get("reason"),
    }
    ok = session.resume(frame_id, decision)
    return {"ok": ok}


_ACTIONS = {
    "attach": _action_attach,
    "detach": _action_detach,
    "list_bp": _action_list_bp,
    "add_bp": _action_add_bp,
    "remove_bp": _action_remove_bp,
    "list_frames": _action_list_frames,
    "resume": _action_resume,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Debugger Runner")
    parser.add_argument("--action", required=True, choices=sorted(_ACTIONS))
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--payload", default="{}")
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload) if args.payload else {}
    except json.JSONDecodeError as exc:
        _emit({"error": f"invalid payload JSON: {exc}"})
        sys.exit(1)

    handler = _ACTIONS[args.action]
    try:
        result = handler(args.session_id, payload)
        _emit(result)
    except Exception as exc:  # noqa: BLE001
        _emit({"error": str(exc)})
        sys.exit(1)


if __name__ == "__main__":
    main()

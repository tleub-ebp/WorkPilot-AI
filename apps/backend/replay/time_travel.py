"""
Agent Time Travel — Temporal debugger for AI agent sessions.

Provides checkpoint management, fork & re-execute capabilities, and decision
scoring. Works with any LLM provider (Anthropic, OpenAI, Google, Ollama, etc.)
by reconstructing a provider-agnostic conversation history at each checkpoint.

Core concepts:
- **Checkpoint**: A restorable snapshot at a decision point in the session
- **Fork**: Re-execute from a checkpoint with modified context/instructions
- **Decision Score**: Confidence/impact scoring for each decision point
"""

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from .models import (
    Checkpoint,
    CheckpointType,
    DecisionScore,
    ForkRequest,
    ForkSession,
    ReplayStep,
    ReplayStepType,
)
from .recorder import get_replay_recorder

logger = logging.getLogger(__name__)

# Step types that trigger automatic checkpoints
_CHECKPOINT_STEP_TYPES = {
    ReplayStepType.DECISION: CheckpointType.AUTO_DECISION,
    ReplayStepType.FILE_CREATE: CheckpointType.AUTO_FILE_CHANGE,
    ReplayStepType.FILE_UPDATE: CheckpointType.AUTO_FILE_CHANGE,
    ReplayStepType.FILE_DELETE: CheckpointType.AUTO_FILE_CHANGE,
    ReplayStepType.TOOL_CALL: CheckpointType.AUTO_TOOL_CALL,
}


class TimeTravelEngine:
    """
    Core time-travel engine for agent sessions.

    Manages checkpoints, forks, and decision scoring. All state is persisted
    to disk alongside replay sessions so it survives app restarts.
    """

    def __init__(self, storage_dir: Path | None = None):
        self._storage_dir = (
            storage_dir or Path.home() / ".workpilot" / "replays" / "time_travel"
        )
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoints_dir = self._storage_dir / "checkpoints"
        self._checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._forks_dir = self._storage_dir / "forks"
        self._forks_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------
    # Checkpoint management
    # -------------------------------------------------------------------

    def create_checkpoints_for_session(self, session_id: str) -> list[Checkpoint]:
        """
        Analyze a completed session and create checkpoints at every
        decision point, major file change, and tool call.
        """
        recorder = get_replay_recorder()
        session = recorder.load_session(session_id)
        if not session:
            logger.error(f"Session not found: {session_id}")
            return []

        checkpoints: list[Checkpoint] = []
        conversation_history: list[dict[str, Any]] = []

        for step in session.steps:
            msg = _step_to_conversation_message(step)
            if msg:
                conversation_history.append(msg)

            cp_type = _CHECKPOINT_STEP_TYPES.get(step.step_type)
            if cp_type is None:
                continue

            checkpoint = Checkpoint(
                session_id=session_id,
                step_index=step.step_index,
                step_id=step.id,
                checkpoint_type=cp_type,
                label=step.label,
                description=step.description,
                created_at=time.time(),
                conversation_history=[dict(m) for m in conversation_history],
                file_snapshots=_collect_file_state(
                    session.steps[: step.step_index + 1]
                ),
                tokens_at_checkpoint=step.cumulative_tokens,
                cost_at_checkpoint=step.cumulative_cost_usd,
            )
            checkpoints.append(checkpoint)

        self._save_checkpoints(session_id, checkpoints)
        logger.info(f"Created {len(checkpoints)} checkpoints for session {session_id}")
        return checkpoints

    def get_checkpoints(self, session_id: str) -> list[Checkpoint]:
        """Load all checkpoints for a session."""
        return self._load_checkpoints(session_id)

    def get_checkpoint(self, session_id: str, checkpoint_id: str) -> Checkpoint | None:
        """Load a specific checkpoint."""
        checkpoints = self._load_checkpoints(session_id)
        return next((cp for cp in checkpoints if cp.id == checkpoint_id), None)

    def add_manual_checkpoint(
        self,
        session_id: str,
        step_index: int,
        label: str = "",
        description: str = "",
    ) -> Checkpoint | None:
        """Add a manual checkpoint at a specific step."""
        recorder = get_replay_recorder()
        session = recorder.load_session(session_id)
        if not session or step_index < 0 or step_index >= len(session.steps):
            return None

        step = session.steps[step_index]

        conversation_history: list[dict[str, Any]] = []
        for s in session.steps[: step_index + 1]:
            msg = _step_to_conversation_message(s)
            if msg:
                conversation_history.append(msg)

        checkpoint = Checkpoint(
            session_id=session_id,
            step_index=step_index,
            step_id=step.id,
            checkpoint_type=CheckpointType.MANUAL,
            label=label or step.label,
            description=description or step.description,
            created_at=time.time(),
            conversation_history=conversation_history,
            file_snapshots=_collect_file_state(session.steps[: step_index + 1]),
            tokens_at_checkpoint=step.cumulative_tokens,
            cost_at_checkpoint=step.cumulative_cost_usd,
        )

        checkpoints = self._load_checkpoints(session_id)
        checkpoints.append(checkpoint)
        checkpoints.sort(key=lambda c: c.step_index)
        self._save_checkpoints(session_id, checkpoints)
        return checkpoint

    def delete_checkpoint(self, session_id: str, checkpoint_id: str) -> bool:
        """Delete a checkpoint."""
        checkpoints = self._load_checkpoints(session_id)
        before = len(checkpoints)
        checkpoints = [cp for cp in checkpoints if cp.id != checkpoint_id]
        if len(checkpoints) == before:
            return False
        self._save_checkpoints(session_id, checkpoints)
        return True

    # -------------------------------------------------------------------
    # Fork & Re-execute
    # -------------------------------------------------------------------

    def create_fork(self, request: ForkRequest) -> ForkSession:
        """
        Create a fork from a checkpoint. The fork produces a provider-agnostic
        conversation history that can be sent to ANY LLM provider.
        """
        fork_session = ForkSession(
            original_session_id=request.session_id,
            checkpoint_id=request.checkpoint_id,
            fork_request=request,
            forked_session_id=str(uuid.uuid4()),
            created_at=time.time(),
            status="pending",
        )
        self._save_fork(fork_session)
        logger.info(
            f"Fork created: {fork_session.fork_id} "
            f"(from session {request.session_id} at checkpoint {request.checkpoint_id})"
        )
        return fork_session

    def get_fork_context(self, fork_id: str) -> dict[str, Any] | None:
        """
        Build the full context needed to re-execute a fork.

        Returns a provider-agnostic payload that can be consumed by any
        LLM client (Anthropic, OpenAI, Google, Ollama, etc.).
        """
        fork = self._load_fork(fork_id)
        if not fork:
            return None

        checkpoint = self.get_checkpoint(fork.original_session_id, fork.checkpoint_id)
        if not checkpoint:
            return None

        return {
            "fork_id": fork.fork_id,
            "original_session_id": fork.original_session_id,
            "forked_session_id": fork.forked_session_id,
            "checkpoint_step_index": checkpoint.step_index,
            "conversation_history": checkpoint.conversation_history,
            "file_snapshots": checkpoint.file_snapshots,
            "modified_prompt": fork.fork_request.modified_prompt,
            "additional_instructions": fork.fork_request.additional_instructions,
            "provider": fork.fork_request.fork_provider,
            "model": fork.fork_request.fork_model,
            "api_key": fork.fork_request.fork_api_key,
            "base_url": fork.fork_request.fork_base_url,
        }

    def update_fork_status(self, fork_id: str, status: str) -> bool:
        """Update the status of a fork."""
        fork = self._load_fork(fork_id)
        if not fork:
            return False
        fork.status = status
        self._save_fork(fork)
        return True

    def list_forks(self, session_id: str | None = None) -> list[ForkSession]:
        """List all forks, optionally filtered by original session."""
        forks: list[ForkSession] = []
        for filepath in self._forks_dir.glob("*.json"):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                fork = ForkSession.from_dict(data)
                if session_id is None or fork.original_session_id == session_id:
                    forks.append(fork)
            except Exception as e:
                logger.warning(f"Failed to load fork {filepath}: {e}")
        return sorted(forks, key=lambda f: f.created_at, reverse=True)

    def get_fork(self, fork_id: str) -> ForkSession | None:
        """Get a specific fork."""
        return self._load_fork(fork_id)

    def delete_fork(self, fork_id: str) -> bool:
        """Delete a fork."""
        filepath = self._forks_dir / f"{fork_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    # -------------------------------------------------------------------
    # Decision Scoring
    # -------------------------------------------------------------------

    def score_decisions(self, session_id: str) -> list[DecisionScore]:
        """
        Analyze a session and score each decision point by confidence and impact.

        Heuristics:
        - Thinking duration (longer = less confident)
        - Number of options considered (more = harder decision)
        - Whether the decision led to errors later
        - File change magnitude after the decision
        - Token cost after the decision
        """
        recorder = get_replay_recorder()
        session = recorder.load_session(session_id)
        if not session:
            return []

        decision_steps = [
            (i, s)
            for i, s in enumerate(session.steps)
            if s.step_type == ReplayStepType.DECISION
        ]

        scores: list[DecisionScore] = []
        for i, (step_idx, step) in enumerate(decision_steps):
            steps_after = self._get_steps_after_decision(
                session, decision_steps, i, step_idx
            )
            score = self._score_single_decision(step, steps_after)
            scores.append(score)

        self._save_decision_scores(session_id, scores)
        return scores

    def _get_steps_after_decision(self, session, decision_steps, current_idx, step_idx):
        """Get the steps that occurred after a decision until the next decision."""
        next_decision_idx = (
            decision_steps[current_idx + 1][0]
            if current_idx + 1 < len(decision_steps)
            else len(session.steps)
        )
        return session.steps[step_idx + 1 : next_decision_idx]

    def _score_single_decision(self, step, steps_after):
        """Score a single decision point based on various factors."""
        factors: list[str] = []
        confidence = 0.5
        impact = 0.5

        confidence, factors = self._apply_duration_scoring(step, confidence, factors)
        confidence, factors = self._apply_options_scoring(step, confidence, factors)
        confidence, impact, factors = self._apply_error_scoring(
            steps_after, confidence, impact, factors
        )
        confidence, impact, factors = self._apply_file_change_scoring(
            steps_after, confidence, impact, factors
        )
        confidence, impact, factors = self._apply_token_scoring(
            steps_after, confidence, impact, factors
        )

        confidence = max(0.0, min(1.0, confidence))
        impact = max(0.0, min(1.0, impact))

        return DecisionScore(
            step_id=step.id,
            step_index=step.step_index,
            confidence_score=round(confidence, 3),
            impact_score=round(impact, 3),
            factors=factors,
            is_critical=impact >= 0.7 or confidence <= 0.3,
        )

    def _apply_duration_scoring(self, step, confidence, factors):
        """Apply scoring based on decision duration."""
        if step.duration_ms > 0:
            if step.duration_ms < 500:
                confidence += 0.2
                factors.append("Quick decision (high confidence)")
            elif step.duration_ms > 5000:
                confidence -= 0.2
                factors.append("Long deliberation (lower confidence)")
        return confidence, factors

    def _apply_options_scoring(self, step, confidence, factors):
        """Apply scoring based on number of options considered."""
        num_options = len(step.options_considered)
        if num_options <= 1:
            confidence += 0.15
            factors.append("Single clear option")
        elif num_options >= 4:
            confidence -= 0.15
            factors.append(f"Many options considered ({num_options})")
        return confidence, factors

    def _apply_error_scoring(self, steps_after, confidence, impact, factors):
        """Apply scoring based on errors that occurred after the decision."""
        errors_after = sum(
            1 for s in steps_after if s.step_type == ReplayStepType.ERROR
        )
        if errors_after > 0:
            confidence -= 0.15 * min(errors_after, 3)
            impact += 0.2
            factors.append(f"Followed by {errors_after} error(s)")
        return confidence, impact, factors

    def _apply_file_change_scoring(self, steps_after, confidence, impact, factors):
        """Apply scoring based on file changes that occurred after the decision."""
        file_changes_after = sum(
            len(s.file_diffs)
            for s in steps_after
            if s.step_type
            in (
                ReplayStepType.FILE_CREATE,
                ReplayStepType.FILE_UPDATE,
                ReplayStepType.FILE_DELETE,
            )
        )
        if file_changes_after > 5:
            impact += 0.2
            factors.append(f"Led to {file_changes_after} file changes")
        elif file_changes_after == 0:
            impact -= 0.1
            factors.append("No file changes followed")
        return confidence, impact, factors

    def _apply_token_scoring(self, steps_after, confidence, impact, factors):
        """Apply scoring based on token cost after the decision."""
        tokens_after = sum(s.input_tokens + s.output_tokens for s in steps_after)
        if tokens_after > 10000:
            impact += 0.15
            factors.append(f"High token cost after ({tokens_after})")
        return confidence, impact, factors

    def get_decision_scores(self, session_id: str) -> list[DecisionScore]:
        """Load decision scores for a session."""
        return self._load_decision_scores(session_id)

    # -------------------------------------------------------------------
    # Decision Heatmap
    # -------------------------------------------------------------------

    def get_decision_heatmap(self, session_id: str) -> dict[str, Any]:
        """Build a decision heatmap showing file impact and scoring overview."""
        recorder = get_replay_recorder()
        session = recorder.load_session(session_id)
        if not session:
            return {}

        scores = self._load_decision_scores(session_id)
        if not scores:
            scores = self.score_decisions(session_id)

        file_impact: dict[str, float] = {}
        for score in scores:
            step_idx = score.step_index
            for s in session.steps[step_idx : step_idx + 10]:
                for diff in s.file_diffs:
                    current = file_impact.get(diff.file_path, 0.0)
                    file_impact[diff.file_path] = current + score.impact_score

        sorted_files = sorted(file_impact.items(), key=lambda x: x[1], reverse=True)
        max_impact = sorted_files[0][1] if sorted_files else 1.0

        return {
            "session_id": session_id,
            "decision_count": len(scores),
            "critical_decisions": sum(1 for s in scores if s.is_critical),
            "avg_confidence": round(
                sum(s.confidence_score for s in scores) / max(len(scores), 1), 3
            ),
            "avg_impact": round(
                sum(s.impact_score for s in scores) / max(len(scores), 1), 3
            ),
            "file_impact": [
                {
                    "file_path": fp,
                    "impact_score": round(imp, 3),
                    "intensity": round(imp / max_impact, 3) if max_impact > 0 else 0,
                }
                for fp, imp in sorted_files[:50]
            ],
            "scores": [s.to_dict() for s in scores],
        }

    # -------------------------------------------------------------------
    # Persistence helpers
    # -------------------------------------------------------------------

    def _save_checkpoints(self, session_id: str, checkpoints: list[Checkpoint]) -> None:
        filepath = self._checkpoints_dir / f"{session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                [cp.to_dict() for cp in checkpoints], f, indent=2, ensure_ascii=False
            )

    def _load_checkpoints(self, session_id: str) -> list[Checkpoint]:
        filepath = self._checkpoints_dir / f"{session_id}.json"
        if not filepath.exists():
            return []
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return [Checkpoint.from_dict(d) for d in data]
        except Exception as e:
            logger.error(f"Failed to load checkpoints for {session_id}: {e}")
            return []

    def _save_fork(self, fork: ForkSession) -> None:
        filepath = self._forks_dir / f"{fork.fork_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(fork.to_dict(), f, indent=2, ensure_ascii=False)

    def _load_fork(self, fork_id: str) -> ForkSession | None:
        filepath = self._forks_dir / f"{fork_id}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return ForkSession.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load fork {fork_id}: {e}")
            return None

    def _save_decision_scores(
        self, session_id: str, scores: list[DecisionScore]
    ) -> None:
        filepath = self._storage_dir / f"scores_{session_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([s.to_dict() for s in scores], f, indent=2, ensure_ascii=False)

    def _load_decision_scores(self, session_id: str) -> list[DecisionScore]:
        filepath = self._storage_dir / f"scores_{session_id}.json"
        if not filepath.exists():
            return []
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return [DecisionScore.from_dict(d) for d in data]
        except Exception as e:
            logger.error(f"Failed to load scores for {session_id}: {e}")
            return []


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _step_to_conversation_message(step: ReplayStep) -> dict[str, Any] | None:
    """
    Convert a replay step into a provider-agnostic conversation message.

    Returns a dict with 'role' and 'content' that can be adapted to any
    LLM provider's message format (OpenAI, Anthropic, Google, etc.).
    """
    if step.step_type == ReplayStepType.SESSION_START:
        return {
            "role": "system",
            "content": f"Session started: {step.description}",
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type == ReplayStepType.AGENT_THINKING:
        return {
            "role": "assistant_thinking",
            "content": step.reasoning or step.description,
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type == ReplayStepType.AGENT_RESPONSE:
        return {
            "role": "assistant",
            "content": step.description,
            "step_type": step.step_type.value,
            "step_index": step.step_index,
            "tokens": {
                "input": step.input_tokens,
                "output": step.output_tokens,
            },
        }
    elif step.step_type == ReplayStepType.TOOL_CALL:
        return {
            "role": "assistant",
            "content": f"[Tool call: {step.tool_name}]",
            "tool_call": {
                "name": step.tool_name,
                "input": step.tool_input,
            },
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type == ReplayStepType.TOOL_RESULT:
        return {
            "role": "tool",
            "content": step.tool_output or "",
            "tool_name": step.tool_name,
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type == ReplayStepType.DECISION:
        return {
            "role": "assistant",
            "content": f"[Decision: {step.description}] Chose: {step.chosen_option}",
            "decision": {
                "options": step.options_considered,
                "chosen": step.chosen_option,
                "reasoning": step.reasoning,
            },
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type in (
        ReplayStepType.FILE_CREATE,
        ReplayStepType.FILE_UPDATE,
        ReplayStepType.FILE_DELETE,
    ):
        return {
            "role": "assistant",
            "content": f"[File {step.step_type.value}: {step.description}]",
            "file_changes": [d.to_dict() for d in step.file_diffs],
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type in (ReplayStepType.COMMAND_RUN, ReplayStepType.COMMAND_OUTPUT):
        return {
            "role": "assistant"
            if step.step_type == ReplayStepType.COMMAND_RUN
            else "tool",
            "content": step.description,
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    elif step.step_type == ReplayStepType.ERROR:
        return {
            "role": "system",
            "content": f"Error: {step.description}",
            "step_type": step.step_type.value,
            "step_index": step.step_index,
        }
    return None


def _collect_file_state(steps: list[ReplayStep]) -> dict[str, str]:
    """
    Reconstruct file states by replaying file diffs from the beginning.
    """
    file_state: dict[str, str] = {}
    for step in steps:
        for diff in step.file_diffs:
            if diff.operation == "delete":
                file_state.pop(diff.file_path, None)
            elif diff.after_content:
                file_state[diff.file_path] = diff.after_content
    return file_state


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_time_travel_engine: TimeTravelEngine | None = None


def get_time_travel_engine() -> TimeTravelEngine:
    """Get or create the global time travel engine instance."""
    global _time_travel_engine
    if _time_travel_engine is None:
        _time_travel_engine = TimeTravelEngine()
    return _time_travel_engine

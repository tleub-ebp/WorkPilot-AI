"""Pair Programming Agent — Interactive step-by-step coding with user validation.

Instead of full-autonomous mode, the agent proposes a plan, then codes
file-by-file with real-time preview, awaiting user approval at each step.
The user can guide the agent via inline comments and suggestions.

Feature 2.3 — Mode "Pair Programming" interactif.

Extends the existing Claude Teams collaborative mode with a user-in-the-loop
workflow where every step requires explicit validation.

Example:
    >>> from apps.backend.agents.pair_programming import PairProgrammingSession
    >>> session = PairProgrammingSession(project_id="proj-1", task="Add login page")
    >>> plan = session.propose_plan()
    >>> session.approve_step(0)  # approve first step
    >>> preview = session.preview_step(1)  # preview code for step 1
    >>> session.add_user_comment(1, "Use bcrypt instead of md5")
    >>> session.approve_step(1, modified=True)
"""

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StepStatus(str, Enum):
    """Status of a pair programming step."""
    PROPOSED = "proposed"
    PREVIEWING = "previewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class StepType(str, Enum):
    """Type of pair programming step."""
    PLAN = "plan"
    CODE = "code"
    TEST = "test"
    REFACTOR = "refactor"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    CONFIG = "config"
    COMMAND = "command"


class SessionMode(str, Enum):
    """Pair programming interaction modes."""
    STEP_BY_STEP = "step_by_step"
    SUGGESTION = "suggestion"
    GUIDED = "guided"


class SuggestionStatus(str, Enum):
    """Status of a real-time code suggestion."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class UserComment:
    """An inline comment from the user to guide the agent.

    Attributes:
        comment_id: Unique identifier.
        step_index: Which step this comment applies to.
        content: The comment text.
        line_number: Optional line reference in the code preview.
        timestamp: When the comment was made.
    """
    comment_id: str
    step_index: int
    content: str
    line_number: int | None = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "UserComment":
        return cls(**data)


@dataclass
class CodeSuggestion:
    """A real-time code suggestion from the agent (like a live code review).

    Attributes:
        suggestion_id: Unique identifier.
        file_path: The file being modified.
        line_start: Starting line of the suggestion.
        line_end: Ending line.
        original_code: The original code snippet.
        suggested_code: The suggested replacement.
        explanation: Why this change is suggested.
        status: Whether the user accepted/rejected.
    """
    suggestion_id: str
    file_path: str
    line_start: int = 0
    line_end: int = 0
    original_code: str = ""
    suggested_code: str = ""
    explanation: str = ""
    status: SuggestionStatus = SuggestionStatus.PENDING

    def to_dict(self) -> dict:
        return {
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "original_code": self.original_code,
            "suggested_code": self.suggested_code,
            "explanation": self.explanation,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CodeSuggestion":
        data["status"] = SuggestionStatus(data.get("status", "pending"))
        return cls(**data)


@dataclass
class PlanStep:
    """A single step in the pair programming plan.

    Attributes:
        index: Step position in the plan.
        step_type: Type of step.
        title: Short title.
        description: Detailed description of what will be done.
        file_path: Target file (if applicable).
        code_preview: Generated code preview (populated on preview/execute).
        status: Current step status.
        user_comments: Comments from the user.
        suggestions: Code suggestions for this step.
        metadata: Additional context.
    """
    index: int
    step_type: StepType
    title: str
    description: str = ""
    file_path: str = ""
    code_preview: str = ""
    status: StepStatus = StepStatus.PROPOSED
    user_comments: list[UserComment] = field(default_factory=list)
    suggestions: list[CodeSuggestion] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "step_type": self.step_type.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "code_preview": self.code_preview,
            "status": self.status.value,
            "user_comments": [c.to_dict() for c in self.user_comments],
            "suggestions": [s.to_dict() for s in self.suggestions],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PlanStep":
        data["step_type"] = StepType(data["step_type"])
        data["status"] = StepStatus(data["status"])
        comments = [UserComment.from_dict(c) for c in data.pop("user_comments", [])]
        suggestions = [CodeSuggestion.from_dict(s) for s in data.pop("suggestions", [])]
        step = cls(**data)
        step.user_comments = comments
        step.suggestions = suggestions
        return step


@dataclass
class PairProgrammingPlan:
    """The overall pair programming plan with steps.

    Attributes:
        task: The task description.
        steps: Ordered list of plan steps.
        created_at: When the plan was created.
        approved: Whether the overall plan was approved.
    """
    task: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: str = ""
    approved: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)

    @property
    def progress_pct(self) -> float:
        if not self.steps:
            return 0.0
        return round(self.completed_steps / self.total_steps * 100, 1)

    def to_dict(self) -> dict:
        return {
            "task": self.task,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
            "approved": self.approved,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "progress_pct": self.progress_pct,
        }


# ---------------------------------------------------------------------------
# Main session class
# ---------------------------------------------------------------------------

class PairProgrammingSession:
    """Interactive pair programming session with user-in-the-loop.

    The agent proposes a plan, then the user approves/modifies/rejects each
    step.  The agent generates code previews, and the user can add inline
    comments to guide the implementation.  Supports real-time suggestions
    (like a live code review).
    """

    def __init__(
        self,
        project_id: str,
        task: str,
        mode: str = "step_by_step",
        llm_provider: Any | None = None,
    ) -> None:
        self.project_id = project_id
        self.task = task
        self.mode = SessionMode(mode) if mode in [m.value for m in SessionMode] else SessionMode.STEP_BY_STEP
        self.llm_provider = llm_provider

        self.session_id = f"pair_{int(time.time())}"
        self.plan: PairProgrammingPlan | None = None
        self._comment_counter = 0
        self._suggestion_counter = 0
        self._event_log: list[dict[str, Any]] = []

        self.started_at = datetime.now(timezone.utc).isoformat()
        self.ended_at: str | None = None

        logger.info("PairProgrammingSession %s started (mode=%s)", self.session_id, self.mode.value)
        self._log_event("session_started", {"task": task, "mode": self.mode.value})

    # -- Plan management -----------------------------------------------------

    def propose_plan(
        self,
        steps: list[dict[str, Any]] | None = None,
    ) -> PairProgrammingPlan:
        """Propose a plan for the task.

        If steps are provided, use them directly.  Otherwise generate a
        default plan from the task description.

        Args:
            steps: Optional list of step dicts with keys:
                   step_type, title, description, file_path.

        Returns:
            The proposed PairProgrammingPlan.
        """
        if steps:
            plan_steps = []
            for i, s in enumerate(steps):
                step_type = StepType(s.get("step_type", "code"))
                plan_steps.append(PlanStep(
                    index=i,
                    step_type=step_type,
                    title=s.get("title", f"Step {i + 1}"),
                    description=s.get("description", ""),
                    file_path=s.get("file_path", ""),
                ))
        else:
            plan_steps = self._generate_default_plan()

        self.plan = PairProgrammingPlan(task=self.task, steps=plan_steps)
        self._log_event("plan_proposed", {"step_count": len(plan_steps)})
        return self.plan

    def approve_plan(self) -> bool:
        """Approve the overall plan. Required before executing steps.

        Returns:
            True if plan was approved, False if no plan exists.
        """
        if not self.plan:
            return False
        self.plan.approved = True
        self._log_event("plan_approved", {})
        return True

    def modify_plan(
        self,
        add_steps: list[dict[str, Any]] | None = None,
        remove_indices: list[int] | None = None,
        reorder: list[int] | None = None,
    ) -> PairProgrammingPlan | None:
        """Modify the plan by adding, removing, or reordering steps.

        Args:
            add_steps: Steps to add at the end.
            remove_indices: Step indices to remove.
            reorder: New order of step indices.

        Returns:
            The modified plan, or None if no plan.
        """
        if not self.plan:
            return None

        # Remove steps
        if remove_indices:
            self.plan.steps = [
                s for s in self.plan.steps if s.index not in remove_indices
            ]

        # Reorder
        if reorder:
            step_map = {s.index: s for s in self.plan.steps}
            new_steps = []
            for new_idx, old_idx in enumerate(reorder):
                if old_idx in step_map:
                    step = step_map[old_idx]
                    step.index = new_idx
                    new_steps.append(step)
            self.plan.steps = new_steps

        # Add steps
        if add_steps:
            start_idx = len(self.plan.steps)
            for i, s in enumerate(add_steps):
                step_type = StepType(s.get("step_type", "code"))
                self.plan.steps.append(PlanStep(
                    index=start_idx + i,
                    step_type=step_type,
                    title=s.get("title", f"Step {start_idx + i + 1}"),
                    description=s.get("description", ""),
                    file_path=s.get("file_path", ""),
                ))

        # Re-index
        for i, step in enumerate(self.plan.steps):
            step.index = i

        self._log_event("plan_modified", {
            "added": len(add_steps) if add_steps else 0,
            "removed": len(remove_indices) if remove_indices else 0,
        })
        return self.plan

    # -- Step execution ------------------------------------------------------

    def preview_step(self, step_index: int) -> PlanStep | None:
        """Generate a code preview for a step.

        Sets the step status to ``previewing`` and populates ``code_preview``.

        Args:
            step_index: Index of the step to preview.

        Returns:
            The step with populated code_preview, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        step.status = StepStatus.PREVIEWING

        # Generate preview based on step type and user comments
        comments_context = "\n".join(
            f"  - [{c.comment_id}] {c.content}" for c in step.user_comments
        )
        step.code_preview = self._generate_preview(step, comments_context)

        self._log_event("step_previewed", {"index": step_index})
        return step

    def approve_step(
        self,
        step_index: int,
        modified: bool = False,
    ) -> PlanStep | None:
        """Approve a step, allowing it to be executed.

        Args:
            step_index: Index of the step to approve.
            modified: True if the user made modifications before approving.

        Returns:
            The approved step, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        step.status = StepStatus.MODIFIED if modified else StepStatus.APPROVED
        self._log_event("step_approved", {"index": step_index, "modified": modified})
        return step

    def reject_step(
        self,
        step_index: int,
        reason: str = "",
    ) -> PlanStep | None:
        """Reject a step.

        Args:
            step_index: Index of the step to reject.
            reason: Reason for rejection.

        Returns:
            The rejected step, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        step.status = StepStatus.REJECTED
        step.metadata["rejection_reason"] = reason
        self._log_event("step_rejected", {"index": step_index, "reason": reason})
        return step

    def skip_step(self, step_index: int) -> PlanStep | None:
        """Skip a step.

        Args:
            step_index: Index of the step to skip.

        Returns:
            The skipped step, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        step.status = StepStatus.SKIPPED
        self._log_event("step_skipped", {"index": step_index})
        return step

    def complete_step(self, step_index: int) -> PlanStep | None:
        """Mark a step as completed after execution.

        Args:
            step_index: Index of the completed step.

        Returns:
            The completed step, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        step.status = StepStatus.COMPLETED
        self._log_event("step_completed", {"index": step_index})
        return step

    # -- User interaction ----------------------------------------------------

    def add_user_comment(
        self,
        step_index: int,
        content: str,
        line_number: int | None = None,
    ) -> UserComment | None:
        """Add a user comment/guidance to a step.

        Args:
            step_index: Which step to comment on.
            content: The comment text.
            line_number: Optional line number reference.

        Returns:
            The created UserComment, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        self._comment_counter += 1
        comment = UserComment(
            comment_id=f"comment_{self._comment_counter}",
            step_index=step_index,
            content=content,
            line_number=line_number,
        )
        step.user_comments.append(comment)
        self._log_event("comment_added", {"step": step_index, "content": content[:100]})
        return comment

    def add_suggestion(
        self,
        step_index: int,
        file_path: str,
        line_start: int,
        line_end: int,
        original_code: str,
        suggested_code: str,
        explanation: str = "",
    ) -> CodeSuggestion | None:
        """Add a code suggestion (like a live code review comment).

        Args:
            step_index: Which step.
            file_path: Target file.
            line_start: Start line.
            line_end: End line.
            original_code: Current code.
            suggested_code: Suggested replacement.
            explanation: Why this is suggested.

        Returns:
            The created CodeSuggestion, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        self._suggestion_counter += 1
        suggestion = CodeSuggestion(
            suggestion_id=f"sug_{self._suggestion_counter}",
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            original_code=original_code,
            suggested_code=suggested_code,
            explanation=explanation,
        )
        step.suggestions.append(suggestion)
        self._log_event("suggestion_added", {"step": step_index, "file": file_path})
        return suggestion

    def respond_to_suggestion(
        self,
        step_index: int,
        suggestion_id: str,
        action: str = "accepted",
    ) -> CodeSuggestion | None:
        """Accept or reject a suggestion.

        Args:
            step_index: Which step.
            suggestion_id: ID of the suggestion.
            action: accepted, rejected, or modified.

        Returns:
            The updated CodeSuggestion, or None.
        """
        step = self._get_step(step_index)
        if not step:
            return None

        for sug in step.suggestions:
            if sug.suggestion_id == suggestion_id:
                sug.status = SuggestionStatus(action) if action in [s.value for s in SuggestionStatus] else SuggestionStatus.ACCEPTED
                self._log_event("suggestion_responded", {
                    "step": step_index, "suggestion": suggestion_id, "action": action
                })
                return sug
        return None

    # -- Session lifecycle ---------------------------------------------------

    def get_progress(self) -> dict[str, Any]:
        """Get current session progress.

        Returns:
            Dict with progress metrics.
        """
        if not self.plan:
            return {"status": "no_plan", "progress_pct": 0.0}

        return {
            "session_id": self.session_id,
            "task": self.task,
            "mode": self.mode.value,
            "plan_approved": self.plan.approved,
            "total_steps": self.plan.total_steps,
            "completed_steps": self.plan.completed_steps,
            "progress_pct": self.plan.progress_pct,
            "steps_by_status": self._count_steps_by_status(),
            "total_comments": sum(len(s.user_comments) for s in self.plan.steps),
            "total_suggestions": sum(len(s.suggestions) for s in self.plan.steps),
        }

    def end_session(self) -> dict[str, Any]:
        """End the pair programming session.

        Returns:
            Summary of the session.
        """
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self._log_event("session_ended", {})
        return {
            "session_id": self.session_id,
            "task": self.task,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "progress": self.get_progress(),
            "event_count": len(self._event_log),
        }

    def get_event_log(self) -> list[dict[str, Any]]:
        """Get the full event log for the session."""
        return list(self._event_log)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full session state."""
        return {
            "session_id": self.session_id,
            "project_id": self.project_id,
            "task": self.task,
            "mode": self.mode.value,
            "plan": self.plan.to_dict() if self.plan else None,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "event_log": self._event_log,
        }

    # -- Helpers -------------------------------------------------------------

    def _get_step(self, index: int) -> PlanStep | None:
        """Get a step by index."""
        if not self.plan:
            return None
        for step in self.plan.steps:
            if step.index == index:
                return step
        return None

    def _count_steps_by_status(self) -> dict[str, int]:
        """Count steps grouped by status."""
        if not self.plan:
            return {}
        counts: dict[str, int] = {}
        for step in self.plan.steps:
            key = step.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _generate_default_plan(self) -> list[PlanStep]:
        """Generate a default plan from the task description."""
        return [
            PlanStep(index=0, step_type=StepType.PLAN, title="Analyze requirements",
                     description=f"Analyze the task: {self.task}"),
            PlanStep(index=1, step_type=StepType.CODE, title="Implement solution",
                     description="Write the main implementation code"),
            PlanStep(index=2, step_type=StepType.TEST, title="Write tests",
                     description="Create unit tests for the implementation"),
            PlanStep(index=3, step_type=StepType.REVIEW, title="Review code",
                     description="Review the implementation for quality"),
        ]

    def _generate_preview(self, step: PlanStep, comments_context: str) -> str:
        """Generate a code preview for a step.

        If an LLM provider is configured, delegates to it.
        Otherwise returns a placeholder.
        """
        preview_lines = [
            f"# Preview for: {step.title}",
            f"# File: {step.file_path or 'TBD'}",
            f"# Type: {step.step_type.value}",
            "",
        ]

        if comments_context:
            preview_lines.append("# User guidance:")
            for line in comments_context.splitlines():
                preview_lines.append(f"# {line}")
            preview_lines.append("")

        preview_lines.append(f"# TODO: Implementation for '{step.description}'")
        preview_lines.append("pass")

        return "\n".join(preview_lines)

    def _log_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Log an event to the session event log."""
        self._event_log.append({
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **data,
        })

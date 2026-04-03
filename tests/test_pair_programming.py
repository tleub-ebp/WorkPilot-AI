"""Tests for Feature 2.3 — Mode "Pair Programming" interactif.

Tests for PairProgrammingSession, PlanStep, UserComment, CodeSuggestion,
PairProgrammingPlan, and all interactive workflows.

40 tests total:
- UserComment: 2
- CodeSuggestion: 2
- PlanStep: 3
- PairProgrammingPlan: 3
- PairProgrammingSession — plan management: 6
- PairProgrammingSession — step execution: 7
- PairProgrammingSession — user interaction: 6
- PairProgrammingSession — suggestions: 4
- PairProgrammingSession — progress & lifecycle: 4
- PairProgrammingSession — serialization: 3
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from apps.backend.agents.pair_programming import (
    CodeSuggestion,
    PairProgrammingPlan,
    PairProgrammingSession,
    PlanStep,
    SessionMode,
    StepStatus,
    StepType,
    SuggestionStatus,
    UserComment,
)

# -----------------------------------------------------------------------
# UserComment
# -----------------------------------------------------------------------

class TestUserComment:
    def test_create_comment(self):
        comment = UserComment(
            comment_id="c1", step_index=0,
            content="Use bcrypt instead of md5",
        )
        assert comment.content == "Use bcrypt instead of md5"
        assert comment.timestamp != ""

    def test_comment_to_dict(self):
        comment = UserComment(comment_id="c1", step_index=1, content="fix this")
        d = comment.to_dict()
        assert d["comment_id"] == "c1"
        assert d["step_index"] == 1


# -----------------------------------------------------------------------
# CodeSuggestion
# -----------------------------------------------------------------------

class TestCodeSuggestion:
    def test_create_suggestion(self):
        sug = CodeSuggestion(
            suggestion_id="s1", file_path="f.py",
            line_start=10, line_end=15,
            original_code="old", suggested_code="new",
            explanation="Better approach",
        )
        assert sug.status == SuggestionStatus.PENDING
        assert sug.explanation == "Better approach"

    def test_suggestion_to_dict(self):
        sug = CodeSuggestion(suggestion_id="s1", file_path="f.py")
        d = sug.to_dict()
        assert d["status"] == "pending"


# -----------------------------------------------------------------------
# PlanStep
# -----------------------------------------------------------------------

class TestPlanStep:
    def test_create_step(self):
        step = PlanStep(
            index=0, step_type=StepType.CODE,
            title="Implement login", file_path="src/login.py",
        )
        assert step.step_type == StepType.CODE
        assert step.status == StepStatus.PROPOSED

    def test_step_to_dict(self):
        step = PlanStep(index=0, step_type=StepType.TEST, title="Write tests")
        d = step.to_dict()
        assert d["step_type"] == "test"
        assert d["status"] == "proposed"
        assert d["user_comments"] == []

    def test_step_from_dict(self):
        d = {
            "index": 0, "step_type": "code", "title": "T",
            "description": "D", "file_path": "f.py",
            "code_preview": "", "status": "approved",
            "user_comments": [], "suggestions": [],
            "metadata": {},
        }
        step = PlanStep.from_dict(d)
        assert step.step_type == StepType.CODE
        assert step.status == StepStatus.APPROVED


# -----------------------------------------------------------------------
# PairProgrammingPlan
# -----------------------------------------------------------------------

class TestPairProgrammingPlan:
    def test_create_plan(self):
        plan = PairProgrammingPlan(
            task="Add login",
            steps=[
                PlanStep(index=0, step_type=StepType.PLAN, title="Plan"),
                PlanStep(index=1, step_type=StepType.CODE, title="Code"),
            ],
        )
        assert plan.total_steps == 2
        assert plan.completed_steps == 0

    def test_plan_progress(self):
        plan = PairProgrammingPlan(
            task="T",
            steps=[
                PlanStep(index=0, step_type=StepType.CODE, title="S1", status=StepStatus.COMPLETED),
                PlanStep(index=1, step_type=StepType.CODE, title="S2"),
            ],
        )
        assert plan.progress_pct == 50.0

    def test_plan_to_dict(self):
        plan = PairProgrammingPlan(task="T", steps=[])
        d = plan.to_dict()
        assert d["task"] == "T"
        assert d["total_steps"] == 0
        assert d["progress_pct"] == 0.0


# -----------------------------------------------------------------------
# PairProgrammingSession — plan management
# -----------------------------------------------------------------------

class TestSessionPlanManagement:
    def setup_method(self):
        self.session = PairProgrammingSession(
            project_id="p1", task="Add login page",
        )

    def test_propose_plan_default(self):
        plan = self.session.propose_plan()
        assert plan is not None
        assert plan.total_steps >= 2

    def test_propose_plan_custom_steps(self):
        plan = self.session.propose_plan(steps=[
            {"step_type": "code", "title": "Write component", "file_path": "src/Login.tsx"},
            {"step_type": "test", "title": "Write tests"},
        ])
        assert plan.total_steps == 2
        assert plan.steps[0].step_type == StepType.CODE

    def test_approve_plan(self):
        self.session.propose_plan()
        result = self.session.approve_plan()
        assert result is True
        assert self.session.plan.approved is True

    def test_approve_plan_no_plan(self):
        result = self.session.approve_plan()
        assert result is False

    def test_modify_plan_add_steps(self):
        self.session.propose_plan(steps=[
            {"step_type": "code", "title": "Step 1"},
        ])
        modified = self.session.modify_plan(add_steps=[
            {"step_type": "test", "title": "Step 2"},
        ])
        assert modified.total_steps == 2

    def test_modify_plan_remove_steps(self):
        self.session.propose_plan(steps=[
            {"step_type": "code", "title": "Step A"},
            {"step_type": "test", "title": "Step B"},
            {"step_type": "review", "title": "Step C"},
        ])
        modified = self.session.modify_plan(remove_indices=[1])
        assert modified.total_steps == 2


# -----------------------------------------------------------------------
# PairProgrammingSession — step execution
# -----------------------------------------------------------------------

class TestSessionStepExecution:
    def setup_method(self):
        self.session = PairProgrammingSession(project_id="p1", task="T")
        self.session.propose_plan(steps=[
            {"step_type": "plan", "title": "Analyze"},
            {"step_type": "code", "title": "Implement"},
            {"step_type": "test", "title": "Test"},
        ])

    def test_preview_step(self):
        step = self.session.preview_step(0)
        assert step is not None
        assert step.status == StepStatus.PREVIEWING
        assert step.code_preview != ""

    def test_preview_step_not_found(self):
        result = self.session.preview_step(99)
        assert result is None

    def test_approve_step(self):
        step = self.session.approve_step(0)
        assert step.status == StepStatus.APPROVED

    def test_approve_step_modified(self):
        step = self.session.approve_step(0, modified=True)
        assert step.status == StepStatus.MODIFIED

    def test_reject_step(self):
        step = self.session.reject_step(1, reason="Wrong approach")
        assert step.status == StepStatus.REJECTED
        assert step.metadata["rejection_reason"] == "Wrong approach"

    def test_skip_step(self):
        step = self.session.skip_step(2)
        assert step.status == StepStatus.SKIPPED

    def test_complete_step(self):
        step = self.session.complete_step(0)
        assert step.status == StepStatus.COMPLETED


# -----------------------------------------------------------------------
# PairProgrammingSession — user interaction
# -----------------------------------------------------------------------

class TestSessionUserInteraction:
    def setup_method(self):
        self.session = PairProgrammingSession(project_id="p1", task="T")
        self.session.propose_plan(steps=[
            {"step_type": "code", "title": "Implement"},
        ])

    def test_add_user_comment(self):
        comment = self.session.add_user_comment(0, "Use async/await")
        assert comment is not None
        assert comment.content == "Use async/await"

    def test_add_comment_with_line(self):
        comment = self.session.add_user_comment(0, "Fix this", line_number=42)
        assert comment.line_number == 42

    def test_add_comment_not_found(self):
        result = self.session.add_user_comment(99, "x")
        assert result is None

    def test_comments_accumulate(self):
        self.session.add_user_comment(0, "Comment 1")
        self.session.add_user_comment(0, "Comment 2")
        step = self.session.plan.steps[0]
        assert len(step.user_comments) == 2

    def test_preview_includes_comments(self):
        self.session.add_user_comment(0, "Use bcrypt")
        step = self.session.preview_step(0)
        assert "bcrypt" in step.code_preview

    def test_comments_have_unique_ids(self):
        c1 = self.session.add_user_comment(0, "A")
        c2 = self.session.add_user_comment(0, "B")
        assert c1.comment_id != c2.comment_id


# -----------------------------------------------------------------------
# PairProgrammingSession — suggestions
# -----------------------------------------------------------------------

class TestSessionSuggestions:
    def setup_method(self):
        self.session = PairProgrammingSession(project_id="p1", task="T")
        self.session.propose_plan(steps=[
            {"step_type": "code", "title": "Implement"},
        ])

    def test_add_suggestion(self):
        sug = self.session.add_suggestion(
            0, "f.py", 10, 15, "old_code", "new_code", "Better approach",
        )
        assert sug is not None
        assert sug.status == SuggestionStatus.PENDING

    def test_accept_suggestion(self):
        sug = self.session.add_suggestion(0, "f.py", 1, 2, "old", "new")
        result = self.session.respond_to_suggestion(0, sug.suggestion_id, "accepted")
        assert result.status == SuggestionStatus.ACCEPTED

    def test_reject_suggestion(self):
        sug = self.session.add_suggestion(0, "f.py", 1, 2, "old", "new")
        result = self.session.respond_to_suggestion(0, sug.suggestion_id, "rejected")
        assert result.status == SuggestionStatus.REJECTED

    def test_respond_unknown_suggestion(self):
        result = self.session.respond_to_suggestion(0, "nonexistent", "accepted")
        assert result is None


# -----------------------------------------------------------------------
# PairProgrammingSession — progress & lifecycle
# -----------------------------------------------------------------------

class TestSessionProgress:
    def setup_method(self):
        self.session = PairProgrammingSession(project_id="p1", task="T")
        self.session.propose_plan(steps=[
            {"step_type": "code", "title": "S1"},
            {"step_type": "test", "title": "S2"},
        ])

    def test_get_progress(self):
        progress = self.session.get_progress()
        assert progress["total_steps"] == 2
        assert progress["completed_steps"] == 0
        assert progress["progress_pct"] == 0.0

    def test_progress_updates(self):
        self.session.complete_step(0)
        progress = self.session.get_progress()
        assert progress["completed_steps"] == 1
        assert progress["progress_pct"] == 50.0

    def test_end_session(self):
        summary = self.session.end_session()
        assert summary["session_id"] == self.session.session_id
        assert summary["ended_at"] is not None

    def test_event_log(self):
        self.session.approve_step(0)
        self.session.add_user_comment(0, "x")
        log = self.session.get_event_log()
        # At least: session_started, plan_proposed, step_approved, comment_added
        assert len(log) >= 4


# -----------------------------------------------------------------------
# PairProgrammingSession — serialization
# -----------------------------------------------------------------------

class TestSessionSerialization:
    def test_to_dict(self):
        session = PairProgrammingSession(project_id="p1", task="T")
        session.propose_plan()
        d = session.to_dict()
        assert d["project_id"] == "p1"
        assert d["task"] == "T"
        assert d["plan"] is not None
        assert len(d["plan"]["steps"]) >= 2

    def test_mode_step_by_step(self):
        session = PairProgrammingSession(project_id="p", task="T", mode="step_by_step")
        assert session.mode == SessionMode.STEP_BY_STEP

    def test_mode_suggestion(self):
        session = PairProgrammingSession(project_id="p", task="T", mode="suggestion")
        assert session.mode == SessionMode.SUGGESTION

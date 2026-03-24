"""
Database schema for Build Analytics Dashboard.

This module defines the SQLAlchemy models for storing build analytics data
including agent performance, token usage, phase durations, QA results, and more.
"""

from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class BuildStatus(str, Enum):
    """Build execution status."""

    PLANNING = "planning"
    CODING = "coding"
    QA_REVIEW = "qa_review"
    QA_FIXING = "qa_fixing"
    COMPLETE = "complete"
    FAILED = "failed"
    RATE_LIMIT_PAUSED = "rate_limit_paused"
    AUTH_FAILURE_PAUSED = "auth_failure_paused"


class AgentType(str, Enum):
    """Agent type classification."""

    PLANNER = "planner"
    CODER = "coder"
    QA_REVIEWER = "qa_reviewer"
    CRITIQUE = "critique"
    SECURITY = "security"
    GENERAL = "general"


class Build(Base):
    """
    Main build record representing a complete execution cycle.
    """

    __tablename__ = "builds"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String(100), unique=True, index=True, nullable=False)
    spec_id = Column(String(100), index=True, nullable=False)
    spec_name = Column(String(255))
    project_path = Column(String(500))

    # Build metadata
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default=BuildStatus.PLANNING, nullable=False)

    # Performance metrics
    total_duration_seconds = Column(Float, nullable=True)
    total_tokens_used = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)

    # QA metrics
    qa_iterations = Column(Integer, default=0)
    qa_success_rate = Column(Float, default=0.0)

    # Build configuration
    llm_provider = Column(String(100))
    llm_model = Column(String(100))
    agent_config = Column(JSON)

    # Relationships
    phases = relationship(
        "BuildPhase", back_populates="build", cascade="all, delete-orphan"
    )
    token_usage = relationship(
        "TokenUsage", back_populates="build", cascade="all, delete-orphan"
    )
    qa_results = relationship(
        "QAResult", back_populates="build", cascade="all, delete-orphan"
    )
    errors = relationship(
        "BuildError", back_populates="build", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_build_spec_started", "spec_id", "started_at"),
        Index("idx_build_status_started", "status", "started_at"),
        Index("idx_build_provider_model", "llm_provider", "llm_model"),
    )


class BuildPhase(Base):
    """
    Individual phase execution within a build.
    """

    __tablename__ = "build_phases"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String(100), ForeignKey("builds.build_id"), nullable=False)

    # Phase information
    phase_name = Column(String(50), nullable=False)  # planning, coding, qa_review, etc.
    phase_type = Column(String(50), nullable=False)  # agent type
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Phase metrics
    duration_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    success = Column(Boolean, default=True)

    # Phase details
    subtask = Column(String(255))
    progress_percentage = Column(Integer, default=0)
    phase_metadata = Column(JSON)

    # Relationships
    build = relationship("Build", back_populates="phases")

    # Indexes
    __table_args__ = (
        Index("idx_phase_build_name", "build_id", "phase_name"),
        Index("idx_phase_type_started", "phase_type", "started_at"),
    )


class TokenUsage(Base):
    """
    Detailed token usage tracking per build and phase.
    """

    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String(100), ForeignKey("builds.build_id"), nullable=False)
    phase_id = Column(Integer, ForeignKey("build_phases.id"), nullable=True)

    # Token metrics
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)

    # Usage context
    llm_provider = Column(String(100))
    llm_model = Column(String(100))
    operation_type = Column(String(50))  # generation, analysis, review, etc.
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    build = relationship("Build", back_populates="token_usage")

    # Indexes
    __table_args__ = (
        Index("idx_token_build_timestamp", "build_id", "timestamp"),
        Index("idx_token_provider_model", "llm_provider", "llm_model"),
    )


class QAResult(Base):
    """
    QA (Quality Assurance) results for builds.
    """

    __tablename__ = "qa_results"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String(100), ForeignKey("builds.build_id"), nullable=False)
    iteration = Column(Integer, nullable=False)

    # QA metrics
    tests_run = Column(Integer, default=0)
    tests_passed = Column(Integer, default=0)
    tests_failed = Column(Integer, default=0)
    test_coverage_percentage = Column(Float, default=0.0)

    # Code quality metrics
    code_quality_score = Column(Float, default=0.0)
    security_issues_found = Column(Integer, default=0)
    security_issues_fixed = Column(Integer, default=0)

    # QA details
    qa_type = Column(String(50))  # unit_test, integration_test, security_scan, etc.
    duration_seconds = Column(Float, nullable=True)
    success = Column(Boolean, default=False)
    feedback_summary = Column(Text)
    detailed_feedback = Column(Text)

    # Timestamps
    started_at = Column(DateTime, default=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    build = relationship("Build", back_populates="qa_results")

    # Indexes
    __table_args__ = (
        Index("idx_qa_build_iteration", "build_id", "iteration"),
        Index("idx_qa_type_success", "qa_type", "success"),
    )


class BuildError(Base):
    """
    Error tracking for builds and phases.
    """

    __tablename__ = "build_errors"

    id = Column(Integer, primary_key=True, index=True)
    build_id = Column(String(100), ForeignKey("builds.build_id"), nullable=False)
    phase_id = Column(Integer, ForeignKey("build_phases.id"), nullable=True)

    # Error information
    error_type = Column(String(100), nullable=False)  # syntax_error, logic_error, etc.
    error_message = Column(Text, nullable=False)
    error_category = Column(String(50))  # user_error, system_error, rate_limit, etc.

    # Error context
    file_path = Column(String(500))
    line_number = Column(Integer)
    function_name = Column(String(255))
    stack_trace = Column(Text)

    # Error resolution
    resolved = Column(Boolean, default=False)
    resolution_strategy = Column(String(100))  # auto_fix, manual_fix, retry, etc.
    resolution_time_seconds = Column(Float, nullable=True)

    # Timestamps
    occurred_at = Column(DateTime, default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    build = relationship("Build", back_populates="errors")

    # Indexes
    __table_args__ = (
        Index("idx_error_build_type", "build_id", "error_type"),
        Index("idx_error_category_occurred", "error_category", "occurred_at"),
    )


class AgentPerformance(Base):
    """
    Agent performance metrics aggregated over time.
    """

    __tablename__ = "agent_performance"

    id = Column(Integer, primary_key=True, index=True)

    # Agent identification
    agent_type = Column(String(50), nullable=False)
    llm_provider = Column(String(100))
    llm_model = Column(String(100))

    # Performance metrics (aggregated)
    total_builds = Column(Integer, default=0)
    successful_builds = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    # Efficiency metrics
    avg_duration_seconds = Column(Float, default=0.0)
    avg_tokens_per_build = Column(Float, default=0.0)
    avg_cost_per_build = Column(Float, default=0.0)

    # Quality metrics
    avg_qa_iterations = Column(Float, default=0.0)
    avg_code_quality_score = Column(Float, default=0.0)

    # Time period
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_type = Column(String(20))  # daily, weekly, monthly

    # Additional metadata
    performance_metadata = Column(JSON)

    # Indexes
    __table_args__ = (
        Index(
            "idx_agent_performance_type_period",
            "agent_type",
            "period_type",
            "period_start",
        ),
        Index("idx_agent_performance_provider_model", "llm_provider", "llm_model"),
        UniqueConstraint(
            "agent_type",
            "llm_provider",
            "llm_model",
            "period_start",
            "period_type",
            name="uq_agent_performance_period",
        ),
    )


class AnalyticsConfig(Base):
    """
    Configuration for analytics collection and processing.
    """

    __tablename__ = "analytics_config"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    created_by = Column(String(100))

    # Indexes
    __table_args__ = (Index("idx_config_key", "config_key"),)

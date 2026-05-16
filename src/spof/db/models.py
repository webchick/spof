from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from spof.db.base import Base
from spof.db.enums import (
    AnalysisStatus,
    EvidenceType,
    InferenceStatus,
    ProjectSnapshotStatus,
    RepoTargetStatus,
    RiskTier,
    SourceClass,
    SourceType,
    WorkflowEventStatus,
)

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text)
    primary_github_org: Mapped[str | None] = mapped_column(Text)
    github_orgs: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        Index("idx_analyses_company_id", "company_id"),
        Index("idx_analyses_status", "status"),
        Index("idx_analyses_temporal_workflow_id", "temporal_workflow_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysis_status"),
        nullable=False,
    )
    temporal_workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    temporal_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_version: Mapped[str] = mapped_column(Text, nullable=False)
    scoring_version: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_user_id: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AnalysisRepoTarget(Base):
    __tablename__ = "analysis_repo_targets"
    __table_args__ = (
        UniqueConstraint("analysis_id", "repo_full_name"),
        Index("idx_analysis_repo_targets_analysis_id", "analysis_id"),
        Index("idx_analysis_repo_targets_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    repo_host: Mapped[str] = mapped_column(
        Text, nullable=False, default="github", server_default=text("'github'")
    )
    repo_owner: Mapped[str] = mapped_column(Text, nullable=False)
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    repo_full_name: Mapped[str] = mapped_column(Text, nullable=False)
    is_fork: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    repo_rank: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[RepoTargetStatus] = mapped_column(
        Enum(RepoTargetStatus, name="repo_target_status"),
        nullable=False,
        default=RepoTargetStatus.SELECTED,
        server_default=text(f"'{RepoTargetStatus.SELECTED.value}'"),
    )
    selection_reason: Mapped[str | None] = mapped_column(Text)
    extraction_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"
    __table_args__ = (
        Index("idx_evidence_sources_analysis_id", "analysis_id"),
        Index("idx_evidence_sources_repo_target_id", "analysis_repo_target_id"),
        Index("idx_evidence_sources_source_type", "source_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    analysis_repo_target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_repo_targets.id", ondelete="CASCADE")
    )
    source_class: Mapped[SourceClass] = mapped_column(Enum(SourceClass, name="source_class"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(Text)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trust_level: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    raw_content_ref: Mapped[str | None] = mapped_column(Text)
    source_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (
        Index("idx_evidence_items_analysis_id", "analysis_id"),
        Index("idx_evidence_items_source_id", "source_id"),
        Index("idx_evidence_items_repo_target_id", "analysis_repo_target_id"),
        Index("idx_evidence_items_effective_weight", "effective_weight"),
        Index("idx_evidence_items_normalized_value", "normalized_value"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    analysis_repo_target_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analysis_repo_targets.id", ondelete="CASCADE")
    )
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False)
    evidence_type: Mapped[EvidenceType] = mapped_column(Enum(EvidenceType, name="evidence_type"), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    normalized_value: Mapped[str | None] = mapped_column(Text)
    artifact_path: Mapped[str | None] = mapped_column(Text)
    line_start: Mapped[int | None] = mapped_column(Integer)
    line_end: Mapped[int | None] = mapped_column(Integer)
    parser_method: Mapped[str | None] = mapped_column(Text)
    specificity_modifier: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    context_modifier: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    recency_modifier: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    repo_relevance_modifier: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    base_weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    effective_weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    source_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    structured_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_repo_identity", "repo_host", "repo_owner", "repo_name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    ecosystem: Mapped[str | None] = mapped_column(Text)
    package_name: Mapped[str | None] = mapped_column(Text)
    repo_url: Mapped[str | None] = mapped_column(Text)
    repo_host: Mapped[str | None] = mapped_column(Text)
    repo_owner: Mapped[str | None] = mapped_column(Text)
    repo_name: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    project_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProjectAlias(Base):
    __tablename__ = "project_aliases"
    __table_args__ = (
        UniqueConstraint("alias_type", "alias_value"),
        Index("idx_project_aliases_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    alias_type: Mapped[str] = mapped_column(Text, nullable=False)
    alias_value: Mapped[str] = mapped_column(Text, nullable=False)
    ecosystem: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CompanyProjectInference(Base):
    __tablename__ = "company_project_inferences"
    __table_args__ = (
        UniqueConstraint("analysis_id", "project_id"),
        Index("idx_company_project_inferences_analysis_id", "analysis_id"),
        Index("idx_company_project_inferences_project_id", "project_id"),
        Index("idx_company_project_inferences_status", "status"),
        Index(
            "idx_company_project_inferences_priority_inputs",
            "analysis_id",
            "exposure_score",
            "confidence_score",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    status: Mapped[InferenceStatus] = mapped_column(
        Enum(InferenceStatus, name="inference_status"),
        nullable=False,
        default=InferenceStatus.CANDIDATE,
        server_default=text(f"'{InferenceStatus.CANDIDATE.value}'"),
    )
    inference_reason: Mapped[str | None] = mapped_column(Text)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    direct_github_evidence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    supporting_signal_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    repo_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    exposure_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    preliminary_signal_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    suppression_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InferenceEvidenceItem(Base):
    __tablename__ = "inference_evidence_items"
    __table_args__ = (
        PrimaryKeyConstraint("inference_id", "evidence_item_id"),
        Index("idx_inference_evidence_items_evidence_item_id", "evidence_item_id"),
    )

    inference_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("company_project_inferences.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    rank: Mapped[int | None] = mapped_column(Integer)
    contribution_weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))


class ProjectSnapshot(Base):
    __tablename__ = "project_snapshots"
    __table_args__ = (
        Index("idx_project_snapshots_analysis_id", "analysis_id"),
        Index("idx_project_snapshots_project_id", "project_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    status: Mapped[ProjectSnapshotStatus] = mapped_column(
        Enum(ProjectSnapshotStatus, name="project_snapshot_status"),
        nullable=False,
    )
    snapshot_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completeness_flags: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    repo_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    release_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    advisory_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    maintainer_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    scorecard_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    package_metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    raw_summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        UniqueConstraint("analysis_id", "project_id"),
        Index("idx_risk_assessments_analysis_id", "analysis_id"),
        Index("idx_risk_assessments_priority", "analysis_id", "priority_score"),
        Index("idx_risk_assessments_tier", "analysis_id", "risk_tier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    project_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("project_snapshots.id"))
    company_project_inference_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("company_project_inferences.id"))
    exposure_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fragility_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    threat_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    blast_radius_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    risk_tier: Mapped[RiskTier] = mapped_column(Enum(RiskTier, name="risk_tier"), nullable=False)
    primary_risk_driver: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    recommendation_confidence: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    explanation: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Brief(Base):
    __tablename__ = "briefs"
    __table_args__ = (Index("idx_briefs_analysis_id", "analysis_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    brief_type: Mapped[str] = mapped_column(
        Text, nullable=False, default="executive", server_default=text("'executive'")
    )
    summary_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    generated_by: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        Index("idx_workflow_events_analysis_id", "analysis_id"),
        Index("idx_workflow_events_status", "status"),
        Index("idx_workflow_events_workflow_id", "workflow_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    workflow_type: Mapped[str] = mapped_column(Text, nullable=False)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    parent_workflow_id: Mapped[str | None] = mapped_column(Text)
    task_queue: Mapped[str | None] = mapped_column(Text)
    step_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WorkflowEventStatus] = mapped_column(
        Enum(WorkflowEventStatus, name="workflow_event_status"),
        nullable=False,
    )
    attempt: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_summary: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

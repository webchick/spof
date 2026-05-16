"""Initial schema.

Revision ID: 20250515_0001
Revises:
Create Date: 2025-05-15 23:15:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20250515_0001"
down_revision = None
branch_labels = None
depends_on = None


analysis_status = postgresql.ENUM(
    "queued",
    "discovering",
    "resolving",
    "enriching",
    "scoring",
    "briefing",
    "completed",
    "failed",
    "partial",
    name="analysis_status",
)
source_class = postgresql.ENUM(
    "direct_github_artifact",
    "direct_repo_documentation",
    "supporting_public_signal",
    name="source_class",
)
source_type = postgresql.ENUM(
    "github_org",
    "github_repo",
    "github_file",
    "engineering_blog",
    "job_posting",
    "public_docs",
    "web_fingerprint",
    "advisory_feed",
    "package_registry",
    "scorecard",
    name="source_type",
)
evidence_type = postgresql.ENUM(
    "manifest_dependency",
    "lockfile_dependency",
    "workflow_reference",
    "container_reference",
    "iac_reference",
    "source_import",
    "repo_docs_reference",
    "external_docs_reference",
    "job_posting_reference",
    "stack_fingerprint",
    name="evidence_type",
)
repo_target_status = postgresql.ENUM(
    "selected",
    "skipped",
    "completed",
    "failed",
    "partial",
    name="repo_target_status",
)
inference_status = postgresql.ENUM(
    "candidate",
    "resolved",
    "suppressed",
    "selected_for_enrichment",
    "enriched",
    name="inference_status",
)
project_snapshot_status = postgresql.ENUM(
    "complete",
    "partial",
    "failed",
    name="project_snapshot_status",
)
risk_tier = postgresql.ENUM(
    "tier_1",
    "tier_2",
    "tier_3",
    "tier_4",
    name="risk_tier",
)
workflow_event_status = postgresql.ENUM(
    "started",
    "completed",
    "failed",
    "skipped",
    "partial",
    name="workflow_event_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        analysis_status,
        source_class,
        source_type,
        evidence_type,
        repo_target_status,
        inference_status,
        project_snapshot_status,
        risk_tier,
        workflow_event_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("primary_github_org", sa.Text(), nullable=True),
        sa.Column(
            "github_orgs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("status", analysis_status, nullable=False),
        sa.Column("temporal_workflow_id", sa.Text(), nullable=False),
        sa.Column("temporal_run_id", sa.Text(), nullable=False),
        sa.Column("analysis_version", sa.Text(), nullable=False),
        sa.Column("scoring_version", sa.Text(), nullable=False),
        sa.Column("requested_by_user_id", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_analyses_company_id", "analyses", ["company_id"])
    op.create_index("idx_analyses_status", "analyses", ["status"])
    op.create_index("idx_analyses_temporal_workflow_id", "analyses", ["temporal_workflow_id"], unique=True)

    op.create_table(
        "analysis_repo_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("repo_host", sa.Text(), nullable=False, server_default=sa.text("'github'")),
        sa.Column("repo_owner", sa.Text(), nullable=False),
        sa.Column("repo_name", sa.Text(), nullable=False),
        sa.Column("repo_full_name", sa.Text(), nullable=False),
        sa.Column("is_fork", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("repo_rank", sa.Integer(), nullable=True),
        sa.Column("status", repo_target_status, nullable=False, server_default=sa.text("'selected'")),
        sa.Column("selection_reason", sa.Text(), nullable=True),
        sa.Column("extraction_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("analysis_id", "repo_full_name"),
    )
    op.create_index("idx_analysis_repo_targets_analysis_id", "analysis_repo_targets", ["analysis_id"])
    op.create_index("idx_analysis_repo_targets_status", "analysis_repo_targets", ["status"])

    op.create_table(
        "evidence_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "analysis_repo_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_repo_targets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source_class", source_class, nullable=False),
        sa.Column("source_type", source_type, nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trust_level", sa.Numeric(5, 2), nullable=True),
        sa.Column("raw_content_ref", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_evidence_sources_analysis_id", "evidence_sources", ["analysis_id"])
    op.create_index("idx_evidence_sources_repo_target_id", "evidence_sources", ["analysis_repo_target_id"])
    op.create_index("idx_evidence_sources_source_type", "evidence_sources", ["source_type"])

    op.create_table(
        "evidence_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "analysis_repo_target_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_repo_targets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("parser_method", sa.Text(), nullable=True),
        sa.Column("specificity_modifier", sa.Numeric(6, 3), nullable=True),
        sa.Column("context_modifier", sa.Numeric(6, 3), nullable=True),
        sa.Column("recency_modifier", sa.Numeric(6, 3), nullable=True),
        sa.Column("repo_relevance_modifier", sa.Numeric(6, 3), nullable=True),
        sa.Column("base_weight", sa.Numeric(6, 3), nullable=True),
        sa.Column("effective_weight", sa.Numeric(6, 3), nullable=True),
        sa.Column("source_confidence", sa.Numeric(6, 3), nullable=True),
        sa.Column(
            "structured_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_evidence_items_analysis_id", "evidence_items", ["analysis_id"])
    op.create_index("idx_evidence_items_source_id", "evidence_items", ["source_id"])
    op.create_index("idx_evidence_items_repo_target_id", "evidence_items", ["analysis_repo_target_id"])
    op.create_index("idx_evidence_items_effective_weight", "evidence_items", ["effective_weight"])
    op.create_index("idx_evidence_items_normalized_value", "evidence_items", ["normalized_value"])

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("ecosystem", sa.Text(), nullable=True),
        sa.Column("package_name", sa.Text(), nullable=True),
        sa.Column("repo_url", sa.Text(), nullable=True),
        sa.Column("repo_host", sa.Text(), nullable=True),
        sa.Column("repo_owner", sa.Text(), nullable=True),
        sa.Column("repo_name", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_projects_repo_identity", "projects", ["repo_host", "repo_owner", "repo_name"], unique=True)

    op.create_table(
        "project_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_type", sa.Text(), nullable=False),
        sa.Column("alias_value", sa.Text(), nullable=False),
        sa.Column("ecosystem", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(6, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("alias_type", "alias_value"),
    )
    op.create_index("idx_project_aliases_project_id", "project_aliases", ["project_id"])

    op.create_table(
        "company_project_inferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", inference_status, nullable=False, server_default=sa.text("'candidate'")),
        sa.Column("inference_reason", sa.Text(), nullable=True),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("direct_github_evidence_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("supporting_signal_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("repo_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("exposure_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("confidence_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("preliminary_signal_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("suppression_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("analysis_id", "project_id"),
    )
    op.create_index("idx_company_project_inferences_analysis_id", "company_project_inferences", ["analysis_id"])
    op.create_index("idx_company_project_inferences_project_id", "company_project_inferences", ["project_id"])
    op.create_index("idx_company_project_inferences_status", "company_project_inferences", ["status"])
    op.create_index(
        "idx_company_project_inferences_priority_inputs",
        "company_project_inferences",
        ["analysis_id", "exposure_score", "confidence_score"],
    )

    op.create_table(
        "inference_evidence_items",
        sa.Column(
            "inference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_project_inferences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "evidence_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("contribution_weight", sa.Numeric(6, 3), nullable=True),
        sa.PrimaryKeyConstraint("inference_id", "evidence_item_id"),
    )
    op.create_index(
        "idx_inference_evidence_items_evidence_item_id",
        "inference_evidence_items",
        ["evidence_item_id"],
    )

    op.create_table(
        "project_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", project_snapshot_status, nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "completeness_flags",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("repo_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "release_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "advisory_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "maintainer_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "scorecard_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "package_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("raw_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_project_snapshots_analysis_id", "project_snapshots", ["analysis_id"])
    op.create_index("idx_project_snapshots_project_id", "project_snapshots", ["project_id"])

    op.create_table(
        "risk_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("project_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project_snapshots.id"), nullable=True),
        sa.Column(
            "company_project_inference_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("company_project_inferences.id"),
            nullable=True,
        ),
        sa.Column("exposure_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("confidence_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("fragility_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("threat_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("blast_radius_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("priority_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk_tier", risk_tier, nullable=False),
        sa.Column("primary_risk_driver", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("recommendation_confidence", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("analysis_id", "project_id"),
    )
    op.create_index("idx_risk_assessments_analysis_id", "risk_assessments", ["analysis_id"])
    op.create_index("idx_risk_assessments_priority", "risk_assessments", ["analysis_id", "priority_score"])
    op.create_index("idx_risk_assessments_tier", "risk_assessments", ["analysis_id", "risk_tier"])

    op.create_table(
        "briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("brief_type", sa.Text(), nullable=False, server_default=sa.text("'executive'")),
        sa.Column("summary_markdown", sa.Text(), nullable=False),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("generated_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_briefs_analysis_id", "briefs", ["analysis_id"])

    op.create_table(
        "workflow_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("workflow_type", sa.Text(), nullable=False),
        sa.Column("workflow_id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("parent_workflow_id", sa.Text(), nullable=True),
        sa.Column("task_queue", sa.Text(), nullable=True),
        sa.Column("step_name", sa.Text(), nullable=False),
        sa.Column("status", workflow_event_status, nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_workflow_events_analysis_id", "workflow_events", ["analysis_id"])
    op.create_index("idx_workflow_events_status", "workflow_events", ["status"])
    op.create_index("idx_workflow_events_workflow_id", "workflow_events", ["workflow_id"])


def downgrade() -> None:
    op.drop_index("idx_workflow_events_workflow_id", table_name="workflow_events")
    op.drop_index("idx_workflow_events_status", table_name="workflow_events")
    op.drop_index("idx_workflow_events_analysis_id", table_name="workflow_events")
    op.drop_table("workflow_events")

    op.drop_index("idx_briefs_analysis_id", table_name="briefs")
    op.drop_table("briefs")

    op.drop_index("idx_risk_assessments_tier", table_name="risk_assessments")
    op.drop_index("idx_risk_assessments_priority", table_name="risk_assessments")
    op.drop_index("idx_risk_assessments_analysis_id", table_name="risk_assessments")
    op.drop_table("risk_assessments")

    op.drop_index("idx_project_snapshots_project_id", table_name="project_snapshots")
    op.drop_index("idx_project_snapshots_analysis_id", table_name="project_snapshots")
    op.drop_table("project_snapshots")

    op.drop_index("idx_inference_evidence_items_evidence_item_id", table_name="inference_evidence_items")
    op.drop_table("inference_evidence_items")

    op.drop_index("idx_company_project_inferences_priority_inputs", table_name="company_project_inferences")
    op.drop_index("idx_company_project_inferences_status", table_name="company_project_inferences")
    op.drop_index("idx_company_project_inferences_project_id", table_name="company_project_inferences")
    op.drop_index("idx_company_project_inferences_analysis_id", table_name="company_project_inferences")
    op.drop_table("company_project_inferences")

    op.drop_index("idx_project_aliases_project_id", table_name="project_aliases")
    op.drop_table("project_aliases")

    op.drop_index("idx_projects_repo_identity", table_name="projects")
    op.drop_table("projects")

    op.drop_index("idx_evidence_items_normalized_value", table_name="evidence_items")
    op.drop_index("idx_evidence_items_effective_weight", table_name="evidence_items")
    op.drop_index("idx_evidence_items_repo_target_id", table_name="evidence_items")
    op.drop_index("idx_evidence_items_source_id", table_name="evidence_items")
    op.drop_index("idx_evidence_items_analysis_id", table_name="evidence_items")
    op.drop_table("evidence_items")

    op.drop_index("idx_evidence_sources_source_type", table_name="evidence_sources")
    op.drop_index("idx_evidence_sources_repo_target_id", table_name="evidence_sources")
    op.drop_index("idx_evidence_sources_analysis_id", table_name="evidence_sources")
    op.drop_table("evidence_sources")

    op.drop_index("idx_analysis_repo_targets_status", table_name="analysis_repo_targets")
    op.drop_index("idx_analysis_repo_targets_analysis_id", table_name="analysis_repo_targets")
    op.drop_table("analysis_repo_targets")

    op.drop_index("idx_analyses_temporal_workflow_id", table_name="analyses")
    op.drop_index("idx_analyses_status", table_name="analyses")
    op.drop_index("idx_analyses_company_id", table_name="analyses")
    op.drop_table("analyses")

    op.drop_table("companies")

    bind = op.get_bind()
    for enum_type in (
        workflow_event_status,
        risk_tier,
        project_snapshot_status,
        inference_status,
        repo_target_status,
        evidence_type,
        source_type,
        source_class,
        analysis_status,
    ):
        enum_type.drop(bind, checkfirst=True)

from __future__ import annotations

import enum


class AnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    DISCOVERING = "discovering"
    RESOLVING = "resolving"
    ENRICHING = "enriching"
    SCORING = "scoring"
    BRIEFING = "briefing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SourceClass(str, enum.Enum):
    DIRECT_GITHUB_ARTIFACT = "direct_github_artifact"
    DIRECT_REPO_DOCUMENTATION = "direct_repo_documentation"
    SUPPORTING_PUBLIC_SIGNAL = "supporting_public_signal"


class SourceType(str, enum.Enum):
    GITHUB_ORG = "github_org"
    GITHUB_REPO = "github_repo"
    GITHUB_FILE = "github_file"
    ENGINEERING_BLOG = "engineering_blog"
    JOB_POSTING = "job_posting"
    PUBLIC_DOCS = "public_docs"
    WEB_FINGERPRINT = "web_fingerprint"
    ADVISORY_FEED = "advisory_feed"
    PACKAGE_REGISTRY = "package_registry"
    SCORECARD = "scorecard"


class EvidenceType(str, enum.Enum):
    MANIFEST_DEPENDENCY = "manifest_dependency"
    LOCKFILE_DEPENDENCY = "lockfile_dependency"
    WORKFLOW_REFERENCE = "workflow_reference"
    CONTAINER_REFERENCE = "container_reference"
    IAC_REFERENCE = "iac_reference"
    SOURCE_IMPORT = "source_import"
    REPO_DOCS_REFERENCE = "repo_docs_reference"
    EXTERNAL_DOCS_REFERENCE = "external_docs_reference"
    JOB_POSTING_REFERENCE = "job_posting_reference"
    STACK_FINGERPRINT = "stack_fingerprint"


class RepoTargetStatus(str, enum.Enum):
    SELECTED = "selected"
    SKIPPED = "skipped"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class InferenceStatus(str, enum.Enum):
    CANDIDATE = "candidate"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    SELECTED_FOR_ENRICHMENT = "selected_for_enrichment"
    ENRICHED = "enriched"


class ProjectSnapshotStatus(str, enum.Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"


class RiskTier(str, enum.Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"
    TIER_4 = "tier_4"


class WorkflowEventStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PARTIAL = "partial"


# V1 Schema Design

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Purpose

This document defines the initial PostgreSQL schema for v1.

It is designed to support:

- Temporal-driven analysis workflows
- GitHub-first evidence collection
- canonical project resolution
- deterministic risk scoring
- progressive UI updates
- reruns and auditability

## 2. Design Principles

- Separate raw evidence from normalized conclusions.
- Keep workflow execution metadata distinct from product domain data.
- Prefer append-only snapshots for project health and score outputs.
- Store enough derived state for fast UI reads.
- Use JSONB where source-specific structure varies, but keep core analytical fields typed.

## 3. Core Entity Model

The schema centers on:

- `companies`
- `analyses`
- `analysis_repo_targets`
- `evidence_sources`
- `evidence_items`
- `projects`
- `project_aliases`
- `company_project_inferences`
- `project_snapshots`
- `risk_assessments`
- `briefs`
- `workflow_events`

## 4. Suggested PostgreSQL Enums

```sql
create type analysis_status as enum (
  'queued',
  'discovering',
  'resolving',
  'enriching',
  'scoring',
  'briefing',
  'completed',
  'failed',
  'partial'
);

create type source_class as enum (
  'direct_github_artifact',
  'direct_repo_documentation',
  'supporting_public_signal'
);

create type source_type as enum (
  'github_org',
  'github_repo',
  'github_file',
  'engineering_blog',
  'job_posting',
  'public_docs',
  'web_fingerprint',
  'advisory_feed',
  'package_registry',
  'scorecard'
);

create type evidence_type as enum (
  'manifest_dependency',
  'lockfile_dependency',
  'workflow_reference',
  'container_reference',
  'iac_reference',
  'source_import',
  'repo_docs_reference',
  'external_docs_reference',
  'job_posting_reference',
  'stack_fingerprint'
);

create type repo_target_status as enum (
  'selected',
  'skipped',
  'completed',
  'failed',
  'partial'
);

create type inference_status as enum (
  'candidate',
  'resolved',
  'suppressed',
  'selected_for_enrichment',
  'enriched'
);

create type project_snapshot_status as enum (
  'complete',
  'partial',
  'failed'
);

create type risk_tier as enum (
  'tier_1',
  'tier_2',
  'tier_3',
  'tier_4'
);

create type workflow_event_status as enum (
  'started',
  'completed',
  'failed',
  'skipped',
  'partial'
);
```

## 5. Tables

### 5.1 `companies`

One row per analyzed company target.

```sql
create table companies (
  id uuid primary key,
  name text not null,
  domain text,
  primary_github_org text,
  github_orgs jsonb not null default '[]'::jsonb,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Notes:

- `github_orgs` supports multiple candidate orgs even if one is primary.
- `domain` is nullable because some analyses may start from GitHub org only.

### 5.2 `analyses`

One row per analysis run.

```sql
create table analyses (
  id uuid primary key,
  company_id uuid not null references companies(id),
  status analysis_status not null,
  temporal_workflow_id text not null,
  temporal_run_id text not null,
  analysis_version text not null,
  scoring_version text not null,
  requested_by_user_id text,
  notes text,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Notes:

- `analysis_version` tracks workflow/schema generation.
- `scoring_version` tracks score semantics.

### 5.3 `analysis_repo_targets`

Tracks which public repos are in scope for a given analysis.

```sql
create table analysis_repo_targets (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  repo_host text not null default 'github',
  repo_owner text not null,
  repo_name text not null,
  repo_full_name text not null,
  is_fork boolean not null default false,
  is_archived boolean not null default false,
  is_private boolean not null default false,
  repo_rank integer,
  status repo_target_status not null default 'selected',
  selection_reason text,
  extraction_summary jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (analysis_id, repo_full_name)
);
```

Notes:

- this table gives the UI and workflow layer a stable repo-scoped checkpoint
- `repo_rank` supports heuristics for primary versus noisy repos

### 5.4 `evidence_sources`

Represents a fetched source container such as a repo file, blog page, advisory feed record, or package metadata document.

```sql
create table evidence_sources (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  analysis_repo_target_id uuid references analysis_repo_targets(id) on delete cascade,
  source_class source_class not null,
  source_type source_type not null,
  url text,
  title text,
  external_id text,
  artifact_path text,
  fetched_at timestamptz not null,
  trust_level numeric(5,2),
  raw_content_ref text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Notes:

- `raw_content_ref` points to object storage or cached raw payloads
- `metadata` holds source-specific fetch details

### 5.5 `evidence_items`

Normalized atomic observations extracted from sources.

```sql
create table evidence_items (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  analysis_repo_target_id uuid references analysis_repo_targets(id) on delete cascade,
  source_id uuid not null references evidence_sources(id) on delete cascade,
  evidence_type evidence_type not null,
  raw_value text,
  normalized_value text,
  artifact_path text,
  line_start integer,
  line_end integer,
  parser_method text,
  specificity_modifier numeric(6,3),
  context_modifier numeric(6,3),
  recency_modifier numeric(6,3),
  repo_relevance_modifier numeric(6,3),
  base_weight numeric(6,3),
  effective_weight numeric(6,3),
  source_confidence numeric(6,3),
  structured_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Notes:

- this is the core analytical table for exposure and confidence
- `structured_payload` supports parser-specific fields without schema churn

### 5.6 `projects`

Canonical OSS project identity.

```sql
create table projects (
  id uuid primary key,
  canonical_name text not null,
  ecosystem text,
  package_name text,
  repo_url text,
  repo_host text,
  repo_owner text,
  repo_name text,
  category text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

Notes:

- supports both package-native and repo-native project identities

### 5.7 `project_aliases`

Maps variant identifiers to canonical projects.

```sql
create table project_aliases (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  alias_type text not null,
  alias_value text not null,
  ecosystem text,
  confidence numeric(6,3),
  created_at timestamptz not null default now(),
  unique (alias_type, alias_value)
);
```

Notes:

- useful for package names, import paths, GitHub Actions slugs, image names, Terraform providers

### 5.8 `company_project_inferences`

Resolved candidate or selected company-to-project links.

```sql
create table company_project_inferences (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  project_id uuid not null references projects(id),
  status inference_status not null default 'candidate',
  inference_reason text,
  evidence_count integer not null default 0,
  direct_github_evidence_count integer not null default 0,
  supporting_signal_count integer not null default 0,
  repo_count integer not null default 0,
  exposure_score numeric(6,2),
  confidence_score numeric(6,2),
  preliminary_signal_score numeric(6,3),
  suppression_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (analysis_id, project_id)
);
```

Notes:

- supports the transition from candidate inference to enriched project

### 5.9 `inference_evidence_items`

Join table linking inferences to the evidence items that support them.

```sql
create table inference_evidence_items (
  inference_id uuid not null references company_project_inferences(id) on delete cascade,
  evidence_item_id uuid not null references evidence_items(id) on delete cascade,
  rank integer,
  contribution_weight numeric(6,3),
  primary key (inference_id, evidence_item_id)
);
```

Notes:

- enables dossier-style evidence drill-down without re-running ranking logic

### 5.10 `project_snapshots`

Time-bound enrichment output for one project during one analysis.

```sql
create table project_snapshots (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  project_id uuid not null references projects(id),
  status project_snapshot_status not null,
  snapshot_date timestamptz not null,
  completeness_flags jsonb not null default '{}'::jsonb,
  repo_metrics jsonb not null default '{}'::jsonb,
  release_metrics jsonb not null default '{}'::jsonb,
  advisory_metrics jsonb not null default '{}'::jsonb,
  maintainer_metrics jsonb not null default '{}'::jsonb,
  scorecard_metrics jsonb not null default '{}'::jsonb,
  package_metrics jsonb not null default '{}'::jsonb,
  raw_summary jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Notes:

- append-only snapshots make reruns and later monitoring simpler

### 5.11 `risk_assessments`

Final scored outputs for a company-project pair in one analysis.

```sql
create table risk_assessments (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  project_id uuid not null references projects(id),
  project_snapshot_id uuid references project_snapshots(id),
  company_project_inference_id uuid references company_project_inferences(id),
  exposure_score numeric(6,2) not null,
  confidence_score numeric(6,2) not null,
  fragility_score numeric(6,2) not null,
  threat_score numeric(6,2) not null,
  blast_radius_score numeric(6,2) not null,
  priority_score numeric(6,2) not null,
  risk_tier risk_tier not null,
  primary_risk_driver text,
  recommendation text,
  recommendation_confidence numeric(6,2),
  explanation jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (analysis_id, project_id)
);
```

Notes:

- `explanation` can hold structured rationale blocks used by the dossier UI

### 5.12 `briefs`

One or more generated narrative summaries for an analysis.

```sql
create table briefs (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  brief_type text not null default 'executive',
  summary_markdown text not null,
  summary_json jsonb not null default '{}'::jsonb,
  generated_by text,
  created_at timestamptz not null default now()
);
```

Notes:

- supports future variants like executive brief, analyst brief, or delta brief

### 5.13 `workflow_events`

Product-facing checkpoint summaries for Temporal execution.

```sql
create table workflow_events (
  id uuid primary key,
  analysis_id uuid not null references analyses(id) on delete cascade,
  workflow_type text not null,
  workflow_id text not null,
  run_id text not null,
  parent_workflow_id text,
  task_queue text,
  step_name text not null,
  status workflow_event_status not null,
  attempt integer,
  started_at timestamptz,
  ended_at timestamptz,
  error_summary text,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

Notes:

- this is not a replacement for Temporal history
- it exists for UI progress and operational debugging

## 6. Recommended Indexes

```sql
create index idx_analyses_company_id on analyses(company_id);
create index idx_analyses_status on analyses(status);
create unique index idx_analyses_temporal_workflow_id on analyses(temporal_workflow_id);

create index idx_analysis_repo_targets_analysis_id on analysis_repo_targets(analysis_id);
create index idx_analysis_repo_targets_status on analysis_repo_targets(status);

create index idx_evidence_sources_analysis_id on evidence_sources(analysis_id);
create index idx_evidence_sources_repo_target_id on evidence_sources(analysis_repo_target_id);
create index idx_evidence_sources_source_type on evidence_sources(source_type);

create index idx_evidence_items_analysis_id on evidence_items(analysis_id);
create index idx_evidence_items_source_id on evidence_items(source_id);
create index idx_evidence_items_repo_target_id on evidence_items(analysis_repo_target_id);
create index idx_evidence_items_effective_weight on evidence_items(effective_weight desc);
create index idx_evidence_items_normalized_value on evidence_items(normalized_value);

create unique index idx_projects_repo_identity
  on projects(repo_host, repo_owner, repo_name);

create index idx_project_aliases_project_id on project_aliases(project_id);

create index idx_company_project_inferences_analysis_id on company_project_inferences(analysis_id);
create index idx_company_project_inferences_project_id on company_project_inferences(project_id);
create index idx_company_project_inferences_status on company_project_inferences(status);
create index idx_company_project_inferences_priority_inputs
  on company_project_inferences(analysis_id, exposure_score desc, confidence_score desc);

create index idx_inference_evidence_items_evidence_item_id on inference_evidence_items(evidence_item_id);

create index idx_project_snapshots_analysis_id on project_snapshots(analysis_id);
create index idx_project_snapshots_project_id on project_snapshots(project_id);

create index idx_risk_assessments_analysis_id on risk_assessments(analysis_id);
create index idx_risk_assessments_priority on risk_assessments(analysis_id, priority_score desc);
create index idx_risk_assessments_tier on risk_assessments(analysis_id, risk_tier);

create index idx_briefs_analysis_id on briefs(analysis_id);

create index idx_workflow_events_analysis_id on workflow_events(analysis_id);
create index idx_workflow_events_status on workflow_events(status);
create index idx_workflow_events_workflow_id on workflow_events(workflow_id);
```

## 7. JSONB Usage Guidance

Use JSONB for:

- source-specific metadata
- parser-specific payloads
- Scorecard check-level details
- advisory payload details
- workflow payload summaries
- explanation block structure

Do not hide core filter/sort fields in JSONB when they will be used in:

- portfolio ranking
- workflow status queries
- dossier evidence lookup

## 8. Temporal Integration Notes

The application database should store:

- current analysis state
- analysis-to-workflow mapping
- step-level workflow summaries
- partial outputs from completed activities

Temporal should remain the source of truth for:

- exact execution history
- retry attempts
- workflow replay state

The app should never require reading Temporal history just to render standard UI pages.

## 9. Minimal Read Models Supported

This schema supports these UI queries efficiently:

- list analyses for a company
- get current analysis progress
- show selected repos and extraction status
- show top 10 risk portfolio for an analysis
- open a project dossier with supporting evidence
- open the latest executive brief

## 10. Recommended Migration Order

1. create enums
2. create `companies`
3. create `analyses`
4. create `analysis_repo_targets`
5. create `evidence_sources`
6. create `evidence_items`
7. create `projects`
8. create `project_aliases`
9. create `company_project_inferences`
10. create `inference_evidence_items`
11. create `project_snapshots`
12. create `risk_assessments`
13. create `briefs`
14. create `workflow_events`
15. create indexes

## 11. Likely V1 Simplifications

If we need to cut scope during implementation:

- keep `requested_by_user_id` as nullable text rather than introducing a users table
- keep repo and project metadata in JSONB rather than over-normalizing early
- omit materialized views until query patterns are proven
- use one `briefs` table instead of separate report tables

## 12. Open Decisions

- whether `projects` should distinguish package identity and repo identity more formally in v1
- whether `analysis_repo_targets` should store GitHub numeric repo ids for easier deduplication
- whether advisory records deserve their own table in v1 or can remain summarized inside `project_snapshots`
- whether `workflow_events` should be append-only or allow upserts for the latest step state
- whether risk explanation blocks need their own table for fine-grained review comments later

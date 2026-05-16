# V1 Temporal Workflow Backlog

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Purpose

This document turns the Temporal-oriented architecture into an implementation backlog.

It defines:

- workflow types
- activity boundaries
- task queues
- retry and timeout posture
- persistence checkpoints
- build order for the first working vertical slice

## 2. Principles

- Keep workflows deterministic.
- Push all external I/O into activities.
- Prefer a few meaningful workflows over many tiny workflows.
- Persist normalized results and progress checkpoints to PostgreSQL.
- Treat partial completion as a valid product outcome.
- Make retries explicit and source-aware.

## 3. Workflow Topology

### Parent workflow

- `AnalysisWorkflow`

### Child workflows

- `RepoEvidenceWorkflow`
- `ProjectEnrichmentWorkflow`

### Activity groups

- intake and persistence
- GitHub discovery
- artifact extraction
- supporting-signal collection
- project resolution
- project enrichment
- scoring
- explanation and brief generation
- export

## 4. Task Queues

Recommended v1 task queues:

- `analysis`
- `repo-evidence`
- `project-enrichment`
- `github-io`
- `external-io`
- `llm`
- `exports`

### Queue intent

- `analysis`
  - parent workflow coordination and lightweight orchestration-side activities
- `repo-evidence`
  - repo-scoped child workflows and artifact extraction work
- `project-enrichment`
  - project-scoped enrichment child workflows
- `github-io`
  - GitHub API and repo-content fetches
- `external-io`
  - OSV/CVE, package registry, and softer web-source fetches
- `llm`
  - bounded synthesis and explanation tasks
- `exports`
  - markdown-to-report or downloadable asset generation

## 5. Parent Workflow Backlog

### Workflow: `AnalysisWorkflow`

Purpose:

- own one company analysis from intake to final brief

Inputs:

- analysis id
- company name
- domain
- optional GitHub org
- optional notes

Outputs:

- completed, partial, or failed analysis state
- persisted company, evidence, inference, snapshot, and assessment records
- generated brief

### Step backlog

1. `CreateAnalysisRun`
   - ensure analysis row exists
   - attach workflow id and run id
   - set status to `queued`

2. `ResolveAnalysisTarget`
   - resolve GitHub org from explicit input or company/domain hints
   - fail fast if no meaningful public GitHub target is resolvable in v1

3. `EnumeratePublicRepos`
   - fetch repo inventory for target org
   - filter forks, archived repos, or obvious noise according to v1 rules

4. `FanOutRepoEvidence`
   - spawn one `RepoEvidenceWorkflow` per selected repo
   - collect repo-level partial failures without aborting immediately

5. `FetchSupportingSignals`
   - fetch softer public sources in parallel with repo evidence when possible

6. `InferCandidateProjects`
   - aggregate evidence across repos and supporting sources
   - create candidate company-project inference rows

7. `ResolveCanonicalProjects`
   - normalize inferred technologies into canonical projects

8. `SelectProjectsForEnrichment`
   - choose top N projects by preliminary signal strength

9. `FanOutProjectEnrichment`
   - spawn one `ProjectEnrichmentWorkflow` per selected project

10. `ComputeRiskAssessments`
   - run deterministic scoring over persisted normalized data

11. `GenerateProjectExplanations`
   - produce rationale text and recommendation explanations

12. `GenerateBrief`
   - synthesize executive summary and top findings

13. `FinalizeAnalysis`
   - compute final workflow outcome
   - set status to `completed`, `partial`, or `failed`

## 6. Child Workflow Backlog

### Workflow: `RepoEvidenceWorkflow`

Purpose:

- extract high-confidence usage evidence from one public repo

Inputs:

- analysis id
- repo id or canonical repo reference

Outputs:

- persisted evidence sources
- persisted evidence items
- repo-level extraction summary

### Step backlog

1. `FetchRepoMetadata`
2. `ListRelevantRepoFiles`
3. `ExtractManifestEvidence`
4. `ExtractWorkflowEvidence`
5. `ExtractContainerEvidence`
6. `ExtractInfrastructureEvidence`
7. `ExtractRepoDocsEvidence`
8. `PersistRepoEvidenceSummary`

### Workflow: `ProjectEnrichmentWorkflow`

Purpose:

- gather risk and health signals for one canonical OSS project

Inputs:

- analysis id
- canonical project id

Outputs:

- project snapshot
- normalized enrichment metrics
- enrichment completeness flags

### Step backlog

1. `FetchProjectRepoMetadata`
2. `FetchReleaseHistory`
3. `FetchPackageRegistryMetadata`
4. `FetchScorecardSignals`
5. `FetchAdvisoryData`
6. `FetchIssueAndPRTimings`
7. `NormalizeProjectSignals`
8. `PersistProjectSnapshot`

## 7. Activity Inventory

### Intake and persistence

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `create_analysis_run` | `analysis` | persist workflow ids and initialize status | Required |
| `update_analysis_status` | `analysis` | update state transitions and summaries | Required |
| `record_workflow_event` | `analysis` | persist step-level progress summaries | Useful |

### GitHub discovery

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `resolve_github_org` | `github-io` | map company/domain to public GitHub org | Required |
| `fetch_org_repos` | `github-io` | enumerate public repos and repo metadata | Required |
| `fetch_repo_tree` | `github-io` | list relevant files in repo | Required |
| `fetch_repo_file` | `github-io` | retrieve raw file content for parsing | Required |

### Artifact extraction

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `extract_manifest_evidence` | `repo-evidence` | parse manifests and lockfiles | Required |
| `extract_workflow_evidence` | `repo-evidence` | parse GitHub Actions and CI config | Required |
| `extract_container_evidence` | `repo-evidence` | parse Dockerfiles and related files | Required |
| `extract_iac_evidence` | `repo-evidence` | parse Terraform, Helm, Kubernetes, Pulumi, etc. | Required |
| `extract_repo_docs_evidence` | `repo-evidence` | parse README and repo docs | Required |

### Supporting-signal collection

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `fetch_engineering_blog_signals` | `external-io` | gather supporting technical signals | Useful |
| `fetch_job_posting_signals` | `external-io` | gather low-confidence stack hints | Useful |
| `fetch_public_docs_signals` | `external-io` | gather soft corroborating signals | Useful |

### Project resolution and inference

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `resolve_canonical_projects` | `analysis` | normalize raw references into projects | Required |
| `infer_candidate_projects` | `analysis` | roll up repo evidence into company-project candidates | Required |
| `select_projects_for_enrichment` | `analysis` | choose top N projects for deeper enrichment | Required |

### Project enrichment

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `fetch_project_repo_metadata` | `github-io` | repo activity and structural metadata | Required |
| `fetch_release_history` | `github-io` | releases, tags, and cadence data | Required |
| `fetch_package_registry_metadata` | `external-io` | package ecosystem metadata | Required |
| `fetch_scorecard_signals` | `external-io` | OpenSSF check-level posture data | Required |
| `fetch_advisory_data` | `external-io` | OSV/CVE/advisory normalization | Required |
| `fetch_issue_pr_timings` | `github-io` | responsiveness and closure data | Required |
| `normalize_project_signals` | `project-enrichment` | shape raw enrichment into scoring-ready data | Required |

### Scoring and explanation

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `compute_risk_assessments` | `analysis` | deterministic scoring pass | Required |
| `generate_project_explanations` | `llm` | bounded rationale generation from structured inputs | Required |
| `generate_brief` | `llm` | executive summary synthesis | Required |

### Export

| Activity | Queue | Purpose | Required |
| --- | --- | --- | --- |
| `render_exportable_brief` | `exports` | produce downloadable report output | Useful |

## 8. Retry Policy Backlog

Use retry policies by activity class instead of one global policy.

### GitHub and external fetches

- retry: yes
- backoff: exponential
- max attempts: medium
- non-retry cases:
  - 404 not found for expected absent resources
  - clearly malformed target identifiers
  - unsupported ecosystem/resource patterns

### Artifact parsing

- retry: limited
- retry only for transient fetch or decode issues
- non-retry cases:
  - unsupported file syntax
  - deterministic parser failure on stable content

### LLM activities

- retry: limited
- require schema validation on outputs
- non-retry cases:
  - repeated schema-invalid responses after bounded attempts

### Scoring

- retry: generally no
- fail fast on invariant violations
- rerun only after upstream data correction

## 9. Timeout Posture

### Parent workflow

- longer end-to-end timeout
- intended to survive slow fan-out and retries

### Repo child workflows

- medium timeout
- enough to fetch repo content and parse artifacts

### Project child workflows

- medium timeout
- enough for multiple external lookups

### Single fetch activities

- short timeout

### LLM activities

- medium timeout

### Export activities

- short to medium timeout

Exact numbers can be tuned during implementation, but the hierarchy should remain:

- parent workflow > child workflow > LLM/fetch activity > single request activity

## 10. Persistence Checkpoints

Persist domain state at workflow boundaries rather than only at the end.

### Required checkpoints

- analysis created
- GitHub org resolved
- repo inventory stored
- repo evidence persisted per repo
- candidate projects persisted
- selected projects for enrichment persisted
- project snapshot persisted per project
- risk assessments persisted
- brief persisted
- final analysis status persisted

### Why this matters

- UI can show progressive results
- reruns can reuse completed work
- failures do not discard already useful analysis
- support/debugging is simpler

## 11. Partial-Failure Rules

### Parent workflow rules

- continue if some repos fail extraction
- continue if some projects fail enrichment
- mark analysis `partial` when enough signal exists to score top risks
- mark analysis `failed` only when core prerequisites are missing or almost all primary evidence work fails

### Repo workflow rules

- if one artifact parser fails, continue with the other parsers
- persist whatever evidence was successfully extracted

### Project enrichment rules

- if one enrichment source fails, persist completeness flags and continue where possible
- do not fabricate missing health or threat data

## 12. Build Order

### Phase 1: Temporal skeleton

- Temporal environment setup
- worker process structure
- `AnalysisWorkflow` stub
- `create_analysis_run`
- `update_analysis_status`
- `record_workflow_event`

### Phase 2: Repo evidence vertical slice

- `resolve_github_org`
- `fetch_org_repos`
- `RepoEvidenceWorkflow`
- `fetch_repo_tree`
- `fetch_repo_file`
- `extract_manifest_evidence`
- evidence persistence

Goal:

- from GitHub org to candidate dependency evidence in Postgres

### Phase 3: Project resolution and selection

- `infer_candidate_projects`
- `resolve_canonical_projects`
- `select_projects_for_enrichment`

Goal:

- from raw evidence to canonical company-project inferences

### Phase 4: Project enrichment vertical slice

- `ProjectEnrichmentWorkflow`
- `fetch_project_repo_metadata`
- `fetch_release_history`
- `fetch_scorecard_signals`
- `fetch_advisory_data`
- `normalize_project_signals`
- snapshot persistence

Goal:

- from inferred project to scoring-ready enrichment data

### Phase 5: Deterministic scoring

- `compute_risk_assessments`
- scoring persistence
- status transitions for `completed` and `partial`

Goal:

- produce ranked risk outputs without full brief generation yet

### Phase 6: Explanations and brief

- `generate_project_explanations`
- `generate_brief`
- `render_exportable_brief`

Goal:

- produce user-facing narrative output

## 13. First Vertical Slice Recommendation

The first working slice should be:

1. input GitHub org
2. enumerate repos
3. parse manifests and lockfiles only
4. infer candidate projects
5. enrich top 5 projects with:
   - release history
   - Scorecard
   - advisory data
6. compute exposure, confidence, and a limited threat score
7. return a preliminary ranked list

This is narrower than the full MVP, but it proves:

- Temporal orchestration
- evidence persistence
- project resolution
- scoring pipeline

before adding softer signals and full fragility metrics.

## 14. Ownership Suggestions

Suggested implementation ownership by subsystem:

- Temporal workflows and workers
  - platform/backend
- GitHub and external fetch activities
  - backend/integration
- artifact parsers
  - backend/data pipeline
- scoring functions
  - backend/risk engine
- explanation generation
  - backend/AI integration
- progress and results UI
  - frontend/product engineering

## 15. Open Decisions

- whether `resolve_github_org` should be an activity or a small child workflow if resolution becomes multi-step
- whether repo evidence fan-out should be bounded by concurrency caps at the workflow layer or only at the worker layer
- whether `fetch_scorecard_signals` should call a public API, cached store, or run scorecard tooling directly
- whether brief generation should happen before all project explanations complete or after
- whether supporting-signal collection should be parallel with repo evidence from day one or deferred to a later phase

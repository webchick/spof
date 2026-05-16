# Technical Architecture

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Purpose

This document translates the PRD into a buildable MVP architecture.

The architecture is optimized for:

- public GitHub org and repository analysis as the primary input path
- explainable risk scoring rather than black-box prediction
- agent-assisted evidence gathering with deterministic scoring stages
- interactive single-company analysis
- Temporal-based orchestration for long-running and failure-prone work
- future expansion into private artifact ingestion and investment planning

## 2. System Goal

Given a company name, domain, or GitHub org, the system should:

1. infer the company's likely OSS footprint primarily from public GitHub software artifacts
2. enrich the most likely projects with ecosystem and security intelligence
3. compute explainable risk scores
4. rank the top OSS risks
5. generate a concise executive brief and detailed project dossiers

## 3. Architecture Principles

- Keep inference and scoring separate.
- Store raw evidence before generating conclusions.
- Make agents gather and synthesize evidence, but keep final scoring logic inspectable.
- Prefer reproducible pipelines over free-form agent autonomy.
- Design for uncertainty, provenance, and re-runs.
- Keep the MVP synchronous enough for interactive use, but structure jobs for later background processing.

## 4. High-Level System Design

The MVP can be implemented as five logical layers:

1. `Application Layer`
   - web UI
   - API server
   - auth and user/session handling

2. `Orchestration Layer`
   - Temporal workflows
   - Temporal activities
   - agent task routing
   - workflow state management

3. `Intelligence Layer`
   - company footprint inference
   - project intelligence enrichment
   - risk scoring
   - recommendation generation
   - briefing generation

4. `Data Layer`
   - operational database
   - search/index store for evidence snippets
   - cache for fetched external data

5. `Integration Layer`
   - GitHub and source artifact adapters
   - secondary web discovery adapters
   - source control and package metadata adapters
   - advisory and CVE data adapters
   - optional LLM provider adapters

## 5. Recommended MVP Stack

This is the most pragmatic first stack:

- Frontend: `Next.js`
- Backend/API: `Next.js route handlers` or a separate `FastAPI` service
- Worker/orchestration: `Python` Temporal workers
- Database: `PostgreSQL`
- Workflow engine: `Temporal`
- Search/index: PostgreSQL full-text first, dedicated vector store later only if needed
- Object storage: S3-compatible bucket for raw reports and exports
- LLM provider: one primary model provider with structured-output support

Why this split:

- Python is a better fit for enrichment pipelines, scraping normalization, scoring logic, and Temporal workers.
- Next.js gives a fast path for shipping an analyst-facing app.
- PostgreSQL is sufficient for the MVP if the schema is designed well.
- Temporal is a better fit than a basic queue because the analysis pipeline is long-running, retry-heavy, fan-out oriented, and needs durable execution history.

## 5.1 Why Temporal Fits This Product

This product has workflow characteristics that align well with Temporal:

- external dependencies are slow and flaky
- many analysis steps are parallelizable
- some steps may take minutes rather than seconds
- partial progress is useful and should be resumable
- retries and backoff are a first-class requirement
- future monitoring and scheduled re-runs map naturally to recurring workflows
- auditability matters for explaining how a risk assessment was produced

Temporal should own execution state and retries.

PostgreSQL should remain the source of truth for domain state, analysis results, and user-facing data.

## 6. End-to-End Workflow

### Step 1: Analysis creation

User submits:

- company name
- domain
- GitHub org where known
- optional notes

System creates:

- analysis record
- target company record
- workflow state = `queued`
- Temporal `AnalysisWorkflow` execution

### Step 2: GitHub footprint discovery

The company footprint workflow collects:

- public GitHub org metadata
- public repositories
- dependency manifests and lockfiles
- GitHub Actions workflows
- Dockerfiles and container definitions
- IaC and deployment configs
- README and repo docs references

The workflow may also collect supporting lower-confidence signals from:

- company website pages
- engineering blog pages
- docs pages
- careers/job pages
- observable stack clues from public web assets and headers where permitted

Outputs:

- normalized evidence items
- candidate technologies
- candidate OSS projects
- evidence-confidence links

### Step 3: Candidate project resolution

The system resolves inferred technologies into canonical projects:

- repo URL
- package name
- ecosystem
- project category

It deduplicates aliases and maps multiple evidence sources to one project entity.

Direct GitHub software artifacts should dominate supporting soft-signal sources when evidence conflicts.

### Step 4: Project enrichment

For the top N candidate projects, the enrichment workflow gathers:

- repo activity metrics
- release history
- maintainer and contributor patterns
- open issue and PR response signals
- advisory and CVE data
- package metadata
- category criticality metadata

Outputs:

- project intelligence snapshot
- normalized metrics
- raw evidence references

### Step 5: Risk scoring

A deterministic scoring service:

- computes exposure, confidence, fragility, threat, and blast radius
- generates overall priority
- assigns a risk tier
- produces explanation text from template-backed reasoning

### Step 6: Recommendation generation

A constrained recommendation engine maps score patterns to:

- monitor
- validate internal usage
- reduce dependency concentration
- add compensating controls
- contribute upstream fixes
- sponsor maintainers
- plan migration or replacement

### Step 7: Briefing generation

The briefing service compiles:

- top findings
- cross-cutting themes
- high-confidence risks
- recommended next steps

### Step 8: Presentation

The UI exposes:

- company overview
- risk portfolio
- project dossier
- executive brief export

## 6.1 Temporal Workflow Topology

The MVP should use one top-level workflow per company analysis.

### Parent workflow

`AnalysisWorkflow`

Responsibilities:

- coordinate the end-to-end analysis
- fan out repo-level extraction
- fan out project-level enrichment
- collect partial failures
- trigger final scoring and brief generation

### Child workflows

Use child workflows when a subtask is substantial, parallel, and worth isolating for retries and observability.

Recommended child workflows:

- `RepoEvidenceWorkflow(repo)`
- `ProjectEnrichmentWorkflow(project)`

### Activities

Use activities for side-effecting or external calls such as:

- GitHub API access
- repo file fetching
- web crawling
- package registry lookups
- OSV/CVE lookups
- LLM inference
- persistence writes
- export generation

### Determinism rule

Temporal workflows must remain deterministic.

Therefore:

- external I/O belongs in activities
- LLM calls belong in activities
- scoring code may run in workflows only if fully deterministic and versioned
- if scoring logic depends on data fetching or model calls, keep it in activities and persist the outputs

## 7. Agent Design

The system should use agents as bounded workers inside a larger orchestrated workflow.

The key architectural rule is:

Agents may propose structured outputs, but they should not directly mutate final scores without a deterministic scoring pass.

### 7.1 Company Footprint Agent

Inputs:

- company name
- domain
- GitHub org and repo corpus
- supporting public sources where available

Responsibilities:

- extract dependency and infrastructure clues from software artifacts
- infer likely OSS projects
- attach evidence snippets
- estimate confidence

Structured output:

- candidate project list
- evidence list
- confidence estimate
- explanation of inference

The agent should label each evidence item by source class, such as:

- direct GitHub artifact
- direct repo documentation
- supporting public signal

### 7.2 Project Intelligence Agent

Inputs:

- canonical project identity
- repo/package/advisory sources

Responsibilities:

- summarize maintainer structure
- summarize release and issue behavior
- summarize threat signals
- flag signs of instability or under-resourcing

Structured output:

- project intelligence summary
- normalized metric candidates
- cited evidence

### 7.3 Risk Explanation Agent

Inputs:

- computed scores
- normalized signals
- evidence provenance

Responsibilities:

- convert scores into human-readable reasoning
- explain uncertainty
- produce dossier narrative

Structured output:

- score explanations
- recommendation rationale
- executive-summary paragraphs

### 7.4 Why not fully autonomous agents

For this product, unrestricted autonomous agents create three problems:

- inconsistent outputs across runs
- weak auditability
- hard-to-defend scoring

The architecture should therefore use workflow-controlled agents with typed outputs and bounded prompts.

## 8. Service Decomposition

The MVP can start with four backend services or modules.

### 8.1 API Service

Responsibilities:

- create analysis jobs
- serve UI data
- manage users and saved analyses
- trigger exports

Suggested endpoints:

- `POST /analyses`
- `GET /analyses/:id`
- `GET /analyses/:id/portfolio`
- `GET /analyses/:id/projects/:projectId`
- `GET /analyses/:id/brief`
- `POST /analyses/:id/rerun`

### 8.2 Workflow Orchestrator

Responsibilities:

- execute multi-step Temporal workflows
- manage retries, timeouts, and partial failures
- track workflow states

Suggested states:

- `queued`
- `discovering`
- `resolving`
- `enriching`
- `scoring`
- `briefing`
- `completed`
- `failed`
- `partial`

Suggested Temporal workflow types:

- `AnalysisWorkflow`
- `RepoEvidenceWorkflow`
- `ProjectEnrichmentWorkflow`

Suggested Temporal task queues:

- `analysis`
- `repo-evidence`
- `project-enrichment`
- `llm`
- `exports`

### 8.3 Data Collection and Enrichment Service

Responsibilities:

- fetch external data
- normalize source-specific fields
- cache results
- maintain adapter boundaries per source
- run as Temporal activities behind clear retry policies

### 8.4 Scoring and Recommendation Service

Responsibilities:

- calculate all risk dimensions
- assign tiers
- generate constrained recommendations
- expose score explanations

This service should be invoked after enrichment fan-out has settled, either:

- as deterministic in-workflow logic for purely local scoring, or
- as a dedicated Temporal activity if implementation simplicity is preferred

## 9. Data Model

The MVP should store both raw evidence and normalized conclusions.

### 9.1 Core entities

#### Company

- `id`
- `name`
- `domain`
- `github_orgs[]`
- `primary_github_org`
- `created_at`

#### Analysis

- `id`
- `company_id`
- `status`
- `temporal_workflow_id`
- `temporal_run_id`
- `requested_by_user_id`
- `created_at`
- `completed_at`
- `analysis_version`
- `scoring_version`
- `notes`

#### EvidenceSource

- `id`
- `analysis_id`
- `source_type`
- `source_class`
- `url`
- `title`
- `fetched_at`
- `raw_content_ref`
- `trust_level`

#### EvidenceItem

- `id`
- `analysis_id`
- `source_id`
- `evidence_type`
- `artifact_path`
- `snippet`
- `structured_payload`
- `parser_method`
- `confidence_weight`
- `created_at`

#### Project

- `id`
- `canonical_name`
- `repo_url`
- `ecosystem`
- `package_name`
- `category`

#### CompanyProjectInference

- `id`
- `analysis_id`
- `project_id`
- `inference_reason`
- `exposure_score`
- `confidence_score`
- `evidence_count`
- `direct_github_evidence_count`
- `supporting_signal_count`
- `status`

#### ProjectSnapshot

- `id`
- `project_id`
- `snapshot_date`
- `repo_metrics_json`
- `release_metrics_json`
- `advisory_metrics_json`
- `maintainer_metrics_json`
- `raw_summary`

#### WorkflowEvent

- `id`
- `analysis_id`
- `workflow_type`
- `workflow_id`
- `run_id`
- `step_name`
- `status`
- `started_at`
- `ended_at`
- `attempt`
- `error_summary`

#### RiskAssessment

- `id`
- `analysis_id`
- `project_id`
- `exposure_score`
- `confidence_score`
- `fragility_score`
- `threat_score`
- `blast_radius_score`
- `priority_score`
- `risk_tier`
- `primary_risk_driver`
- `recommendation`
- `explanation`

#### Brief

- `id`
- `analysis_id`
- `summary_markdown`
- `generated_at`

### 9.2 Why snapshots matter

Project signals change over time. The architecture should snapshot project intelligence so that:

- old reports remain explainable
- re-runs can compare deltas
- later monitoring features have a foundation

### 9.3 Why workflow metadata matters

Temporal already stores execution history, but the product should still persist workflow identifiers and selected step summaries in Postgres so that:

- UI screens can show progress without reading raw Temporal history
- support and debugging are simpler
- analytics queries stay out of the workflow engine

## 10. External Data Adapters

The MVP should use adapters with a common interface:

- `fetch()`
- `normalize()`
- `cache_key()`
- `freshness_policy()`

### 10.1 Company discovery adapters

- GitHub org/repo enumerator
- manifest and lockfile extractor
- workflow and CI config extractor
- container and IaC extractor
- repo README/docs extractor
- company website crawler
- public docs fetcher
- engineering blog parser
- job posting parser

### 10.2 Project intelligence adapters

- GitHub repository metadata
- release/tag metadata
- package registry metadata
- advisory/CVE sources

### 10.3 Adapter design rules

- keep source-specific parsing isolated
- store raw upstream responses where feasible
- normalize into stable internal schemas
- include freshness metadata and fetch timestamps
- mark each adapter as primary evidence or supporting evidence

## 11. Scoring Pipeline

The scoring layer should be deterministic and versioned.

### 11.1 Pipeline stages

1. raw signal collection
2. signal normalization
3. feature derivation
4. score computation
5. explanation generation

### 11.2 Signal normalization examples

- release intervals become a cadence consistency metric
- contributor counts become concentration ratios
- CVE counts become time-bounded threat indicators
- evidence snippets become weighted exposure features

### 11.3 Scoring versioning

Every analysis should store:

- scoring algorithm version
- weight configuration
- feature extraction version

This is required to compare results over time and explain drift.

## 11.4 Temporal execution guidance

Recommended execution model:

- evidence collection = activities
- enrichment = child workflows plus activities
- scoring = one final stage after enrichment joins
- explanation generation = activities

This keeps the high-fan-out and failure-prone stages isolated while preserving a single parent execution record for each analysis.

## 12. Confidence Model

Confidence is not a side field. It is central to the architecture.

The system should track confidence at three levels:

1. source confidence
2. inference confidence
3. recommendation confidence

### 12.1 Source confidence

Examples:

- public manifest from company repo = high confidence
- GitHub Actions workflow or deployment config in company repo = high confidence
- Dockerfile or Terraform/Helm/Kubernetes config in company repo = high confidence
- engineering blog mention = medium confidence
- job posting keyword = low to medium confidence

### 12.2 Inference confidence

Calculated from:

- direct GitHub evidence count
- evidence diversity
- evidence recency
- evidence specificity
- agreement across sources

### 12.3 Recommendation confidence

Derived from:

- inference confidence
- completeness of project intelligence
- score separation from lower-ranked projects

## 13. Explanation System

The product must explain:

- why a project is believed to be in the company's footprint
- why its risk tier is high or low
- why the recommended action fits

To make this reliable, explanations should combine:

- deterministic templates for core facts
- bounded LLM synthesis for readable narrative

This avoids hallucinated rationale while still producing useful prose.

## 14. UI Architecture

The frontend should be read-optimized rather than form-heavy.

### Main routes

- `/analyses/new`
- `/analyses/[id]`
- `/analyses/[id]/portfolio`
- `/analyses/[id]/projects/[projectId]`
- `/analyses/[id]/brief`

### UI state needs

- job progress states
- partial result rendering
- confidence badges
- evidence drill-down
- export actions

### Key UX requirement

Every portfolio row should show:

- project
- risk tier
- confidence
- primary risk driver
- recommended action
- "why we think they use it"
- evidence mix, distinguishing direct GitHub artifacts from supporting signals

## 15. Job Orchestration Model

The MVP should use Temporal workflows rather than one monolithic job or a simple background queue.

### Parent workflow: `AnalysisWorkflow`

Suggested flow:

1. `create_analysis_record`
2. `resolve_github_org`
3. `enumerate_public_repos`
4. fan out `RepoEvidenceWorkflow(repo)` across repos
5. `fetch_supporting_public_signals`
6. `infer_candidate_projects`
7. `resolve_canonical_projects`
8. `select_top_projects_for_enrichment`
9. fan out `ProjectEnrichmentWorkflow(project)` across selected projects
10. `compute_risk_assessments`
11. `generate_brief`
12. `finalize_analysis`

### Child workflow: `RepoEvidenceWorkflow(repo)`

Suggested flow:

1. `fetch_repo_metadata`
2. `discover_repo_artifacts`
3. `extract_manifest_evidence`
4. `extract_workflow_evidence`
5. `extract_container_and_iac_evidence`
6. `extract_repo_docs_evidence`
7. `persist_repo_evidence`

### Child workflow: `ProjectEnrichmentWorkflow(project)`

Suggested flow:

1. `fetch_project_repo_metadata`
2. `fetch_release_history`
3. `fetch_package_registry_metadata`
4. `fetch_advisory_data`
5. `compute_normalized_project_signals`
6. `persist_project_snapshot`

Parallelizable stages:

- repo fetching
- artifact extraction
- supporting-source fetching
- per-project enrichment

Serialized stages:

- final scoring
- brief generation

### Retry posture

Recommended Temporal retry behavior:

- GitHub/API/network fetches: automatic retries with exponential backoff
- crawling and parsing: retries for transient failures, capped for malformed content
- LLM activities: limited retries, with prompt/output validation
- scoring: fail fast if inputs are incomplete in unexpected ways

### Timeouts

Recommended timeout posture:

- short activity timeouts for single fetches
- longer child workflow timeouts for repo and project processing
- longer parent workflow timeout for end-to-end analysis

## 16. Failure Handling

Public-data workflows will be noisy. The architecture must support partial success.

Examples:

- if one data source fails, continue with reduced confidence
- if project enrichment fails for one project, mark that project incomplete and continue
- if briefing fails, preserve portfolio results and allow manual regeneration

The `partial` analysis state should be treated as a first-class status.

Temporal-specific guidance:

- a child workflow failure should not necessarily fail the parent
- repo-level failures should be recorded and the parent should continue when enough evidence remains
- project enrichment failures should mark the project incomplete rather than abort the whole analysis
- the parent workflow should aggregate unresolved failures into the final analysis status

## 17. Caching and Freshness

Caching matters because the same projects will recur across analyses.

### Cache levels

- raw source fetch cache
- normalized project snapshot cache
- score cache only when underlying inputs are unchanged

### Freshness guidance

- project repo and release metrics: refresh frequently
- advisory data: refresh frequently
- company GitHub footprint signals: refresh on re-run or explicit invalidation
- supporting public signals: refresh on re-run or explicit invalidation

Temporal should not replace caching. Activities should consult caches before doing expensive or rate-limited work.

## 18. Security and Compliance

Even though the MVP relies on public data, basic controls still matter.

- store only necessary user metadata
- isolate fetched raw content from rendered UI content
- sanitize HTML before display
- rate-limit external fetching
- maintain source attribution to avoid ambiguous provenance

Deferred:

- enterprise SSO
- fine-grained tenant isolation beyond standard account scoping
- private artifact secret handling

## 19. Observability

The MVP should track:

- workflow duration by stage
- fetch failures by source
- inference counts by company
- enrichment coverage
- score distribution
- export generation success

Temporal-native observability should also capture:

- parent workflow duration
- child workflow duration distribution
- activity retry counts
- failure rate by activity type
- fan-out size by analysis

It should also persist audit logs for:

- analysis created
- scoring version used
- reruns
- export events

## 20. Testing Strategy

### Unit tests

- signal normalization
- score computation
- recommendation mapping
- confidence calculation

### Integration tests

- adapter normalization
- Temporal workflow execution with fixture data
- API responses for completed and partial analyses

### Evaluation tests

- curated company fixtures with expected likely dependencies
- scoring sanity checks across known fragile vs stable projects
- explanation accuracy checks against stored evidence

## 21. MVP Delivery Sequence

### Milestone 1: Core pipeline

- company intake
- Temporal environment and worker setup
- GitHub org resolution
- repo and artifact extraction
- supporting-source ingestion
- candidate project inference

### Milestone 2: Enrichment and scoring

- project resolution
- project intelligence adapters
- scoring service
- recommendation engine

### Milestone 3: User-facing product

- portfolio UI
- dossier UI
- brief generation
- rerun support

### Milestone 4: Quality hardening

- caching
- partial-failure handling
- observability
- evaluation fixtures

## 22. Explicit Tradeoffs

### Tradeoff 1: Structured workflows over autonomous flexibility

Chosen because explainability and reproducibility matter more than agent freedom.

### Tradeoff 2: PostgreSQL-first over polyglot data infrastructure

Chosen because the MVP does not yet justify a more complex stack.

### Tradeoff 2a: Temporal over a simpler queue

Chosen because the core analysis path is long-running, fan-out heavy, retry-heavy, and benefits from durable workflow history.

### Tradeoff 3: Deterministic scores plus generated explanations

Chosen because pure LLM scoring is too hard to defend.

### Tradeoff 4: GitHub-first public evidence over broader open-web coverage

Chosen because GitHub artifacts provide more defensible dependency evidence than softer public sources while still supporting analysis without insider access.

## 23. Future Extension Points

- SBOM and manifest upload ingestion
- company correction loops that feed confidence recalibration
- recurring portfolio monitoring
- governance and licensing signals
- investment recommendation and sponsorship planning
- multi-company comparison views

## 24. Open Technical Questions

- which external sources are reliable enough for the first adapter set?
- how broad should ecosystem support be in v1?
- should the first release support near-real-time analysis, or queue-first with progressive rendering?
- what confidence threshold should suppress Tier 1 recommendations when exposure evidence is thin?
- should a resolvable public GitHub org be mandatory, or should users be allowed to provide a curated set of public repos instead?

## 25. Recommended Implementation Posture

Build the MVP as a Temporal-orchestrated, workflow-centric analyst system, not as a general-purpose autonomous agent platform.

The durable assets to invest in first are:

- evidence schema
- project normalization
- deterministic scoring
- explanation quality
- snapshot and rerun support

If those are solid, later agents and product surfaces become much easier to add.

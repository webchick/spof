# Decisions

## Purpose

This log records major product and architecture decisions for the agentic open source risk-reduction app.

Each entry captures:

- context
- options considered
- decision
- rationale
- consequences

## D-001: Start With Risk Reduction

### Context

The original product direction could have focused on:

- risk reduction
- strategic influence
- budget and portfolio planning

### Options considered

- lead with risk reduction
- lead with strategic influence
- lead with sponsorship or contribution portfolio planning

### Decision

Start with `risk reduction`.

### Rationale

- it works without insider access to company roadmaps or budget processes
- it is relevant to a broad set of companies
- it is easier to validate with public evidence
- it gives a clear MVP question:
  - which OSS dependencies are likely to create material risk?

### Consequences

- the app focuses first on dependency exposure, fragility, threat, and blast radius
- strategy and budget planning become later-stage expansions

## D-002: GitHub-First MVP

### Context

Public web inference alone creates too much ambiguity for dependency analysis.

### Options considered

- broad public-web inference from blogs, docs, jobs, and technical signals
- GitHub-first analysis using public repos and software artifacts as primary evidence

### Decision

Make the MVP `GitHub-first`.

### Rationale

- manifests, lockfiles, workflows, Dockerfiles, and IaC are stronger signals than marketing pages or hiring text
- this reduces ambiguity in exposure scoring
- it creates a narrower, more credible MVP

### Consequences

- the MVP targets companies with a meaningful public GitHub footprint
- softer public sources remain supporting evidence only
- results are framed as inference from public GitHub footprint, not full internal truth

## D-003: Soft Signals Stay In, But At Lower Confidence

### Context

Engineering blogs, docs, and job postings can still contain useful context.

### Options considered

- exclude softer sources entirely
- include softer sources as full peers to GitHub evidence
- include softer sources as supporting evidence with lower weight

### Decision

Keep softer sources as `supporting evidence with lower confidence`.

### Rationale

- they can corroborate GitHub evidence
- they help with explanation and context
- they should not be able to overpower direct artifact evidence

### Consequences

- soft signals can improve confidence modestly
- soft signals cannot independently create a top-risk item

## D-004: Use OpenSSF And CHAOSS As Inputs, Not Final Scores

### Context

The risk model needs defensible external grounding.

### Options considered

- invent a fully bespoke scoring model
- adopt one external framework wholesale
- compose multiple external frameworks into a product-specific model

### Decision

Use `OpenSSF` and `CHAOSS` as aligned inputs, then compose them into a product-specific model.

### Rationale

- OpenSSF is strong for security posture and supply-chain practices
- CHAOSS is strong for responsiveness and community health
- neither framework covers company-specific exposure inference or blast radius

### Consequences

- `Threat` is primarily OpenSSF-aligned
- `Fragility` is primarily CHAOSS-aligned
- `Exposure`, `Confidence`, `Blast Radius`, and final `Priority` remain product-specific

## D-005: Deterministic Scoring Over Black-Box Agent Judgment

### Context

The system uses agents for evidence gathering and synthesis, but users need defensible outputs.

### Options considered

- let agents assign final scores directly
- use agents only for evidence gathering and explanation, with deterministic final scoring

### Decision

Use `deterministic scoring` for final assessments.

### Rationale

- deterministic scoring is easier to audit and compare across runs
- it reduces hallucinated rationale and drift
- it makes score versioning tractable

### Consequences

- agents gather, structure, and explain
- final risk scores come from explicit scoring logic

## D-006: Temporal As The Orchestration Backbone

### Context

The analysis pipeline is long-running, fan-out oriented, dependent on flaky external systems, and useful even when partially complete.

### Options considered

- simple request/response flow
- generic background queue
- Temporal workflows and activities

### Decision

Use `Temporal` as the orchestration backbone.

### Rationale

- the workload naturally maps to parent and child workflows
- retries, timeouts, and partial failures are first-class needs
- durable workflow history supports auditability and monitoring

### Consequences

- the architecture uses `AnalysisWorkflow`, `RepoEvidenceWorkflow`, and `ProjectEnrichmentWorkflow`
- PostgreSQL stores domain state, while Temporal owns execution state and retries

## D-007: PostgreSQL As The Primary Product Data Store

### Context

The product needs durable, queryable domain state for analyses, evidence, inferences, snapshots, and results.

### Options considered

- workflow-engine-only state
- heavily polyglot data stack from the start
- PostgreSQL-first domain persistence

### Decision

Use `PostgreSQL` as the primary product data store.

### Rationale

- it is sufficient for the MVP
- it supports transactional domain writes and efficient read models
- it keeps the system simpler while the product model stabilizes

### Consequences

- raw content may live in object storage
- some source-specific data lives in JSONB
- core sort/filter fields remain typed columns

## D-008: The First Vertical Slice Should Be Narrow

### Context

The full MVP includes many evidence types and metrics, but implementation needs a safe first slice.

### Options considered

- implement all planned evidence types and all metrics immediately
- prove the core loop with a smaller vertical slice first

### Decision

Start with a narrower vertical slice:

- GitHub org input
- repo enumeration
- manifest and lockfile parsing
- candidate project inference
- limited project enrichment
- preliminary ranking

### Rationale

- it proves the hardest architectural assumptions early
- it reduces risk before softer signals and broader fragility metrics are added

### Consequences

- the first implementation will not cover the full planned signal set
- the product can still produce a credible early ranked list

## D-009: Preserve Reasoning In Public Artifacts

### Context

The model’s internal hidden reasoning is not directly visible, but the project benefits from a durable decision trail.

### Options considered

- rely only on chat history
- create a repository-level decision log

### Decision

Maintain a `DECISIONS.md` file in the branch.

### Rationale

- it makes the planning process inspectable
- it preserves rationale outside transient chat history
- it helps future implementation and collaboration

### Consequences

- major product and architecture decisions should be added here as the work evolves

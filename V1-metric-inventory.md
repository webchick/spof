# V1 Metric Inventory

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Purpose

This document defines the minimum viable metric set for v1.

It bridges planning into implementation by answering:

1. which metrics exist in v1
2. which framework or methodology each metric comes from
3. what raw data each metric needs
4. how each metric is computed
5. where each metric runs in the Temporal architecture
6. which top-level score bucket each metric feeds

## 2. Conventions

### Methodology source

- `OpenSSF-aligned`
- `CHAOSS-aligned`
- `Product-specific`

### Execution boundary

- `Temporal activity`
  - requires external I/O, crawling, API fetches, or LLM calls
- `Deterministic scoring`
  - computed from already persisted normalized data

### Priority

- `Required`
- `Useful`
- `Later`

## 3. Scoring Buckets

The v1 model keeps five top-level score buckets:

- `Exposure`
- `Confidence`
- `Fragility`
- `Threat`
- `Blast Radius`

The final `Priority` score is a product-specific rollup of those buckets.

## 4. MVP Metric Selection

The recommended minimum set for v1 is:

- product-specific metrics for `Exposure`, `Confidence`, and `Blast Radius`
- a small set of `OpenSSF-aligned` project security posture metrics for `Threat`
- a small set of `CHAOSS-aligned` project health metrics for `Fragility`

This keeps the model defensible without requiring exhaustive ecosystem coverage on day one.

## 5. Exposure Metrics

| Metric | Source | Raw data needed | Computation | Range | Feeds | Execution | Priority | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| Evidence strength | Product-specific | normalized evidence items with effective weights | roll up top weighted evidence across repos using diminishing returns | 0-45 | Exposure | Deterministic scoring | Required | Core signal for likely usage |
| Repo breadth | Product-specific | distinct repos containing non-trivial evidence for project | count repos whose strongest evidence exceeds threshold | 0-20 | Exposure | Deterministic scoring | Required | Prevents one-repo overfitting |
| Production adjacency | Product-specific | evidence item context labels such as deploy, CI, docs, runtime | assign score from strongest observed context, with bonus for multiple production-adjacent contexts | 0-20 | Exposure, Blast Radius | Deterministic scoring | Required | Strongly shapes prioritization |
| Category criticality | Product-specific | canonical project category | map category to coarse business criticality band | 0-15 | Exposure, Blast Radius | Deterministic scoring | Required | Uses static rules table |
| Direct dependency presence | Product-specific | manifest and lockfile entries | boolean or weighted signal for explicit direct package declaration | support metric | Exposure | Deterministic scoring | Required | Not user-facing alone; strengthens evidence strength |
| Cross-artifact corroboration | Product-specific | evidence classes per project | count corroborating artifact classes such as manifest + workflow + IaC | support metric | Exposure, Confidence | Deterministic scoring | Required | Helps separate real usage from mentions |
| Recency of usage evidence | Product-specific | last modified timestamps for relevant files and repos | discount stale evidence according to recency rules | support metric | Exposure, Confidence | Deterministic scoring | Required | Applied through modifiers |

## 6. Confidence Metrics

| Metric | Source | Raw data needed | Computation | Range | Feeds | Execution | Priority | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| Evidence source quality | Product-specific | evidence classes for project | assign score band based on strongest evidence class present | 0-40 | Confidence | Deterministic scoring | Required | Lockfiles/manifests dominate |
| Artifact corroboration | Product-specific | unique artifact classes per project | score based on count of corroborating artifact classes | 0-20 | Confidence | Deterministic scoring | Required | Distinguishes one-off clues from repeated confirmation |
| Evidence recency | Product-specific | timestamps of relevant files and repos | score based on age of strongest and median relevant evidence | 0-15 | Confidence | Deterministic scoring | Required | Stale repos reduce confidence |
| Resolution certainty | Product-specific | canonical project resolution results | exact package or repo match scores highest, ambiguous text scores lowest | 0-15 | Confidence | Deterministic scoring | Required | Important for avoiding false positives |
| Soft-signal agreement | Product-specific | blog/docs/job-post signals plus direct evidence | add small score only when soft signals agree with direct evidence | 0-10 | Confidence | Deterministic scoring | Useful | Never sufficient alone |
| Direct GitHub evidence count | Product-specific | count of class A-D evidence items | count direct evidence items above threshold | support metric | Confidence | Deterministic scoring | Required | Useful for analyst explanations |

## 7. Fragility Metrics

| Metric | Source | Raw data needed | Computation | Range | Feeds | Execution | Priority | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| Bus factor | CHAOSS-aligned | contributions by contributor over time window | smallest number of people accounting for 50 percent of contributions | normalized to 0-25 | Fragility | Deterministic scoring after fetch | Required | Derived from CHAOSS bus factor concept |
| Contributor concentration | CHAOSS-aligned | commit, PR, or review distribution across contributors | concentration ratio such as top 1 or top 3 share of contribution volume | normalized to 0-20 | Fragility | Deterministic scoring after fetch | Required | Simpler than elephant factor for v1 |
| Time to first response | CHAOSS-aligned | issue and PR open timestamps and first human response timestamps | median or percentile response time over recent window | normalized to 0-20 | Fragility | Deterministic scoring after fetch | Required | Exclude bots |
| Time to close | CHAOSS-aligned | issue and PR open and close timestamps | median or percentile close time over recent window | normalized to 0-15 | Fragility | Deterministic scoring after fetch | Required | Separate from first response |
| Release frequency | CHAOSS-aligned | tagged releases and release timestamps | cadence score based on expected frequency band for category | normalized to 0-10 | Fragility | Deterministic scoring after fetch | Required | Very stale projects score worse |
| Change request closure ratio | CHAOSS-aligned | opened versus closed PRs in time window | ratio of closed to opened change requests over recent period | normalized to 0-10 | Fragility | Deterministic scoring after fetch | Useful | Helps estimate maintainer throughput |

## 8. Threat Metrics

| Metric | Source | Raw data needed | Computation | Range | Feeds | Execution | Priority | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| Known vulnerabilities | OpenSSF-aligned | OSV/CVE records mapped to project | score from count, severity, and recency of known vulnerabilities | normalized to 0-20 | Threat | Deterministic scoring after fetch | Required | Core threat signal |
| Maintained status | OpenSSF-aligned | Scorecard maintained signal plus repo activity | penalize projects with poor maintained status or very stale activity | normalized to 0-10 | Threat, Fragility | Deterministic scoring after fetch | Required | Do not rely on Scorecard aggregate alone |
| Dangerous workflow posture | OpenSSF-aligned | Scorecard dangerous workflow result | high penalty if dangerous workflow patterns present | normalized to 0-10 | Threat | Deterministic scoring after fetch | Required | High-risk supply chain signal |
| Branch protection posture | OpenSSF-aligned | Scorecard branch protection result | penalty for absent or weak branch protection | normalized to 0-10 | Threat | Deterministic scoring after fetch | Required | Security governance proxy |
| Code review posture | OpenSSF-aligned | Scorecard code review result | penalty for lack of human review on recent changes | normalized to 0-10 | Threat | Deterministic scoring after fetch | Required | Also helps trust of maintainer workflow |
| Pinned dependencies posture | OpenSSF-aligned | Scorecard pinned dependencies result | penalty for weak dependency pinning practices | normalized to 0-8 | Threat | Deterministic scoring after fetch | Useful | Good supply-chain hygiene signal |
| Token permissions posture | OpenSSF-aligned | Scorecard token permissions result | penalty for unsafe workflow token configuration | normalized to 0-8 | Threat | Deterministic scoring after fetch | Useful | Especially relevant for GitHub-native projects |
| Signed releases posture | OpenSSF-aligned | Scorecard signed releases result and release metadata | penalty if official release signing is absent where expected | normalized to 0-8 | Threat | Deterministic scoring after fetch | Useful | Ecosystem support may vary |
| Security policy presence | OpenSSF-aligned | Scorecard security policy result or repo files | low-weight penalty if security policy absent | normalized to 0-6 | Threat | Deterministic scoring after fetch | Useful | Better as supporting signal |

## 9. Blast Radius Metrics

| Metric | Source | Raw data needed | Computation | Range | Feeds | Execution | Priority | Notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| Category baseline | Product-specific | canonical project category | static risk band by project class | 0-40 | Blast Radius | Deterministic scoring | Required | Identity and runtime infra score highest |
| Production adjacency | Product-specific | artifact context labels | reuse strongest production context signal from exposure pipeline | 0-25 | Blast Radius | Deterministic scoring | Required | Shared metric, different weighting |
| Repo breadth | Product-specific | count of distinct relevant repos | more repos implies wider internal footprint | 0-20 | Blast Radius | Deterministic scoring | Required | Shared input, different interpretation |
| Sensitivity clues | Product-specific | evidence that project touches auth, secrets, deployment, customer data, supply chain | additive points per high-sensitivity usage clue | 0-15 | Blast Radius | Deterministic scoring | Required | Rules-based and explainable |

## 10. Collection Activities

These metrics require upstream data collection before deterministic scoring can happen.

| Activity | Produces raw data for | Notes |
| --- | --- | --- |
| `FetchGitHubOrgRepos` | repo breadth, evidence strength | enumerates public repos and metadata |
| `ExtractRepoArtifacts` | direct dependency presence, production adjacency, corroboration, recency | parses manifests, lockfiles, workflows, Dockerfiles, IaC, docs |
| `ResolveCanonicalProjects` | resolution certainty, category criticality | maps raw references to canonical projects |
| `FetchProjectRepoMetadata` | maintained status, contributor concentration | repo activity, default branch, issue/PR summaries |
| `FetchReleaseHistory` | release frequency, signed releases posture | tag and release timelines |
| `FetchScorecardSignals` | maintained, dangerous workflow, branch protection, code review, pinned dependencies, token permissions, signed releases, security policy | check-level results preferred over aggregate score |
| `FetchAdvisoryData` | known vulnerabilities | OSV, CVE, advisory normalization |
| `FetchIssueAndPRTimings` | time to first response, time to close, closure ratio | exclude bots where possible |
| `FetchSupportingPublicSignals` | soft-signal agreement | engineering blogs, docs, job posts |

## 11. Deterministic Scoring Responsibilities

These computations should happen after the collection activities persist normalized inputs.

| Scoring function | Inputs | Outputs |
| --- | --- | --- |
| `score_exposure()` | evidence strength, repo breadth, production adjacency, category criticality | exposure score |
| `score_confidence()` | source quality, corroboration, recency, resolution certainty, soft-signal agreement | confidence score |
| `score_fragility()` | bus factor, contributor concentration, responsiveness, release frequency, closure ratio | fragility score |
| `score_threat()` | vulnerabilities and OpenSSF posture metrics | threat score |
| `score_blast_radius()` | category baseline, production adjacency, repo breadth, sensitivity clues | blast radius score |
| `score_priority()` | exposure, confidence, fragility, threat, blast radius | final priority score and tier |

## 12. Minimum Required Normalized Data Model

To support the v1 inventory, the normalized project data model should capture at least:

- canonical project identity
- project category
- evidence items with source class, path context, recency, and effective weight
- repo counts per company-project pair
- contributor activity distribution
- issue and PR response timing summaries
- release timestamps
- Scorecard check-level results
- advisory records with severity and recency
- sensitivity flags for auth, secrets, deployment, customer data, and supply-chain relevance

## 13. Recommended v1 Cut Line

If the implementation team needs a harder MVP cut, ship these first:

### Exposure and confidence

- evidence strength
- repo breadth
- production adjacency
- category criticality
- evidence source quality
- artifact corroboration
- evidence recency
- resolution certainty

### Fragility

- bus factor
- contributor concentration
- time to first response
- release frequency

### Threat

- known vulnerabilities
- maintained status
- dangerous workflow posture
- branch protection posture
- code review posture

### Blast radius

- category baseline
- production adjacency
- sensitivity clues

That set is enough to produce a credible first pass.

## 14. Deferred Metrics

These are reasonable second-wave additions:

- elephant factor as a separate metric
- security policy maturity beyond simple presence
- fuzzing and SAST posture
- dependency update tool posture
- packaging hygiene
- deeper release signing nuance by ecosystem
- maintainer organization diversity beyond simple contributor concentration

## 15. Implementation Difficulty Notes

### Low difficulty

- repo breadth
- category criticality
- evidence source quality
- artifact corroboration
- production adjacency

### Medium difficulty

- resolution certainty
- bus factor
- contributor concentration
- release frequency
- branch protection and code review posture ingestion

### Higher difficulty

- time to first response with bot filtering
- time to close with meaningful windows
- robust advisory normalization across ecosystems
- signed release posture normalization across non-uniform ecosystems

## 16. Open Decisions

- whether `go.sum` and lockfile-only hits should be downweighted relative to direct manifest dependencies
- whether contributor concentration should be based on commits only or a blended contribution model
- whether issue responsiveness should be repository-level, project-level, or both for multi-repo projects
- whether Scorecard signals should be fetched live, cached centrally, or recomputed on demand
- whether time-window defaults should be 90 days, 180 days, or 12 months for health metrics

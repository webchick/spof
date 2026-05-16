# V1 Evidence And Scoring Spec

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Purpose

This document defines the concrete evidence model and scoring heuristics for the GitHub-first MVP.

It answers four implementation questions:

1. which GitHub artifacts count as dependency evidence
2. how evidence is resolved to canonical OSS projects
3. how evidence rolls up into exposure and confidence
4. what gates must be met before a project can be surfaced as a top risk

## 2. Scope

This spec covers:

- company-to-project inference
- evidence weighting
- exposure scoring
- confidence scoring
- blast radius heuristics
- top-risk tier gating

This spec does not try to fully define:

- fragility feature extraction internals
- threat ingestion internals
- recommendation copy templates

Those should be specified separately once the inference layer is stable.

## 2.1 Methodology Sources

The MVP risk model is a composition of three methodology sources:

- `OpenSSF-aligned`
  - security posture and software supply-chain practice signals
- `CHAOSS-aligned`
  - community health, responsiveness, and contributor sustainability signals
- `Product-specific`
  - company exposure inference, confidence calibration, blast-radius estimation, and portfolio ranking logic

The system should explicitly report this distinction in internal documentation and, where useful, in analyst-facing explanations.

## 3. Core Principle

Not all evidence is equal.

For v1:

- direct GitHub software artifacts outrank all other signals
- explicit dependency declarations outrank mentions
- production-adjacent artifacts outrank local-dev artifacts
- repeated evidence across repos outranks one-off mentions
- recent evidence outranks stale evidence

This principle is `product-specific`, because neither OpenSSF nor CHAOSS defines company-specific dependency inference from a target organization's public GitHub footprint.

## 4. Primary Evidence Classes

### Class A: Explicit dependency declarations

These are the strongest signals.

Examples:

- `package.json`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `requirements.txt`
- `poetry.lock`
- `pyproject.toml`
- `Pipfile.lock`
- `go.mod`
- `go.sum`
- `Cargo.toml`
- `Cargo.lock`
- `pom.xml`
- `build.gradle`

Interpretation:

- exact package reference
- usually direct or transitive dependency evidence
- high canonicalization confidence

### Class B: Build and runtime artifacts

These are strong signals, especially for infra and operational tooling.

Examples:

- `Dockerfile`
- `docker-compose.yml`
- `.devcontainer/*`
- `Makefile`
- shell scripts used for build or deploy
- runtime base images
- install commands in build scripts

Interpretation:

- may indicate runtime dependencies, deployment dependencies, or build chain dependencies
- stronger for infra projects than for application libraries

### Class C: CI/CD and automation artifacts

These are strong signals for build, delivery, security, and quality tooling.

Examples:

- `.github/workflows/*.yml`
- reusable GitHub Actions references
- CI setup scripts
- release automation config

Interpretation:

- strong signal for OSS tools used in delivery, testing, and supply chain
- weak signal for core production runtime unless corroborated elsewhere

### Class D: Infrastructure and deployment artifacts

These are strong production-adjacent signals.

Examples:

- `terraform/*.tf`
- `helm/*.yaml`
- `k8s/*.yaml`
- `charts/*`
- `skaffold.yaml`
- `ansible/*`
- `pulumi/*`

Interpretation:

- strong signal for operational tooling, platforms, and infra dependencies
- often raises blast-radius relevance

### Class E: Source code references

Examples:

- `import` statements
- `require()` calls
- module paths
- package namespaces in code

Interpretation:

- useful corroborating evidence
- weaker than manifests because import paths can be ambiguous
- often better for confirming usage than for canonical package resolution

### Class F: Repository documentation

Examples:

- repo `README`
- `/docs`
- onboarding instructions
- architecture notes

Interpretation:

- medium-confidence evidence
- useful for confirming role and context
- should not outweigh stronger artifact evidence

### Class G: Supporting public signals

Examples:

- engineering blog posts
- public technical docs outside GitHub repos
- conference talks
- job postings
- public stack fingerprinting

Interpretation:

- supporting evidence only
- useful when it corroborates GitHub signals
- insufficient on its own for high-priority exposure tiers

## 5. Initial Ecosystem Coverage

V1 should explicitly support:

- `npm`
- `PyPI`
- `Go modules`
- `Docker/container images`
- `GitHub Actions`
- `Kubernetes/Helm/Terraform-adjacent infrastructure`

V1 may parse other ecosystems when found, but should not promise equal coverage.

## 5.1 Framework Mapping

### OpenSSF-aligned inputs

Use OpenSSF-aligned signals primarily for `threat` and selected parts of `fragility`.

Examples:

- Scorecard check results
- OSV or CVE-linked project vulnerability signals
- security-policy presence
- dangerous workflow patterns
- branch protection and code review posture
- signed releases or packaging-related signals
- maintained status and dependency update automation

OpenSSF sources:

- [OpenSSF Scorecard](https://scorecard.dev/)
- [OpenSSF Scorecard checks documentation](https://github.com/ossf/scorecard/blob/main/docs/checks.md)
- [OpenSSF on custom policy enforcement](https://openssf.org/blog/2024/04/17/beyond-scores-with-openssf-scorecard-granular-structured-results-for-custom-policy-enforcement/)
- [Security Insights Specification](https://openssf.org/security-insights-spec/)

### CHAOSS-aligned inputs

Use CHAOSS-aligned signals primarily for `fragility`.

Examples:

- bus factor
- committers / contributor robustness
- elephant factor or concentration metrics
- time to first response
- time to close
- change request closure ratio
- release frequency

CHAOSS sources:

- [CHAOSS metrics and metrics models](https://chaoss.community/kb-metrics-and-metrics-models/)
- [Starter Project Health Metrics Model](https://chaoss.community/starter-project-health-metrics-model/)
- [Development Responsiveness model](https://chaoss.community/kb/metrics-model-development-responsiveness/)
- [Time to First Response](https://chaoss.community/kb/metric-time-to-first-response/)
- [Time to Close](https://chaoss.community/kb/metric-time-to-close/)

### Product-specific inputs

These remain unique to this product:

- company-to-project exposure inference
- evidence weighting across GitHub artifact classes
- confidence scoring for inferred usage
- production adjacency estimation
- blast-radius estimation
- tier gating for company-contextual prioritization

## 6. Evidence Weight Table

These are base weights before modifiers.

| Evidence type | Base weight |
| --- | ---: |
| Lockfile entry | 1.00 |
| Manifest dependency entry | 0.95 |
| Workflow action reference | 0.90 |
| Deployment or IaC artifact reference | 0.90 |
| Runtime container base image | 0.88 |
| Build script install/reference | 0.82 |
| Source code import/reference | 0.72 |
| README or repo docs mention | 0.50 |
| Engineering blog or external docs mention | 0.35 |
| Job posting mention | 0.20 |
| Generic stack fingerprint | 0.15 |

## 7. Evidence Modifiers

Each evidence item should receive modifiers based on context.

### 7.1 Specificity modifier

- exact package or repo match: `1.00`
- exact namespace but ambiguous package: `0.85`
- fuzzy or text-only match: `0.60`

### 7.2 Context modifier

- production or deploy path: `1.25`
- CI/CD or build path: `1.10`
- app runtime path: `1.10`
- docs/example/sample path: `0.70`
- test-only path: `0.75`

### 7.3 Recency modifier

- file changed within 12 months: `1.00`
- changed within 12-24 months: `0.85`
- changed more than 24 months ago: `0.65`
- archived repo: `0.50`

### 7.4 Repo relevance modifier

- top-tier active repo in org: `1.00`
- medium-activity repo: `0.85`
- sandbox or experimental repo: `0.60`
- fork with no unique activity: `0.40`

## 8. Canonical Project Resolution Rules

Project resolution should follow a strict precedence order.

### Resolution order

1. exact manifest or lockfile package identifier
2. exact GitHub Action slug
3. exact image name or registry path
4. exact Terraform provider/module reference
5. exact import/module path
6. exact repo URL mention
7. text-only mention with disambiguation

### Resolution rules

- prefer ecosystem-native package IDs over display names
- map aliases to a canonical project record
- separate packages from upstream repos when that distinction matters
- record ambiguity rather than forcing a match

### When not to resolve

Do not promote an ambiguous text mention into a canonical project if:

- multiple well-known projects share the same name
- the mention is generic and lacks ecosystem context
- the only source is a low-confidence public signal

## 9. Evidence Item Schema Requirements

Each evidence item should store:

- `source_class`
- `evidence_type`
- `repo_name`
- `file_path`
- `line_span` where available
- `raw_value`
- `normalized_value`
- `canonical_project_id` if resolved
- `base_weight`
- `specificity_modifier`
- `context_modifier`
- `recency_modifier`
- `repo_relevance_modifier`
- `effective_weight`

`effective_weight` =

`base_weight * specificity_modifier * context_modifier * recency_modifier * repo_relevance_modifier`

## 10. Company-to-Project Rollup

Evidence must roll up from many file-level observations into one company-project inference.

### 10.1 Per-repo aggregation

For each project within a repo:

- group all evidence items by project
- take the top 3 highest-weight items
- sum them with diminishing returns

Suggested formula:

`repo_project_score = w1 + (0.6 * w2) + (0.35 * w3)`

This avoids one repo with 40 repeated references dominating the result.

### 10.2 Cross-repo aggregation

For the company-level project score:

- sort `repo_project_score` descending across repos
- sum with diminishing returns

Suggested formula:

`company_project_signal = r1 + (0.7 * r2) + (0.5 * r3) + (0.35 * r4+)`

Cap the final raw signal at `3.0` before normalization.

### 10.3 Direct vs supporting evidence rule

Supporting public signals may only:

- increase confidence modestly
- break ties
- improve narrative explanation

They may not, by themselves, push a project into the top-risk set.

## 11. Exposure Score

Exposure should answer:

"How likely is this company to meaningfully depend on this project?"

### 11.1 Exposure components

`exposure_score` is composed of:

- evidence strength: `0-45`
- repo breadth: `0-20`
- production adjacency: `0-20`
- category criticality: `0-15`

Total:

- `0-100`

### 11.2 Evidence strength

Normalize `company_project_signal` into `0-45`.

Suggested heuristic:

- very weak signal: `0-10`
- moderate signal: `11-25`
- strong multi-artifact signal: `26-35`
- repeated strong signal across multiple repos: `36-45`

### 11.3 Repo breadth

Award based on number of distinct repos with non-trivial evidence.

- 1 repo: `5`
- 2 repos: `10`
- 3 repos: `14`
- 4 repos: `17`
- 5 or more repos: `20`

Ignore repos whose best evidence item has `effective_weight < 0.35`.

### 11.4 Production adjacency

Award based on the strongest context in which the project appears.

- docs only: `0`
- dev/test only: `4`
- CI/build only: `8`
- runtime app code or container build: `12`
- deployment/IaC/cluster/runtime infrastructure: `16`
- multiple production-adjacent contexts: `20`

### 11.5 Category criticality

Award a coarse baseline based on project class.

- peripheral dev tooling: `2-5`
- testing/quality/security tooling: `5-8`
- observability/build/runtime tooling: `8-11`
- messaging/database/networking/storage: `10-13`
- identity/crypto/package distribution/runtime platform: `12-15`

## 12. Confidence Score

Confidence should answer:

"How confident are we that the exposure claim is directionally correct?"

Confidence is not the same as exposure.

### 12.1 Confidence components

`confidence_score` is composed of:

- evidence source quality: `0-40`
- corroboration across artifact types: `0-20`
- recency: `0-15`
- resolution certainty: `0-15`
- soft-signal agreement: `0-10`

Total:

- `0-100`

### 12.2 Evidence source quality

- explicit lockfile or manifest evidence: `30-40`
- workflow/IaC/container evidence only: `20-30`
- code-import evidence only: `12-22`
- docs-only repo evidence: `8-15`
- soft signals only: `0-8`

### 12.3 Corroboration

- one artifact class only: `4`
- two corroborating artifact classes: `10`
- three or more corroborating artifact classes: `15-20`

### 12.4 Recency

- strong evidence in active repo within 12 months: `12-15`
- evidence mostly 12-24 months old: `7-11`
- evidence mostly stale: `0-6`

### 12.5 Resolution certainty

- exact canonical package or repo mapping: `12-15`
- ecosystem-known but somewhat ambiguous mapping: `7-11`
- text-based or weakly resolved mapping: `0-6`

### 12.6 Soft-signal agreement

- no supporting signals: `0`
- supporting signals consistent with direct evidence: `4-8`
- multiple external supporting signals consistent with direct evidence: `9-10`

## 13. Blast Radius Heuristics

Blast radius should remain heuristic in v1, but it must be anchored in observable context.

### Blast radius components

- project category baseline: `0-40`
- production adjacency: `0-25`
- repo breadth: `0-20`
- security/operational sensitivity clues: `0-15`

### Category baseline guidance

- test or local-dev tooling: `5-12`
- CI/build/release tooling: `15-22`
- observability tooling: `18-25`
- app framework/runtime: `20-28`
- databases, messaging, networking: `24-32`
- identity, crypto, package distribution, cluster/runtime control plane: `30-40`

### Sensitivity clues

Add points if evidence indicates the project touches:

- authentication or authorization
- secret handling
- software supply chain
- production deployment
- customer data paths

## 14. Fragility And Threat Summary Rules

These remain separate subsystems, but v1 should observe these guardrails.

### Fragility should emphasize

- maintainer concentration
- contributor concentration
- release irregularity
- stale issue or PR responsiveness

Primary methodology source:

- `CHAOSS-aligned`

Suggested first metrics to adopt:

- Bus Factor
- Committers or contributor robustness
- Time to First Response
- Time to Close
- Release Frequency

These map well to CHAOSS starter and responsiveness models, even if the final normalized `fragility_score` remains product-specific.

### Threat should emphasize

- recent advisories and CVEs
- repeated severe incidents
- supply-chain compromise patterns
- abandonment or end-of-life signals

Primary methodology source:

- `OpenSSF-aligned`

Suggested first signals to adopt:

- Scorecard `Vulnerabilities`
- Scorecard `Maintained`
- Scorecard `Branch-Protection`
- Scorecard `Code-Review`
- Scorecard `Dangerous-Workflow`
- Scorecard `Pinned-Dependencies`
- Scorecard `Token-Permissions`
- Scorecard `Signed-Releases`
- OSV/CVE advisory presence and severity

The final `threat_score` should not simply mirror the aggregate Scorecard value. It should use selected check-level outputs plus external advisory data.

## 14.1 Feature Provenance Table

| Feature area | Primary source |
| --- | --- |
| Company GitHub artifact evidence | Product-specific |
| Evidence weighting and modifiers | Product-specific |
| Canonical project resolution | Product-specific |
| Exposure score | Product-specific |
| Confidence score | Product-specific |
| Blast radius heuristics | Product-specific |
| Vulnerability/advisory signals | OpenSSF-aligned |
| Secure development practice signals | OpenSSF-aligned |
| Maintained status signals | OpenSSF-aligned |
| Responsiveness signals | CHAOSS-aligned |
| Contributor concentration signals | CHAOSS-aligned |
| Release frequency / cadence health | CHAOSS-aligned |
| Final priority and tier gating | Product-specific |

## 15. Priority Score

V1 keeps the architecture-level formula:

`priority = (exposure_score * confidence_score / 100) * (0.30 * fragility + 0.35 * threat + 0.35 * blast_radius) / 100`

Normalize final output to `0-100`.

Interpretation:

- high threat with low confidence should not dominate
- high-confidence low-blast-radius dev tooling should usually not outrank weaker but critical infra risks

The final priority score is intentionally `product-specific`. It composes OpenSSF-aligned and CHAOSS-aligned signals into a company-contextual decision model rather than reproducing any external framework's aggregate score.

## 16. Tier Gating Rules

These rules are more important than precision.

### Tier 1: Act now

Requirements:

- `priority >= 75`
- `confidence_score >= 65`
- at least one direct GitHub artifact of Class A, B, C, or D
- at least one of:
  - `threat >= 70`
  - `fragility >= 75`
  - `blast_radius >= 75`

### Tier 2: Investigate this quarter

Requirements:

- `priority >= 55`
- `confidence_score >= 50`
- at least one direct GitHub artifact or multiple corroborating medium-confidence signals

### Tier 3: Monitor

Requirements:

- `priority >= 30`
- some evidence exists, but confidence, severity, or production adjacency is weaker

### Tier 4: Low priority or weak evidence

Requirements:

- below Tier 3 thresholds
- or confidence is too weak to support action

## 17. Suppression Rules

Do not surface a project in the top 10 if:

- all evidence is soft-signal only
- the project resolution is ambiguous
- the only GitHub evidence is stale docs/examples/tests
- the project is only present in archived or abandoned internal repos

Unless:

- threat signals are extreme and external evidence strongly suggests real usage

That exception should be rare in v1.

## 18. Recommendation Mapping Heuristics

These should remain constrained and score-driven.

- high confidence + high threat + high blast radius: `add compensating controls`, `plan migration or replacement`, or `validate internal usage`
- high confidence + high fragility + moderate threat: `sponsor maintainers` or `contribute upstream fixes`
- medium confidence + high severity: `validate internal usage`
- low confidence + moderate severity: `monitor`

In v1, `validate internal usage` should be common. It is the safest action under uncertainty.

## 19. Analyst-Facing Explanation Requirements

For each surfaced project, the UI should show:

- top 3 evidence items
- source classes for those items
- confidence explanation
- why the project matters operationally
- why the recommendation fits
- which parts of the assessment are OpenSSF-aligned, CHAOSS-aligned, or product-specific when relevant

The user should be able to answer:

- why do you think they use this?
- how sure are you?
- why is it risky?
- what should I do next?

## 20. Evaluation Fixtures

To validate the model, build fixture sets for:

- companies with strong public repos and obvious dependencies
- companies with mixed public/private footprints
- repos where tooling appears only in CI
- repos where docs mentions would otherwise create false positives
- infra-heavy orgs with Kubernetes/Terraform evidence

The model should be tested against false positives such as:

- examples directories
- dependency tutorials
- archived demos
- forked repos with inherited manifests

## 21. Recommended First Implementation Order

1. manifest and lockfile parsers
2. workflow and IaC parsers
3. canonical project resolution
4. evidence weighting and rollup
5. confidence calculation
6. exposure scoring
7. tier gating
8. explanation rendering

## 22. Open Decisions

- whether `README` and repo docs should be treated as one evidence class or split
- whether GitHub Actions should resolve to marketplace actions, underlying repos, or both
- whether transitive dependencies from lockfiles should receive lower exposure than direct manifest dependencies in v1
- whether archived repos should be fully ignored or just heavily discounted
- which OpenSSF Scorecard checks should be first-class inputs versus secondary enrichments in v1
- which CHAOSS metrics should be implemented directly versus approximated from available GitHub data

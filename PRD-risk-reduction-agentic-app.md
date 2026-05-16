# Product Requirements Document

## Product

Open source risk-reduction agent for company dependency exposure analysis

## Version

V1 MVP

## Status

Draft

## 1. Summary

This product helps users identify the open source projects most likely to create material risk for a target company, even when the user does not have insider access to that company's internal roadmap, budget, or software inventory.

The MVP is GitHub-first. It uses a company's public GitHub organization and repositories as the primary observable evidence base for inferring likely open source dependencies, then supplements that evidence with softer public signals such as engineering blogs, docs, and job postings at lower confidence.

The system enriches the most relevant projects with ecosystem health and security signals, then produces a ranked risk brief with recommended actions.

The product is designed as an agentic decision-support system, not an autonomous decision-maker. It gathers evidence, scores risk, explains uncertainty, and recommends next steps.

## 2. Problem Statement

Companies depend heavily on open source software, but many lack a clear view of which upstream projects create the greatest business risk. This is especially hard for external analysts, investors, partners, or strategy teams who want to assess a company without privileged internal access.

Current alternatives are weak:

- Generic OSS health dashboards lack company-specific context.
- Security tools focus too narrowly on CVEs and known inventories.
- Manual research is slow, inconsistent, and difficult to defend.

Users need a system that can answer:

"Given what this company likely depends on, which open source projects pose the highest risk, why, and what should be done next?"

## 3. Product Goal

Deliver a credible, explainable top-10 OSS risk assessment for a target company with a meaningful public GitHub footprint, using GitHub-derived dependency evidence plus ecosystem intelligence.

## 4. Target Users

Primary users:

- Engineering strategy teams
- Platform and architecture leads
- OSPO teams
- Security and supply-chain risk teams
- External analysts evaluating companies

Economic buyers:

- CTO
- VP Engineering
- Head of Platform
- OSPO lead
- Security leadership

## 5. User Needs

Users need to:

- infer a target company's likely critical OSS dependencies
- understand where the highest upstream risks are
- see the evidence behind each inference
- understand uncertainty rather than false precision
- receive a concise list of recommended next actions
- export a memo suitable for leadership review

## 6. JTBD

When I am evaluating a company with a public GitHub footprint and do not have full internal context, I want to identify the open source projects most likely to create material risk, so I can prioritize investigation or intervention.

## 7. MVP Scope

### In scope

- company-level analysis starting from a company name, domain, or GitHub org
- GitHub-first inference of likely OSS dependencies from public repos and software artifacts
- secondary evidence from softer public sources, such as engineering blogs, docs, and job postings
- enrichment of the top inferred projects with health and threat signals
- risk scoring across exposure, fragility, threat, and blast radius
- ranked portfolio of top OSS risks
- project dossiers with evidence and explanation
- executive brief / exportable memo
- recommendation generation for each high-risk project

### Out of scope

- analysis for companies with no meaningful public GitHub footprint
- full internal dependency inventory accuracy
- private codebase scanning
- SBOM ingestion as a primary path
- budget allocation or portfolio optimization
- licensing and governance scoring
- automated sponsorship or procurement workflows
- autonomous outreach to maintainers or vendors

## 8. Product Principles

- Be explicit about uncertainty.
- Prefer explainability over model complexity.
- Recommend actions, not just scores.
- Treat public GitHub evidence as the primary observable footprint, not ground truth.
- Treat softer public sources as supporting evidence unless corroborated.
- Optimize for defensible analysis over exhaustive coverage.

## 9. Core User Flow

1. User enters a company name, domain, or GitHub org.
2. System discovers the company's public GitHub organization and repositories.
3. System extracts likely dependency and infrastructure evidence from public software artifacts.
4. System supplements with softer public signals where helpful.
5. System assembles a probable OSS footprint with confidence levels.
6. System enriches the top candidate projects with risk intelligence.
7. System scores and ranks the top risks.
8. User reviews the portfolio and drills into project dossiers.
9. User exports an executive brief or shares findings internally.

## 10. User Stories

### Company Intake

- As a user, I want to enter a company domain or GitHub org and start an analysis without uploading internal artifacts.
- As a user, I want to see what evidence the system used to infer likely technologies and dependencies from GitHub.
- As a user, I want softer public sources to support the analysis without outweighing direct software artifact evidence.

### Risk Portfolio

- As a user, I want a ranked list of the most material OSS risks for a company.
- As a user, I want each risk to show confidence, rationale, and recommended next action.

### Project Dossier

- As a user, I want to inspect the evidence behind a project's score.
- As a user, I want to understand whether the risk comes from maintainer fragility, security exposure, or likely blast radius.

### Executive Brief

- As a user, I want an exportable summary I can hand to a CTO or strategy lead.
- As a user, I want the summary to be readable without opening the dashboard.

## 11. Functional Requirements

### 11.1 Company Footprint Inference

The system must:

- accept a company name, domain, or GitHub org as input
- discover relevant public signals such as:
  - GitHub organizations
  - public repositories
  - dependency manifests and lockfiles
  - CI/CD workflows
  - Dockerfiles and container definitions
  - IaC and deployment configs
  - engineering blogs
  - job postings
  - technical docs
  - stack fingerprints where appropriate
- infer likely OSS technologies and projects
- attach evidence and confidence to each inference

GitHub-derived software artifacts are the primary evidence source in v1. Non-GitHub public signals are supporting evidence with lower default confidence.

### 11.2 Project Intelligence Enrichment

The system must:

- resolve inferred projects to canonical repositories or packages where possible
- collect health and security signals for each project
- normalize signals into structured attributes

Signals in v1 should include:

- release cadence and recency
- maintainer concentration
- contributor concentration
- issue and PR responsiveness patterns
- advisory and CVE history
- signs of abandonment or instability
- indicators of criticality category, such as identity, build, crypto, database, messaging, observability, or runtime infrastructure

### 11.3 Risk Scoring

The system must produce:

- exposure score
- confidence score
- fragility score
- threat score
- blast radius score
- overall priority score
- risk tier

The system must show a plain-language explanation of why a project received its tier.

### 11.4 Recommendations

The system must generate one or more next actions from a constrained set:

- monitor
- validate internal usage
- reduce dependency concentration
- add compensating controls
- contribute upstream fixes
- sponsor maintainers
- plan migration or replacement

### 11.5 Reporting

The system must provide:

- a ranked portfolio view
- a project detail view
- a short executive brief
- exportable output in markdown or PDF-ready format

## 12. Non-Functional Requirements

- analysis should complete fast enough for interactive use on a single company
- evidence provenance must be retained for each inference and score
- the system must never present inferred usage as certain fact
- the UI should make confidence and uncertainty obvious
- the system should support re-running analyses as new signals emerge
- the system should distinguish direct GitHub-derived evidence from supporting soft-signal evidence

## 13. Risk Model

### Exposure

How likely is the company to depend on the project, and how important is it if true?

Inputs:

- direct evidence from public repos, manifests, lockfiles, workflows, infra files, docs, and package traces
- indirect evidence from public architecture clues and hiring signals
- category criticality
- likely direct versus transitive usage
- cross-repo occurrence and recency of use

Outputs:

- exposure score
- confidence score

### Fragility

How brittle is the project or its maintainer base?

Inputs:

- maintainer concentration
- contributor concentration
- release inconsistency
- issue backlog and response patterns
- signals of under-resourcing

Output:

- fragility score

### Threat

How likely is a security or operational problem to surface?

Inputs:

- recent advisories and CVEs
- exploitability patterns where available
- abandonment signals
- repeated supply-chain or release issues

Output:

- threat score

### Blast Radius

If the project fails or is compromised, how bad is the impact likely to be?

Inputs:

- likely placement in critical production paths
- security sensitivity
- customer-facing versus internal role
- role in identity, build, runtime, storage, networking, or observability layers

Output:

- blast radius score

### V1 Score Formula

`priority = (exposure_score * confidence_score) * (0.30 * fragility + 0.35 * threat + 0.35 * blast_radius)`

### Risk Tiers

- Tier 1: act now
- Tier 2: investigate this quarter
- Tier 3: monitor
- Tier 4: low priority or weak evidence

## 14. Agent Responsibilities

### Company Footprint Agent

Responsibilities:

- discover public evidence
- infer likely stack components
- map evidence to candidate OSS projects
- assign confidence

### Project Intelligence Agent

Responsibilities:

- gather repo, package, release, and advisory data
- evaluate maintainer and contributor concentration
- detect signs of project instability

### Risk Scoring Agent

Responsibilities:

- normalize raw evidence
- generate dimension scores
- assign overall priority and tier

### Recommendation Agent

Responsibilities:

- map risk patterns to recommended actions
- explain why a recommendation fits the project

### Briefing Agent

Responsibilities:

- write the executive brief
- summarize top findings
- preserve uncertainty and evidence references

## 15. Core Screens

### Company Overview

Shows:

- target company
- analysis status
- inferred stack areas
- top inferred dependencies
- confidence distribution

### Risk Portfolio

Shows:

- ranked OSS projects
- tier
- confidence
- primary risk driver
- recommended action
- evidence type mix, such as direct GitHub evidence versus supporting public signals

### Project Dossier

Shows:

- why the system believes the company uses the project
- evidence sources
- evidence confidence by source type
- score breakdown
- maintainer and threat indicators
- recommended action

### Executive Brief

Shows:

- top 5 to 10 risks
- major themes
- highest-confidence findings
- next-step recommendations

## 16. Data Inputs

### Required in v1

- public GitHub org and repository data
- dependency manifests, lockfiles, workflows, container files, and infra files where available
- supporting public web evidence
- package and project metadata
- release history
- advisory and CVE data

### Deferred

- private repository access
- SBOM and manifest uploads
- service catalog integration
- incident and ticketing system integration

## 17. Success Metrics

### Product usefulness

- users can identify the top 10 risks for a company within one session
- users report that recommendations are understandable and defensible
- users can export a brief without significant manual rewriting

### Analysis quality

- each top-ranked project includes clear evidence and confidence
- users accept or retain a meaningful share of the top recommendations after review
- false-confidence incidents are minimized

### Business value

- users return to analyze multiple companies
- users use exported briefs in internal discussions or sales motions

## 18. Assumptions

- a meaningful public GitHub footprint is sufficient to infer enough of a company's footprint to generate useful first-pass risk analysis
- users will accept a probabilistic model if confidence and evidence are clearly shown
- maintainership fragility and threat exposure are strong enough signals to create actionable output without insider roadmap data

## 19. Main Risks

- inference quality may be too weak for companies with sparse, unrepresentative, or stale public GitHub repositories
- public evidence may over-index on visible systems rather than business-critical systems
- scoring could appear overly precise if the UI does not foreground uncertainty
- advisory data may be uneven across ecosystems

## 20. Mitigations

- show evidence and confidence on every inference
- prefer GitHub-derived software artifacts over softer public signals when sources conflict
- separate "likely used" from "confirmed used"
- restrict v1 to a short list of high-signal ecosystems and project categories
- keep recommendations constrained and explainable

## 21. Go-To-Market Wedge

Positioning:

"An AI analyst that estimates open source dependency risk from a company's public GitHub footprint and supporting public technical signals."

Best early use cases:

- external company analysis
- platform and architecture reviews
- OSPO prioritization
- enterprise supply-chain risk review

## 22. Phase Roadmap

### Phase 1: MVP

- public GitHub org and repo analysis
- extraction from manifests, lockfiles, workflows, container files, and infra configs
- softer public-source supplementation at lower confidence
- risk scoring for security, fragility, and blast radius
- ranked portfolio
- project dossiers
- executive brief

### Phase 2

- private artifact upload such as SBOMs and manifests
- analyst corrections and feedback loops
- deeper ecosystem coverage
- historical re-scan and change tracking

### Phase 3

- investment recommendation depth
- sponsorship and contribution planning
- governance and licensing expansion
- portfolio management workflows

## 23. Open Questions

- which ecosystems should be first-class in v1, such as npm, PyPI, Go, containers, or Kubernetes-adjacent infrastructure?
- what minimum evidence threshold is required before a project can enter Tier 1 or Tier 2?
- should the first release optimize for interactive web analysis, exported reports, or both equally?
- should analysis require a resolvable public GitHub org, or allow user-supplied public repos as an alternative entry path?

## 24. Non-Goals For V1

- proving exact dependency inventories
- replacing enterprise SCA tools
- making legal judgments on licensing
- making financial allocation decisions
- acting autonomously on behalf of users

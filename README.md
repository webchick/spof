# SPOF - Single Point of Failure Analysis Tool

A utility to analyze OSS dependencies for GitHub organizations and calculate SPOF (Single Point of Failure) scores to guide open source investment decisions.

## Overview

SPOF helps OSPOs, DevRel teams, and Marketing teams understand which open source projects are most critical to their organization and where to invest resources for maximum impact.

The tool:
1. Fetches the most popular repositories from a GitHub organization
2. Generates Software Bill of Materials (SBOMs) for each repository
3. Analyzes dependencies using multiple data sources (GitHub API, deps.dev)
4. Calculates SPOF scores based on configurable weights
5. Generates actionable recommendations for OSS investment

## Features

- **Automated dependency discovery** using Syft for multi-language support
- **Configurable scoring weights** to match your organization's priorities
- **Multiple data sources** for comprehensive analysis (GitHub, deps.dev)
- **JSON and CSV exports** for further analysis
- **Actionable recommendations** prioritized by impact

## Installation

### Prerequisites

- Python 3.8+
- Git
- Syft (for SBOM generation)
- GitHub Personal Access Token

### 1. Install Syft

macOS:
```bash
brew install syft
```

Linux:
```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
```

For other installation methods, see: https://github.com/anchore/syft

### 2. Clone the repository

```bash
git clone https://github.com/yourusername/spof.git
cd spof
```

### 3. Install the package

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

This installs the `spof` command and all dependencies.

### 4. Set up configuration

```bash
cp .env.example .env
```

Edit `.env` and add your GitHub Personal Access Token:
```
GITHUB_TOKEN=your_github_token_here
```

To create a GitHub token:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo` (or `repo` for private repos)
4. Copy the token to your `.env` file

## Configuration

Edit `config.yaml` to customize your analysis:

```yaml
github:
  org: "your-org-name"        # GitHub organization to analyze
  token: "${GITHUB_TOKEN}"    # Reference to environment variable
  max_repos: 20               # Number of top repos to analyze

scoring:
  weights:
    internal_criticality: 0.30  # How critical to your org
    ecosystem_popularity: 0.25  # Broader ecosystem usage
    maintainer_risk: 0.20       # Maintenance SPOF risk
    security_health: 0.15       # Security posture
    upstream_activity: 0.10     # Active maintenance

data_sources:
  enabled:
    - github
    - depsdev

output:
  format: json
  file: "spof_analysis_{org}_{date}.json"
  directory: "output"
```

### Adjusting Scoring Weights

Customize the scoring weights to match your organization's priorities:

- **High internal focus**: Increase `internal_criticality` weight
- **Security-conscious**: Increase `security_health` weight
- **Sustainability focus**: Increase `maintainer_risk` and `upstream_activity` weights
- **Popular projects**: Increase `ecosystem_popularity` weight

Weights must sum to 1.0.

## Usage

### Basic analysis with organization name

```bash
spof <org-name>
```

Example:
```bash
spof kubernetes
```

### With additional options

```bash
# Analyze with debug logging
spof kubernetes --debug

# Limit to 5 repos
spof kubernetes --max-repos 5

# Generate CSV export
spof kubernetes --output-csv

# Disable caching (always fetch fresh data)
spof kubernetes --no-cache

# Clear cache before running
spof kubernetes --clear-cache

# Combine multiple options
spof kubernetes --max-repos 10 --debug --output-csv
```

### Caching

The tool automatically caches API responses for 24 hours to:
- **Reduce API calls** and avoid rate limits
- **Speed up repeated analyses** (10x+ faster on cache hits)
- **Save your GitHub API quota** (5,000 requests/hour limit)

Cache is stored in `.cache/` directory. Use `--no-cache` to bypass or `--clear-cache` to reset.

### Using config file only

If you prefer to set the organization in `config.yaml`, you can run without arguments:

```bash
spof
```

### Custom configuration file

```bash
spof kubernetes --config my-config.yaml
```

## Output

### JSON Report

The tool generates a comprehensive JSON report with:

```json
{
  "organization": "example-org",
  "analysis_date": "2025-11-30T...",
  "config": {
    "repos_analyzed": 15,
    "scoring_weights": { ... }
  },
  "summary": {
    "total_dependencies": 234,
    "critical_dependencies": 8,
    "high_priority": 15
  },
  "dependencies": [
    {
      "name": "requests",
      "ecosystem": "PyPI",
      "spof_score": 85.3,
      "confidence": 0.92,
      "metrics": {
        "internal_criticality": 90,
        "ecosystem_popularity": 95,
        "maintainer_risk": 60,
        "security_health": 88,
        "upstream_activity": 92
      },
      "usage": {
        "repos_using": ["repo1", "repo2"],
        "usage_count": 14
      },
      "recommendation": "CRITICAL - Monitor closely..."
    }
  ],
  "recommendations": [...]
}
```

### Console Output

The tool prints an executive summary to the console:

```
============================================================
SPOF Analysis Report: kubernetes
============================================================

Analysis Date: 2025-12-01...
Repositories Analyzed: 20

Total Dependencies: 1,234
  Critical (≥80):  8
  High (60-79):    45
  Medium (40-59):  183
  Low (20-39):     847
  Minimal (<20):   151

🔴 CRITICAL (Top 3 of 8):
  1. go (Go) - Score: 94.2
     Internal: 95 | Ecosystem: 98
  2. kubernetes/client-go (Go) - Score: 91.5
     Internal: 88 | Ecosystem: 92
  3. etcd (Go) - Score: 87.3
     Internal: 90 | Ecosystem: 85

🟡 HIGH PRIORITY (Top 3 of 45):
  1. prometheus/client_golang (Go) - Score: 76.8
     Internal: 75 | Ecosystem: 80
  2. grpc-go (Go) - Score: 74.2
     Internal: 70 | Ecosystem: 85
  3. cobra (Go) - Score: 71.5
     Internal: 65 | Ecosystem: 78

🟢 MEDIUM PRIORITY (Top 3 of 183):
  1. logrus (Go) - Score: 58.3
     Internal: 55 | Ecosystem: 65
  2. yaml.v3 (Go) - Score: 56.7
     Internal: 60 | Ecosystem: 58
  3. crypto (Go) - Score: 54.1
     Internal: 50 | Ecosystem: 62

📋 Recommendations:

  [CRITICAL] 8 dependencies
  Top investment priorities - these dependencies are critical to your
  organization and/or the broader ecosystem. Consider: direct sponsorship,
  hiring maintainers, contributing code, or establishing ongoing support
  relationships.
```

## Understanding SPOF Scores

SPOF scores range from 0-100, where higher scores indicate higher priority for OSS investment:

- **80-100 (CRITICAL)**: Top investment priorities - essential dependencies
- **60-79 (HIGH)**: Strong candidates for sponsorship and contribution
- **40-59 (MEDIUM)**: Moderate priority - consider community support programs
- **20-39 (LOW)**: Limited impact - may benefit from ecosystem-wide initiatives
- **0-19 (MINIMAL)**: Well-supported or low organizational impact

### Investment Focus Areas

The tool specifically highlights:
- **Dual-critical dependencies**: Projects critical to BOTH your organization and the broader ecosystem (highest ROI)
- **Organization-critical**: Core dependencies your team relies on heavily
- **Ecosystem-critical**: Widely-used projects that benefit the entire community

### Score Components

1. **Internal Criticality (default 30%)**: How many of your repos depend on it
2. **Ecosystem Popularity (default 25%)**: Broader ecosystem usage and adoption
3. **Maintainer Risk (default 20%)**: Single points of failure in maintenance
4. **Security Health (default 15%)**: Known vulnerabilities (one factor among many)
5. **Upstream Activity (default 10%)**: Active maintenance indicators

## Architecture

```
SPOF Analysis Pipeline:

1. GitHub Repository Fetching
   ↓ (Ranked by stars + 2×forks)
2. SBOM Generation (Syft)
   ↓ (Multi-language dependency extraction)
3. Data Collection
   ├─ GitHub API (stars, contributors, activity)
   └─ deps.dev API (popularity, dependents, vulnerabilities)
   ↓
4. SPOF Score Calculation
   ↓ (Configurable weighted metrics)
5. Report Generation
   └─ JSON / CSV exports
```

## Troubleshooting

### "GitHub token not provided"

Make sure you've created a `.env` file with your `GITHUB_TOKEN`. See Installation step 4.

### "Syft not found"

Install Syft using the instructions in Installation step 1.

### "Rate limit exceeded"

GitHub API has rate limits (5,000 requests/hour for authenticated users). If analyzing large organizations:
- Reduce `max_repos` in config.yaml
- Wait for rate limit to reset
- Consider using a GitHub App token for higher limits

### "No dependencies found"

Some repositories may not have recognizable dependency files. This is normal for:
- Documentation-only repos
- Repos without standard dependency manifests
- Archived or empty repos

## Roadmap

### Phase 2 Features (Planned)
- Google Sheets export with formatted dashboards
- Additional data sources (libraries.io, OpenSSF BigQuery, package registries)
- GitHub metrics for upstream packages (last commit, releases, contributors)
- Web-based dashboard for visualization
- Customizable recommendation templates

### Phase 3 Features (Temporal Integration)
- **Durable workflow execution** using [Temporal](https://temporal.io/)
- **Async/parallel processing** - Analyze multiple repos and dependencies concurrently
- **Checkpoint/resume capability** - Pause and resume long-running analyses
- **Automatic retry logic** - Handle API rate limits and transient failures gracefully
- **Scheduled analyses** - Periodic SPOF analysis for tracking changes over time
- **Progress monitoring** - Real-time visibility into analysis progress
- **Workflow versioning** - Update analysis logic without breaking in-flight runs
- **Signal handling** - Dynamically adjust running analyses (e.g., add more repos)

Benefits of Temporal integration:
- Analyze organizations with 100+ repos without timeouts or manual intervention
- Gracefully handle GitHub API rate limits with built-in backoff
- Resume from exact checkpoint if process crashes or is interrupted
- Run analyses on a schedule to track dependency health over time
- Scale horizontally by adding more workers

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

Apache License 2.0 - See LICENSE file for details.

## Target Audience

- **OSPOs (Open Source Program Offices)**: Identify strategic investment opportunities that maximize organizational and ecosystem impact
- **DevRel Teams**: Understand which projects to engage with, contribute to, and build relationships with
- **Engineering Leadership**: Make data-driven decisions about OSS sponsorship, contribution priorities, and strategic partnerships
- **Marketing Teams**: Understand ecosystem dependencies to align community engagement and sponsorship programs

## Acknowledgments

This tool leverages excellent open source projects:
- [Syft](https://github.com/anchore/syft) for SBOM generation
- [deps.dev](https://deps.dev) for dependency insights
- [PyGithub](https://github.com/PyGithub/PyGithub) for GitHub API access

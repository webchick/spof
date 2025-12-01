# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**spof** (Single Point of Failure) is a Python-based tool that analyzes OSS dependencies for GitHub organizations and calculates SPOF scores to guide open source investment decisions.

Target users: OSPOs, DevRel teams, Marketing teams, Engineering leadership

## Commands

### Setup and Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package and dependencies (creates 'spof' command)
pip install -e .

# Install Syft (required for SBOM generation)
brew install syft  # macOS
# OR
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin  # Linux
```

### Running the Tool

```bash
# Basic analysis (specify org via command line)
spof <org-name>

# With additional options
spof kubernetes --debug
spof kubernetes --max-repos 5
spof kubernetes --output-csv

# Combine multiple options
spof kubernetes --max-repos 10 --debug --output-csv

# Custom config file
spof kubernetes --config my-config.yaml

# Use config.yaml for org (if not specified via CLI)
spof

# Alternative (without installing): Use Python module directly
python -m src.main kubernetes
```

### Configuration

```bash
# Set up environment variables (REQUIRED)
cp .env.example .env
# Edit .env and add GITHUB_TOKEN

# Edit config.yaml to customize (OPTIONAL):
# - Default organization (can be overridden via CLI)
# - Scoring weights
# - Default number of repos to analyze (can be overridden via --max-repos)
# - Data sources
# - Output settings
```

**Note**: Organization and max repos can be specified via command line arguments, which override the config file.

## Architecture

### Pipeline Flow

```
1. GitHub Repository Fetching (github_client.py)
   ↓ Ranks repos by weighted score: stars + (2 × forks)

2. SBOM Generation (sbom_generator.py)
   ↓ Uses Syft CLI to generate SBOMs for multiple languages
   ↓ Parses CycloneDX JSON format

3. Data Collection
   ├─ GitHub API metrics (github_client.py)
   │  Stars, forks, contributors, commits, releases
   └─ deps.dev API (depsdev_client.py)
      Popularity, dependents, vulnerabilities

4. SPOF Scoring (scorer.py)
   ↓ Calculates weighted composite score from:
   │  - Internal Criticality (30%)
   │  - Ecosystem Popularity (25%)
   │  - Maintainer Risk (20%)
   │  - Security Health (15%)
   │  - Upstream Activity (10%)

5. Output Generation (output.py)
   └─ JSON reports, CSV exports, console summaries
```

### Module Responsibilities

**src/main.py**: CLI entry point and orchestration. Coordinates the entire analysis pipeline.

**src/config.py**: Configuration management. Loads YAML config and environment variables with `${VAR}` substitution.

**src/github_client.py**: GitHub API wrapper using PyGithub. Fetches repositories and metrics with rate limit handling.

**src/sbom_generator.py**: SBOM generation using Syft CLI. Parses CycloneDX format and aggregates dependencies across repos.

**src/depsdev_client.py**: deps.dev REST API client. Fetches package popularity, dependents, and vulnerability data.

**src/scorer.py**: SPOF score calculation engine. Implements configurable weighted scoring algorithm.

**src/output.py**: Report generation and formatting. Creates JSON reports, CSV exports, and console summaries.

### Key Data Structures

**RepoInfo** (github_client.py): Repository metadata with calculated weighted score.

**Dependency** (sbom_generator.py): Represents a software dependency with name, version, ecosystem, PURL.

**ScoredDependency** (scorer.py): Dependency with calculated SPOF score, confidence, and metrics breakdown.

### Configuration System

The tool uses a two-tier configuration:
1. **config.yaml**: User-facing settings (org, weights, data sources)
2. **.env**: Sensitive data (API tokens)

Scoring weights are fully configurable to match organizational priorities. All weights must sum to 1.0.

## Development Notes

### Adding New Data Sources

To add a new data source (e.g., libraries.io, OpenSSF):

1. Create new client module in `src/` (e.g., `librariesio_client.py`)
2. Add data source to `config.yaml` enabled list
3. Update `main.py` to conditionally use new data source
4. Update `scorer.py` to incorporate new metrics
5. Test with `--debug` flag

### Modifying Scoring Algorithm

The scoring algorithm is in `scorer.py`:
- Each metric calculator (`_calc_*`) returns 0-100 score
- Final score is weighted combination of all metrics
- Add new metrics by:
  1. Adding weight to config.yaml
  2. Creating `_calc_new_metric()` method
  3. Including in `score_dependency()` calculation

### Testing with Small Datasets

For development, use small GitHub orgs or reduce `max_repos` in config:
```yaml
github:
  max_repos: 3  # Fast testing with just 3 repos
```

### Common Development Tasks

**Test SBOM generation**:
```bash
syft /path/to/repo -o cyclonedx-json
```

**Check GitHub rate limit**:
```python
from src.github_client import GitHubClient
client = GitHubClient(token)
client.check_rate_limit()
```

**Test scoring in isolation**:
```python
from src.scorer import SPOFScorer
scorer = SPOFScorer(weights)
result = scorer.score_dependency(dep_info, github_metrics, depsdev_metrics)
```

## External Dependencies

**Runtime dependencies** (in requirements.txt):
- **PyGithub**: GitHub API client
- **requests**: HTTP client for REST APIs
- **PyYAML**: Configuration file parsing
- **python-dotenv**: Environment variable loading

**External tools** (must be installed separately):
- **Syft**: Multi-language SBOM generator (brew install syft)

## Data Sources

**GitHub API**: Repository metadata, stars, forks, contributors, commits, releases. Rate limit: 5,000 req/hr authenticated.

**deps.dev API**: Package popularity, dependent counts, vulnerability advisories. No published rate limit, but be respectful.

## Known Limitations

1. **GitHub-only**: Currently only analyzes GitHub organizations, not GitLab/Bitbucket
2. **Limited GitHub metrics**: MVP doesn't fetch detailed GitHub metrics for individual packages (Phase 2)
3. **No caching**: API responses not cached, can hit rate limits on large orgs (Phase 2)
4. **Synchronous**: Single-threaded execution, slow for large orgs (Phase 2: async)
5. **Direct dependencies only**: Doesn't distinguish direct vs transitive dependencies (SBOM limitation)

## Future Enhancements (Phase 2)

- Google Sheets export with formatted dashboards
- Additional data sources: libraries.io, OpenSSF BigQuery, package registries
- Response caching (SQLite/Redis)
- Async/parallel processing for performance
- Checkpoint/resume for interrupted analyses
- Enhanced GitHub linking (map packages to GitHub repos)
- Web-based dashboard
- Transitive dependency depth analysis

## Troubleshooting

**"GitHub token not provided"**: Create `.env` file with `GITHUB_TOKEN=your_token_here`

**"Syft not found"**: Install Syft via `brew install syft` or download binary

**Rate limit errors**: Reduce `max_repos` in config.yaml or wait for rate limit reset

**No dependencies found**: Some repos lack standard dependency manifests (normal for docs repos)

**Import errors**: Make sure to run from repo root: `python -m src.main` (not `python src/main.py`)

## License

Apache License 2.0

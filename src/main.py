#!/usr/bin/env python3
"""
SPOF Analysis Tool - Main entry point
Analyzes OSS dependencies for GitHub organizations to guide investment decisions.
"""

import argparse
import logging
import sys
import time
from pathlib import Path

from .config import Config
from .github_client import GitHubClient
from .sbom_generator import SBOMGenerator
from .depsdev_client import DepsDevClient
from .scorer import SPOFScorer
from .output import OutputFormatter
from .cache import Cache


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('spof_analysis.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='SPOF Analysis Tool - Analyze OSS dependencies for GitHub organizations'
    )
    parser.add_argument(
        'org',
        nargs='?',
        help='GitHub organization to analyze (overrides config file)'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--max-repos',
        type=int,
        help='Maximum number of repositories to analyze (overrides config file)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    parser.add_argument(
        '--output-csv',
        action='store_true',
        help='Also generate CSV export'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching of API responses'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear all cached data before running'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = Config(args.config)

        # Override config with command line arguments if provided
        if args.org:
            config._config['github']['org'] = args.org
            logger.info(f"Organization overridden via command line: {args.org}")

        if args.max_repos:
            config._config['github']['max_repos'] = args.max_repos
            logger.info(f"Max repos overridden via command line: {args.max_repos}")

        # Validate that org is not the example value
        if config.github_org == "example-org":
            logger.error("Please specify a GitHub organization:")
            logger.error("  - Via command line: python -m src.main <org-name>")
            logger.error("  - Or in config.yaml: update github.org setting")
            return 1

        logger.info(f"Analyzing organization: {config.github_org}")
        logger.info(f"Max repositories: {config.max_repos}")

        # Initialize cache
        cache = Cache()
        if args.clear_cache:
            logger.info("Clearing cache...")
            cache.clear()
        if args.no_cache:
            logger.info("Cache disabled")
            cache.disable()
        else:
            stats = cache.get_stats()
            logger.info(f"Cache: {stats['files']} files, {stats['size_mb']:.2f} MB")

        # Initialize clients
        logger.info("Initializing GitHub client...")
        github_client = GitHubClient(config.github_token, cache=cache)

        logger.info("Initializing SBOM generator...")
        sbom_generator = SBOMGenerator(
            syft_path=config.syft_path,
            syft_format=config.syft_format,
            cache=cache
        )

        logger.info("Initializing deps.dev client...")
        depsdev_client = DepsDevClient(cache=cache)

        logger.info("Initializing scorer...")
        scorer = SPOFScorer(config.scoring_weights)

        logger.info("Initializing output formatter...")
        output_formatter = OutputFormatter(config.output_directory)

        # Check rate limit
        github_client.check_rate_limit()

        # Phase 1: Fetch top repositories
        logger.info(f"\n{'='*60}")
        logger.info("Phase 1: Fetching top repositories")
        logger.info(f"{'='*60}")

        phase1_start = time.time()
        top_repos = github_client.get_top_repos(config.github_org, config.max_repos)
        phase1_time = time.time() - phase1_start

        if not top_repos:
            logger.error("No repositories found. Exiting.")
            return 1

        logger.info(f"Selected {len(top_repos)} repositories for analysis")

        # Phase 2: Generate SBOMs and collect dependencies
        logger.info(f"\n{'='*60}")
        logger.info("Phase 2: Generating SBOMs and collecting dependencies")
        logger.info(f"{'='*60}")

        phase2_start = time.time()
        repo_dependencies = {}
        for i, repo in enumerate(top_repos, 1):
            logger.info(f"[{i}/{len(top_repos)}] Processing {repo.name}...")
            try:
                dependencies = sbom_generator.generate_sbom_for_repo(
                    repo.clone_url,
                    repo.full_name
                )
                repo_dependencies[repo.full_name] = dependencies
                logger.info(f"  ✓ Found {len(dependencies)} dependencies")
            except Exception as e:
                logger.error(f"  ✗ Failed to generate SBOM: {e}")
                repo_dependencies[repo.full_name] = []

        # Aggregate dependencies across repos
        logger.info("\nAggregating dependencies across repositories...")
        aggregated_deps = sbom_generator.aggregate_dependencies(repo_dependencies)
        phase2_time = time.time() - phase2_start

        # Phase 3: Collect ecosystem data
        logger.info(f"\n{'='*60}")
        logger.info("Phase 3: Collecting ecosystem data")
        logger.info(f"{'='*60}")

        scored_dependencies = []
        total_deps = len(aggregated_deps)

        # Timing stats
        timing_stats = {
            'github_api': 0,
            'depsdev_api': 0,
            'scoring': 0,
            'total': 0
        }

        for i, (dep_key, dep_info) in enumerate(aggregated_deps.items(), 1):
            dep_start = time.time()
            logger.info(f"[{i}/{total_deps}] Analyzing {dep_info['ecosystem']}:{dep_info['name']}...")

            # Collect GitHub metrics (if available)
            github_metrics = None
            github_repo = None
            if 'github' in config.enabled_data_sources:
                try:
                    # Strategy 1: For Go modules, extract GitHub repo from module path
                    if dep_info['ecosystem'].lower() in ['go', 'golang']:
                        module_path = dep_info['name']
                        logger.debug(f"  Go module detected: {module_path}")
                        # Go modules often have paths like: github.com/owner/repo or github.com/owner/repo/v2
                        if module_path.startswith('github.com/'):
                            # Extract owner/repo from path
                            parts = module_path.replace('github.com/', '').split('/')
                            if len(parts) >= 2:
                                # Take first two parts (owner/repo), ignore subpaths and version suffixes
                                github_repo = f"{parts[0]}/{parts[1]}"
                                logger.debug(f"  Extracted GitHub repo from Go module: {github_repo}")

                    # Strategy 2: Extract GitHub repo from deps.dev links (for all ecosystems)
                    # This will be populated after we fetch deps.dev metrics below

                except Exception as e:
                    logger.debug(f"  Could not extract GitHub repo: {e}")

            # Collect deps.dev metrics
            depsdev_metrics = None
            if 'depsdev' in config.enabled_data_sources:
                try:
                    depsdev_start = time.time()
                    # Pick a version to query (use first version found in our SBOM)
                    version = None
                    if dep_info.get('versions'):
                        version = list(dep_info['versions'])[0]

                    depsdev_metrics = depsdev_client.get_package_metrics(
                        dep_info['ecosystem'],
                        dep_info['normalized_name'],
                        version
                    )
                    depsdev_elapsed = time.time() - depsdev_start
                    timing_stats['depsdev_api'] += depsdev_elapsed
                    logger.debug(f"  deps.dev: {depsdev_metrics.get('dependent_count', 0)} dependents ({depsdev_elapsed:.2f}s)")

                    # Extract GitHub repo from deps.dev links if not already found
                    if not github_repo and depsdev_metrics and depsdev_metrics.get('links'):
                        repo_url = depsdev_metrics['links'].get('repository', '')
                        if 'github.com' in repo_url:
                            # Extract owner/repo from GitHub URL
                            # URLs like: https://github.com/owner/repo or https://github.com/owner/repo.git
                            import re
                            match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', repo_url)
                            if match:
                                github_repo = f"{match.group(1)}/{match.group(2)}"
                                logger.debug(f"  Extracted GitHub repo from deps.dev: {github_repo}")

                except Exception as e:
                    logger.warning(f"  Failed to fetch deps.dev data: {e}")

            # Fetch GitHub metrics if we found a repo
            if github_repo and 'github' in config.enabled_data_sources and not github_metrics:
                try:
                    github_start = time.time()
                    logger.debug(f"  Fetching GitHub metrics for: {github_repo}")
                    github_metrics = github_client.get_repo_metrics(github_repo)
                    github_elapsed = time.time() - github_start
                    timing_stats['github_api'] += github_elapsed
                    if github_metrics:
                        logger.debug(f"  GitHub: {github_metrics.get('stars', 0)} stars, "
                                   f"{github_metrics.get('contributors', 0)} contributors ({github_elapsed:.2f}s)")
                except Exception as e:
                    logger.debug(f"  Could not fetch GitHub metrics: {e}")

            # Calculate SPOF score
            try:
                score_start = time.time()
                scored_dep = scorer.score_dependency(
                    dep_info,
                    github_metrics=github_metrics,
                    depsdev_metrics=depsdev_metrics,
                    total_repos_analyzed=len(top_repos)
                )
                score_elapsed = time.time() - score_start
                timing_stats['scoring'] += score_elapsed
                scored_dependencies.append(scored_dep)

                dep_elapsed = time.time() - dep_start
                timing_stats['total'] += dep_elapsed
                logger.info(f"  SPOF Score: {scored_dep.spof_score:.1f} (confidence: {scored_dep.confidence:.2f}) [{dep_elapsed:.2f}s]")
            except Exception as e:
                logger.error(f"  Failed to score dependency: {e}")

        # Normalize scores for better distribution
        logger.info("\nNormalizing scores for better distribution...")
        scored_dependencies = scorer.normalize_dependency_scores(scored_dependencies)

        # Print timing summary
        total_time = phase1_time + phase2_time + timing_stats['total']
        logger.info(f"\n{'='*60}")
        logger.info("Performance Summary")
        logger.info(f"{'='*60}")
        logger.info(f"Total pipeline time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        logger.info(f"")
        logger.info(f"Phase 1 - Fetch repositories: {phase1_time:.1f}s ({phase1_time/total_time*100:.0f}%)")
        logger.info(f"Phase 2 - Generate SBOMs: {phase2_time:.1f}s ({phase2_time/total_time*100:.0f}%)")
        logger.info(f"Phase 3 - Analyze dependencies: {timing_stats['total']:.1f}s ({timing_stats['total']/total_time*100:.0f}%)")
        logger.info(f"  └─ deps.dev API: {timing_stats['depsdev_api']:.1f}s")
        logger.info(f"  └─ GitHub API: {timing_stats['github_api']:.1f}s")
        logger.info(f"  └─ Scoring: {timing_stats['scoring']:.1f}s")
        logger.info(f"")
        logger.info(f"Averages:")
        logger.info(f"  {phase2_time/len(top_repos):.1f}s per repository (SBOM generation)")
        logger.info(f"  {timing_stats['total']/total_deps:.2f}s per dependency (analysis)")

        # Phase 4: Generate report
        logger.info(f"\n{'='*60}")
        logger.info("Phase 4: Generating report")
        logger.info(f"{'='*60}")

        report = output_formatter.generate_json_report(
            organization=config.github_org,
            scored_dependencies=scored_dependencies,
            config={
                'scoring_weights': config.scoring_weights,
                'data_sources_enabled': config.enabled_data_sources,
            },
            repos_analyzed=len(top_repos)
        )

        # Save JSON report
        json_path = output_formatter.save_json_report(report, config.output_file)
        logger.info(f"JSON report saved: {json_path}")

        # Optionally generate CSV
        if args.output_csv:
            csv_path = output_formatter.generate_csv_export(report)
            logger.info(f"CSV export saved: {csv_path}")

        # Print summary to console
        output_formatter.print_summary(report)

        logger.info("Analysis complete! ✓")

        return 0

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.warning("\nAnalysis interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())

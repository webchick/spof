#!/usr/bin/env python3
"""
SPOF Analysis Tool - Main entry point
Analyzes OSS dependencies for GitHub organizations to guide investment decisions.
"""

import argparse
import logging
import sys
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

        top_repos = github_client.get_top_repos(config.github_org, config.max_repos)

        if not top_repos:
            logger.error("No repositories found. Exiting.")
            return 1

        logger.info(f"Selected {len(top_repos)} repositories for analysis")

        # Phase 2: Generate SBOMs and collect dependencies
        logger.info(f"\n{'='*60}")
        logger.info("Phase 2: Generating SBOMs and collecting dependencies")
        logger.info(f"{'='*60}")

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

        # Phase 3: Collect ecosystem data
        logger.info(f"\n{'='*60}")
        logger.info("Phase 3: Collecting ecosystem data")
        logger.info(f"{'='*60}")

        scored_dependencies = []
        total_deps = len(aggregated_deps)

        for i, (dep_key, dep_info) in enumerate(aggregated_deps.items(), 1):
            logger.info(f"[{i}/{total_deps}] Analyzing {dep_info['ecosystem']}:{dep_info['name']}...")

            # Collect GitHub metrics (if available via search)
            github_metrics = None
            if 'github' in config.enabled_data_sources:
                try:
                    # Try to get GitHub repo metrics if the package has a GitHub link
                    # For MVP, we'll skip this for non-GitHub packages
                    # In Phase 2, we can enhance this with better linking
                    pass
                except Exception as e:
                    logger.debug(f"  Could not fetch GitHub metrics: {e}")

            # Collect deps.dev metrics
            depsdev_metrics = None
            if 'depsdev' in config.enabled_data_sources:
                try:
                    depsdev_metrics = depsdev_client.get_package_metrics(
                        dep_info['ecosystem'],
                        dep_info['normalized_name']
                    )
                    logger.debug(f"  deps.dev: {depsdev_metrics.get('dependent_count', 0)} dependents")
                except Exception as e:
                    logger.warning(f"  Failed to fetch deps.dev data: {e}")

            # Calculate SPOF score
            try:
                scored_dep = scorer.score_dependency(
                    dep_info,
                    github_metrics=github_metrics,
                    depsdev_metrics=depsdev_metrics,
                    total_repos_analyzed=len(top_repos)
                )
                scored_dependencies.append(scored_dep)
                logger.info(f"  SPOF Score: {scored_dep.spof_score:.1f} (confidence: {scored_dep.confidence:.2f})")
            except Exception as e:
                logger.error(f"  Failed to score dependency: {e}")

        # Normalize scores for better distribution
        logger.info("\nNormalizing scores for better distribution...")
        scored_dependencies = scorer.normalize_dependency_scores(scored_dependencies)

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

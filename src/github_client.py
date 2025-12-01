"""
GitHub API client for fetching and ranking repositories.
"""

import logging
from typing import List, Dict, Any, Optional
from github import Github, Repository, GithubException
from dataclasses import dataclass

from .cache import Cache


logger = logging.getLogger(__name__)


@dataclass
class RepoInfo:
    """Repository information."""
    name: str
    full_name: str
    url: str
    stars: int
    forks: int
    score: float
    language: Optional[str]
    default_branch: str
    clone_url: str


class GitHubClient:
    """GitHub API client with repository fetching and ranking."""

    def __init__(self, token: str, cache: Optional[Cache] = None):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            cache: Optional cache instance
        """
        self.github = Github(token)
        self.user = self.github.get_user()
        self.cache = cache or Cache()
        logger.info(f"Authenticated as GitHub user: {self.user.login}")

    def get_top_repos(self, org_name: str, max_repos: int = 20) -> List[RepoInfo]:
        """
        Fetch and rank repositories from a GitHub organization.

        Repositories are ranked by: stars + (2 × forks)
        Forks are weighted higher to prioritize repos with active usage.

        Args:
            org_name: GitHub organization name
            max_repos: Maximum number of repositories to return

        Returns:
            List of RepoInfo objects, sorted by score (highest first)

        Raises:
            GithubException: If organization not found or access denied
        """
        logger.info(f"Fetching repositories from organization: {org_name}")

        try:
            org = self.github.get_organization(org_name)
        except GithubException as e:
            logger.error(f"Failed to access organization '{org_name}': {e}")
            raise

        # Fetch all repositories
        repos = []
        try:
            for repo in org.get_repos():
                # Skip forks and archived repos
                if repo.fork or repo.archived:
                    logger.debug(f"Skipping {repo.name}: fork={repo.fork}, archived={repo.archived}")
                    continue

                # Calculate weighted score: stars + (2 × forks)
                score = repo.stargazers_count + (2 * repo.forks_count)

                repo_info = RepoInfo(
                    name=repo.name,
                    full_name=repo.full_name,
                    url=repo.html_url,
                    stars=repo.stargazers_count,
                    forks=repo.forks_count,
                    score=score,
                    language=repo.language,
                    default_branch=repo.default_branch,
                    clone_url=repo.clone_url
                )
                repos.append(repo_info)

                logger.debug(f"  {repo.name}: stars={repo.stargazers_count}, "
                           f"forks={repo.forks_count}, score={score}")

        except GithubException as e:
            logger.error(f"Error fetching repositories: {e}")
            raise

        # Sort by score (highest first) and take top N
        repos.sort(key=lambda r: r.score, reverse=True)
        top_repos = repos[:max_repos]

        logger.info(f"Selected top {len(top_repos)} repositories (out of {len(repos)} total)")
        if top_repos:
            logger.info(f"  Top repository: {top_repos[0].name} (score: {top_repos[0].score})")
            if len(top_repos) > 1:
                logger.info(f"  Last repository: {top_repos[-1].name} (score: {top_repos[-1].score})")

        return top_repos

    def get_repo_metrics(self, full_name: str) -> Dict[str, Any]:
        """
        Get detailed metrics for a repository (with caching).

        Args:
            full_name: Full repository name (e.g., "owner/repo")

        Returns:
            Dictionary of repository metrics

        Raises:
            GithubException: If repository not found or access denied
        """
        # Check cache first
        cache_key = f"github_repo_metrics:{full_name}"
        cached_metrics = self.cache.get(cache_key)
        if cached_metrics:
            logger.debug(f"Using cached metrics for {full_name}")
            return cached_metrics

        logger.debug(f"Fetching metrics for repository: {full_name}")

        try:
            repo = self.github.get_repo(full_name)

            # Get contributor count
            try:
                contributors = repo.get_contributors()
                contributor_count = contributors.totalCount
            except GithubException:
                logger.warning(f"Could not fetch contributors for {full_name}")
                contributor_count = 0

            # Get recent commit activity (last 90 days)
            try:
                commits = repo.get_commits(since=None)  # Will limit in scoring
                # Note: We'll count commits in scorer.py to avoid rate limits
                recent_commits_available = True
            except GithubException:
                logger.warning(f"Could not fetch commits for {full_name}")
                recent_commits_available = False

            # Get issue stats
            open_issues = repo.open_issues_count

            # Get last release date
            try:
                releases = repo.get_releases()
                if releases.totalCount > 0:
                    latest_release = releases[0]
                    last_release_date = latest_release.created_at
                else:
                    last_release_date = None
            except GithubException:
                logger.warning(f"Could not fetch releases for {full_name}")
                last_release_date = None

            # Get last commit date
            try:
                commits = repo.get_commits()
                if commits.totalCount > 0:
                    commit = commits[0]
                    # Handle cases where author might be None
                    if commit and commit.commit and commit.commit.author:
                        last_commit_date = commit.commit.author.date
                    else:
                        last_commit_date = None
                else:
                    last_commit_date = None
            except (GithubException, AssertionError, AttributeError) as e:
                logger.warning(f"Could not fetch last commit for {full_name}: {e}")
                last_commit_date = None

            # Check for organization backing
            has_org_backing = repo.organization is not None

            metrics = {
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.watchers_count,
                'contributors': contributor_count,
                'open_issues': open_issues,
                'last_release_date': last_release_date.isoformat() if last_release_date else None,
                'last_commit_date': last_commit_date.isoformat() if last_commit_date else None,
                'has_org_backing': has_org_backing,
                'language': repo.language,
                'created_at': repo.created_at.isoformat(),
                'updated_at': repo.updated_at.isoformat(),
            }

            logger.debug(f"  Metrics for {full_name}: {metrics}")

            # Cache the metrics
            self.cache.set(cache_key, metrics)

            return metrics

        except GithubException as e:
            logger.error(f"Error fetching metrics for {full_name}: {e}")
            raise

    def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check GitHub API rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        rate_limit = self.github.get_rate_limit()
        core = rate_limit.core

        info = {
            'limit': core.limit,
            'remaining': core.remaining,
            'reset': core.reset.isoformat(),
            'used': core.limit - core.remaining,
        }

        logger.info(f"GitHub API rate limit: {info['remaining']}/{info['limit']} remaining "
                   f"(resets at {info['reset']})")

        return info

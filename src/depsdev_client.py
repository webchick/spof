"""
deps.dev API client for fetching dependency metrics.
API docs: https://docs.deps.dev/api/v3alpha/
"""

import logging
import requests
from typing import Dict, Any, Optional
from urllib.parse import quote


logger = logging.getLogger(__name__)


class DepsDevClient:
    """Client for deps.dev API."""

    BASE_URL = "https://api.deps.dev/v3alpha"

    def __init__(self):
        """Initialize deps.dev API client."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SPOF-Analysis-Tool/0.1.0'
        })

    def get_package_info(self, ecosystem: str, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get package information from deps.dev.

        Args:
            ecosystem: Package ecosystem (npm, pypi, maven, cargo, go)
            package_name: Package name

        Returns:
            Package information dict, or None if not found

        Example response structure:
        {
            "package": {
                "name": "requests",
                "system": "PyPI"
            },
            "versionKey": {
                "system": "PyPI",
                "name": "requests",
                "version": "2.31.0"
            },
            "links": {...},
            "dependentCount": 12345,
            "advisories": [...]
        }
        """
        # Map ecosystem names to deps.dev system names
        system_map = {
            'npm': 'NPM',
            'pypi': 'PyPI',
            'maven': 'Maven',
            'cargo': 'Cargo',
            'go': 'Go',
        }

        system = system_map.get(ecosystem.lower(), ecosystem.upper())

        # URL encode the package name
        encoded_name = quote(package_name, safe='')

        url = f"{self.BASE_URL}/systems/{system}/packages/{encoded_name}"

        logger.debug(f"Fetching deps.dev data for {system}:{package_name}")

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 404:
                logger.debug(f"Package not found in deps.dev: {system}:{package_name}")
                return None
            elif response.status_code != 200:
                logger.warning(f"deps.dev API error for {system}:{package_name}: "
                             f"Status {response.status_code}")
                return None

            data = response.json()
            return data

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch deps.dev data for {system}:{package_name}: {e}")
            return None

    def get_version_info(self, ecosystem: str, package_name: str, version: str) -> Optional[Dict[str, Any]]:
        """
        Get specific version information from deps.dev.

        Args:
            ecosystem: Package ecosystem
            package_name: Package name
            version: Package version

        Returns:
            Version information dict, or None if not found
        """
        system_map = {
            'npm': 'NPM',
            'pypi': 'PyPI',
            'maven': 'Maven',
            'cargo': 'Cargo',
            'go': 'Go',
        }

        system = system_map.get(ecosystem.lower(), ecosystem.upper())
        encoded_name = quote(package_name, safe='')
        encoded_version = quote(version, safe='')

        url = f"{self.BASE_URL}/systems/{system}/packages/{encoded_name}/versions/{encoded_version}"

        logger.debug(f"Fetching deps.dev version data for {system}:{package_name}@{version}")

        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 404:
                logger.debug(f"Version not found in deps.dev: {system}:{package_name}@{version}")
                return None
            elif response.status_code != 200:
                logger.warning(f"deps.dev API error for {system}:{package_name}@{version}: "
                             f"Status {response.status_code}")
                return None

            data = response.json()
            return data

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch deps.dev version data: {e}")
            return None

    def get_package_metrics(self, ecosystem: str, package_name: str) -> Dict[str, Any]:
        """
        Extract key metrics from package information.

        Args:
            ecosystem: Package ecosystem
            package_name: Package name

        Returns:
            Dict with extracted metrics
        """
        metrics = {
            'dependent_count': 0,
            'dependent_repo_count': 0,
            'advisory_count': 0,
            'has_vulnerabilities': False,
            'links': {},
            'data_available': False,
        }

        package_info = self.get_package_info(ecosystem, package_name)
        if not package_info:
            return metrics

        metrics['data_available'] = True

        # Extract dependent counts
        if 'version' in package_info:
            version_data = package_info['version']
            metrics['dependent_count'] = version_data.get('dependentCount', 0)
            metrics['dependent_repo_count'] = version_data.get('dependentRepoCount', 0)

        # Extract advisories (vulnerabilities)
        advisories = package_info.get('advisories', [])
        metrics['advisory_count'] = len(advisories)
        metrics['has_vulnerabilities'] = len(advisories) > 0

        # Extract links (repository, homepage, etc.)
        if 'version' in package_info and 'links' in package_info['version']:
            links = package_info['version']['links']
            metrics['links'] = {
                'repository': links.get('repo', ''),
                'homepage': links.get('homepage', ''),
                'documentation': links.get('documentation', ''),
            }

        logger.debug(f"Extracted metrics for {ecosystem}:{package_name}: "
                    f"dependents={metrics['dependent_count']}, "
                    f"advisories={metrics['advisory_count']}")

        return metrics

    def get_popularity_score(self, ecosystem: str, package_name: str) -> float:
        """
        Calculate a popularity score from deps.dev metrics.

        Score is based on:
        - Number of dependent packages
        - Number of dependent repositories

        Args:
            ecosystem: Package ecosystem
            package_name: Package name

        Returns:
            Popularity score (0-100)
        """
        metrics = self.get_package_metrics(ecosystem, package_name)

        if not metrics['data_available']:
            return 0.0

        # Log scale for dependent counts (popular packages have 10K+ dependents)
        import math
        dependent_count = metrics['dependent_count']
        dependent_repo_count = metrics['dependent_repo_count']

        if dependent_count == 0 and dependent_repo_count == 0:
            return 0.0

        # Calculate score with log scaling
        # 10,000+ dependents -> ~100 score
        # 1,000 dependents -> ~80 score
        # 100 dependents -> ~60 score
        # 10 dependents -> ~40 score
        dependent_score = min(100, (math.log10(max(1, dependent_count)) / 4) * 100)
        repo_score = min(100, (math.log10(max(1, dependent_repo_count)) / 4) * 100)

        # Weight package dependents higher than repo dependents
        popularity = (dependent_score * 0.7) + (repo_score * 0.3)

        return min(100, popularity)

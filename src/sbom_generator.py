"""
SBOM (Software Bill of Materials) generator using Syft.
"""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from .cache import Cache


logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a software dependency."""
    name: str
    version: str
    ecosystem: str  # npm, pypi, maven, go, etc.
    purl: Optional[str] = None  # Package URL
    is_direct: bool = False  # True if direct dependency, False if transitive


class SBOMGenerator:
    """Generate and parse SBOMs using Syft."""

    def __init__(self, syft_path: str = "", syft_format: str = "cyclonedx-json", cache: Optional[Cache] = None):
        """
        Initialize SBOM generator.

        Args:
            syft_path: Path to syft binary (empty string uses system PATH)
            syft_format: Output format for Syft (default: cyclonedx-json)
            cache: Optional cache instance
        """
        self.syft_cmd = syft_path if syft_path else "syft"
        self.syft_format = syft_format
        self.cache = cache or Cache()

    def generate_sbom_for_repo(self, repo_url: str, repo_name: str) -> List[Dependency]:
        """
        Generate SBOM for a GitHub repository (with caching).

        Args:
            repo_url: Git clone URL for the repository
            repo_name: Repository name (for logging)

        Returns:
            List of Dependency objects

        Raises:
            subprocess.CalledProcessError: If Syft execution fails
            ValueError: If SBOM parsing fails
        """
        # Check cache first
        cache_key = f"sbom:{repo_name}"
        cached_deps = self.cache.get(cache_key)
        if cached_deps:
            logger.info(f"Using cached SBOM for repository: {repo_name}")
            # Convert dicts back to Dependency objects
            return [Dependency(**dep) for dep in cached_deps]

        logger.info(f"Generating SBOM for repository: {repo_name}")

        # Create temporary directory for cloning
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            repo_dir = tmppath / repo_name.replace("/", "_")

            # Clone repository (shallow clone to save time/space)
            logger.debug(f"Cloning {repo_url} to {repo_dir}")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(repo_dir)],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to clone {repo_url}: {e.stderr}")
                raise

            # Run Syft to generate SBOM
            sbom_data = self._run_syft(str(repo_dir), repo_name)

            # Parse SBOM and extract dependencies
            dependencies = self._parse_cyclonedx(sbom_data, repo_name)

            logger.info(f"Found {len(dependencies)} dependencies in {repo_name}")

            # Cache the dependencies (convert to dicts for JSON serialization)
            self.cache.set(cache_key, [asdict(dep) for dep in dependencies])

            return dependencies

    def _run_syft(self, target_path: str, repo_name: str) -> Dict[str, Any]:
        """
        Run Syft to generate SBOM.

        Args:
            target_path: Path to analyze
            repo_name: Repository name (for logging)

        Returns:
            Parsed SBOM JSON data

        Raises:
            subprocess.CalledProcessError: If Syft fails
            ValueError: If output is not valid JSON
        """
        logger.debug(f"Running Syft on {target_path}")

        cmd = [
            self.syft_cmd,
            target_path,
            "-o", self.syft_format,
            "-q"  # Quiet mode - suppress progress output
        ]

        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Syft failed for {repo_name}: {e.stderr}")
            raise

        # Parse JSON output
        try:
            sbom_data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Syft output for {repo_name}: {e}")
            raise ValueError(f"Invalid JSON from Syft: {e}")

        return sbom_data

    def _parse_cyclonedx(self, sbom_data: Dict[str, Any], repo_name: str) -> List[Dependency]:
        """
        Parse CycloneDX SBOM format.

        Args:
            sbom_data: Parsed CycloneDX JSON data
            repo_name: Repository name (for logging)

        Returns:
            List of Dependency objects
        """
        dependencies = []

        # CycloneDX components are in the "components" array
        components = sbom_data.get("components", [])

        for component in components:
            name = component.get("name")
            version = component.get("version", "unknown")
            purl = component.get("purl", "")

            # Extract ecosystem from purl (e.g., pkg:npm/... -> npm)
            ecosystem = self._extract_ecosystem_from_purl(purl)

            if name:
                dep = Dependency(
                    name=name,
                    version=version,
                    ecosystem=ecosystem,
                    purl=purl,
                    is_direct=False  # We'll try to determine this later if needed
                )
                dependencies.append(dep)

        logger.debug(f"Parsed {len(dependencies)} components from {repo_name}")
        return dependencies

    def _extract_ecosystem_from_purl(self, purl: str) -> str:
        """
        Extract ecosystem type from Package URL.

        Examples:
            pkg:npm/@babel/core@7.12.3 -> npm
            pkg:pypi/requests@2.28.0 -> pypi
            pkg:maven/org.springframework/spring-core@5.3.0 -> maven

        Args:
            purl: Package URL

        Returns:
            Ecosystem type (lowercase)
        """
        if not purl:
            return "unknown"

        # PURL format: pkg:<type>/...
        if purl.startswith("pkg:"):
            parts = purl.split("/")
            if len(parts) >= 1:
                ecosystem_type = parts[0].replace("pkg:", "")
                return ecosystem_type.lower()

        return "unknown"

    def normalize_package_name(self, dep: Dependency) -> str:
        """
        Normalize package name for cross-ecosystem identification.

        Some ecosystems have different naming conventions:
        - npm: @scope/package
        - PyPI: package-name (normalized to lowercase, - becomes _)
        - Maven: groupId:artifactId

        Args:
            dep: Dependency object

        Returns:
            Normalized package identifier
        """
        ecosystem = dep.ecosystem.lower()
        name = dep.name

        if ecosystem == "pypi":
            # PyPI normalizes package names: lowercase, _ and - are equivalent
            return name.lower().replace("_", "-")
        elif ecosystem == "maven":
            # Maven uses groupId:artifactId format, already normalized
            return name
        elif ecosystem == "npm":
            # npm package names are case-sensitive and include scope
            return name
        else:
            # Default: lowercase normalization
            return name.lower()

    def aggregate_dependencies(self, repo_dependencies: Dict[str, List[Dependency]]) -> Dict[str, Dict[str, Any]]:
        """
        Aggregate dependencies across multiple repositories.

        Args:
            repo_dependencies: Dict mapping repo names to their dependency lists

        Returns:
            Dict mapping normalized package names to aggregated dependency info
        """
        aggregated = {}

        for repo_name, deps in repo_dependencies.items():
            for dep in deps:
                normalized_name = self.normalize_package_name(dep)
                key = f"{dep.ecosystem}:{normalized_name}"

                if key not in aggregated:
                    aggregated[key] = {
                        'name': dep.name,
                        'normalized_name': normalized_name,
                        'ecosystem': dep.ecosystem,
                        'versions': set(),
                        'repos_using': [],
                        'purl': dep.purl,
                    }

                aggregated[key]['versions'].add(dep.version)
                if repo_name not in aggregated[key]['repos_using']:
                    aggregated[key]['repos_using'].append(repo_name)

        # Convert sets to lists for JSON serialization
        for key in aggregated:
            aggregated[key]['versions'] = list(aggregated[key]['versions'])
            aggregated[key]['usage_count'] = len(aggregated[key]['repos_using'])

        logger.info(f"Aggregated {len(aggregated)} unique dependencies across {len(repo_dependencies)} repositories")

        return aggregated

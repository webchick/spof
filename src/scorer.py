"""
SPOF score calculation engine.
Calculates Single Point of Failure scores for dependencies.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class ScoredDependency:
    """Dependency with calculated SPOF score."""
    name: str
    ecosystem: str
    spof_score: float
    confidence: float
    metrics: Dict[str, float]
    raw_data: Dict[str, Any]
    recommendation: str


class SPOFScorer:
    """Calculate SPOF scores for dependencies."""

    def __init__(self, weights: Dict[str, float]):
        """
        Initialize scorer with configurable weights.

        Args:
            weights: Dict with keys: internal_criticality, ecosystem_popularity,
                    maintainer_risk, security_health, upstream_activity
        """
        self.weights = weights
        self._validate_weights()

    def _validate_weights(self):
        """Validate that weights sum to 1.0."""
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total}")

    def score_dependency(
        self,
        dep_info: Dict[str, Any],
        github_metrics: Optional[Dict[str, Any]] = None,
        depsdev_metrics: Optional[Dict[str, Any]] = None,
        total_repos_analyzed: int = 1
    ) -> ScoredDependency:
        """
        Calculate SPOF score for a dependency.

        Args:
            dep_info: Aggregated dependency info from SBOM analysis
            github_metrics: GitHub API metrics for the package
            depsdev_metrics: deps.dev API metrics for the package
            total_repos_analyzed: Total number of repos in the analysis

        Returns:
            ScoredDependency with calculated scores
        """
        name = dep_info['name']
        ecosystem = dep_info['ecosystem']

        logger.debug(f"Scoring dependency: {ecosystem}:{name}")

        # Calculate individual metric scores
        internal_crit = self._calc_internal_criticality(dep_info, total_repos_analyzed)
        ecosystem_pop = self._calc_ecosystem_popularity(github_metrics, depsdev_metrics)
        maintainer_risk = self._calc_maintainer_risk(github_metrics)
        security_health = self._calc_security_health(github_metrics, depsdev_metrics)
        upstream_activity = self._calc_upstream_activity(github_metrics)

        # Calculate composite SPOF score
        spof_score = (
            self.weights['internal_criticality'] * internal_crit +
            self.weights['ecosystem_popularity'] * ecosystem_pop +
            self.weights['maintainer_risk'] * maintainer_risk +
            self.weights['security_health'] * security_health +
            self.weights['upstream_activity'] * upstream_activity
        )

        # Calculate confidence based on data availability
        confidence = self._calc_confidence(github_metrics, depsdev_metrics)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            spof_score, internal_crit, ecosystem_pop, maintainer_risk
        )

        metrics = {
            'internal_criticality': round(internal_crit, 2),
            'ecosystem_popularity': round(ecosystem_pop, 2),
            'maintainer_risk': round(maintainer_risk, 2),
            'security_health': round(security_health, 2),
            'upstream_activity': round(upstream_activity, 2),
        }

        raw_data = {
            'github': github_metrics or {},
            'depsdev': depsdev_metrics or {},
            'usage': dep_info,
        }

        return ScoredDependency(
            name=name,
            ecosystem=ecosystem,
            spof_score=round(spof_score, 2),
            confidence=round(confidence, 2),
            metrics=metrics,
            raw_data=raw_data,
            recommendation=recommendation
        )

    def _calc_internal_criticality(self, dep_info: Dict[str, Any], total_repos: int) -> float:
        """
        Calculate internal criticality score (0-100).

        Based on:
        - How many org repos use this dependency
        - Direct vs transitive (all dependencies weighted equally for MVP)

        Args:
            dep_info: Dependency usage information
            total_repos: Total repos analyzed

        Returns:
            Internal criticality score (0-100)
        """
        usage_count = dep_info.get('usage_count', 0)

        if total_repos == 0:
            return 0.0

        # Simple percentage-based score
        usage_ratio = usage_count / total_repos
        score = usage_ratio * 100

        logger.debug(f"Internal criticality: {usage_count}/{total_repos} repos = {score:.1f}")

        return min(100, score)

    def _calc_ecosystem_popularity(
        self,
        github_metrics: Optional[Dict[str, Any]],
        depsdev_metrics: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate ecosystem popularity score (0-100).

        Based on:
        - GitHub stars
        - deps.dev dependent package count
        - deps.dev dependent repo count

        Args:
            github_metrics: GitHub metrics
            depsdev_metrics: deps.dev metrics

        Returns:
            Ecosystem popularity score (0-100)
        """
        if not github_metrics and not depsdev_metrics:
            return 0.0

        # GitHub stars component (log scale)
        stars = 0
        if github_metrics:
            stars = github_metrics.get('stars', 0)

        stars_score = 0
        if stars > 0:
            # 10K+ stars -> 100, 1K stars -> ~75, 100 stars -> ~50
            stars_score = min(100, (math.log10(stars) / 4) * 100)

        # deps.dev dependents component
        dependents_score = 0
        if depsdev_metrics and depsdev_metrics.get('data_available'):
            dependent_count = depsdev_metrics.get('dependent_count', 0)
            if dependent_count > 0:
                # 10K+ dependents -> 100, 1K -> ~75, 100 -> ~50
                dependents_score = min(100, (math.log10(dependent_count) / 4) * 100)

        # Weighted combination
        # If we have both, weight them equally
        # If only one, use that
        if stars_score > 0 and dependents_score > 0:
            score = (stars_score * 0.5) + (dependents_score * 0.5)
        elif stars_score > 0:
            score = stars_score
        else:
            score = dependents_score

        logger.debug(f"Ecosystem popularity: stars={stars}, score={score:.1f}")

        return min(100, score)

    def _calc_maintainer_risk(self, github_metrics: Optional[Dict[str, Any]]) -> float:
        """
        Calculate maintainer risk score (0-100, higher = more risk).

        Based on:
        - Number of contributors (more = less risk)
        - Organization backing (org = less risk)

        Args:
            github_metrics: GitHub metrics

        Returns:
            Maintainer risk score (0-100, higher = more risky)
        """
        if not github_metrics:
            return 50.0  # Unknown = medium risk

        contributors = github_metrics.get('contributors', 0)
        has_org = github_metrics.get('has_org_backing', False)

        # More contributors = lower risk
        # 20+ contributors -> low risk (20)
        # 5-10 contributors -> medium risk (50)
        # 1-2 contributors -> high risk (80)
        if contributors >= 20:
            contributor_risk = 20
        elif contributors >= 10:
            contributor_risk = 30
        elif contributors >= 5:
            contributor_risk = 50
        elif contributors >= 2:
            contributor_risk = 70
        else:
            contributor_risk = 90

        # Organization backing reduces risk
        org_factor = 0.7 if has_org else 1.0

        risk_score = contributor_risk * org_factor

        logger.debug(f"Maintainer risk: contributors={contributors}, "
                    f"org={has_org}, risk={risk_score:.1f}")

        return min(100, risk_score)

    def _calc_security_health(
        self,
        github_metrics: Optional[Dict[str, Any]],
        depsdev_metrics: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate security health score (0-100, higher = healthier).

        Based on:
        - Known vulnerabilities from deps.dev
        - Open security issues on GitHub

        Args:
            github_metrics: GitHub metrics
            depsdev_metrics: deps.dev metrics

        Returns:
            Security health score (0-100)
        """
        score = 100.0  # Start with perfect score

        # Deduct points for vulnerabilities
        if depsdev_metrics and depsdev_metrics.get('data_available'):
            advisory_count = depsdev_metrics.get('advisory_count', 0)
            # Each advisory reduces score by 15 points (max deduction: 60)
            score -= min(60, advisory_count * 15)

        # Deduct points for open security issues
        if github_metrics:
            open_issues = github_metrics.get('open_issues', 0)
            # Estimate ~5% of issues are security-related
            est_security_issues = open_issues * 0.05
            score -= min(20, est_security_issues * 2)

        logger.debug(f"Security health: score={score:.1f}")

        return max(0, score)

    def _calc_upstream_activity(self, github_metrics: Optional[Dict[str, Any]]) -> float:
        """
        Calculate upstream activity score (0-100).

        Based on:
        - Last commit date
        - Last release date
        - Open vs closed issue ratio

        Args:
            github_metrics: GitHub metrics

        Returns:
            Upstream activity score (0-100)
        """
        if not github_metrics:
            return 0.0

        score = 0.0
        components = 0

        # Last commit recency
        last_commit_str = github_metrics.get('last_commit_date')
        if last_commit_str:
            try:
                last_commit = datetime.fromisoformat(last_commit_str.replace('Z', '+00:00'))
                days_since_commit = (datetime.now(last_commit.tzinfo) - last_commit).days

                # < 30 days -> 100, 90 days -> 66, 180 days -> 33, > 365 -> 0
                if days_since_commit < 30:
                    commit_score = 100
                elif days_since_commit < 90:
                    commit_score = 66
                elif days_since_commit < 180:
                    commit_score = 33
                else:
                    commit_score = max(0, 100 - (days_since_commit / 365 * 100))

                score += commit_score
                components += 1
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse last_commit_date: {e}")

        # Last release recency
        last_release_str = github_metrics.get('last_release_date')
        if last_release_str:
            try:
                last_release = datetime.fromisoformat(last_release_str.replace('Z', '+00:00'))
                days_since_release = (datetime.now(last_release.tzinfo) - last_release).days

                # Similar scoring to commits
                if days_since_release < 90:
                    release_score = 100
                elif days_since_release < 180:
                    release_score = 66
                elif days_since_release < 365:
                    release_score = 33
                else:
                    release_score = max(0, 100 - (days_since_release / 730 * 100))

                score += release_score
                components += 1
            except (ValueError, TypeError) as e:
                logger.debug(f"Could not parse last_release_date: {e}")

        # If no commit or release data, use a default medium score
        if components == 0:
            return 50.0

        activity_score = score / components

        logger.debug(f"Upstream activity: score={activity_score:.1f}")

        return activity_score

    def _calc_confidence(
        self,
        github_metrics: Optional[Dict[str, Any]],
        depsdev_metrics: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence score based on data availability.

        Args:
            github_metrics: GitHub metrics
            depsdev_metrics: deps.dev metrics

        Returns:
            Confidence score (0-1)
        """
        available_sources = 0
        total_sources = 2

        if github_metrics and len(github_metrics) > 0:
            available_sources += 1

        if depsdev_metrics and depsdev_metrics.get('data_available'):
            available_sources += 1

        confidence = available_sources / total_sources

        return confidence

    def _generate_recommendation(
        self,
        spof_score: float,
        internal_crit: float,
        ecosystem_pop: float,
        maintainer_risk: float
    ) -> str:
        """
        Generate actionable recommendation based on scores.

        Args:
            spof_score: Overall SPOF score
            internal_crit: Internal criticality score
            ecosystem_pop: Ecosystem popularity score
            maintainer_risk: Maintainer risk score

        Returns:
            Recommendation string
        """
        if spof_score >= 80:
            # Critical
            if maintainer_risk > 70:
                return "CRITICAL - High internal usage with maintenance concerns. Consider contributing or sponsoring."
            else:
                return "CRITICAL - Monitor closely, very high impact to organization."

        elif spof_score >= 60:
            # High priority
            if internal_crit > 70:
                return "HIGH - Significant internal dependency. Monitor for updates and security issues."
            else:
                return "HIGH - Consider investment to ensure long-term sustainability."

        elif spof_score >= 40:
            # Medium priority
            return "MEDIUM - Moderate impact. Monitor periodically."

        elif spof_score >= 20:
            # Low priority
            return "LOW - Limited impact. Standard monitoring sufficient."

        else:
            # Minimal priority
            if ecosystem_pop > 80:
                return "MINIMAL - Healthy, well-maintained project."
            else:
                return "MINIMAL - Low impact to organization."

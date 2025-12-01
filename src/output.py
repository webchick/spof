"""
Output formatting for SPOF analysis results.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import asdict

from .scorer import ScoredDependency


logger = logging.getLogger(__name__)


class OutputFormatter:
    """Format and export analysis results."""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize output formatter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(
        self,
        organization: str,
        scored_dependencies: List[ScoredDependency],
        config: Dict[str, Any],
        repos_analyzed: int
    ) -> Dict[str, Any]:
        """
        Generate JSON report structure.

        Args:
            organization: GitHub organization name
            scored_dependencies: List of scored dependencies
            config: Configuration used for analysis
            repos_analyzed: Number of repositories analyzed

        Returns:
            Complete report as dictionary
        """
        # Sort dependencies by SPOF score (highest first)
        sorted_deps = sorted(scored_dependencies, key=lambda d: d.spof_score, reverse=True)

        # Categorize dependencies by priority
        critical = [d for d in sorted_deps if d.spof_score >= 80]
        high = [d for d in sorted_deps if 60 <= d.spof_score < 80]
        medium = [d for d in sorted_deps if 40 <= d.spof_score < 60]
        low = [d for d in sorted_deps if 20 <= d.spof_score < 40]
        minimal = [d for d in sorted_deps if d.spof_score < 20]

        # Build summary
        summary = {
            'total_dependencies': len(scored_dependencies),
            'critical_dependencies': len(critical),
            'high_priority': len(high),
            'medium_priority': len(medium),
            'low_priority': len(low),
            'minimal_priority': len(minimal),
        }

        # Build recommendations by priority
        recommendations = self._generate_recommendations(critical, high, medium)

        # Format dependencies for output
        dependencies_output = []
        for dep in sorted_deps:
            dep_dict = {
                'name': dep.name,
                'ecosystem': dep.ecosystem,
                'spof_score': dep.spof_score,
                'confidence': dep.confidence,
                'metrics': dep.metrics,
                'recommendation': dep.recommendation,
                'usage': {
                    'repos_using': dep.raw_data['usage'].get('repos_using', []),
                    'usage_count': dep.raw_data['usage'].get('usage_count', 0),
                    'versions': dep.raw_data['usage'].get('versions', []),
                },
            }

            # Optionally include full raw data for transparency
            # dep_dict['raw_data'] = dep.raw_data

            dependencies_output.append(dep_dict)

        # Build complete report
        report = {
            'organization': organization,
            'analysis_date': datetime.now().isoformat(),
            'config': {
                'repos_analyzed': repos_analyzed,
                'scoring_weights': config.get('scoring_weights', {}),
                'data_sources_enabled': config.get('data_sources_enabled', []),
            },
            'summary': summary,
            'dependencies': dependencies_output,
            'recommendations': recommendations,
        }

        return report

    def _generate_recommendations(
        self,
        critical: List[ScoredDependency],
        high: List[ScoredDependency],
        medium: List[ScoredDependency]
    ) -> List[Dict[str, Any]]:
        """
        Generate prioritized recommendations.

        Args:
            critical: Critical priority dependencies
            high: High priority dependencies
            medium: Medium priority dependencies

        Returns:
            List of recommendation objects
        """
        recommendations = []

        if critical:
            recommendations.append({
                'priority': 'critical',
                'count': len(critical),
                'dependencies': [d.name for d in critical[:5]],  # Top 5
                'action': 'Top investment priorities - these dependencies are critical to your organization and/or '
                         'the broader ecosystem. Consider: direct sponsorship, hiring maintainers, contributing code, '
                         'or establishing ongoing support relationships.'
            })

        if high:
            recommendations.append({
                'priority': 'high',
                'count': len(high),
                'dependencies': [d.name for d in high[:5]],  # Top 5
                'action': 'Strong investment candidates - significant organizational or ecosystem dependencies. '
                         'Consider: sponsorship programs, contributor time allocation, or participation in '
                         'governance/foundation support.'
            })

        if medium:
            recommendations.append({
                'priority': 'medium',
                'count': len(medium),
                'dependencies': [d.name for d in medium[:5]],  # Top 5
                'action': 'Moderate priority for investment. Consider: community sponsorship programs, one-time '
                         'contributions, or tracking for future support as usage grows.'
            })

        return recommendations

    def save_json_report(
        self,
        report: Dict[str, Any],
        filename_template: str = "spof_analysis_{org}_{date}.json"
    ) -> Path:
        """
        Save JSON report to file.

        Args:
            report: Report dictionary
            filename_template: Filename template (supports {org}, {date})

        Returns:
            Path to saved file
        """
        # Format filename
        filename = filename_template.format(
            org=report['organization'],
            date=datetime.now().strftime('%Y%m%d_%H%M%S')
        )

        output_path = self.output_dir / filename

        # Write JSON with pretty formatting
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved to: {output_path}")

        return output_path

    def print_summary(self, report: Dict[str, Any]):
        """
        Print executive summary to console.

        Args:
            report: Report dictionary
        """
        print("\n" + "="*60)
        print(f"SPOF Analysis Report: {report['organization']}")
        print("="*60)
        print(f"\nAnalysis Date: {report['analysis_date']}")
        print(f"Repositories Analyzed: {report['config']['repos_analyzed']}")

        summary = report['summary']
        print(f"\nTotal Dependencies: {summary['total_dependencies']}")
        print(f"  Critical (≥80):  {summary['critical_dependencies']}")
        print(f"  High (60-79):    {summary['high_priority']}")
        print(f"  Medium (40-59):  {summary['medium_priority']}")
        print(f"  Low (20-39):     {summary['low_priority']}")
        print(f"  Minimal (<20):   {summary['minimal_priority']}")

        # Categorize dependencies
        critical_deps = [d for d in report['dependencies'] if d['spof_score'] >= 80]
        high_deps = [d for d in report['dependencies'] if 60 <= d['spof_score'] < 80]
        medium_deps = [d for d in report['dependencies'] if 40 <= d['spof_score'] < 60]

        # Print top 3 in each major category
        if critical_deps:
            print(f"\n🔴 CRITICAL (Top 3 of {len(critical_deps)}):")
            for i, dep in enumerate(critical_deps[:3], 1):
                internal = dep['metrics']['internal_criticality']
                ecosystem = dep['metrics']['ecosystem_popularity']
                print(f"  {i}. {dep['name']} ({dep['ecosystem']}) - Score: {dep['spof_score']:.1f}")
                print(f"     Internal: {internal:.0f} | Ecosystem: {ecosystem:.0f}")

        if high_deps:
            print(f"\n🟡 HIGH PRIORITY (Top 3 of {len(high_deps)}):")
            for i, dep in enumerate(high_deps[:3], 1):
                internal = dep['metrics']['internal_criticality']
                ecosystem = dep['metrics']['ecosystem_popularity']
                print(f"  {i}. {dep['name']} ({dep['ecosystem']}) - Score: {dep['spof_score']:.1f}")
                print(f"     Internal: {internal:.0f} | Ecosystem: {ecosystem:.0f}")

        if medium_deps:
            print(f"\n🟢 MEDIUM PRIORITY (Top 3 of {len(medium_deps)}):")
            for i, dep in enumerate(medium_deps[:3], 1):
                internal = dep['metrics']['internal_criticality']
                ecosystem = dep['metrics']['ecosystem_popularity']
                print(f"  {i}. {dep['name']} ({dep['ecosystem']}) - Score: {dep['spof_score']:.1f}")
                print(f"     Internal: {internal:.0f} | Ecosystem: {ecosystem:.0f}")

        # Print recommendations
        if report['recommendations']:
            print(f"\n📋 Recommendations:")
            for rec in report['recommendations']:
                print(f"\n  [{rec['priority'].upper()}] {rec['count']} dependencies")
                print(f"  {rec['action']}")

        print("\n" + "="*60 + "\n")

    def generate_csv_export(self, report: Dict[str, Any]) -> Path:
        """
        Generate CSV export for spreadsheet analysis.

        Args:
            report: Report dictionary

        Returns:
            Path to CSV file
        """
        import csv

        filename = f"spof_analysis_{report['organization']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = self.output_dir / filename

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Name',
                'Ecosystem',
                'SPOF Score',
                'Confidence',
                'Internal Criticality',
                'Ecosystem Popularity',
                'Maintainer Risk',
                'Security Health',
                'Upstream Activity',
                'Usage Count',
                'Recommendation'
            ])

            # Data rows
            for dep in report['dependencies']:
                writer.writerow([
                    dep['name'],
                    dep['ecosystem'],
                    dep['spof_score'],
                    dep['confidence'],
                    dep['metrics']['internal_criticality'],
                    dep['metrics']['ecosystem_popularity'],
                    dep['metrics']['maintainer_risk'],
                    dep['metrics']['security_health'],
                    dep['metrics']['upstream_activity'],
                    dep['usage']['usage_count'],
                    dep['recommendation']
                ])

        logger.info(f"CSV export saved to: {output_path}")

        return output_path

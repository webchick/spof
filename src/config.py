"""
Configuration management for SPOF analysis tool.
Loads settings from config.yaml and environment variables.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv


class Config:
    """Configuration loader with environment variable substitution."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Load configuration from YAML file and environment.

        Args:
            config_path: Path to the YAML configuration file
        """
        # Load environment variables from .env file
        load_dotenv()

        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(self.config_path, 'r') as f:
            self._raw_config = yaml.safe_load(f)

        # Substitute environment variables in the config
        self._config = self._substitute_env_vars(self._raw_config)

        # Validate configuration
        self._validate()

    def _substitute_env_vars(self, obj: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Supports ${VAR_NAME} syntax for environment variable substitution.

        Args:
            obj: Configuration object (dict, list, str, or other)

        Returns:
            Object with environment variables substituted
        """
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Match ${VAR_NAME} pattern
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, obj)
            for var_name in matches:
                var_value = os.getenv(var_name, '')
                if not var_value:
                    raise ValueError(f"Environment variable not set: {var_name}")
                obj = obj.replace(f"${{{var_name}}}", var_value)
            return obj
        else:
            return obj

    def _validate(self):
        """Validate configuration values."""
        # Check that GitHub token is provided
        if not self.github_token:
            raise ValueError("GitHub token not provided. Set GITHUB_TOKEN environment variable.")

        # Check that GitHub org is provided
        if not self.github_org:
            raise ValueError("GitHub organization not specified in config.yaml")

        # Validate scoring weights sum to 1.0
        weights = self.scoring_weights
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):  # Allow for floating point rounding
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")

        # Validate max_repos is positive
        if self.max_repos <= 0:
            raise ValueError(f"max_repos must be positive, got {self.max_repos}")

    @property
    def github_org(self) -> str:
        """Get GitHub organization name."""
        return self._config['github']['org']

    @property
    def github_token(self) -> str:
        """Get GitHub personal access token."""
        return self._config['github']['token']

    @property
    def max_repos(self) -> int:
        """Get maximum number of repositories to analyze."""
        return self._config['github']['max_repos']

    @property
    def scoring_weights(self) -> Dict[str, float]:
        """Get scoring weights configuration."""
        return self._config['scoring']['weights']

    @property
    def enabled_data_sources(self) -> list:
        """Get list of enabled data sources."""
        return self._config['data_sources']['enabled']

    @property
    def output_format(self) -> str:
        """Get output format."""
        return self._config['output']['format']

    @property
    def output_file(self) -> str:
        """Get output file path template."""
        return self._config['output']['file']

    @property
    def output_directory(self) -> str:
        """Get output directory."""
        return self._config['output']['directory']

    @property
    def syft_path(self) -> str:
        """Get path to syft binary (empty string means use system PATH)."""
        return self._config.get('syft', {}).get('path', '')

    @property
    def syft_format(self) -> str:
        """Get syft SBOM output format."""
        return self._config.get('syft', {}).get('format', 'cyclonedx-json')

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by dot-notation key.

        Args:
            key: Dot-notation key (e.g., 'github.org')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

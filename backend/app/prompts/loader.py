"""Prompt template loader and renderer."""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


class PromptTemplate:
    """Prompt template class."""

    def __init__(self, template_data: Dict[str, Any]) -> None:
        """Initialize prompt template.

        Args:
            template_data: Template data from YAML
        """
        self.metadata = template_data.get("metadata", {})
        self.variables = {
            var["name"]: var.get("default") for var in template_data.get("variables", [])
        }
        self.system_prompt = template_data.get("system_prompt", "")
        self.user_prompt = template_data.get("user_prompt", "")
        self.output_schema = template_data.get("output_schema")

    def render(self, **kwargs: Any) -> Tuple[str, str]:
        """Render template with variables.

        Args:
            **kwargs: Template variables

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            ValueError: If required variable is missing
        """
        # Merge defaults with provided kwargs
        variables = {**self.variables, **kwargs}

        # Check required variables
        for var_name, default in self.variables.items():
            if default is None and var_name not in kwargs:
                raise ValueError(f"Required variable '{var_name}' not provided")

        # Render prompts
        system = self.system_prompt.format(**variables)
        user = self.user_prompt.format(**variables)

        return system, user


class PromptLoader:
    """Prompt template loader."""

    def __init__(self, templates_dir: Optional[Path] = None) -> None:
        """Initialize prompt loader.

        Args:
            templates_dir: Directory containing prompt templates
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        self.templates_dir = templates_dir
        self._cache: Dict[str, PromptTemplate] = {}

    def load(self, template_path: str) -> PromptTemplate:
        """Load prompt template from YAML file.

        Args:
            template_path: Relative path to template (e.g., 'extraction/entity_extraction.yaml')

        Returns:
            Loaded prompt template

        Raises:
            FileNotFoundError: If template file not found
        """
        if template_path in self._cache:
            return self._cache[template_path]

        full_path = self.templates_dir / template_path

        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")

        with open(full_path) as f:
            template_data = yaml.safe_load(f)

        template = PromptTemplate(template_data)
        self._cache[template_path] = template

        return template

    def render(self, template_path: str, **variables: Any) -> Tuple[str, str]:
        """Load and render template in one call.

        Args:
            template_path: Relative path to template
            **variables: Template variables

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        template = self.load(template_path)
        return template.render(**variables)


# Global loader instance
_loader = PromptLoader()


def get_prompt_loader() -> PromptLoader:
    """Get global prompt loader instance."""
    return _loader

"""Jinja2-backed template loader."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import yaml
import jinja2

from .exceptions import TemplateError
from .models import TemplateMetadata


class TemplateLoader:
    """Loads and manages Jinja2 email templates."""

    def __init__(self, template_dir: str):
        """Initialize the template loader.

        Args:
            template_dir: Path to the directory containing templates
        """
        self.template_dir = Path(template_dir)
        if not self.template_dir.exists():
            raise TemplateError(f"Template directory does not exist: {template_dir}")

        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=jinja2.select_autoescape(
                enabled_extensions=("html", "xml"), default_for_string=True
            ),
            undefined=jinja2.StrictUndefined,
        )
        self._cache: Dict[str, TemplateMetadata] = {}

    def load_template(self, template_name: str) -> jinja2.Template:
        """Load a Jinja2 template.

        Args:
            template_name: Name of the template (without .jinja2 extension)

        Returns:
            Loaded Jinja2 template

        Raises:
            TemplateError: If template cannot be loaded
        """
        try:
            return self.env.get_template(f"{template_name}.jinja2")
        except jinja2.TemplateNotFound as e:
            raise TemplateError(f"Template not found: {template_name}") from e
        except jinja2.TemplateError as e:
            raise TemplateError(f"Error loading template {template_name}: {e}") from e

    def load_metadata(self, template_name: str) -> TemplateMetadata:
        """Load template metadata from YAML file.

        Args:
            template_name: Name of the template

        Returns:
            Template metadata

        Raises:
            TemplateError: If metadata file cannot be loaded or parsed
        """
        if template_name in self._cache:
            return self._cache[template_name]

        metadata_path = self.template_dir / f"{template_name}.yaml"
        if not metadata_path.exists():
            raise TemplateError(f"Template metadata not found: {metadata_path}")

        try:
            with open(metadata_path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                raise TemplateError(f"Empty metadata file: {metadata_path}")

            metadata = TemplateMetadata(
                name=data.get("name", template_name),
                subject=data.get("subject", ""),
                required_variables=data.get("required_variables", []),
                optional_variables=data.get("optional_variables", []),
                has_html=data.get("has_html", True),
                has_text=data.get("has_text", False),
                description=data.get("description"),
            )

            self._cache[template_name] = metadata
            return metadata
        except yaml.YAMLError as e:
            raise TemplateError(f"Error parsing metadata {metadata_path}: {e}") from e
        except Exception as e:
            raise TemplateError(f"Error loading metadata {metadata_path}: {e}") from e

    def extract_variables(self, template: jinja2.Template) -> Tuple[set, set]:
        """Extract all variables from a template.

        Args:
            template: Jinja2 template object

        Returns:
            Tuple of (required_variables, optional_variables) sets
        """
        # Parse the template source to find all variable references
        # Get source using the environment's loader
        try:
            source, _, _ = self.env.get_loader().get_source(self.env, template.name)
        except Exception:
            # Fallback: try to read the file directly
            template_path = self.template_dir / f"{template.name}"
            with open(template_path, "r") as f:
                source = f.read()
        
        # Find all {{ variable }} references
        pattern = r"\{\{.*?([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}"
        explicit_vars = set(re.findall(pattern, source))

        # Find all {% if variable %} references for conditional variables
        conditional_pattern = r"\{%\s*if\s+([a-zA-Z_][a-zA-Z0-9_]*)"
        conditional_vars = set(re.findall(conditional_pattern, source))

        # Variables in {% if %} are typically optional
        optional_vars = conditional_vars
        required_vars = explicit_vars - conditional_vars

        return required_vars, optional_vars

    def validate_template(
        self, template_name: str, available_fields: List[str]
    ) -> Dict[str, Any]:
        """Validate that a template's required variables match available fields.

        Args:
            template_name: Name of the template
            available_fields: List of available recipient fields

        Returns:
            Dictionary with validation results

        Raises:
            TemplateError: If validation fails
        """
        try:
            metadata = self.load_metadata(template_name)
            template = self.load_template(template_name)
        except TemplateError:
            raise

        # Extract variables from template
        required_vars, optional_vars = self.extract_variables(template)

        # Compare with metadata
        metadata_required = set(metadata.required_variables)
        metadata_optional = set(metadata.optional_variables)

        # Check that metadata required variables are a subset of extracted variables
        if not metadata_required.issubset(required_vars | optional_vars):
            missing = metadata_required - (required_vars | optional_vars)
            raise TemplateError(
                f"Metadata declares required variables not found in template: {missing}"
            )

        # Check that all extracted required variables are in available fields
        available = set(available_fields)
        missing_required = metadata_required - available
        missing_optional = metadata_optional - available

        results = {
            "template_name": template_name,
            "metadata_required": list(metadata_required),
            "metadata_optional": list(metadata_optional),
            "extracted_required": list(required_vars),
            "extracted_optional": list(optional_vars),
            "available_fields": available_fields,
            "missing_required": list(missing_required),
            "missing_optional": list(missing_optional),
            "is_valid": len(missing_required) == 0,
        }

        if not results["is_valid"]:
            raise TemplateError(
                f"Template validation failed. Missing required fields: {results['missing_required']}"
            )

        return results

    def render_template(
        self, template_name: str, context: Dict[str, Any]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Render a template with the given context.

        Args:
            template_name: Name of the template
            context: Context dictionary for template rendering

        Returns:
            Tuple of (html_body, text_body)

        Raises:
            TemplateError: If rendering fails
        """
        try:
            metadata = self.load_metadata(template_name)
            template = self.load_template(template_name)

            # Render the main template (typically HTML)
            html_body = template.render(**context) if metadata.has_html else None

            # Try to load text version if it exists
            text_body = None
            if metadata.has_text:
                try:
                    text_template = self.env.get_template(
                        f"{template_name}.text.jinja2"
                    )
                    text_body = text_template.render(**context)
                except jinja2.TemplateNotFound:
                    pass

            return html_body, text_body
        except jinja2.UndefinedError as e:
            raise TemplateError(f"Missing variable in template: {e}") from e
        except jinja2.TemplateError as e:
            raise TemplateError(f"Error rendering template: {e}") from e
        except TemplateError:
            raise

    def list_templates(self) -> List[str]:
        """List all available templates.

        Returns:
            List of template names
        """
        templates = set()
        for file in self.template_dir.glob("*.jinja2"):
            # Get the base name (remove .jinja2)
            name = file.stem
            if not name.endswith(".text"):
                templates.add(name)
        return sorted(list(templates))

"""Tests for template loading and rendering."""

import pytest
from pathlib import Path

from email_sender.template import TemplateLoader
from email_sender.exceptions import TemplateError


class TestTemplateLoader:
    """Tests for TemplateLoader."""

    def test_load_metadata(self, sample_template):
        """Test loading template metadata."""
        loader = TemplateLoader(str(sample_template))
        metadata = loader.load_metadata("test")

        assert metadata.name == "Test Email"
        assert metadata.subject == "Hello {{ name }}"
        assert "name" in metadata.required_variables
        assert "company" in metadata.optional_variables

    def test_load_nonexistent_metadata(self, sample_template):
        """Test loading nonexistent metadata raises error."""
        loader = TemplateLoader(str(sample_template))

        with pytest.raises(TemplateError):
            loader.load_metadata("nonexistent")

    def test_load_template(self, sample_template):
        """Test loading template."""
        loader = TemplateLoader(str(sample_template))
        template = loader.load_template("test")

        assert template is not None
        # Verify template was loaded correctly by attempting to render it
        result = template.render(name="Test", company="Corp")
        assert "Test" in result

    def test_render_template(self, sample_template):
        """Test rendering template with context."""
        loader = TemplateLoader(str(sample_template))
        html, text = loader.render_template("test", {"name": "John", "company": "Acme"})

        assert "John" in html
        assert "Acme" in html
        assert "John" in text

    def test_render_template_missing_required_variable(self, sample_template):
        """Test rendering without required variable raises error."""
        loader = TemplateLoader(str(sample_template))

        with pytest.raises(TemplateError):
            loader.render_template("test", {"company": "Acme"})

    def test_list_templates(self, sample_template):
        """Test listing available templates."""
        loader = TemplateLoader(str(sample_template))
        templates = loader.list_templates()

        assert "test" in templates

    def test_extract_variables(self, sample_template):
        """Test extracting variables from template."""
        loader = TemplateLoader(str(sample_template))
        template = loader.load_template("test")
        required, optional = loader.extract_variables(template)

        assert "name" in required
        assert "company" in optional

    def test_validate_template(self, sample_template):
        """Test template validation."""
        loader = TemplateLoader(str(sample_template))
        result = loader.validate_template("test", ["name", "company"])

        assert result["is_valid"] is True
        assert len(result["missing_required"]) == 0

    def test_validate_template_missing_field(self, sample_template):
        """Test template validation with missing fields."""
        loader = TemplateLoader(str(sample_template))

        with pytest.raises(TemplateError):
            loader.validate_template("test", ["company"])

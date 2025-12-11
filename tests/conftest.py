"""Shared test fixtures."""

import pytest
from pathlib import Path
import tempfile
import json


@pytest.fixture
def temp_template_dir():
    """Create a temporary template directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_template(temp_template_dir):
    """Create a sample template."""
    template_dir = Path(temp_template_dir)

    # Create metadata
    metadata = {
        "name": "Test Email",
        "subject": "Hello {{ name }}",
        "required_variables": ["name"],
        "optional_variables": ["company"],
        "has_html": True,
        "has_text": True,
    }

    with open(template_dir / "test.yaml", "w") as f:
        import yaml

        yaml.dump(metadata, f)

    # Create HTML template
    html_template = """
    <html>
        <body>
            <h1>Hello {{ name }}!</h1>
            {% if company %}<p>Company: {{ company }}</p>{% endif %}
        </body>
    </html>
    """
    with open(template_dir / "test.jinja2", "w") as f:
        f.write(html_template)

    # Create text template
    text_template = """Hello {{ name }}!
{% if company %}Company: {{ company }}{% endif %}"""
    with open(template_dir / "test.text.jinja2", "w") as f:
        f.write(text_template)

    return template_dir


@pytest.fixture
def sample_recipients():
    """Create sample recipients data."""
    return [
        {
            "email": "alice@example.com",
            "name": "Alice",
            "company": "Acme Corp",
        },
        {
            "email": "bob@example.com",
            "name": "Bob",
            "company": "Acme Corp",
        },
        {
            "email": "invalid-email",
            "name": "Charlie",
            "company": "Acme Corp",
        },
    ]

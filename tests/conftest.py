"""
Pytest configuration and fixtures for the multi-platform blog publishing system.
"""

import pytest
from hypothesis import settings, Verbosity

# Configure Hypothesis for property-based testing
settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.load_profile("default")


@pytest.fixture
def sample_frontmatter_data():
    """Sample frontmatter data for testing."""
    return {
        "title": "Test Article",
        "subtitle": "A test article for unit testing",
        "slug": "test-article",
        "tags": "python,testing,blog",
        "cover": "https://example.com/cover.jpg",
        "domain": "example.com",
        "saveAsDraft": False,
        "enableToc": True,
        "seriesName": "Test Series",
    }


@pytest.fixture
def sample_markdown_content():
    """Sample markdown content for testing."""
    return """# Test Article

This is a test article with some **bold** text and *italic* text.

## Section 1

Some content here.

## Section 2

More content here with a [link](https://example.com).
"""

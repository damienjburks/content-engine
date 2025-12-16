"""
Test that the project structure is properly set up.
"""

import pytest
from src.interfaces.platform_client import PlatformClient
from src.models.post_content import PostContent, ArticleStatus, PublicationResult
from src.processors.content_processor import ContentProcessor
from src.managers.publication_manager import PublicationManager


def test_platform_client_interface():
    """Test that PlatformClient interface can be imported and is abstract."""
    assert PlatformClient is not None

    # Verify it's abstract by trying to instantiate it
    with pytest.raises(TypeError):
        PlatformClient()


def test_post_content_model():
    """Test PostContent model creation and from_frontmatter method."""
    frontmatter_data = {
        "title": "Test Article",
        "subtitle": "Test subtitle",
        "slug": "test-article",
        "tags": "python,testing",
        "cover": "https://example.com/cover.jpg",
        "domain": "example.com",
        "saveAsDraft": False,
        "enableToc": True,
    }

    post_content = PostContent.from_frontmatter(frontmatter_data, "# Test Content")

    assert post_content.title == "Test Article"
    assert post_content.subtitle == "Test subtitle"
    assert post_content.tags == ["python", "testing"]
    assert post_content.save_as_draft is False
    assert post_content.body_markdown == "# Test Content"
    assert "example.com/test-article" in post_content.canonical_url


def test_content_processor():
    """Test ContentProcessor functionality."""
    processor = ContentProcessor()

    # Test normalization
    content = "# Test\n\nSome content with   extra   spaces"
    normalized = processor.normalize_content_for_comparison(content)
    assert "extra spaces" in normalized

    # Test Hashnode transformations
    content_with_align = '<div align="center">Centered content</div>'
    transformed = processor._apply_hashnode_transformations(content_with_align)
    assert 'align="center"' not in transformed


def test_article_status_model():
    """Test ArticleStatus model."""
    status = ArticleStatus(
        platform="devto",
        article_id="123",
        exists=True,
        published=True,
        needs_update=False,
        content_hash="abc123",
    )

    assert status.platform == "devto"
    assert status.exists is True
    assert status.published is True


def test_publication_result_model():
    """Test PublicationResult model."""
    result = PublicationResult(
        platform="hashnode", success=True, action="created", article_id="456"
    )

    assert result.platform == "hashnode"
    assert result.success is True
    assert result.action == "created"
    assert result.article_id == "456"


def test_publication_manager_initialization():
    """Test PublicationManager can be initialized."""
    # Test with empty platform clients dict
    manager = PublicationManager({})
    assert manager.platform_clients == {}
    assert manager.content_processor is not None

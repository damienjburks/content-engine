"""
Basic integration test to verify the project structure works end-to-end.
"""

from src.models.post_content import PostContent
from src.processors.content_processor import ContentProcessor
from src.managers.publication_manager import PublicationManager


def test_basic_integration():
    """Test that the main components can work together."""
    # Create sample frontmatter data
    frontmatter_data = {
        "title": "Integration Test Article",
        "subtitle": "Testing the integration",
        "slug": "integration-test",
        "tags": "python,testing,integration",
        "cover": "https://example.com/cover.jpg",
        "domain": "example.com",
        "saveAsDraft": False,
        "enableToc": True,
    }

    # Create PostContent
    post_content = PostContent.from_frontmatter(
        frontmatter_data, "# Integration Test\n\nThis is a test article."
    )

    # Test ContentProcessor
    processor = ContentProcessor()
    processed_content = processor.process_content_for_platform(post_content, "devto")
    assert "Integration Test" in processed_content
    assert "Table of Contents" in processed_content

    # Test PublicationManager initialization (without actual platform clients)
    manager = PublicationManager({})
    assert manager.content_processor is not None

    # Test content normalization
    normalized = processor.normalize_content_for_comparison(post_content.body_markdown)
    assert "Integration Test" in normalized


def test_post_content_tag_handling():
    """Test that PostContent properly handles different tag formats."""
    # Test comma-separated string tags
    frontmatter_with_string_tags = {
        "title": "Tag Test",
        "subtitle": "Testing tags",
        "slug": "tag-test",
        "tags": "python, testing, blog",
        "cover": "",
        "domain": "example.com",
        "saveAsDraft": False,
    }

    post_content = PostContent.from_frontmatter(frontmatter_with_string_tags, "Content")
    assert post_content.tags == ["python", "testing", "blog"]

    # Test list tags
    frontmatter_with_list_tags = {
        "title": "Tag Test 2",
        "subtitle": "Testing tags",
        "slug": "tag-test-2",
        "tags": ["python", "testing", "blog"],
        "cover": "",
        "domain": "example.com",
        "saveAsDraft": False,
    }

    post_content2 = PostContent.from_frontmatter(frontmatter_with_list_tags, "Content")
    assert post_content2.tags == ["python", "testing", "blog"]


def test_content_processor_platform_transformations():
    """Test platform-specific content transformations."""
    processor = ContentProcessor()

    # Test content with alignment attributes
    content_with_alignment = """
    # Test Article
    
    <div align="center">
        <img src="test.jpg" alt="Test" align="center">
    </div>
    
    Some regular content.
    """

    # Test Hashnode transformation (should remove align attributes)
    hashnode_content = processor._apply_hashnode_transformations(content_with_alignment)
    assert 'align="center"' not in hashnode_content

    # Test dev.to transformation (should preserve content)
    devto_content = processor._apply_devto_transformations(content_with_alignment)
    assert 'align="center"' in devto_content  # dev.to preserves alignment


def test_content_processor_tag_conversion():
    """Test tag conversion for different platforms."""
    processor = ContentProcessor()

    # Test comma-separated tags
    tags_with_commas = ["python,testing,integration"]

    # Test Hashnode tag conversion
    hashnode_tags = processor.convert_tags_for_platform(tags_with_commas, "hashnode")
    assert "python" in hashnode_tags
    assert "testing" in hashnode_tags
    assert "integration" in hashnode_tags
    assert len(hashnode_tags) == 3

    # Test dev.to tag conversion
    devto_tags = processor.convert_tags_for_platform(tags_with_commas, "devto")
    assert "python" in devto_tags
    assert "testing" in devto_tags
    assert "integration" in devto_tags

    # Test tag sanitization for Hashnode
    special_tags = ["C++", "Node.js", "Web Development"]
    hashnode_special = processor.convert_tags_for_platform(special_tags, "hashnode")
    assert "c" in hashnode_special  # C++ becomes c
    assert "nodejs" in hashnode_special  # Node.js becomes nodejs
    assert (
        "web-development" in hashnode_special
    )  # Web Development becomes web-development


def test_content_processor_canonical_url():
    """Test canonical URL generation."""
    processor = ContentProcessor()

    # Create test post content
    post_content = PostContent(
        title="Test Article",
        subtitle="Test Subtitle",
        slug="test-article",
        tags=["test"],
        cover="",
        domain="example.com",
        save_as_draft=False,
        enable_toc=True,
        body_markdown="# Test",
        canonical_url="https://example.com/test-article",
    )

    # Test canonical URL for both platforms
    devto_url = processor.generate_canonical_url(post_content, "devto")
    hashnode_url = processor.generate_canonical_url(post_content, "hashnode")

    assert devto_url == "https://example.com/test-article"
    assert hashnode_url == "https://example.com/test-article"


def test_content_processor_toc_generation():
    """Test table of contents generation."""
    processor = ContentProcessor()

    # Test content with multiple headers
    content_with_headers = """# Main Title

## Section 1

Some content here.

### Subsection 1.1

More content.

## Section 2

Final content.
"""

    toc = processor._generate_table_of_contents(content_with_headers)
    assert "Table of Contents" in toc
    assert "Main Title" in toc
    assert "Section 1" in toc
    assert "Subsection 1.1" in toc
    assert "Section 2" in toc

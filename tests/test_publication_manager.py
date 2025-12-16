"""
Tests for the PublicationManager class.
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.managers.publication_manager import PublicationManager
from src.models.post_content import PostContent, PublicationResult


class MockPlatformClient:
    """Mock platform client for testing."""

    def __init__(self, platform_name: str, should_fail: bool = False):
        self.platform_name = platform_name
        self.should_fail = should_fail
        self.articles = {}
        self.next_id = 1

    def find_article_by_title(self, title: str):
        """Find article by title."""
        if self.should_fail:
            raise Exception(f"Mock error in {self.platform_name}")

        for article_id, article in self.articles.items():
            if article["title"] == title:
                return article_id, article["published"]
        return None, None

    def publish_article(self, post_content: dict, published: bool):
        """Publish new article."""
        if self.should_fail:
            raise Exception(f"Mock error in {self.platform_name}")

        article_id = str(self.next_id)
        self.next_id += 1

        self.articles[article_id] = {
            "id": article_id,
            "title": post_content["frontmatterData"]["title"],
            "body_markdown": post_content["bodyMarkdown"],
            "published": published,
            "tags": (
                post_content["frontmatterData"]["tags"].split(",")
                if post_content["frontmatterData"]["tags"]
                else []
            ),
            "cover_image": post_content["frontmatterData"]["cover"],
        }

        return {"id": article_id}

    def update_article(self, article_id: str, post_content: dict, published: bool):
        """Update existing article."""
        if self.should_fail:
            raise Exception(f"Mock error in {self.platform_name}")

        if article_id in self.articles:
            self.articles[article_id].update(
                {
                    "title": post_content["frontmatterData"]["title"],
                    "body_markdown": post_content["bodyMarkdown"],
                    "published": published,
                    "tags": (
                        post_content["frontmatterData"]["tags"].split(",")
                        if post_content["frontmatterData"]["tags"]
                        else []
                    ),
                    "cover_image": post_content["frontmatterData"]["cover"],
                }
            )

        return {"id": article_id}

    def get_article(self, article_id: str, published: bool):
        """Get article by ID."""
        if self.should_fail:
            raise Exception(f"Mock error in {self.platform_name}")

        article = self.articles.get(article_id)
        if article and article["published"] == published:
            return article
        return None

    def get_articles(self):
        """Get all articles."""
        if self.should_fail:
            raise Exception(f"Mock error in {self.platform_name}")
        return list(self.articles.values())


def create_test_post_content():
    """Create test post content."""
    return PostContent(
        title="Test Article",
        subtitle="Test Subtitle",
        slug="test-article",
        tags=["python", "testing"],
        cover="https://example.com/cover.jpg",
        domain="example.com",
        save_as_draft=False,
        enable_toc=True,
        body_markdown="# Test Article\n\nThis is test content.",
        canonical_url="https://example.com/test-article",
    )


def test_publication_manager_initialization():
    """Test PublicationManager initialization."""
    mock_client1 = MockPlatformClient("devto")
    mock_client2 = MockPlatformClient("hashnode")

    clients = {"devto": mock_client1, "hashnode": mock_client2}
    manager = PublicationManager(clients)

    assert len(manager.platform_clients) == 2
    assert "devto" in manager.platform_clients
    assert "hashnode" in manager.platform_clients
    assert manager.content_processor is not None


def test_publish_new_article_to_all_platforms():
    """Test publishing new article to all platforms."""
    mock_client1 = MockPlatformClient("devto")
    mock_client2 = MockPlatformClient("hashnode")

    clients = {"devto": mock_client1, "hashnode": mock_client2}
    manager = PublicationManager(clients)

    post_content = create_test_post_content()
    results = manager.publish_to_all_platforms(post_content)

    assert len(results) == 2

    # Check that both platforms created new articles
    devto_result = next(r for r in results if r.platform == "devto")
    hashnode_result = next(r for r in results if r.platform == "hashnode")

    assert devto_result.success is True
    assert devto_result.action == "created"
    assert devto_result.article_id is not None

    assert hashnode_result.success is True
    assert hashnode_result.action == "created"
    assert hashnode_result.article_id is not None


def test_update_existing_article():
    """Test updating existing article when content changes."""
    mock_client = MockPlatformClient("devto")

    # Pre-populate with an existing article
    existing_article = {
        "id": "1",
        "title": "Test Article",
        "body_markdown": "# Old Content",
        "published": True,
        "tags": ["old", "tags"],
        "cover_image": "",
    }
    mock_client.articles["1"] = existing_article

    clients = {"devto": mock_client}
    manager = PublicationManager(clients)

    # Create post content with different content
    post_content = create_test_post_content()
    results = manager.publish_to_all_platforms(post_content)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    assert result.action == "updated"
    assert result.article_id == "1"


def test_skip_update_when_no_changes():
    """Test skipping update when content is identical."""
    mock_client = MockPlatformClient("devto")

    # Create post content
    post_content = create_test_post_content()

    # Pre-populate with identical article
    existing_article = {
        "id": "1",
        "title": post_content.title,
        "body_markdown": post_content.body_markdown,
        "published": not post_content.save_as_draft,
        "tags": post_content.tags,
        "cover_image": post_content.cover,
    }
    mock_client.articles["1"] = existing_article

    clients = {"devto": mock_client}
    manager = PublicationManager(clients)

    results = manager.publish_to_all_platforms(post_content)

    assert len(results) == 1
    result = results[0]

    assert result.success is True
    assert result.action == "skipped"
    assert result.article_id == "1"


def test_error_isolation_between_platforms():
    """Test that errors on one platform don't affect others."""
    mock_client1 = MockPlatformClient("devto", should_fail=True)  # This will fail
    mock_client2 = MockPlatformClient(
        "hashnode", should_fail=False
    )  # This will succeed

    clients = {"devto": mock_client1, "hashnode": mock_client2}
    manager = PublicationManager(clients)

    post_content = create_test_post_content()
    results = manager.publish_to_all_platforms(post_content)

    assert len(results) == 2

    # Check that devto failed but hashnode succeeded
    devto_result = next(r for r in results if r.platform == "devto")
    hashnode_result = next(r for r in results if r.platform == "hashnode")

    assert devto_result.success is False
    assert devto_result.action == "error"
    assert "Mock error in devto" in devto_result.error_message

    assert hashnode_result.success is True
    assert hashnode_result.action == "created"


def test_get_platform_status():
    """Test getting platform status for an article."""
    mock_client1 = MockPlatformClient("devto")
    mock_client2 = MockPlatformClient("hashnode")

    # Add existing article to devto
    existing_article = {
        "id": "1",
        "title": "Test Article",
        "body_markdown": "# Old Content",
        "published": True,
        "tags": ["old"],
        "cover_image": "",
    }
    mock_client1.articles["1"] = existing_article

    clients = {"devto": mock_client1, "hashnode": mock_client2}
    manager = PublicationManager(clients)

    post_content = create_test_post_content()
    status = manager.get_platform_status(post_content)

    assert len(status) == 2

    # devto should show existing article that needs update
    assert status["devto"]["exists"] is True
    assert status["devto"]["article_id"] == "1"
    assert status["devto"]["published"] is True
    assert status["devto"]["needs_update"] is True

    # hashnode should show no existing article
    assert status["hashnode"]["exists"] is False
    assert status["hashnode"]["article_id"] is None


def test_validate_platform_clients():
    """Test platform client validation."""
    mock_client1 = MockPlatformClient("devto", should_fail=False)
    mock_client2 = MockPlatformClient("hashnode", should_fail=True)

    clients = {"devto": mock_client1, "hashnode": mock_client2}
    manager = PublicationManager(clients)

    validation_results = manager.validate_platform_clients()

    assert len(validation_results) == 2
    assert validation_results["devto"] is True
    assert validation_results["hashnode"] is False


def test_content_change_detection():
    """Test comprehensive content change detection."""
    mock_client = MockPlatformClient("devto")

    # Test different types of changes
    test_cases = [
        # (existing_article, expected_needs_update, change_type)
        (
            {
                "title": "Different Title",
                "body_markdown": "# Test Article\n\nThis is test content.",
                "published": True,
                "tags": ["python", "testing"],
                "cover_image": "https://example.com/cover.jpg",
            },
            True,
            "title change",
        ),
        (
            {
                "title": "Test Article",
                "body_markdown": "# Different Content",
                "published": True,
                "tags": ["python", "testing"],
                "cover_image": "https://example.com/cover.jpg",
            },
            True,
            "content change",
        ),
        (
            {
                "title": "Test Article",
                "body_markdown": "# Test Article\n\nThis is test content.",
                "published": False,  # Different publication status
                "tags": ["python", "testing"],
                "cover_image": "https://example.com/cover.jpg",
            },
            True,
            "publication status change",
        ),
        (
            {
                "title": "Test Article",
                "body_markdown": "# Test Article\n\nThis is test content.",
                "published": True,
                "tags": ["different", "tags"],
                "cover_image": "https://example.com/cover.jpg",
            },
            True,
            "tags change",
        ),
        (
            {
                "title": "Test Article",
                "body_markdown": "# Test Article\n\nThis is test content.",
                "published": True,
                "tags": ["python", "testing"],
                "cover_image": "https://different.com/cover.jpg",
            },
            True,
            "cover image change",
        ),
    ]

    clients = {"devto": mock_client}
    manager = PublicationManager(clients)
    post_content = create_test_post_content()

    for existing_article, expected_needs_update, change_type in test_cases:
        # Reset mock client
        mock_client.articles = {"1": {**existing_article, "id": "1"}}

        needs_update = manager._needs_update(post_content, "1", mock_client, "devto")
        assert needs_update == expected_needs_update, f"Failed for {change_type}"

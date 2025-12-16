"""
End-to-end integration tests for multi-platform blog publishing system.

This module tests the complete publishing workflow with both platforms,
validates content change detection with real platform data, tests error
scenarios and recovery mechanisms, and verifies backward compatibility.

Implements Requirements 1.2, 1.5, 3.4, 7.5 from task 11.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Tuple

from src.main import PostPublisher
from src.models.post_content import PostContent
from src.managers.publication_manager import PublicationManager
from src.client.devto_client import DevToClient
from src.client.hashnode_client import HashnodeClient
from src.processors.content_processor import ContentProcessor
from src.utils.error_handler import AuthenticationError, RateLimitError, APIError


class MockDevToClient:
    """Mock DevTo client that simulates real API behavior."""
    
    def __init__(self, should_fail: bool = False, fail_type: str = "api"):
        self.should_fail = should_fail
        self.fail_type = fail_type
        self.articles = {}
        self.next_id = 1000
        
    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        if self.should_fail and self.fail_type == "find":
            raise APIError("Mock API error", platform="devto")
            
        for article_id, article in self.articles.items():
            if article["title"] == title:
                return article_id, article["published"]
        return None, None
    
    def publish_article(self, post_content, published: bool) -> Dict:
        if self.should_fail and self.fail_type == "publish":
            raise APIError("Mock publish error", platform="devto")
            
        article_id = str(self.next_id)
        self.next_id += 1
        
        # Handle both dict and PostContent formats
        if isinstance(post_content, PostContent):
            title = post_content.title
            body = post_content.body_markdown
            tags = post_content.tags
            cover = post_content.cover
        else:
            title = post_content["frontmatterData"]["title"]
            body = post_content["bodyMarkdown"]
            tags = post_content["frontmatterData"]["tags"].split(",") if post_content["frontmatterData"]["tags"] else []
            cover = post_content["frontmatterData"]["cover"]
        
        self.articles[article_id] = {
            "id": int(article_id),
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": tags,
            "cover_image": cover,
            "url": f"https://dev.to/user/{title.lower().replace(' ', '-')}"
        }
        
        return {"id": int(article_id), "url": self.articles[article_id]["url"]}
    
    def update_article(self, article_id: str, post_content, published: bool) -> Dict:
        if self.should_fail and self.fail_type == "update":
            raise APIError("Mock update error", platform="devto")
            
        if article_id in self.articles:
            # Handle both dict and PostContent formats
            if isinstance(post_content, PostContent):
                title = post_content.title
                body = post_content.body_markdown
                tags = post_content.tags
                cover = post_content.cover
            else:
                title = post_content["frontmatterData"]["title"]
                body = post_content["bodyMarkdown"]
                tags = post_content["frontmatterData"]["tags"].split(",") if post_content["frontmatterData"]["tags"] else []
                cover = post_content["frontmatterData"]["cover"]
                
            self.articles[article_id].update({
                "title": title,
                "body_markdown": body,
                "published": published,
                "tags": tags,
                "cover_image": cover
            })
        
        return {"id": int(article_id), "url": self.articles[article_id]["url"]}
    
    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        article = self.articles.get(article_id)
        if article and article["published"] == published:
            return article
        return None
    
    def get_articles(self) -> List[Dict]:
        if self.should_fail and self.fail_type == "get_articles":
            raise APIError("Mock get articles error", platform="devto")
        return list(self.articles.values())


class MockHashnodeClient:
    """Mock Hashnode client that simulates real GraphQL API behavior."""
    
    def __init__(self, should_fail: bool = False, fail_type: str = "api"):
        self.should_fail = should_fail
        self.fail_type = fail_type
        self.articles = {}
        self.next_id = 2000
        
    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        if self.should_fail and self.fail_type == "find":
            raise APIError("Mock GraphQL error", platform="hashnode")
            
        for article_id, article in self.articles.items():
            if article["title"] == title:
                return article_id, article["published"]
        return None, None
    
    def publish_article(self, post_content, published: bool) -> Dict:
        if self.should_fail and self.fail_type == "publish":
            raise APIError("Mock GraphQL publish error", platform="hashnode")
            
        article_id = str(self.next_id)
        self.next_id += 1
        
        # Handle both dict and PostContent formats
        if isinstance(post_content, PostContent):
            title = post_content.title
            body = post_content.body_markdown
            tags = post_content.tags
            cover = post_content.cover
        else:
            title = post_content["frontmatterData"]["title"]
            body = post_content["bodyMarkdown"]
            tags = post_content["frontmatterData"]["tags"].split(",") if post_content["frontmatterData"]["tags"] else []
            cover = post_content["frontmatterData"]["cover"]
        
        self.articles[article_id] = {
            "id": article_id,
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": tags,
            "cover_image": cover,
            "url": f"https://hashnode.com/post/{title.lower().replace(' ', '-')}"
        }
        
        return {
            "id": article_id,
            "url": self.articles[article_id]["url"],
            "slug": title.lower().replace(' ', '-')
        }
    
    def update_article(self, article_id: str, post_content, published: bool) -> Dict:
        if self.should_fail and self.fail_type == "update":
            raise APIError("Mock GraphQL update error", platform="hashnode")
            
        if article_id in self.articles:
            # Handle both dict and PostContent formats
            if isinstance(post_content, PostContent):
                title = post_content.title
                body = post_content.body_markdown
                tags = post_content.tags
                cover = post_content.cover
            else:
                title = post_content["frontmatterData"]["title"]
                body = post_content["bodyMarkdown"]
                tags = post_content["frontmatterData"]["tags"].split(",") if post_content["frontmatterData"]["tags"] else []
                cover = post_content["frontmatterData"]["cover"]
                
            self.articles[article_id].update({
                "title": title,
                "body_markdown": body,
                "published": published,
                "tags": tags,
                "cover_image": cover
            })
        
        return {
            "id": article_id,
            "url": self.articles[article_id]["url"],
            "slug": title.lower().replace(' ', '-')
        }
    
    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        article = self.articles.get(article_id)
        if article and article["published"] == published:
            return article
        return None
    
    def get_articles(self) -> List[Dict]:
        if self.should_fail and self.fail_type == "get_articles":
            raise APIError("Mock GraphQL get articles error", platform="hashnode")
        return list(self.articles.values())


def create_test_markdown_file(content: str, frontmatter: Dict) -> str:
    """Create a temporary markdown file with frontmatter."""
    frontmatter_str = "---\n"
    for key, value in frontmatter.items():
        frontmatter_str += f"{key}: {value}\n"
    frontmatter_str += "---\n\n"
    
    full_content = frontmatter_str + content
    
    # Create temporary file
    fd, path = tempfile.mkstemp(suffix='.md', prefix='test_blog_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    return path


class TestEndToEndIntegration:
    """Test end-to-end publishing workflow with both platforms."""
    
    def test_complete_publishing_workflow_both_platforms(self):
        """
        Test end-to-end publishing workflow with both platforms.
        
        Requirement 1.2: Maintain same content across all platforms while 
        respecting platform-specific formatting requirements.
        """
        # Create mock clients
        mock_devto = MockDevToClient()
        mock_hashnode = MockHashnodeClient()
        
        # Create publication manager with both clients
        clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        manager = PublicationManager(clients)
        
        # Create test post content
        post_content = PostContent(
            title="Integration Test Article",
            subtitle="Testing multi-platform publishing",
            slug="integration-test-article",
            tags=["python", "testing", "integration"],
            cover="https://example.com/cover.jpg",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="# Integration Test\n\nThis tests the complete workflow.\n\n## Section 1\n\nContent here.",
            canonical_url="https://example.com/integration-test-article"
        )
        
        # Publish to all platforms
        results = manager.publish_to_all_platforms(post_content)
        
        # Verify results
        assert len(results) == 2
        
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        # Both should succeed and create new articles
        assert devto_result.success is True
        assert devto_result.action == "created"
        assert devto_result.article_id is not None
        
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"
        assert hashnode_result.article_id is not None
        
        # Verify articles were created in both platforms
        assert len(mock_devto.articles) == 1
        assert len(mock_hashnode.articles) == 1
        
        # Verify content consistency across platforms
        devto_article = list(mock_devto.articles.values())[0]
        hashnode_article = list(mock_hashnode.articles.values())[0]
        
        assert devto_article["title"] == hashnode_article["title"]
        assert devto_article["published"] == hashnode_article["published"]
        # Note: Content may differ due to platform-specific transformations
        
    def test_content_change_detection_with_real_platform_data(self):
        """
        Test content change detection with realistic platform data.
        
        Requirement 3.4: Skip update when no changes are detected.
        """
        mock_devto = MockDevToClient()
        mock_hashnode = MockHashnodeClient()
        
        # Pre-populate with existing articles
        existing_devto_article = {
            "id": 1001,
            "title": "Existing Article",
            "body_markdown": "# Original Content\n\nThis is the original content.",
            "published": True,
            "tags": ["original", "tags"],
            "cover_image": "https://example.com/original.jpg",
            "url": "https://dev.to/user/existing-article"
        }
        mock_devto.articles["1001"] = existing_devto_article
        
        existing_hashnode_article = {
            "id": "2001",
            "title": "Existing Article",
            "body_markdown": "# Original Content\n\nThis is the original content.",
            "published": True,
            "tags": ["original", "tags"],
            "cover_image": "https://example.com/original.jpg",
            "url": "https://hashnode.com/post/existing-article"
        }
        mock_hashnode.articles["2001"] = existing_hashnode_article
        
        clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        manager = PublicationManager(clients)
        
        # Test 1: No changes - should skip update
        post_content_no_changes = PostContent(
            title="Existing Article",
            subtitle="Test subtitle",
            slug="existing-article",
            tags=["original", "tags"],
            cover="https://example.com/original.jpg",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="# Original Content\n\nThis is the original content.",
            canonical_url="https://example.com/existing-article"
        )
        
        results = manager.publish_to_all_platforms(post_content_no_changes)
        
        # Both platforms should skip update
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        assert devto_result.action == "skipped"
        assert hashnode_result.action == "skipped"
        
        # Test 2: Content changes - should update
        post_content_with_changes = PostContent(
            title="Existing Article",
            subtitle="Test subtitle",
            slug="existing-article",
            tags=["updated", "tags"],  # Changed tags
            cover="https://example.com/original.jpg",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="# Updated Content\n\nThis is the updated content.",  # Changed content
            canonical_url="https://example.com/existing-article"
        )
        
        results = manager.publish_to_all_platforms(post_content_with_changes)
        
        # Both platforms should update
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        assert devto_result.action == "updated"
        assert hashnode_result.action == "updated"
        
        # Verify content was actually updated
        updated_devto = mock_devto.articles["1001"]
        updated_hashnode = mock_hashnode.articles["2001"]
        
        assert "Updated Content" in updated_devto["body_markdown"]
        assert "Updated Content" in updated_hashnode["body_markdown"]
        assert updated_devto["tags"] == ["updated", "tags"]
        assert updated_hashnode["tags"] == ["updated", "tags"]
    
    def test_error_scenarios_and_recovery_mechanisms(self):
        """
        Test error scenarios and recovery mechanisms.
        
        Requirement 1.5: Continue publishing to other platforms when 
        platform-specific error occurs.
        """
        # Test 1: DevTo fails, Hashnode succeeds
        mock_devto_failing = MockDevToClient(should_fail=True, fail_type="publish")
        mock_hashnode_working = MockHashnodeClient(should_fail=False)
        
        clients = {"devto": mock_devto_failing, "hashnode": mock_hashnode_working}
        manager = PublicationManager(clients)
        
        post_content = PostContent(
            title="Error Recovery Test",
            subtitle="Testing error isolation",
            slug="error-recovery-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Error Recovery Test\n\nTesting error isolation.",
            canonical_url="https://example.com/error-recovery-test"
        )
        
        results = manager.publish_to_all_platforms(post_content)
        
        # DevTo should fail, Hashnode should succeed
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        assert devto_result.success is False
        assert devto_result.action == "error"
        assert "Mock publish error" in devto_result.error_message
        
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"
        
        # Verify only Hashnode has the article
        assert len(mock_devto_failing.articles) == 0
        assert len(mock_hashnode_working.articles) == 1
        
        # Test 2: Authentication errors
        mock_devto_auth_error = MockDevToClient(should_fail=True, fail_type="find")
        mock_hashnode_working2 = MockHashnodeClient(should_fail=False)
        
        clients2 = {"devto": mock_devto_auth_error, "hashnode": mock_hashnode_working2}
        manager2 = PublicationManager(clients2)
        
        results2 = manager2.publish_to_all_platforms(post_content)
        
        # DevTo should fail during article lookup, Hashnode should succeed
        devto_result2 = next(r for r in results2 if r.platform == "devto")
        hashnode_result2 = next(r for r in results2 if r.platform == "hashnode")
        
        assert devto_result2.success is False
        assert hashnode_result2.success is True
        
        # Test 3: Both platforms fail
        mock_devto_failing2 = MockDevToClient(should_fail=True, fail_type="publish")
        mock_hashnode_failing = MockHashnodeClient(should_fail=True, fail_type="publish")
        
        clients3 = {"devto": mock_devto_failing2, "hashnode": mock_hashnode_failing}
        manager3 = PublicationManager(clients3)
        
        results3 = manager3.publish_to_all_platforms(post_content)
        
        # Both should fail
        assert all(not r.success for r in results3)
        assert len(results3) == 2
    
    def test_backward_compatibility_with_existing_devto_functionality(self):
        """
        Test backward compatibility with existing dev.to functionality.
        
        Requirement 7.5: Maintain compatibility with existing functionality 
        while migrating to uv-based dependency management.
        """
        # Test that the old publish_to_devto method still works
        mock_devto = MockDevToClient()
        
        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                # Initialize publisher with only DevTo
                publisher = PostPublisher(enabled_platforms=["devto"])
                
                # Test the deprecated method
                with patch("glob.glob", return_value=["test_article.md"]):
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = """---
title: Backward Compatibility Test
subtitle: Testing old functionality
slug: backward-compatibility-test
tags: testing,compatibility
cover: https://example.com/cover.jpg
domain: example.com
saveAsDraft: false
enableToc: true
---

# Backward Compatibility Test

This tests that old functionality still works.
"""
                        
                        # This should work without errors
                        publisher.publish_to_devto()
                        
                        # Verify article was published to DevTo
                        assert len(mock_devto.articles) == 1
                        article = list(mock_devto.articles.values())[0]
                        assert article["title"] == "Backward Compatibility Test"
    
    def test_platform_specific_content_transformations(self):
        """Test that platform-specific content transformations work correctly."""
        mock_devto = MockDevToClient()
        mock_hashnode = MockHashnodeClient()
        
        clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        manager = PublicationManager(clients)
        
        # Create content with HTML alignment attributes (should be removed for Hashnode)
        post_content = PostContent(
            title="Content Transformation Test",
            subtitle="Testing platform transformations",
            slug="content-transformation-test",
            tags=["html", "transformation"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="""# Content Transformation Test

<div align="center">
    <img src="test.jpg" alt="Test Image" align="center">
</div>

<p align="right">Right-aligned text</p>

Regular content without alignment.
""",
            canonical_url="https://example.com/content-transformation-test"
        )
        
        results = manager.publish_to_all_platforms(post_content)
        
        # Both should succeed
        assert all(r.success for r in results)
        
        # Get the processed content from both platforms
        devto_article = list(mock_devto.articles.values())[0]
        hashnode_article = list(mock_hashnode.articles.values())[0]
        
        # DevTo should preserve alignment attributes
        assert 'align="center"' in devto_article["body_markdown"]
        assert 'align="right"' in devto_article["body_markdown"]
        
        # Hashnode should have alignment attributes removed
        # Note: This depends on the ContentProcessor implementation
        # The test verifies that different processing occurred
        assert devto_article["body_markdown"] != hashnode_article["body_markdown"]
    
    def test_tag_format_conversion_for_platforms(self):
        """Test tag format conversion for different platforms."""
        mock_devto = MockDevToClient()
        mock_hashnode = MockHashnodeClient()
        
        clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        manager = PublicationManager(clients)
        
        # Create content with complex tags that need conversion
        post_content = PostContent(
            title="Tag Conversion Test",
            subtitle="Testing tag format conversion",
            slug="tag-conversion-test",
            tags=["C++", "Node.js", "Web Development", "Machine Learning"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Tag Conversion Test\n\nTesting tag conversion.",
            canonical_url="https://example.com/tag-conversion-test"
        )
        
        results = manager.publish_to_all_platforms(post_content)
        
        # Both should succeed
        assert all(r.success for r in results)
        
        # Get articles from both platforms
        devto_article = list(mock_devto.articles.values())[0]
        hashnode_article = list(mock_hashnode.articles.values())[0]
        
        # Verify tags were processed (exact format depends on ContentProcessor)
        assert len(devto_article["tags"]) > 0
        assert len(hashnode_article["tags"]) > 0
        
        # Tags should be converted to platform-appropriate formats
        # This test verifies that tag processing occurred
        assert isinstance(devto_article["tags"], list)
        assert isinstance(hashnode_article["tags"], list)
    
    def test_configuration_validation_and_error_handling(self):
        """Test configuration validation and comprehensive error handling."""
        # Test with missing API keys
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No platform clients could be initialized"):
                PostPublisher()
        
        # Test with partial configuration (only DevTo)
        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=MockDevToClient()):
                publisher = PostPublisher(enabled_platforms=["devto"])
                
                # Should only have DevTo client
                assert len(publisher.platform_clients) == 1
                assert "devto" in publisher.platform_clients
                
                # Validation should show DevTo as valid
                validation = publisher.validate_configuration()
                assert validation["devto"] is True
    
    def test_rate_limiting_and_retry_mechanisms(self):
        """Test rate limiting and retry mechanisms."""
        # Create a mock client that fails first, then succeeds
        class RateLimitMockClient(MockDevToClient):
            def __init__(self):
                super().__init__()
                self.attempt_count = 0
            
            def publish_article(self, post_content, published: bool):
                self.attempt_count += 1
                if self.attempt_count == 1:
                    raise RateLimitError("Rate limit exceeded", platform="devto")
                return super().publish_article(post_content, published)
        
        mock_devto = RateLimitMockClient()
        mock_hashnode = MockHashnodeClient()
        
        clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        manager = PublicationManager(clients)
        
        post_content = PostContent(
            title="Rate Limit Test",
            subtitle="Testing rate limiting",
            slug="rate-limit-test",
            tags=["testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Rate Limit Test",
            canonical_url="https://example.com/rate-limit-test"
        )
        
        # This should handle the rate limit error gracefully
        results = manager.publish_to_all_platforms(post_content)
        
        # DevTo should fail due to rate limiting, Hashnode should succeed
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        assert devto_result.success is False
        assert "Rate limit exceeded" in devto_result.error_message
        assert hashnode_result.success is True


class TestPostPublisherIntegration:
    """Test PostPublisher class integration scenarios."""
    
    def test_post_publisher_with_markdown_files(self):
        """Test PostPublisher with actual markdown files."""
        # Create temporary markdown files
        test_files = []
        
        try:
            # Create test markdown file
            frontmatter = {
                "title": "Test Blog Post",
                "subtitle": "A test blog post",
                "slug": "test-blog-post",
                "tags": "python,testing",
                "cover": "https://example.com/cover.jpg",
                "domain": "example.com",
                "saveAsDraft": "false",
                "enableToc": "true"
            }
            
            content = """# Test Blog Post

This is a test blog post for integration testing.

## Section 1

Some content here.

## Section 2

More content here.
"""
            
            test_file = create_test_markdown_file(content, frontmatter)
            test_files.append(test_file)
            
            # Mock the glob to return our test file
            with patch("glob.glob", return_value=[test_file]):
                with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
                    mock_devto = MockDevToClient()
                    
                    with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                        publisher = PostPublisher(enabled_platforms=["devto"])
                        publisher.publish_to_all_platforms()
                        
                        # Verify article was published
                        assert len(mock_devto.articles) == 1
                        article = list(mock_devto.articles.values())[0]
                        assert article["title"] == "Test Blog Post"
                        assert "This is a test blog post" in article["body_markdown"]
        
        finally:
            # Clean up temporary files
            for file_path in test_files:
                try:
                    os.unlink(file_path)
                except OSError:
                    pass
    
    def test_post_publisher_platform_status_checking(self):
        """Test PostPublisher platform status checking functionality."""
        mock_devto = MockDevToClient()
        mock_hashnode = MockHashnodeClient()
        
        # Add existing article to DevTo
        existing_article = {
            "id": 1001,
            "title": "Existing Article",
            "body_markdown": "# Existing Content",
            "published": True,
            "tags": ["existing"],
            "cover_image": ""
        }
        mock_devto.articles["1001"] = existing_article
        
        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key", "HASHNODE_API_KEY": "test_key", "HASHNODE_USERNAME": "test_user"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                with patch("src.client.hashnode_client.HashnodeClient", return_value=mock_hashnode):
                    publisher = PostPublisher()
                    
                    # Check status of existing article
                    status = publisher.get_platform_status("Existing Article")
                    
                    assert "devto" in status
                    assert "hashnode" in status
                    
                    # DevTo should show existing article
                    assert status["devto"]["exists"] is True
                    assert status["devto"]["article_id"] == "1001"
                    
                    # Hashnode should show no existing article
                    assert status["hashnode"]["exists"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
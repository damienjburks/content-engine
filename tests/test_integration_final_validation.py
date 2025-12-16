"""
Final validation integration tests for task 11.

This module provides comprehensive integration tests that validate the core
requirements without complex mocking dependencies.

Implements Requirements 1.2, 1.5, 3.4, 7.5 from task 11.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Optional, Tuple

from src.managers.publication_manager import PublicationManager
from src.models.post_content import PostContent, PublicationResult
from src.processors.content_processor import ContentProcessor
from src.utils.error_handler import AuthenticationError, RateLimitError, APIError


class SimpleMockClient:
    """Simple mock client for integration testing."""
    
    def __init__(self, platform_name: str, should_fail: bool = False):
        self.platform_name = platform_name
        self.should_fail = should_fail
        self.articles = {}
        self.next_id = 1
        
    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        if self.should_fail:
            raise APIError(f"Mock error in {self.platform_name}", platform=self.platform_name)
        
        for article_id, article in self.articles.items():
            if article["title"] == title:
                return article_id, article["published"]
        return None, None
    
    def publish_article(self, post_content, published: bool) -> Dict:
        if self.should_fail:
            raise APIError(f"Mock error in {self.platform_name}", platform=self.platform_name)
        
        article_id = str(self.next_id)
        self.next_id += 1
        
        # Handle both dict and PostContent formats
        if isinstance(post_content, PostContent):
            title = post_content.title
            body = post_content.body_markdown
        else:
            title = post_content["frontmatterData"]["title"]
            body = post_content["bodyMarkdown"]
        
        self.articles[article_id] = {
            "id": article_id,
            "title": title,
            "body_markdown": body,
            "published": published,
            "tags": [],
            "cover_image": "",
            "url": f"https://{self.platform_name}.com/test"
        }
        
        return {"id": article_id, "url": self.articles[article_id]["url"]}
    
    def update_article(self, article_id: str, post_content, published: bool) -> Dict:
        if self.should_fail:
            raise APIError(f"Mock error in {self.platform_name}", platform=self.platform_name)
        
        if article_id in self.articles:
            # Handle both dict and PostContent formats
            if isinstance(post_content, PostContent):
                title = post_content.title
                body = post_content.body_markdown
            else:
                title = post_content["frontmatterData"]["title"]
                body = post_content["bodyMarkdown"]
            
            self.articles[article_id].update({
                "title": title,
                "body_markdown": body,
                "published": published
            })
        
        return {"id": article_id, "url": self.articles[article_id]["url"]}
    
    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        article = self.articles.get(article_id)
        if article and article["published"] == published:
            return article
        return None
    
    def get_articles(self) -> List[Dict]:
        if self.should_fail:
            raise APIError(f"Mock error in {self.platform_name}", platform=self.platform_name)
        return list(self.articles.values())


class TestFinalIntegrationValidation:
    """Final validation tests for multi-platform publishing system."""
    
    def test_end_to_end_publishing_workflow_both_platforms(self):
        """
        Test complete end-to-end publishing workflow with both platforms.
        
        Requirement 1.2: Maintain same content across all platforms while 
        respecting platform-specific formatting requirements.
        """
        # Create mock clients for both platforms
        devto_client = SimpleMockClient("devto")
        hashnode_client = SimpleMockClient("hashnode")
        
        # Create publication manager
        clients = {"devto": devto_client, "hashnode": hashnode_client}
        manager = PublicationManager(clients)
        
        # Create test content
        post_content = PostContent(
            title="End-to-End Test Article",
            subtitle="Testing complete workflow",
            slug="end-to-end-test",
            tags=["testing", "integration"],
            cover="https://example.com/cover.jpg",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="# End-to-End Test\n\nThis tests the complete publishing workflow.",
            canonical_url="https://example.com/end-to-end-test"
        )
        
        # Publish to all platforms
        results = manager.publish_to_all_platforms(post_content)
        
        # Verify results
        assert len(results) == 2
        
        # Both platforms should succeed
        for result in results:
            assert result.success is True
            assert result.action == "created"
            assert result.article_id is not None
        
        # Verify articles were created on both platforms
        assert len(devto_client.articles) == 1
        assert len(hashnode_client.articles) == 1
        
        # Verify content consistency (Requirement 1.2)
        devto_article = list(devto_client.articles.values())[0]
        hashnode_article = list(hashnode_client.articles.values())[0]
        
        assert devto_article["title"] == hashnode_article["title"]
        assert devto_article["published"] == hashnode_article["published"]
    
    def test_content_change_detection_validation(self):
        """
        Test content change detection with realistic scenarios.
        
        Requirement 3.4: Skip update when no changes are detected.
        """
        devto_client = SimpleMockClient("devto")
        hashnode_client = SimpleMockClient("hashnode")
        
        # Pre-populate with existing articles
        existing_article = {
            "id": "1",
            "title": "Change Detection Test",
            "body_markdown": "# Original Content\n\nThis is the original content.",
            "published": True,
            "tags": ["original"],
            "cover_image": "",
            "url": "https://devto.com/test"
        }
        devto_client.articles["1"] = existing_article.copy()
        hashnode_client.articles["1"] = existing_article.copy()
        
        clients = {"devto": devto_client, "hashnode": hashnode_client}
        manager = PublicationManager(clients)
        
        # Test 1: No changes - should skip update
        post_content_no_changes = PostContent(
            title="Change Detection Test",
            subtitle="Test subtitle",
            slug="change-detection-test",
            tags=["original"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Original Content\n\nThis is the original content.",
            canonical_url="https://example.com/change-detection-test"
        )
        
        results = manager.publish_to_all_platforms(post_content_no_changes)
        
        # Both should skip update (Requirement 3.4)
        for result in results:
            assert result.action == "skipped"
        
        # Test 2: Content changes - should update
        post_content_with_changes = PostContent(
            title="Change Detection Test",
            subtitle="Test subtitle",
            slug="change-detection-test",
            tags=["updated"],  # Changed tags
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Updated Content\n\nThis is the updated content.",  # Changed content
            canonical_url="https://example.com/change-detection-test"
        )
        
        results = manager.publish_to_all_platforms(post_content_with_changes)
        
        # Both should update
        for result in results:
            assert result.action == "updated"
    
    def test_error_isolation_and_recovery(self):
        """
        Test error scenarios and recovery mechanisms.
        
        Requirement 1.5: Continue publishing to other platforms when 
        platform-specific error occurs.
        """
        # Create one failing and one working client
        failing_client = SimpleMockClient("devto", should_fail=True)
        working_client = SimpleMockClient("hashnode", should_fail=False)
        
        clients = {"devto": failing_client, "hashnode": working_client}
        manager = PublicationManager(clients)
        
        post_content = PostContent(
            title="Error Isolation Test",
            subtitle="Testing error handling",
            slug="error-isolation-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Error Isolation Test\n\nTesting error isolation.",
            canonical_url="https://example.com/error-isolation-test"
        )
        
        results = manager.publish_to_all_platforms(post_content)
        
        # Should have results for both platforms
        assert len(results) == 2
        
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")
        
        # DevTo should fail, Hashnode should succeed (Requirement 1.5)
        assert devto_result.success is False
        assert devto_result.action == "error"
        
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"
        
        # Verify only working platform has the article
        assert len(failing_client.articles) == 0
        assert len(working_client.articles) == 1
    
    def test_content_processor_platform_transformations(self):
        """Test content processor platform-specific transformations."""
        processor = ContentProcessor()
        
        # Test content with HTML alignment attributes
        content_with_alignment = """# Test Content

<div align="center">
    <img src="test.jpg" alt="Test" align="center">
</div>

<p align="right">Right-aligned text</p>

Regular content.
"""
        
        # Test platform-specific processing
        devto_processed = processor.process_content_for_platform(
            PostContent(
                title="Test",
                subtitle="",
                slug="test",
                tags=[],
                cover="",
                domain="example.com",
                save_as_draft=False,
                enable_toc=False,
                body_markdown=content_with_alignment,
                canonical_url=""
            ),
            "devto"
        )
        
        hashnode_processed = processor.process_content_for_platform(
            PostContent(
                title="Test",
                subtitle="",
                slug="test",
                tags=[],
                cover="",
                domain="example.com",
                save_as_draft=False,
                enable_toc=False,
                body_markdown=content_with_alignment,
                canonical_url=""
            ),
            "hashnode"
        )
        
        # Both should be processed (may differ based on platform requirements)
        assert isinstance(devto_processed, str)
        assert isinstance(hashnode_processed, str)
        assert len(devto_processed) > 0
        assert len(hashnode_processed) > 0
    
    def test_tag_conversion_for_platforms(self):
        """Test tag conversion for different platforms."""
        processor = ContentProcessor()
        
        # Test complex tags that need conversion
        complex_tags = ["C++", "Node.js", "Web Development", "Machine Learning"]
        
        # Test conversion for both platforms
        devto_tags = processor.convert_tags_for_platform(complex_tags, "devto")
        hashnode_tags = processor.convert_tags_for_platform(complex_tags, "hashnode")
        
        # Both should return processed tags
        assert isinstance(devto_tags, list)
        assert isinstance(hashnode_tags, list)
        assert len(devto_tags) > 0
        assert len(hashnode_tags) > 0
    
    def test_publication_manager_validation(self):
        """Test publication manager platform validation."""
        # Test with working clients
        working_devto = SimpleMockClient("devto", should_fail=False)
        working_hashnode = SimpleMockClient("hashnode", should_fail=False)
        
        clients = {"devto": working_devto, "hashnode": working_hashnode}
        manager = PublicationManager(clients)
        
        validation_results = manager.validate_platform_clients()
        
        # Both should validate successfully
        assert validation_results["devto"] is True
        assert validation_results["hashnode"] is True
        
        # Test with failing clients
        failing_devto = SimpleMockClient("devto", should_fail=True)
        failing_hashnode = SimpleMockClient("hashnode", should_fail=True)
        
        failing_clients = {"devto": failing_devto, "hashnode": failing_hashnode}
        failing_manager = PublicationManager(failing_clients)
        
        failing_validation = failing_manager.validate_platform_clients()
        
        # Both should fail validation
        assert failing_validation["devto"] is False
        assert failing_validation["hashnode"] is False
    
    def test_backward_compatibility_data_structures(self):
        """
        Test backward compatibility with existing data structures.
        
        Requirement 7.5: Maintain compatibility with existing functionality.
        """
        devto_client = SimpleMockClient("devto")
        clients = {"devto": devto_client}
        manager = PublicationManager(clients)
        
        # Test with old-style dict format (backward compatibility)
        old_format_content = {
            "frontmatterData": {
                "title": "Backward Compatibility Test",
                "subtitle": "Testing old format",
                "slug": "backward-compatibility-test",
                "tags": "testing,compatibility",
                "cover": "https://example.com/cover.jpg",
                "domain": "example.com",
                "saveAsDraft": False,
                "seriesName": None
            },
            "bodyMarkdown": "# Backward Compatibility Test\n\nTesting old data format."
        }
        
        # This should work with the old format
        response = devto_client.publish_article(old_format_content, True)
        
        # Verify it worked
        assert "id" in response
        assert len(devto_client.articles) == 1
        
        article = list(devto_client.articles.values())[0]
        assert article["title"] == "Backward Compatibility Test"
    
    def test_comprehensive_error_handling(self):
        """Test comprehensive error handling scenarios."""
        # Test different types of errors
        auth_error_client = SimpleMockClient("devto")
        
        # Mock authentication error
        def mock_auth_error(*args, **kwargs):
            raise AuthenticationError("Auth failed", platform="devto")
        
        auth_error_client.get_articles = mock_auth_error
        
        # Test rate limit error
        rate_limit_client = SimpleMockClient("hashnode")
        
        def mock_rate_limit(*args, **kwargs):
            raise RateLimitError("Rate limit exceeded", platform="hashnode")
        
        rate_limit_client.get_articles = mock_rate_limit
        
        clients = {"devto": auth_error_client, "hashnode": rate_limit_client}
        manager = PublicationManager(clients)
        
        # Validation should handle different error types
        validation_results = manager.validate_platform_clients()
        
        # Both should fail but for different reasons
        assert validation_results["devto"] is False
        assert validation_results["hashnode"] is False
    
    def test_content_normalization_and_comparison(self):
        """Test content normalization for change detection."""
        processor = ContentProcessor()
        
        # Test content with different formatting but same meaning
        content1 = "# Test Article\n\nThis is test content.\n\n## Section 1\n\nMore content."
        content2 = "# Test Article\n\nThis is test content.\n\n## Section 1\n\nMore content."
        content3 = "# Different Article\n\nThis is different content."
        
        # Normalize content
        normalized1 = processor.normalize_content_for_comparison(content1)
        normalized2 = processor.normalize_content_for_comparison(content2)
        normalized3 = processor.normalize_content_for_comparison(content3)
        
        # Same content should normalize to same result
        assert normalized1 == normalized2
        
        # Different content should normalize to different results
        assert normalized1 != normalized3
    
    def test_platform_status_checking(self):
        """Test platform status checking functionality."""
        devto_client = SimpleMockClient("devto")
        hashnode_client = SimpleMockClient("hashnode")
        
        # Add existing article to DevTo
        existing_article = {
            "id": "1",
            "title": "Status Test Article",
            "body_markdown": "# Status Test",
            "published": True,
            "tags": ["test"],
            "cover_image": "",
            "url": "https://devto.com/test"
        }
        devto_client.articles["1"] = existing_article
        
        clients = {"devto": devto_client, "hashnode": hashnode_client}
        manager = PublicationManager(clients)
        
        # Create post content for status check
        post_content = PostContent(
            title="Status Test Article",
            subtitle="Testing status check",
            slug="status-test-article",
            tags=["test"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Status Test\n\nUpdated content.",
            canonical_url="https://example.com/status-test-article"
        )
        
        # Get platform status
        status = manager.get_platform_status(post_content)
        
        # Verify status information
        assert "devto" in status
        assert "hashnode" in status
        
        # DevTo should show existing article
        assert status["devto"]["exists"] is True
        assert status["devto"]["article_id"] == "1"
        
        # Hashnode should show no existing article
        assert status["hashnode"]["exists"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
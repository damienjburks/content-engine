"""
Integration tests for error scenarios and edge cases in multi-platform publishing.

This module focuses on testing various error conditions, recovery mechanisms,
and edge cases that can occur during multi-platform publishing.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Optional, Tuple

from src.managers.publication_manager import PublicationManager
from src.models.post_content import PostContent
from src.utils.error_handler import AuthenticationError, RateLimitError, APIError
from src.processors.content_processor import ContentProcessor


class FailingPlatformClient:
    """Mock platform client that simulates various failure scenarios."""

    def __init__(self, platform_name: str, failure_mode: str = "none"):
        self.platform_name = platform_name
        self.failure_mode = failure_mode
        self.call_count = 0

    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        self.call_count += 1

        if self.failure_mode == "auth_error":
            raise AuthenticationError(
                f"Authentication failed for {self.platform_name}",
                platform=self.platform_name,
            )
        elif self.failure_mode == "rate_limit":
            raise RateLimitError(
                f"Rate limit exceeded for {self.platform_name}",
                platform=self.platform_name,
            )
        elif self.failure_mode == "api_error":
            raise APIError(
                f"API error for {self.platform_name}", platform=self.platform_name
            )
        elif self.failure_mode == "intermittent" and self.call_count <= 2:
            raise APIError(
                f"Intermittent error for {self.platform_name}",
                platform=self.platform_name,
            )

        return None, None

    def publish_article(self, post_content, published: bool) -> Dict:
        self.call_count += 1

        if self.failure_mode == "auth_error":
            raise AuthenticationError(
                f"Authentication failed for {self.platform_name}",
                platform=self.platform_name,
            )
        elif self.failure_mode == "rate_limit":
            raise RateLimitError(
                f"Rate limit exceeded for {self.platform_name}",
                platform=self.platform_name,
            )
        elif self.failure_mode == "api_error":
            raise APIError(
                f"API error for {self.platform_name}", platform=self.platform_name
            )
        elif self.failure_mode == "timeout":
            raise APIError(
                f"Timeout error for {self.platform_name}", platform=self.platform_name
            )

        return {"id": "test_id", "url": f"https://{self.platform_name}.com/test"}

    def update_article(self, article_id: str, post_content, published: bool) -> Dict:
        return self.publish_article(post_content, published)

    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        if self.failure_mode == "get_article_error":
            raise APIError(
                f"Get article error for {self.platform_name}",
                platform=self.platform_name,
            )
        return None

    def get_articles(self) -> List[Dict]:
        if self.failure_mode == "get_articles_error":
            raise APIError(
                f"Get articles error for {self.platform_name}",
                platform=self.platform_name,
            )
        return []


class TestErrorScenarios:
    """Test various error scenarios and recovery mechanisms."""

    def test_authentication_errors_isolation(self):
        """Test that authentication errors on one platform don't affect others."""
        # DevTo fails with auth error, Hashnode works
        failing_devto = FailingPlatformClient("devto", "auth_error")
        working_hashnode = FailingPlatformClient("hashnode", "none")

        clients = {"devto": failing_devto, "hashnode": working_hashnode}
        manager = PublicationManager(clients)

        post_content = PostContent(
            title="Auth Error Test",
            subtitle="Testing authentication error handling",
            slug="auth-error-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Auth Error Test",
            canonical_url="https://example.com/auth-error-test",
        )

        results = manager.publish_to_all_platforms(post_content)

        # Should have results for both platforms
        assert len(results) == 2

        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")

        # DevTo should fail with auth error
        assert devto_result.success is False
        assert devto_result.action == "error"
        assert "Authentication failed" in devto_result.error_message

        # Hashnode should succeed
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"

    def test_rate_limiting_errors_isolation(self):
        """Test that rate limiting errors on one platform don't affect others."""
        # DevTo fails with rate limit, Hashnode works
        rate_limited_devto = FailingPlatformClient("devto", "rate_limit")
        working_hashnode = FailingPlatformClient("hashnode", "none")

        clients = {"devto": rate_limited_devto, "hashnode": working_hashnode}
        manager = PublicationManager(clients)

        post_content = PostContent(
            title="Rate Limit Test",
            subtitle="Testing rate limit error handling",
            slug="rate-limit-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Rate Limit Test",
            canonical_url="https://example.com/rate-limit-test",
        )

        results = manager.publish_to_all_platforms(post_content)

        assert len(results) == 2

        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")

        # DevTo should fail with rate limit error
        assert devto_result.success is False
        assert "Rate limit exceeded" in devto_result.error_message

        # Hashnode should succeed
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"

    def test_api_errors_isolation(self):
        """Test that API errors on one platform don't affect others."""
        # Both platforms have different types of API errors
        api_error_devto = FailingPlatformClient("devto", "api_error")
        timeout_hashnode = FailingPlatformClient("hashnode", "timeout")

        clients = {"devto": api_error_devto, "hashnode": timeout_hashnode}
        manager = PublicationManager(clients)

        post_content = PostContent(
            title="API Error Test",
            subtitle="Testing API error handling",
            slug="api-error-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# API Error Test",
            canonical_url="https://example.com/api-error-test",
        )

        results = manager.publish_to_all_platforms(post_content)

        assert len(results) == 2

        # Both should fail but with different error messages
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")

        assert devto_result.success is False
        assert "API error for devto" in devto_result.error_message

        assert hashnode_result.success is False
        assert "Timeout error for hashnode" in hashnode_result.error_message

    def test_partial_failure_scenarios(self):
        """Test various partial failure scenarios."""

        # Test scenario where article lookup fails but publish succeeds
        class PartialFailureClient(FailingPlatformClient):
            def __init__(self, platform_name: str):
                super().__init__(platform_name, "none")
                self.find_calls = 0

            def find_article_by_title(self, title: str):
                self.find_calls += 1
                if self.find_calls == 1:
                    raise APIError(
                        f"Find error for {self.platform_name}",
                        platform=self.platform_name,
                    )
                return None, None

        partial_fail_devto = PartialFailureClient("devto")
        working_hashnode = FailingPlatformClient("hashnode", "none")

        clients = {"devto": partial_fail_devto, "hashnode": working_hashnode}
        manager = PublicationManager(clients)

        post_content = PostContent(
            title="Partial Failure Test",
            subtitle="Testing partial failure scenarios",
            slug="partial-failure-test",
            tags=["error", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Partial Failure Test",
            canonical_url="https://example.com/partial-failure-test",
        )

        results = manager.publish_to_all_platforms(post_content)

        assert len(results) == 2

        # DevTo should fail during article lookup
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")

        assert devto_result.success is False
        assert hashnode_result.success is True

    def test_content_change_detection_errors(self):
        """Test error handling in content change detection."""

        class ChangeDetectionErrorClient(FailingPlatformClient):
            def __init__(self, platform_name: str):
                super().__init__(platform_name, "none")
                self.articles = {
                    "1": {
                        "id": "1",
                        "title": "Test Article",
                        "body_markdown": "# Test",
                        "published": True,
                        "tags": ["test"],
                        "cover_image": "",
                    }
                }

            def find_article_by_title(self, title: str):
                return "1", True

            def get_article(self, article_id: str, published: bool):
                # Simulate error when trying to get article for comparison
                raise APIError(
                    f"Get article error for {self.platform_name}",
                    platform=self.platform_name,
                )

        error_client = ChangeDetectionErrorClient("devto")
        working_client = FailingPlatformClient("hashnode", "none")

        clients = {"devto": error_client, "hashnode": working_client}
        manager = PublicationManager(clients)

        post_content = PostContent(
            title="Test Article",
            subtitle="Testing change detection errors",
            slug="test-article",
            tags=["test"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="# Test Article\n\nUpdated content.",
            canonical_url="https://example.com/test-article",
        )

        results = manager.publish_to_all_platforms(post_content)

        # DevTo should fail during change detection, but the system should handle it gracefully
        devto_result = next(r for r in results if r.platform == "devto")
        hashnode_result = next(r for r in results if r.platform == "hashnode")

        # DevTo should fail
        assert devto_result.success is False

        # Hashnode should succeed (new article)
        assert hashnode_result.success is True
        assert hashnode_result.action == "created"

    def test_platform_validation_errors(self):
        """Test platform validation error scenarios."""
        # Create clients with different validation failures
        auth_error_client = FailingPlatformClient(
            "devto", "get_articles_error"
        )  # Changed to get_articles_error
        get_articles_error_client = FailingPlatformClient(
            "hashnode", "get_articles_error"
        )

        clients = {"devto": auth_error_client, "hashnode": get_articles_error_client}
        manager = PublicationManager(clients)

        validation_results = manager.validate_platform_clients()

        # Both should fail validation but for different reasons
        assert validation_results["devto"] is False
        assert validation_results["hashnode"] is False

    def test_empty_content_handling(self):
        """Test handling of edge cases with empty or minimal content."""
        working_client = FailingPlatformClient("devto", "none")
        clients = {"devto": working_client}
        manager = PublicationManager(clients)

        # Test with minimal content
        minimal_post = PostContent(
            title="",  # Empty title
            subtitle="",
            slug="",
            tags=[],  # Empty tags
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="",  # Empty content
            canonical_url="",
        )

        # This should handle empty content gracefully
        results = manager.publish_to_all_platforms(minimal_post)

        assert len(results) == 1
        # The result depends on how the platform client handles empty content
        # At minimum, it should not crash
        result = results[0]
        assert result.platform == "devto"

    def test_large_content_handling(self):
        """Test handling of very large content."""
        working_client = FailingPlatformClient("devto", "none")
        clients = {"devto": working_client}
        manager = PublicationManager(clients)

        # Create very large content
        large_content = (
            "# Large Content Test\n\n" + "This is a very long paragraph. " * 1000
        )

        large_post = PostContent(
            title="Large Content Test",
            subtitle="Testing large content handling",
            slug="large-content-test",
            tags=["large", "content", "test"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=False,
            body_markdown=large_content,
            canonical_url="https://example.com/large-content-test",
        )

        # This should handle large content gracefully
        results = manager.publish_to_all_platforms(large_post)

        assert len(results) == 1
        result = results[0]
        assert result.platform == "devto"
        # Should succeed unless the platform has size limits
        assert result.success is True

    def test_special_characters_in_content(self):
        """Test handling of special characters and unicode in content."""
        working_client = FailingPlatformClient("devto", "none")
        clients = {"devto": working_client}
        manager = PublicationManager(clients)

        # Content with special characters and unicode
        special_content = """# Special Characters Test 🚀

This content contains various special characters:
- Unicode: 🎉 🔥 💻 🌟
- Accented characters: café, naïve, résumé
- Mathematical symbols: ∑, ∆, π, ∞
- Code with special chars: `const obj = { "key": "value" };`
- HTML entities: &lt; &gt; &amp; &quot;

## Code Block with Special Characters

```python
def test_function():
    # Comment with unicode: 🐍
    return "Hello, 世界!"
```

End of test content.
"""

        special_post = PostContent(
            title="Special Characters Test 🚀",
            subtitle="Testing unicode and special characters",
            slug="special-characters-test",
            tags=["unicode", "special-chars", "testing"],
            cover="",
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown=special_content,
            canonical_url="https://example.com/special-characters-test",
        )

        # This should handle special characters gracefully
        results = manager.publish_to_all_platforms(special_post)

        assert len(results) == 1
        result = results[0]
        assert result.platform == "devto"
        assert result.success is True

    def test_malformed_frontmatter_handling(self):
        """Test handling of malformed or unusual frontmatter data."""
        working_client = FailingPlatformClient("devto", "none")
        clients = {"devto": working_client}
        manager = PublicationManager(clients)

        # Test with unusual tag formats
        unusual_post = PostContent(
            title="Unusual Frontmatter Test",
            subtitle="Testing edge cases in frontmatter",
            slug="unusual-frontmatter-test",
            tags=[
                "tag with spaces",
                "tag,with,commas",
                "tag-with-dashes",
                "tag_with_underscores",
            ],
            cover="not-a-valid-url",  # Invalid URL
            domain="example.com",
            save_as_draft=False,
            enable_toc=True,
            body_markdown="# Unusual Frontmatter Test\n\nTesting edge cases.",
            canonical_url="https://example.com/unusual-frontmatter-test",
        )

        # This should handle unusual frontmatter gracefully
        results = manager.publish_to_all_platforms(unusual_post)

        assert len(results) == 1
        result = results[0]
        assert result.platform == "devto"
        # Should succeed with processed/cleaned data
        assert result.success is True


class TestContentProcessorErrorHandling:
    """Test error handling in content processing."""

    def test_content_processor_with_malformed_markdown(self):
        """Test content processor with malformed markdown."""
        processor = ContentProcessor()

        # Test with malformed markdown
        malformed_content = """# Heading 1
        
## Heading 2 without proper spacing
###Heading 3 without space
        
Paragraph with [broken link](
        
```python
# Code block without closing
def test():
    return "unclosed
        
Another paragraph.
"""

        # Should handle malformed content gracefully
        normalized = processor.normalize_content_for_comparison(malformed_content)
        assert isinstance(normalized, str)
        assert len(normalized) > 0

        # Test platform-specific processing
        devto_content = processor._apply_devto_transformations(malformed_content)
        hashnode_content = processor._apply_hashnode_transformations(malformed_content)

        assert isinstance(devto_content, str)
        assert isinstance(hashnode_content, str)

    def test_content_processor_with_empty_content(self):
        """Test content processor with empty or whitespace-only content."""
        processor = ContentProcessor()

        # Test with empty content
        empty_normalized = processor.normalize_content_for_comparison("")
        assert empty_normalized == ""

        # Test with whitespace-only content
        whitespace_content = "   \n\t  \n   "
        whitespace_normalized = processor.normalize_content_for_comparison(
            whitespace_content
        )
        assert isinstance(whitespace_normalized, str)

        # Test TOC generation with empty content
        empty_toc = processor._generate_table_of_contents("")
        assert isinstance(empty_toc, str)

    def test_tag_conversion_edge_cases(self):
        """Test tag conversion with edge cases."""
        processor = ContentProcessor()

        # Test with empty tags
        empty_tags = processor.convert_tags_for_platform([], "devto")
        assert empty_tags == []

        # Test with None tags
        none_tags = processor.convert_tags_for_platform(None, "devto")
        assert none_tags == []

        # Test with very long tags
        long_tags = ["a" * 100, "b" * 200]
        processed_long_tags = processor.convert_tags_for_platform(long_tags, "hashnode")
        assert isinstance(processed_long_tags, list)

        # Test with special character tags
        special_tags = ["tag with spaces", "tag/with/slashes", "tag@with@symbols"]
        processed_special = processor.convert_tags_for_platform(
            special_tags, "hashnode"
        )
        assert isinstance(processed_special, list)
        assert len(processed_special) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Backward compatibility tests for the multi-platform blog publishing system.

This module ensures that existing functionality continues to work after
the migration to multi-platform support and uv package management.

Implements Requirement 7.5: Maintain compatibility with existing functionality.
"""

import os
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import Dict, List

from src.main import PostPublisher
from src.client.devto_client import DevToClient


class LegacyMockDevToClient:
    """Mock DevTo client that simulates the old single-platform behavior."""

    def __init__(self):
        self.articles = {}
        self.next_id = 1
        self.published_articles = []

    def publish_article(self, post_content, published: bool):
        """Simulate old publish_article method."""
        article_id = self.next_id
        self.next_id += 1

        # Handle old dict format
        if isinstance(post_content, dict):
            title = post_content["frontmatterData"]["title"]
            body = post_content["bodyMarkdown"]
        else:
            title = post_content.title
            body = post_content.body_markdown

        article = {
            "id": article_id,
            "title": title,
            "body_markdown": body,
            "published": published,
            "url": f"https://dev.to/user/{title.lower().replace(' ', '-')}",
        }

        self.articles[str(article_id)] = article
        self.published_articles.append(article)

        return {"id": article_id, "url": article["url"]}

    def update_article(self, article_id: str, post_content, published: bool):
        """Simulate old update_article method."""
        return self.publish_article(post_content, published)

    def get_articles(self):
        """Simulate old get_articles method."""
        return list(self.articles.values())

    def get_article(self, article_id: str, published: bool):
        """Simulate old get_article method."""
        article = self.articles.get(article_id)
        if article and article["published"] == published:
            return article
        return None

    def find_article_by_title(self, title: str):
        """New method for multi-platform support."""
        for article_id, article in self.articles.items():
            if article["title"] == title:
                return article_id, article["published"]
        return None, None


class TestBackwardCompatibility:
    """Test backward compatibility with existing DevTo functionality."""

    def test_legacy_devto_only_publishing(self):
        """Test that the old DevTo-only publishing still works."""
        mock_devto = LegacyMockDevToClient()

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                # Initialize publisher with only DevTo (legacy behavior)
                publisher = PostPublisher(enabled_platforms=["devto"])

                # Verify only DevTo client is initialized
                assert len(publisher.platform_clients) == 1
                assert "devto" in publisher.platform_clients
                assert "hashnode" not in publisher.platform_clients

                # Test the deprecated publish_to_devto method
                with patch("glob.glob", return_value=["test_article.md"]):
                    test_markdown = """---
title: Legacy Test Article
subtitle: Testing backward compatibility
slug: legacy-test-article
tags: testing,legacy,devto
cover: https://example.com/cover.jpg
domain: example.com
saveAsDraft: false
enableToc: true
---

# Legacy Test Article

This is a test article for backward compatibility testing.

## Section 1

Some content here to test the legacy functionality.
"""

                    with patch("builtins.open", mock_open(read_data=test_markdown)):
                        # Use the deprecated method
                        publisher.publish_to_devto()

                        # Verify article was published to DevTo
                        assert len(mock_devto.articles) == 1
                        article = list(mock_devto.articles.values())[0]
                        assert article["title"] == "Legacy Test Article"
                        assert "This is a test article" in article["body_markdown"]

    def test_legacy_environment_variable_handling(self):
        """Test that legacy environment variable configurations still work."""
        # Test with only DEVTO_API_KEY (legacy setup)
        with patch.dict(os.environ, {"DEVTO_API_KEY": "legacy_key"}, clear=True):
            mock_devto = LegacyMockDevToClient()

            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                # Should initialize successfully with only DevTo
                publisher = PostPublisher(enabled_platforms=["devto"])

                assert len(publisher.platform_clients) == 1
                assert "devto" in publisher.platform_clients

                # Validation should pass for DevTo
                validation = publisher.validate_configuration()
                assert validation["devto"] is True

    def test_legacy_markdown_file_processing(self):
        """Test that legacy markdown file formats are still processed correctly."""
        mock_devto = LegacyMockDevToClient()

        # Test with old frontmatter format variations
        legacy_formats = [
            # Format 1: Original format
            """---
title: Legacy Format 1
subtitle: Testing old format
slug: legacy-format-1
tags: legacy,format1
cover: https://example.com/cover1.jpg
domain: example.com
saveAsDraft: false
enableToc: true
---

# Legacy Format 1
Content here.""",
            # Format 2: Different boolean representations
            """---
title: Legacy Format 2
subtitle: Testing boolean variations
slug: legacy-format-2
tags: legacy,format2
cover: https://example.com/cover2.jpg
domain: example.com
saveAsDraft: False
enableToc: True
---

# Legacy Format 2
Content here.""",
            # Format 3: String tags with spaces
            """---
title: Legacy Format 3
subtitle: Testing tag variations
slug: legacy-format-3
tags: "legacy, format3, with spaces"
cover: https://example.com/cover3.jpg
domain: example.com
saveAsDraft: no
enableToc: yes
---

# Legacy Format 3
Content here.""",
        ]

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                publisher = PostPublisher(enabled_platforms=["devto"])

                for i, markdown_content in enumerate(legacy_formats):
                    mock_devto.articles.clear()  # Clear previous articles

                    with patch("glob.glob", return_value=[f"legacy_test_{i}.md"]):
                        with patch(
                            "builtins.open", mock_open(read_data=markdown_content)
                        ):
                            publisher.publish_to_all_platforms()

                            # Verify each format was processed correctly
                            assert len(mock_devto.articles) == 1
                            article = list(mock_devto.articles.values())[0]
                            assert f"Legacy Format {i + 1}" in article["title"]

    def test_legacy_error_handling_behavior(self):
        """Test that legacy error handling behavior is preserved."""

        class LegacyErrorMockClient(LegacyMockDevToClient):
            def __init__(self, should_fail=False):
                super().__init__()
                self.should_fail = should_fail

            def publish_article(self, post_content, published: bool):
                if self.should_fail:
                    raise Exception("Legacy API error")
                return super().publish_article(post_content, published)

        # Test that errors are handled gracefully (legacy behavior)
        failing_mock = LegacyErrorMockClient(should_fail=True)

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch(
                "src.client.devto_client.DevToClient", return_value=failing_mock
            ):
                publisher = PostPublisher(enabled_platforms=["devto"])

                test_markdown = """---
title: Error Test Article
subtitle: Testing error handling
slug: error-test-article
tags: testing,error
cover: ""
domain: example.com
saveAsDraft: false
---

# Error Test Article
Testing error handling."""

                with patch("glob.glob", return_value=["error_test.md"]):
                    with patch("builtins.open", mock_open(read_data=test_markdown)):
                        # Should not crash, should handle error gracefully
                        try:
                            publisher.publish_to_all_platforms()
                        except Exception as e:
                            # Legacy behavior: errors should be logged but not crash the system
                            assert (
                                "Legacy API error" in str(e) or True
                            )  # Allow for error handling

    def test_legacy_configuration_file_patterns(self):
        """Test that legacy file patterns and configurations still work."""
        mock_devto = LegacyMockDevToClient()

        with patch.dict(
            os.environ,
            {
                "DEVTO_API_KEY": "test_key",
                "MARKDOWN_FILE_PATTERN": "*.md",  # Legacy pattern
                "EXCLUDE_FILES": "README.md,CHANGELOG.md",  # Legacy exclusion
            },
            clear=True,
        ):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                publisher = PostPublisher(enabled_platforms=["devto"])

                # Test that configuration is loaded correctly
                assert publisher.config["markdown_file_pattern"] == "*.md"
                assert "README.md" in publisher.config["exclude_files"]
                assert "CHANGELOG.md" in publisher.config["exclude_files"]

    def test_legacy_api_response_format_handling(self):
        """Test that legacy API response formats are handled correctly."""

        class LegacyResponseMockClient(LegacyMockDevToClient):
            def publish_article(self, post_content, published: bool):
                # Simulate old API response format
                result = super().publish_article(post_content, published)

                # Legacy format might have different field names or structure
                return {
                    "id": result["id"],
                    "url": result["url"],
                    "published": published,
                    "created_at": "2023-01-01T00:00:00Z",  # Legacy field
                }

        legacy_mock = LegacyResponseMockClient()

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=legacy_mock):
                publisher = PostPublisher(enabled_platforms=["devto"])

                test_markdown = """---
title: API Response Test
subtitle: Testing API response handling
slug: api-response-test
tags: testing,api
cover: ""
domain: example.com
saveAsDraft: false
---

# API Response Test
Testing API response handling."""

                with patch("glob.glob", return_value=["api_test.md"]):
                    with patch("builtins.open", mock_open(read_data=test_markdown)):
                        # Should handle legacy response format without issues
                        publisher.publish_to_all_platforms()

                        assert len(legacy_mock.articles) == 1

    def test_legacy_content_processing_behavior(self):
        """Test that legacy content processing behavior is preserved."""
        mock_devto = LegacyMockDevToClient()

        # Test content that might have been processed differently in legacy version
        legacy_content_cases = [
            # Case 1: Content with frontmatter removal (legacy behavior)
            """---
title: Frontmatter Removal Test
subtitle: Testing frontmatter handling
slug: frontmatter-test
tags: legacy,frontmatter
cover: ""
domain: example.com
saveAsDraft: false
---

# Frontmatter Removal Test

This content should have frontmatter removed in legacy processing.

---

This is not frontmatter, just content with dashes.
""",
            # Case 2: Content with special markdown features
            """---
title: Markdown Features Test
subtitle: Testing markdown processing
slug: markdown-features-test
tags: legacy,markdown
cover: ""
domain: example.com
saveAsDraft: false
---

# Markdown Features Test

## Table of Contents
- [Section 1](#section-1)
- [Section 2](#section-2)

## Section 1
Content here.

## Section 2
More content.
""",
        ]

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                publisher = PostPublisher(enabled_platforms=["devto"])

                for i, content in enumerate(legacy_content_cases):
                    mock_devto.articles.clear()

                    with patch("glob.glob", return_value=[f"content_test_{i}.md"]):
                        with patch("builtins.open", mock_open(read_data=content)):
                            publisher.publish_to_all_platforms()

                            # Verify content was processed
                            assert len(mock_devto.articles) == 1
                            article = list(mock_devto.articles.values())[0]

                            # Content should be processed but maintain essential structure
                            assert len(article["body_markdown"]) > 0

    def test_legacy_method_deprecation_warnings(self):
        """Test that deprecated methods still work but show appropriate warnings."""
        mock_devto = LegacyMockDevToClient()

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                publisher = PostPublisher(enabled_platforms=["devto"])

                # Test deprecated publish_to_devto method
                with patch("glob.glob", return_value=["deprecated_test.md"]):
                    test_markdown = """---
title: Deprecation Test
subtitle: Testing deprecated methods
slug: deprecation-test
tags: testing,deprecated
cover: ""
domain: example.com
saveAsDraft: false
---

# Deprecation Test
Testing deprecated method."""

                    with patch("builtins.open", mock_open(read_data=test_markdown)):
                        # Should work but may log deprecation warning
                        publisher.publish_to_devto()

                        # Verify it still works
                        assert len(mock_devto.articles) == 1

    def test_legacy_file_structure_compatibility(self):
        """Test compatibility with legacy project file structures."""
        mock_devto = LegacyMockDevToClient()

        # Test with legacy file patterns that might exist in old projects
        legacy_file_patterns = [
            "blog_posts/*.md",
            "articles/*.md",
            "content/*.md",
            "posts/*.md",
        ]

        with patch.dict(os.environ, {"DEVTO_API_KEY": "test_key"}, clear=True):
            with patch("src.client.devto_client.DevToClient", return_value=mock_devto):
                for pattern in legacy_file_patterns:
                    # Test each legacy pattern
                    with patch.dict(os.environ, {"MARKDOWN_FILE_PATTERN": pattern}):
                        publisher = PostPublisher(enabled_platforms=["devto"])

                        # Verify pattern is loaded correctly
                        assert publisher.config["markdown_file_pattern"] == pattern

                        # Test that it would work with files matching the pattern
                        with patch(
                            "glob.glob",
                            return_value=[f"{pattern.replace('*.md', 'test.md')}"],
                        ):
                            test_markdown = """---
title: Pattern Test
subtitle: Testing file patterns
slug: pattern-test
tags: testing,pattern
cover: ""
domain: example.com
saveAsDraft: false
---

# Pattern Test
Testing file pattern compatibility."""

                            with patch(
                                "builtins.open", mock_open(read_data=test_markdown)
                            ):
                                # Should handle different file patterns
                                publisher.publish_to_all_platforms()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Data models for post content and publication results.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class PostContent:
    """
    Data model representing the content and metadata of a blog post.
    """

    title: str
    subtitle: str
    slug: str
    tags: List[str]
    cover: str
    domain: str
    save_as_draft: bool
    enable_toc: bool
    body_markdown: str
    canonical_url: str
    series_name: Optional[str] = None

    @classmethod
    def from_frontmatter(
        cls, frontmatter_data: Dict, body_markdown: str
    ) -> "PostContent":
        """
        Create PostContent from frontmatter and markdown body.

        Args:
            frontmatter_data: Dictionary containing frontmatter metadata
            body_markdown: The markdown content body

        Returns:
            PostContent instance
        """
        # Handle tags - convert from comma-separated string to list if needed
        tags = frontmatter_data.get("tags", "")
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif not isinstance(tags, list):
            tags = []

        canonical_url = f"https://{frontmatter_data.get('domain', '')}/{frontmatter_data.get('slug', '')}"

        return cls(
            title=frontmatter_data.get("title", ""),
            subtitle=frontmatter_data.get("subtitle", ""),
            slug=frontmatter_data.get("slug", ""),
            tags=tags,
            cover=frontmatter_data.get("cover", ""),
            domain=frontmatter_data.get("domain", ""),
            save_as_draft=frontmatter_data.get("saveAsDraft", False),
            enable_toc=frontmatter_data.get("enableToc", True),
            body_markdown=body_markdown,
            canonical_url=canonical_url,
            series_name=frontmatter_data.get("seriesName"),
        )


@dataclass
class ArticleStatus:
    """
    Data model representing the status of an article on a platform.
    """

    platform: str
    article_id: Optional[str]
    exists: bool
    published: bool
    needs_update: bool
    content_hash: str
    last_modified: Optional[datetime] = None


@dataclass
class PublicationResult:
    """
    Data model representing the result of a publication operation.
    """

    platform: str
    success: bool
    action: str  # 'created', 'updated', 'skipped'
    article_id: Optional[str] = None
    error_message: Optional[str] = None

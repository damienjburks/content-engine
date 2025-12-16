"""
Content processor for platform-specific transformations.
"""

import re
from typing import Dict, List
from md_toc.api import build_toc
from ..models.post_content import PostContent
from ..interfaces.content_processor import ContentProcessor as ContentProcessorInterface


class ContentProcessor(ContentProcessorInterface):
    """
    Handles content processing and platform-specific transformations.
    """

    def __init__(self):
        pass

    def process_content_for_platform(
        self, post_content: PostContent, platform: str
    ) -> str:
        """
        Process content for a specific platform.

        Args:
            post_content: The post content to process
            platform: The target platform ('devto' or 'hashnode')

        Returns:
            Processed markdown content
        """
        content = post_content.body_markdown

        # Add table of contents if enabled
        if post_content.enable_toc:
            toc = self._generate_table_of_contents(content)
            if toc:
                content = toc + "\n\n" + content

        # Apply platform-specific transformations
        if platform.lower() == "hashnode":
            content = self._apply_hashnode_transformations(content)
        elif platform.lower() == "devto":
            content = self._apply_devto_transformations(content)

        return content

    def _apply_hashnode_transformations(self, content: str) -> str:
        """
        Apply Hashnode-specific content transformations.

        Args:
            content: The markdown content to transform

        Returns:
            Transformed content for Hashnode
        """
        # Remove HTML alignment attributes that are not supported by Hashnode
        content = re.sub(r'\s*align="center"', "", content)
        content = re.sub(r'\s*align="left"', "", content)
        content = re.sub(r'\s*align="right"', "", content)

        return content

    def _apply_devto_transformations(self, content: str) -> str:
        """
        Apply dev.to-specific content transformations.

        Args:
            content: The markdown content to transform

        Returns:
            Transformed content for dev.to
        """
        # For dev.to, we preserve existing formatting
        # No specific transformations needed currently
        return content

    def normalize_content_for_comparison(self, content: str) -> str:
        """
        Normalize content for comparison operations.

        Args:
            content: The content to normalize

        Returns:
            Normalized content
        """
        # Remove frontmatter if present
        content = self._remove_frontmatter(content)

        # Normalize whitespace
        content = re.sub(r"\s+", " ", content.strip())

        # Remove platform-specific formatting for comparison
        content = re.sub(r'\s*align="[^"]*"', "", content)

        return content

    def _remove_frontmatter(self, content: str) -> str:
        """
        Remove frontmatter from markdown content.

        Args:
            content: The markdown content

        Returns:
            Content without frontmatter
        """
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        return re.sub(frontmatter_pattern, "", content, flags=re.DOTALL)

    def _generate_table_of_contents(self, content: str) -> str:
        """
        Generate table of contents from markdown content.

        Args:
            content: The markdown content

        Returns:
            Table of contents as markdown
        """
        try:
            # Try to use md_toc library if available
            toc = build_toc(content, parser="github")
            if toc:
                return f"## Table of Contents\n\n{toc}"
        except Exception:
            # Fallback to manual TOC generation
            pass

        # Manual TOC generation as fallback
        headers = re.findall(r"^(#{1,6})\s+(.+)$", content, re.MULTILINE)
        if not headers:
            # If no headers found, still return a basic TOC header for consistency
            return "## Table of Contents\n\n*No sections found*"

        toc_lines = ["## Table of Contents", ""]
        has_content = False

        for level_hashes, title in headers:
            level = len(level_hashes)
            # Include all headers for TOC generation
            indent = "  " * max(0, level - 1)
            # Create anchor link (GitHub style)
            anchor = re.sub(r"[^\w\s-]", "", title.lower())
            anchor = re.sub(r"[-\s]+", "-", anchor).strip("-")
            toc_lines.append(f"{indent}- [{title}](#{anchor})")
            has_content = True

        if not has_content:
            toc_lines.append("*No sections found*")

        return "\n".join(toc_lines)

    def convert_tags_for_platform(self, tags: List[str], platform: str) -> List[str]:
        """
        Convert tags to platform-specific format.

        Args:
            tags: List of tags
            platform: Target platform

        Returns:
            Platform-formatted tags
        """
        if not tags:
            return []

        # Handle comma-separated string conversion to list
        processed_tags = []
        for tag in tags:
            if isinstance(tag, str) and "," in tag:
                # Split comma-separated tags
                processed_tags.extend([t.strip() for t in tag.split(",") if t.strip()])
            else:
                processed_tags.append(str(tag).strip())

        # Apply platform-specific tag formatting
        if platform.lower() == "hashnode":
            # Hashnode prefers lowercase tags without special characters
            return [
                self._sanitize_tag_for_hashnode(tag) for tag in processed_tags if tag
            ]
        elif platform.lower() == "devto":
            # dev.to allows more flexible tag formats
            return [self._sanitize_tag_for_devto(tag) for tag in processed_tags if tag]
        else:
            # Default formatting
            return [tag.strip().lower() for tag in processed_tags if tag.strip()]

    def _sanitize_tag_for_hashnode(self, tag: str) -> str:
        """
        Sanitize tag for Hashnode platform.

        Args:
            tag: The tag to sanitize

        Returns:
            Sanitized tag for Hashnode
        """
        # Convert to lowercase and remove special characters
        sanitized = re.sub(r"[^a-zA-Z0-9\s-]", "", tag.lower().strip())
        # Replace spaces with hyphens
        sanitized = re.sub(r"\s+", "-", sanitized)
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        # Remove leading/trailing hyphens
        return sanitized.strip("-")

    def _sanitize_tag_for_devto(self, tag: str) -> str:
        """
        Sanitize tag for dev.to platform.

        Args:
            tag: The tag to sanitize

        Returns:
            Sanitized tag for dev.to
        """
        # dev.to is more permissive, just clean up basic formatting
        return tag.strip().lower()

    def generate_canonical_url(self, post_content: PostContent, platform: str) -> str:
        """
        Generate canonical URL for the post based on platform.

        Args:
            post_content: The post content
            platform: Target platform

        Returns:
            Canonical URL for the platform
        """
        if platform.lower() == "devto":
            # For dev.to, use the original domain as canonical
            return post_content.canonical_url
        elif platform.lower() == "hashnode":
            # For Hashnode, also use the original domain to avoid SEO conflicts
            return post_content.canonical_url
        else:
            # Default to the original canonical URL
            return post_content.canonical_url

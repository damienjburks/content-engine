"""
Content processor interface for platform-specific transformations.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models.post_content import PostContent


class ContentProcessor(ABC):
    """
    Abstract base class for content processors that handle platform-specific transformations.
    """

    @abstractmethod
    def process_content_for_platform(
        self, post_content: PostContent, platform: str
    ) -> str:
        """
        Process content for a specific platform.

        Args:
            post_content: The post content to process
            platform: The target platform identifier

        Returns:
            Processed markdown content
        """
        pass

    @abstractmethod
    def normalize_content_for_comparison(self, content: str) -> str:
        """
        Normalize content for comparison operations.

        Args:
            content: The content to normalize

        Returns:
            Normalized content suitable for comparison
        """
        pass

    @abstractmethod
    def convert_tags_for_platform(self, tags: List[str], platform: str) -> List[str]:
        """
        Convert tags to platform-specific format.

        Args:
            tags: List of tags to convert
            platform: Target platform identifier

        Returns:
            Platform-formatted tags
        """
        pass

    @abstractmethod
    def generate_canonical_url(self, post_content: PostContent, platform: str) -> str:
        """
        Generate canonical URL for the post based on platform.

        Args:
            post_content: The post content
            platform: Target platform identifier

        Returns:
            Canonical URL for the platform
        """
        pass

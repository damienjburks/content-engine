"""
Platform client interface for multi-platform blog publishing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from src.models.delete_result import DeleteResult


class PlatformClient(ABC):
    """
    Abstract base class for platform clients that interact with blogging platform APIs.
    """

    @abstractmethod
    def publish_article(self, post_content: Dict, published: bool) -> Dict:
        """
        Publish a new article to the platform.

        Args:
            post_content: Dictionary containing article content and metadata
            published: Whether the article should be published or saved as draft

        Returns:
            Dictionary containing the platform's response with article details
        """
        pass

    @abstractmethod
    def update_article(
        self, article_id: str, post_content: Dict, published: bool
    ) -> Dict:
        """
        Update an existing article on the platform.

        Args:
            article_id: Platform-specific identifier for the article
            post_content: Dictionary containing updated article content and metadata
            published: Whether the article should be published or saved as draft

        Returns:
            Dictionary containing the platform's response with updated article details
        """
        pass

    @abstractmethod
    def get_articles(self) -> List[Dict]:
        """
        Retrieve all articles from the platform.

        Returns:
            List of dictionaries containing article information
        """
        pass

    @abstractmethod
    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        """
        Retrieve a specific article by ID.

        Args:
            article_id: Platform-specific identifier for the article
            published: Whether to look for published or draft articles

        Returns:
            Dictionary containing article details or None if not found
        """
        pass

    @abstractmethod
    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        """
        Find article ID and publication status by title.

        Args:
            title: The title of the article to find

        Returns:
            Tuple of (article_id, is_published) or (None, None) if not found
        """
        pass

    @abstractmethod
    def delete_article(self, article_id: str) -> DeleteResult:
        """
        Delete an article from the platform.

        Args:
            article_id: Platform-specific identifier for the article to delete

        Returns:
            DeleteResult indicating success, failure, or already deleted
        """
        pass

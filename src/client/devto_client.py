"""
This module is used to interact with the Dev.to API for
publishing articles and retrieving them.
"""

from os import environ
import logging
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.interfaces.platform_client import PlatformClient
from src.models.post_content import PostContent
from src.utils.error_handler import (
    ErrorHandler,
    with_retry_and_rate_limiting,
    handle_api_response,
    AuthenticationError,
    RateLimitError,
    APIError,
)
from src.models.delete_result import DeleteResult

logging.basicConfig(level=logging.INFO)

API_TOKEN = environ.get("DEVTO_API_KEY")
ARTICLES_URL = "https://dev.to/api/articles"


class DevToClient(PlatformClient):
    # pylint: disable=line-too-long,broad-exception-raised,missing-timeout
    """
    This class is used to interact with the Dev.to API for
    publishing articles and retrieving them.
    """

    def __init__(self) -> None:
        self.logging = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logging)

        # Validate API key on initialization
        if not API_TOKEN:
            self.error_handler.log_authentication_error(
                "devto", "DEVTO_API_KEY environment variable is not set"
            )
            raise AuthenticationError(
                "DEVTO_API_KEY environment variable is required", platform="devto"
            )

    @with_retry_and_rate_limiting(max_retries=3, base_delay=2.0)
    def publish_article(self, post_content: Dict, published: bool) -> Dict:
        """
        Function to publish an article to Dev.to.
        Args:
            post_content: The content of the post (dict or PostContent).
            published: Whether the post is published or not.
        Returns:
            dict: The response from the API.
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limiting occurs
            APIError: If other API errors occur
        """
        # Handle both old format (dict) and new format (PostContent)
        if isinstance(post_content, PostContent):
            title = post_content.title
            canonical_url = post_content.canonical_url
            subtitle = post_content.subtitle
            cover = post_content.cover
            tags = post_content.tags
            body_markdown = post_content.body_markdown
            series_name = post_content.series_name
        else:
            # Backward compatibility with old dict format
            title = post_content["frontmatterData"]["title"]
            canonical_url = f"https://{post_content['frontmatterData']['domain']}/{post_content['frontmatterData']['slug']}"
            subtitle = post_content["frontmatterData"]["subtitle"]
            cover = post_content["frontmatterData"]["cover"]
            tags = (
                post_content["frontmatterData"]["tags"].split(",")
                if isinstance(post_content["frontmatterData"]["tags"], str)
                else post_content["frontmatterData"]["tags"]
            )
            body_markdown = post_content["bodyMarkdown"]
            series_name = post_content["frontmatterData"].get("seriesName")

        data = {
            "article": {
                "title": title,
                "canonical_url": canonical_url,
                "description": subtitle,
                "main_image": cover,
                "tags": tags,
                "body_markdown": body_markdown,
                "series": series_name if series_name is not None else "",
                "published": published,
            }
        }

        try:
            response = requests.post(
                ARTICLES_URL,
                json=data,
                headers=self._generate_authenticated_header(),
                timeout=30,
            )

            result = handle_api_response(response, "devto", "publish", title)

            # Log success
            self.error_handler.log_success(
                "devto", title, "created", result.get("id"), {"url": result.get("url")}
            )

            return result

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            self.error_handler.log_api_error(e, "devto", title, "publish")
            raise APIError(
                f"Unexpected error publishing to DevTo: {str(e)}",
                platform="devto",
                article_title=title,
            )

    @with_retry_and_rate_limiting(max_retries=3, base_delay=2.0)
    def update_article(
        self, article_id: str, post_content: Dict, published: bool
    ) -> Dict:
        """
        Function to update an existing article on Dev.to.
        Args:
            article_id: The ID of the article to update.
            post_content: The content of the post (dict or PostContent).
            published: Whether the post is published or not.
        Returns:
            dict: The response from the API.
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limiting occurs
            APIError: If other API errors occur
        """
        url = f"{ARTICLES_URL}/{article_id}"

        # Handle both old format (dict) and new format (PostContent)
        if isinstance(post_content, PostContent):
            title = post_content.title
            canonical_url = post_content.canonical_url
            subtitle = post_content.subtitle
            cover = post_content.cover
            tags = post_content.tags
            body_markdown = post_content.body_markdown
            series_name = post_content.series_name
        else:
            # Backward compatibility with old dict format
            title = post_content["frontmatterData"]["title"]
            canonical_url = f"https://{post_content['frontmatterData']['domain']}/{post_content['frontmatterData']['slug']}"
            subtitle = post_content["frontmatterData"]["subtitle"]
            cover = post_content["frontmatterData"]["cover"]
            tags = (
                post_content["frontmatterData"]["tags"].split(",")
                if isinstance(post_content["frontmatterData"]["tags"], str)
                else post_content["frontmatterData"]["tags"]
            )
            body_markdown = post_content["bodyMarkdown"]
            series_name = post_content["frontmatterData"].get("seriesName")

        data = {
            "article": {
                "title": title,
                "canonical_url": canonical_url,
                "description": subtitle,
                "main_image": cover,
                "tags": tags,
                "body_markdown": body_markdown,
                "series": series_name if series_name is not None else "",
                "published": published,
            }
        }

        try:
            response = requests.put(
                url,
                json=data,
                headers=self._generate_authenticated_header(),
                timeout=30,
            )

            result = handle_api_response(response, "devto", "update", title)

            # Log success
            self.error_handler.log_success(
                "devto", title, "updated", article_id, {"url": result.get("url")}
            )

            return result

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            self.error_handler.log_api_error(
                e, "devto", title, "update", {"article_id": article_id}
            )
            raise APIError(
                f"Unexpected error updating DevTo article: {str(e)}",
                platform="devto",
                article_title=title,
            )

    @with_retry_and_rate_limiting(max_retries=3, base_delay=1.0)
    def get_articles(self) -> List[Dict]:
        """
        Function to get list of articles published by me.
        Returns:
            List[Dict]: The response from the API.
        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limiting occurs
            APIError: If other API errors occur
        """
        url = f"{ARTICLES_URL}/me/all?per_page=1000"

        try:
            response = requests.get(
                url, headers=self._generate_authenticated_header(), timeout=30
            )

            result = handle_api_response(response, "devto", "get_articles")
            self.logging.debug(f"Retrieved {len(result)} articles from DevTo")
            return result

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            self.error_handler.log_api_error(e, "devto", None, "get_articles")
            raise APIError(
                f"Unexpected error retrieving DevTo articles: {str(e)}",
                platform="devto",
            )

    @with_retry_and_rate_limiting(max_retries=3, base_delay=1.0)
    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        """
        Function to get an article by ID.
        Args:
            article_id: The ID of the article to retrieve.
            published: Whether the article is published or not.
        Returns:
            Optional[Dict]: The response from the API or None if not found.
        """
        # Convert article_id to int for API compatibility
        try:
            article_id_int = int(article_id)
        except (ValueError, TypeError):
            self.error_handler.log_api_error(
                ValueError(f"Invalid article_id format: {article_id}"),
                "devto",
                None,
                "get_article",
                {"article_id": article_id},
            )
            return None

        try:
            if published:
                response = requests.get(
                    f"{ARTICLES_URL}/{article_id}",
                    headers=self._generate_authenticated_header(),
                    timeout=30,
                )

                if response.status_code == 200:
                    return handle_api_response(response, "devto", "get_article")
                elif response.status_code == 404:
                    return None
                else:
                    handle_api_response(response, "devto", "get_article")
            else:
                response = requests.get(
                    f"{ARTICLES_URL}/me/unpublished?per_page=1000",
                    headers=self._generate_authenticated_header(),
                    timeout=30,
                )

                result = handle_api_response(
                    response, "devto", "get_unpublished_articles"
                )

                for article in result:
                    if article["id"] == article_id_int:
                        return article

                return None

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Handle unexpected errors
            self.error_handler.log_api_error(
                e, "devto", None, "get_article", {"article_id": article_id}
            )
            raise APIError(
                f"Unexpected error retrieving DevTo article: {str(e)}", platform="devto"
            )

    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        """
        Find article ID and publication status by title.

        Args:
            title: The title of the article to find

        Returns:
            Tuple of (article_id, is_published) or (None, None) if not found
        """
        try:
            # Get all articles (both published and unpublished)
            articles = self.get_articles()

            # Search for article with matching title
            for article in articles:
                if article.get("title") == title:
                    article_id = str(article.get("id"))
                    is_published = article.get("published", False)
                    self.logging.debug(
                        f"Found article '{title}' on DevTo: ID={article_id}, published={is_published}"
                    )
                    return (article_id, is_published)

            # If not found, return None, None
            self.logging.debug(f"Article '{title}' not found on DevTo")
            return (None, None)

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(e, "devto", title, "find_article_by_title")
            return (None, None)

    @with_retry_and_rate_limiting(max_retries=3, base_delay=2.0)
    def delete_article(self, article_id: str) -> DeleteResult:
        """
        Delete an article from dev.to.

        Args:
            article_id: The ID of the article to delete

        Returns:
            DeleteResult indicating success, failure, or already deleted
        """
        try:
            url = f"{ARTICLES_URL}/articles/{article_id}"
            headers = self._generate_authenticated_header()

            response = requests.delete(url, headers=headers, timeout=30)

            if response.status_code == 204:
                # 204 No Content indicates successful deletion
                self.error_handler.log_success(
                    "devto", f"Article ID {article_id}", "deleted", article_id
                )
                return DeleteResult(success=True)
            elif response.status_code == 404:
                # Article not found - already deleted
                self.logging.debug(
                    f"Article {article_id} already deleted from dev.to"
                )
                return DeleteResult(success=False, already_deleted=True)
            elif response.status_code == 429:
                # Rate limiting - let the decorator handle retries
                raise RateLimitError(
                    f"Rate limit exceeded when deleting article {article_id}",
                    platform="devto",
                    article_title=f"Article ID {article_id}",
                    retry_after=response.headers.get("Retry-After"),
                )
            else:
                # Use the standard error handler for other HTTP errors
                handle_api_response(
                    response, "devto", "delete", f"Article ID {article_id}"
                )
                return DeleteResult(success=False)

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(
                e, "devto", f"Article ID {article_id}", "delete"
            )
            return DeleteResult(success=False)

    def _generate_authenticated_header(self):
        """
        Function to generate authenticated headers for the requests.
        Returns:
            dict: The authenticated header.
        """
        headers = {
            "api_key": API_TOKEN,
            "Content-Type": "application/json",
            "accept": "application/vnd.forem.api-v1+json",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0",
        }
        return headers

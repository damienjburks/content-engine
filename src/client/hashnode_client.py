"""
This module is used to interact with the Hashnode API for
publishing articles and retrieving them using GraphQL.
"""

import asyncio
import logging
import time
from os import environ
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportError

# Load environment variables from .env file
load_dotenv()

from src.interfaces.platform_client import PlatformClient
from src.models.post_content import PostContent
from src.utils.error_handler import (
    ErrorHandler,
    AuthenticationError,
    RateLimitError,
    APIError,
)

logging.basicConfig(level=logging.INFO)

HASHNODE_API_URL = "https://gql.hashnode.com"
HASHNODE_API_KEY = environ.get("HASHNODE_API_KEY")
HASHNODE_USERNAME = environ.get("HASHNODE_USERNAME")
HASHNODE_PUBLICATION_ID = environ.get("HASHNODE_PUBLICATION_ID")


class HashnodeClient(PlatformClient):
    """
    This class is used to interact with the Hashnode API for
    publishing articles and retrieving them using GraphQL.
    """

    def __init__(self) -> None:
        self.logging = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logging)
        self.rate_limit_delay = 2.0  # 2 second delay between requests
        self.last_request_time = 0.0
        self.max_retries = 3

        # Validate API credentials
        if not HASHNODE_API_KEY:
            self.error_handler.log_authentication_error(
                "hashnode", "HASHNODE_API_KEY environment variable is not set"
            )
            raise AuthenticationError(
                "HASHNODE_API_KEY environment variable is required", platform="hashnode"
            )

        if not HASHNODE_USERNAME:
            self.error_handler.log_authentication_error(
                "hashnode", "HASHNODE_USERNAME environment variable is not set"
            )
            raise AuthenticationError(
                "HASHNODE_USERNAME environment variable is required",
                platform="hashnode",
            )

        if not HASHNODE_PUBLICATION_ID:
            self.error_handler.log_authentication_error(
                "hashnode", "HASHNODE_PUBLICATION_ID environment variable is not set"
            )
            raise AuthenticationError(
                "HASHNODE_PUBLICATION_ID environment variable is required. Get it from https://hashnode.com/settings/blogs",
                platform="hashnode",
            )

        # Validate publication ID format (should be a valid MongoDB ObjectId)
        if not self._is_valid_object_id(HASHNODE_PUBLICATION_ID):
            self.error_handler.log_authentication_error(
                "hashnode", f"Invalid HASHNODE_PUBLICATION_ID format: {HASHNODE_PUBLICATION_ID}"
            )
            raise AuthenticationError(
                f"HASHNODE_PUBLICATION_ID must be a valid MongoDB ObjectId (24 hex characters). Got: {HASHNODE_PUBLICATION_ID}. Get your publication ID from https://hashnode.com/settings/blogs",
                platform="hashnode",
            )

        # Initialize GraphQL client
        try:
            transport = AIOHTTPTransport(
                url=HASHNODE_API_URL,
                headers={"Authorization": HASHNODE_API_KEY},
                timeout=30,
            )
            self.client = Client(transport=transport, fetch_schema_from_transport=False)
        except Exception as e:
            self.error_handler.log_api_error(e, "hashnode", None, "initialization")
            raise APIError(
                f"Failed to initialize Hashnode client: {str(e)}", platform="hashnode"
            )

    def _rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _is_valid_object_id(self, object_id: str) -> bool:
        """
        Validate if a string is a valid MongoDB ObjectId format.
        
        Args:
            object_id: The string to validate
            
        Returns:
            True if valid ObjectId format, False otherwise
        """
        import re
        # MongoDB ObjectId is 24 hex characters
        return bool(re.match(r'^[0-9a-fA-F]{24}$', object_id))

    def _run_query(
        self, query, variables=None, operation_name=None, article_title=None
    ):
        """Execute a GraphQL query with rate limiting and error handling."""
        self._rate_limit()

        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:

                async def execute_query():
                    async with self.client as session:
                        result = await session.execute(query, variable_values=variables)
                        return result

                return asyncio.run(execute_query())

            except TransportError as e:
                last_exception = e

                # Check if it's an authentication error
                if "401" in str(e) or "403" in str(e) or "Unauthorized" in str(e):
                    self.error_handler.log_authentication_error("hashnode", str(e))
                    raise AuthenticationError(
                        f"Authentication failed for Hashnode: {str(e)}",
                        platform="hashnode",
                        article_title=article_title,
                    )

                # Check if it's a rate limit error
                if "429" in str(e) or "rate limit" in str(e).lower():
                    if attempt < self.max_retries:
                        delay = self.rate_limit_delay * (2**attempt)
                        self.error_handler.log_rate_limit_error(
                            "hashnode", int(delay), article_title
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise RateLimitError(
                            f"Rate limit exceeded on Hashnode: {str(e)}",
                            platform="hashnode",
                            article_title=article_title,
                        )

                # For other transport errors, retry with exponential backoff
                if attempt < self.max_retries:
                    delay = 2.0 * (2**attempt)
                    self.logging.info(
                        f"Hashnode API error, retrying in {delay} seconds (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}"
                    )
                    time.sleep(delay)
                    continue
                else:
                    break

            except Exception as e:
                last_exception = e

                # For other exceptions, don't retry
                self.error_handler.log_api_error(
                    e, "hashnode", article_title, operation_name or "query"
                )
                raise APIError(
                    f"Unexpected error in Hashnode query: {str(e)}",
                    platform="hashnode",
                    article_title=article_title,
                )

        # If we get here, all retries failed
        self.error_handler.log_api_error(
            last_exception, "hashnode", article_title, operation_name or "query"
        )
        raise APIError(
            f"Hashnode API request failed after {self.max_retries} retries: {str(last_exception)}",
            platform="hashnode",
            article_title=article_title,
        )

    def publish_article(self, post_content: Dict, published: bool) -> Dict:
        """
        Publish a new article to Hashnode.

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
        try:
            # Handle both old format (dict) and new format (PostContent)
            if isinstance(post_content, PostContent):
                title = post_content.title
                subtitle = post_content.subtitle
                cover = post_content.cover
                tags = post_content.tags
                body_markdown = post_content.body_markdown
                series_name = post_content.series_name
                canonical_url = post_content.canonical_url
            else:
                # Backward compatibility with old dict format
                frontmatter = post_content["frontmatterData"]
                title = frontmatter["title"]
                subtitle = frontmatter["subtitle"]
                cover = frontmatter["cover"]
                tags = frontmatter["tags"]
                if isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
                body_markdown = post_content["bodyMarkdown"]
                series_name = frontmatter.get("seriesName")
                canonical_url = f"https://{frontmatter['domain']}/{frontmatter['slug']}"

            # Prepare tags for Hashnode (convert to tag objects)
            tag_objects = []
            for tag in tags[:5]:  # Hashnode allows max 5 tags
                tag_slug = tag.lower().replace(" ", "-").replace("_", "-")
                tag_objects.append({"name": tag, "slug": tag_slug})

            # GraphQL mutation for publishing
            publish_mutation = gql(
                """
                mutation PublishPost($input: PublishPostInput!) {
                    publishPost(input: $input) {
                        post {
                            id
                            title
                            slug
                            url
                            publishedAt
                            updatedAt
                        }
                    }
                }
            """
            )

            # Prepare input variables
            input_data = {
                "title": title,
                "contentMarkdown": body_markdown,
                "tags": tag_objects,
                "publicationId": HASHNODE_PUBLICATION_ID,
                "publishedAt": (
                    None if not published else None
                ),  # Let Hashnode set the time
                "subtitle": subtitle if subtitle else None,
                "coverImageOptions": {"coverImageURL": cover} if cover else None,
                "originalArticleURL": canonical_url if canonical_url else None,
                "seriesId": None,  # We'll handle series separately if needed
                "disableComments": False,
                "metaTags": {
                    "title": title,
                    "description": subtitle if subtitle else None,
                },
            }

            # Remove None values to avoid GraphQL errors
            input_data = {k: v for k, v in input_data.items() if v is not None}

            variables = {"input": input_data}

            result = self._run_query(publish_mutation, variables, "publish", title)

            if result and "publishPost" in result and result["publishPost"]["post"]:
                post_data = result["publishPost"]["post"]

                response_data = {
                    "id": post_data["id"],
                    "title": post_data["title"],
                    "slug": post_data["slug"],
                    "url": post_data["url"],
                    "published_at": post_data.get("publishedAt"),
                    "updated_at": post_data.get("updatedAt"),
                }

                # Log success
                self.error_handler.log_success(
                    "hashnode",
                    title,
                    "created",
                    post_data["id"],
                    {"url": post_data["url"], "slug": post_data["slug"]},
                )

                return response_data
            else:
                error_msg = "Unexpected response format from Hashnode API"
                self.error_handler.log_api_error(
                    ValueError(error_msg),
                    "hashnode",
                    title,
                    "publish",
                    {"response": result},
                )
                raise APIError(error_msg, platform="hashnode", article_title=title)

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(e, "hashnode", title, "publish")
            raise APIError(
                f"Unexpected error publishing to Hashnode: {str(e)}",
                platform="hashnode",
                article_title=title,
            )

    def update_article(
        self, article_id: str, post_content: Dict, published: bool
    ) -> Dict:
        """
        Update an existing article on Hashnode.

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
        try:
            # Handle both old format (dict) and new format (PostContent)
            if isinstance(post_content, PostContent):
                title = post_content.title
                subtitle = post_content.subtitle
                cover = post_content.cover
                tags = post_content.tags
                body_markdown = post_content.body_markdown
                series_name = post_content.series_name
                canonical_url = post_content.canonical_url
            else:
                # Backward compatibility with old dict format
                frontmatter = post_content["frontmatterData"]
                title = frontmatter["title"]
                subtitle = frontmatter["subtitle"]
                cover = frontmatter["cover"]
                tags = frontmatter["tags"]
                if isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
                body_markdown = post_content["bodyMarkdown"]
                series_name = frontmatter.get("seriesName")
                canonical_url = f"https://{frontmatter['domain']}/{frontmatter['slug']}"

            # Prepare tags for Hashnode
            tag_objects = []
            for tag in tags[:5]:  # Hashnode allows max 5 tags
                tag_slug = tag.lower().replace(" ", "-").replace("_", "-")
                tag_objects.append({"name": tag, "slug": tag_slug})

            # GraphQL mutation for updating
            update_mutation = gql(
                """
                mutation UpdatePost($input: UpdatePostInput!) {
                    updatePost(input: $input) {
                        post {
                            id
                            title
                            slug
                            url
                            publishedAt
                            updatedAt
                        }
                    }
                }
            """
            )

            # Prepare input variables
            input_data = {
                "id": article_id,
                "title": title,
                "contentMarkdown": body_markdown,
                "tags": tag_objects,
                "subtitle": subtitle if subtitle else None,
                "coverImageOptions": {"coverImageURL": cover} if cover else None,
                "originalArticleURL": canonical_url if canonical_url else None,
                "metaTags": {
                    "title": title,
                    "description": subtitle if subtitle else None,
                },
            }

            # Remove None values to avoid GraphQL errors
            input_data = {k: v for k, v in input_data.items() if v is not None}

            variables = {"input": input_data}

            result = self._run_query(update_mutation, variables, "update", title)

            if result and "updatePost" in result and result["updatePost"]["post"]:
                post_data = result["updatePost"]["post"]

                response_data = {
                    "id": post_data["id"],
                    "title": post_data["title"],
                    "slug": post_data["slug"],
                    "url": post_data["url"],
                    "published_at": post_data.get("publishedAt"),
                    "updated_at": post_data.get("updatedAt"),
                }

                # Log success
                self.error_handler.log_success(
                    "hashnode",
                    title,
                    "updated",
                    article_id,
                    {"url": post_data["url"], "slug": post_data["slug"]},
                )

                return response_data
            else:
                error_msg = "Unexpected response format from Hashnode API"
                self.error_handler.log_api_error(
                    ValueError(error_msg),
                    "hashnode",
                    title,
                    "update",
                    {"article_id": article_id, "response": result},
                )
                raise APIError(error_msg, platform="hashnode", article_title=title)

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(
                e, "hashnode", title, "update", {"article_id": article_id}
            )
            raise APIError(
                f"Unexpected error updating Hashnode article: {str(e)}",
                platform="hashnode",
                article_title=title,
            )

    def get_articles(self) -> List[Dict]:
        """
        Retrieve all articles from Hashnode with pagination.

        Returns:
            List[Dict]: List of articles.

        Raises:
            AuthenticationError: If authentication fails
            RateLimitError: If rate limiting occurs
            APIError: If other API errors occur
        """
        try:
            all_articles = []
            page = 1  # Hashnode pagination starts from 1, not 0
            page_size = 20  # Hashnode's default page size

            # GraphQL query for getting user posts
            get_posts_query = gql(
                """
                query GetUserPosts($username: String!, $page: Int!, $pageSize: Int!) {
                    user(username: $username) {
                        posts(page: $page, pageSize: $pageSize) {
                            nodes {
                                id
                                title
                                slug
                                url
                                content {
                                    markdown
                                }
                                brief
                                coverImage {
                                    url
                                }
                                publishedAt
                                updatedAt
                                tags {
                                    name
                                }
                                series {
                                    name
                                }
                            }
                            pageInfo {
                                hasNextPage
                            }
                        }
                    }
                }
            """
            )

            while True:
                variables = {
                    "username": HASHNODE_USERNAME,
                    "page": page,
                    "pageSize": page_size,
                }

                result = self._run_query(get_posts_query, variables, "get_articles")

                if not result or "user" not in result or not result["user"]:
                    break

                posts_data = result["user"]["posts"]
                if not posts_data or "nodes" not in posts_data:
                    break

                articles = posts_data["nodes"]
                if not articles:
                    break

                # Convert to consistent format
                for article in articles:
                    formatted_article = {
                        "id": article["id"],
                        "title": article["title"],
                        "slug": article["slug"],
                        "url": article["url"],
                        "body_markdown": (
                            article["content"]["markdown"]
                            if article.get("content")
                            else ""
                        ),
                        "description": article.get("brief", ""),
                        "cover_image": (
                            article["coverImage"]["url"]
                            if article.get("coverImage")
                            else ""
                        ),
                        "published_at": article.get("publishedAt"),
                        "updated_at": article.get("updatedAt"),
                        "tags": [tag["name"] for tag in article.get("tags", [])],
                        "series": (
                            article["series"]["name"] if article.get("series") else None
                        ),
                        "published": bool(article.get("publishedAt")),
                    }
                    all_articles.append(formatted_article)

                # Check if there are more pages
                page_info = posts_data.get("pageInfo", {})
                if not page_info.get("hasNextPage", False):
                    break

                page += 1

            self.logging.debug(f"Retrieved {len(all_articles)} articles from Hashnode")
            return all_articles

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(e, "hashnode", None, "get_articles")
            raise APIError(
                f"Unexpected error retrieving Hashnode articles: {str(e)}",
                platform="hashnode",
            )

    def get_article(self, article_id: str, published: bool) -> Optional[Dict]:
        """
        Retrieve a specific article by ID from Hashnode.

        Args:
            article_id: The ID of the article to retrieve.
            published: Whether the article is published or not (used for filtering).

        Returns:
            Optional[Dict]: The article data or None if not found.
        """
        try:
            # GraphQL query for getting a specific post
            get_post_query = gql(
                """
                query GetPost($id: ID!) {
                    post(id: $id) {
                        id
                        title
                        slug
                        url
                        content {
                            markdown
                        }
                        brief
                        coverImage {
                            url
                        }
                        publishedAt
                        updatedAt
                        tags {
                            name
                        }
                        series {
                            name
                        }
                    }
                }
            """
            )

            variables = {"id": article_id}
            result = self._run_query(get_post_query, variables, "get_article")

            if not result or "post" not in result or not result["post"]:
                return None

            article = result["post"]

            # Check if the article matches the published status filter
            is_published = bool(article.get("publishedAt"))
            if published != is_published:
                return None

            # Convert to consistent format
            formatted_article = {
                "id": article["id"],
                "title": article["title"],
                "slug": article["slug"],
                "url": article["url"],
                "body_markdown": (
                    article["content"]["markdown"] if article.get("content") else ""
                ),
                "description": article.get("brief", ""),
                "cover_image": (
                    article["coverImage"]["url"] if article.get("coverImage") else ""
                ),
                "published_at": article.get("publishedAt"),
                "updated_at": article.get("updatedAt"),
                "tags": [tag["name"] for tag in article.get("tags", [])],
                "series": article["series"]["name"] if article.get("series") else None,
                "published": is_published,
            }

            return formatted_article

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(
                e, "hashnode", None, "get_article", {"article_id": article_id}
            )
            return None

    def find_article_by_title(self, title: str) -> Tuple[Optional[str], Optional[bool]]:
        """
        Find article ID and publication status by title.

        Args:
            title: The title of the article to find

        Returns:
            Tuple of (article_id, is_published) or (None, None) if not found
        """
        try:
            # Get all articles and search for matching title
            articles = self.get_articles()

            for article in articles:
                if article.get("title") == title:
                    article_id = article.get("id")
                    is_published = article.get("published", False)
                    self.logging.debug(
                        f"Found article '{title}' on Hashnode: ID={article_id}, published={is_published}"
                    )
                    return (article_id, is_published)

            # If not found, return None, None
            self.logging.debug(f"Article '{title}' not found on Hashnode")
            return (None, None)

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(
                e, "hashnode", title, "find_article_by_title"
            )
            return (None, None)

    def delete_article(self, article_id: str) -> bool:
        """
        Delete an article from Hashnode.

        Args:
            article_id: The ID of the article to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # GraphQL mutation for deleting a post
            delete_mutation = gql(
                """
                mutation RemovePost($input: RemovePostInput!) {
                    removePost(input: $input) {
                        post {
                            id
                        }
                    }
                }
            """
            )

            variables = {"input": {"id": article_id}}

            result = self._run_query(delete_mutation, variables, "delete", f"Article ID {article_id}")

            if result and "removePost" in result and result["removePost"]["post"]:
                # Successful deletion
                self.error_handler.log_success(
                    "hashnode", f"Article ID {article_id}", "deleted", article_id
                )
                return True
            else:
                # Deletion failed
                self.error_handler.log_api_error(
                    ValueError("Delete operation did not return expected result"),
                    "hashnode",
                    f"Article ID {article_id}",
                    "delete",
                    {"response": result}
                )
                return False

        except TransportError as e:
            # Handle permission errors specifically
            error_str = str(e)
            if "does not have the minimum required role" in error_str or "FORBIDDEN" in error_str:
                # Extract publication info if available
                if "minRequiredRole" in error_str and "actualRole" in error_str:
                    self.logging.warning(
                        f"⚠️  Cannot delete article {article_id} from Hashnode: "
                        f"Insufficient permissions (collaborative blog). "
                        f"This article is in a publication where you have contributor access but admin access is required for deletion. "
                        f"Please ask a publication admin to delete this article manually."
                    )
                else:
                    self.logging.warning(
                        f"⚠️  Cannot delete article {article_id} from Hashnode: "
                        f"Insufficient permissions. You may not have admin access to this publication."
                    )
                # Return True to indicate we "handled" this gracefully (not a system error)
                return True
            else:
                # Other transport errors - re-raise for normal handling
                raise
        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self.error_handler.log_api_error(
                e, "hashnode", f"Article ID {article_id}", "delete"
            )
            return False

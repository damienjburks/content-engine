"""
Publication manager for coordinating multi-platform publishing.
"""

import logging
from typing import Dict, List, Optional, Tuple
from ..interfaces.platform_client import PlatformClient
from ..models.post_content import PostContent, PublicationResult
from ..processors.content_processor import ContentProcessor
from ..utils.error_handler import (
    ErrorHandler,
    AuthenticationError,
    RateLimitError,
    APIError,
)


class PublicationManager:
    """
    Coordinates publishing across multiple platforms.

    This class implements the core coordination logic for multi-platform publishing,
    including content change detection, error isolation, and platform-specific
    content transformations.
    """

    def __init__(self, platform_clients: Dict[str, PlatformClient]):
        """
        Initialize the publication manager.

        Args:
            platform_clients: Dictionary mapping platform names to client instances
        """
        self.platform_clients = platform_clients
        self.content_processor = ContentProcessor()
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)

        # Log initialization
        self.logger.debug(
            f"PublicationManager initialized with {len(platform_clients)} platforms: {list(platform_clients.keys())}"
        )

    def publish_to_all_platforms(
        self, post_content: PostContent
    ) -> List[PublicationResult]:
        """
        Publish content to all configured platforms.

        Implements Requirements 1.5, 5.3, 5.4:
        - Iterates through all configured platform clients
        - Isolates failures between platforms
        - Continues processing other platforms when one fails

        Args:
            post_content: The content to publish

        Returns:
            List of publication results for each platform
        """
        results = []

        self.logger.debug(
            f"Starting publication of '{post_content.title}' to {len(self.platform_clients)} platforms"
        )

        # Requirement 5.3: Iterate through all configured platform clients
        for platform_name, client in self.platform_clients.items():
            try:
                self.logger.debug(f"Publishing to {platform_name}...")
                result = self._publish_to_platform(post_content, platform_name, client)
                results.append(result)

            except (AuthenticationError, RateLimitError, APIError) as e:
                # Requirement 1.5 & 5.4: Isolate failure and continue with other platforms
                # These are already logged by the error handler in the clients
                results.append(
                    PublicationResult(
                        platform=platform_name,
                        success=False,
                        action="error",
                        error_message=str(e),
                    )
                )

                # Continue processing other platforms (error isolation)
                continue

            except Exception as e:
                # Requirement 1.5 & 5.4: Handle unexpected errors
                self.error_handler.log_api_error(
                    e, platform_name, post_content.title, "publish"
                )

                results.append(
                    PublicationResult(
                        platform=platform_name,
                        success=False,
                        action="error",
                        error_message=f"Unexpected error: {str(e)}",
                    )
                )

                # Continue processing other platforms (error isolation)
                continue

        # Requirement 9.5: Report partial failure summary
        successful_platforms = [r.platform for r in results if r.success]
        failed_platforms = [
            (r.platform, r.error_message) for r in results if not r.success
        ]

        if successful_platforms or failed_platforms:
            self.error_handler.log_partial_failure_summary(
                post_content.title, successful_platforms, failed_platforms
            )

        return results

    def _publish_to_platform(
        self, post_content: PostContent, platform_name: str, client: PlatformClient
    ) -> PublicationResult:
        """
        Publish content to a specific platform.

        Implements Requirements 1.3, 1.4:
        - Updates existing articles only if content has changed
        - Creates new articles when no existing articles are found

        Args:
            post_content: The content to publish
            platform_name: Name of the platform
            client: Platform client instance

        Returns:
            Publication result
        """
        try:
            # Requirement 1.1: Check for existing articles before creating new ones
            self.logger.debug(
                f"Checking for existing article '{post_content.title}' on {platform_name}"
            )
            article_id, is_published = client.find_article_by_title(post_content.title)

            # Process content for this platform with platform-specific transformations
            processed_content = self.content_processor.process_content_for_platform(
                post_content, platform_name
            )

            # Create content dictionary for the platform API
            content_dict = self._create_content_dict(
                post_content, processed_content, platform_name
            )

            if article_id is None:
                # Requirement 1.4: Create new articles when no existing articles are found
                self.logger.debug(
                    f"No existing article found, creating new article on {platform_name}"
                )
                response = client.publish_article(
                    content_dict, not post_content.save_as_draft
                )
                return PublicationResult(
                    platform=platform_name,
                    success=True,
                    action="created",
                    article_id=response.get("id"),
                )
            else:
                # Requirement 1.3: Update existing articles only if content has changed
                self.logger.debug(
                    f"Found existing article (ID: {article_id}), checking for changes"
                )
                if self._needs_update(post_content, article_id, client, platform_name):
                    self.logger.debug(
                        f"Content changes detected, updating article on {platform_name}"
                    )
                    response = client.update_article(
                        article_id, content_dict, not post_content.save_as_draft
                    )
                    return PublicationResult(
                        platform=platform_name,
                        success=True,
                        action="updated",
                        article_id=article_id,
                    )
                else:
                    # Requirement 3.4: Skip update when no changes are detected
                    self.logger.debug(
                        f"No changes detected, skipping update on {platform_name}"
                    )
                    return PublicationResult(
                        platform=platform_name,
                        success=True,
                        action="skipped",
                        article_id=article_id,
                    )
        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions (already logged by clients)
            raise
        except Exception as e:
            # Enhanced error logging with platform and article information (Requirement 9.1)
            self.error_handler.log_api_error(
                e, platform_name, post_content.title, "publish_to_platform"
            )
            raise

    def _create_content_dict(
        self, post_content: PostContent, processed_content: str, platform_name: str
    ) -> Dict:
        """
        Create content dictionary for platform API.

        Applies platform-specific formatting and includes canonical URL handling
        to avoid SEO conflicts (Requirement 4.5).

        Args:
            post_content: Original post content
            processed_content: Platform-processed content
            platform_name: Target platform name

        Returns:
            Dictionary formatted for platform API
        """
        # Convert tags to platform-specific format (Requirement 4.4)
        platform_tags = self.content_processor.convert_tags_for_platform(
            post_content.tags, platform_name
        )

        # Generate canonical URL for the platform (Requirement 4.5)
        canonical_url = self.content_processor.generate_canonical_url(
            post_content, platform_name
        )

        return {
            "frontmatterData": {
                "title": post_content.title,
                "subtitle": post_content.subtitle,
                "slug": post_content.slug,
                "tags": ",".join(platform_tags),
                "cover": post_content.cover,
                "domain": post_content.domain,
                "saveAsDraft": post_content.save_as_draft,
                "seriesName": post_content.series_name,
                "canonicalUrl": canonical_url,
            },
            "bodyMarkdown": processed_content,
        }

    def _needs_update(
        self,
        post_content: PostContent,
        article_id: str,
        client: PlatformClient,
        platform_name: str,
    ) -> bool:
        """
        Check if an existing article needs to be updated.

        Implements Requirement 3.3: Detect differences in markdown content,
        publication status, tags, or metadata.

        Args:
            post_content: Local post content
            article_id: Platform article ID
            client: Platform client
            platform_name: Platform name

        Returns:
            True if update is needed, False otherwise
        """
        try:
            # Requirement 3.5: Handle both published and draft articles
            existing_article = client.get_article(
                article_id, True
            )  # Try published first
            if not existing_article:
                existing_article = client.get_article(article_id, False)  # Try draft

            if not existing_article:
                self.logger.warning(
                    f"Could not retrieve existing article {article_id} from {platform_name}"
                )
                return True  # If we can't get the article, assume update is needed

            # Requirement 6.1: Normalize content for comparison by removing frontmatter and platform-specific formatting
            local_content = self.content_processor.normalize_content_for_comparison(
                post_content.body_markdown
            )
            platform_content = self.content_processor.normalize_content_for_comparison(
                existing_article.get("body_markdown", "")
            )

            # Requirement 3.3 & 6.2: Detect differences in all relevant fields
            title_changed = post_content.title != existing_article.get("title", "")
            content_changed = local_content != platform_content

            # Handle tag comparison - convert platform tags to comparable format
            existing_tags = existing_article.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [
                    tag.strip() for tag in existing_tags.split(",") if tag.strip()
                ]
            elif not isinstance(existing_tags, list):
                existing_tags = []

            tags_changed = set(post_content.tags) != set(existing_tags)

            # Check publication status
            published_changed = (
                not post_content.save_as_draft
            ) != existing_article.get("published", False)

            # Check cover image (Requirement 6.2)
            cover_changed = post_content.cover != existing_article.get(
                "cover_image", ""
            )

            changes_detected = any(
                [
                    title_changed,
                    content_changed,
                    tags_changed,
                    published_changed,
                    cover_changed,
                ]
            )

            if changes_detected:
                change_details = []
                if title_changed:
                    change_details.append("title")
                if content_changed:
                    change_details.append("content")
                if tags_changed:
                    change_details.append("tags")
                if published_changed:
                    change_details.append("publication status")
                if cover_changed:
                    change_details.append("cover image")

                self.logger.debug(
                    f"Changes detected in {platform_name}: {', '.join(change_details)}"
                )
            else:
                self.logger.debug(f"No changes detected for article on {platform_name}")

            return changes_detected

        except (AuthenticationError, RateLimitError, APIError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Enhanced error logging (Requirement 9.1)
            self.error_handler.log_api_error(
                e, platform_name, post_content.title, "needs_update_check"
            )
            return True  # If we can't check, assume update is needed

    def get_platform_status(self, post_content: PostContent) -> Dict[str, Dict]:
        """
        Get the status of an article across all configured platforms.

        Args:
            post_content: The post content to check

        Returns:
            Dictionary mapping platform names to their article status
        """
        status = {}

        for platform_name, client in self.platform_clients.items():
            try:
                article_id, is_published = client.find_article_by_title(
                    post_content.title
                )

                if article_id:
                    needs_update = self._needs_update(
                        post_content, article_id, client, platform_name
                    )
                    status[platform_name] = {
                        "exists": True,
                        "article_id": article_id,
                        "published": is_published,
                        "needs_update": needs_update,
                    }
                else:
                    status[platform_name] = {
                        "exists": False,
                        "article_id": None,
                        "published": False,
                        "needs_update": False,
                    }

            except (AuthenticationError, RateLimitError, APIError) as e:
                self.logger.error(f"Error checking status on {platform_name}: {str(e)}")
                status[platform_name] = {
                    "exists": False,
                    "article_id": None,
                    "published": False,
                    "needs_update": False,
                    "error": str(e),
                }
            except Exception as e:
                self.error_handler.log_api_error(
                    e, platform_name, post_content.title, "get_platform_status"
                )
                status[platform_name] = {
                    "exists": False,
                    "article_id": None,
                    "published": False,
                    "needs_update": False,
                    "error": f"Unexpected error: {str(e)}",
                }

        return status

    def validate_platform_clients(self) -> Dict[str, bool]:
        """
        Validate that all platform clients are properly configured and accessible.

        Returns:
            Dictionary mapping platform names to their validation status
        """
        validation_results = {}

        for platform_name, client in self.platform_clients.items():
            try:
                # Try to get articles to test the connection
                client.get_articles()
                validation_results[platform_name] = True
                self.logger.debug(
                    f"Platform client {platform_name} validated successfully"
                )
            except AuthenticationError as e:
                validation_results[platform_name] = False
                # Authentication errors are already logged by the error handler
            except (RateLimitError, APIError) as e:
                validation_results[platform_name] = False
                self.logger.warning(
                    f"Platform client {platform_name} validation failed: {str(e)}"
                )
            except Exception as e:
                validation_results[platform_name] = False
                self.error_handler.log_api_error(e, platform_name, None, "validation")
                self.logger.error(
                    f"Platform client {platform_name} validation failed: {str(e)}"
                )

        return validation_results

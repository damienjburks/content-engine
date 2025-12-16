"""
This module is responsible for publishing posts to multiple platforms.
"""

import glob
import logging
import os
import re
import time
from typing import Dict, List, Optional

import frontmatter

from src.client.devto_client import DevToClient
from src.client.hashnode_client import HashnodeClient
from src.managers.publication_manager import PublicationManager
from src.models.post_content import PostContent
from src.utils.error_handler import (
    ErrorHandler,
    AuthenticationError,
    RateLimitError,
    APIError,
)

logging.basicConfig(level=logging.INFO)


class PostPublisher:
    """
    This class is responsible for publishing posts to multiple platforms.

    Implements Requirements 1.1, 1.6, 3.1, 5.5:
    - Uses PublicationManager for multi-platform coordination
    - Manages configuration for multiple platforms
    - Initializes and manages platform clients
    - Updates existing article detection logic for multiple platforms
    """

    def __init__(self, enabled_platforms: Optional[List[str]] = None) -> None:
        """
        Initialize PostPublisher with platform configuration.

        Args:
            enabled_platforms: List of platform names to enable.
                             If None, enables all available platforms.
        """
        self.logger = logging.getLogger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        self.non_updated_articles = []

        # Configuration management for multiple platforms (Requirement 5.5)
        self.config = self._load_configuration()

        # Platform client initialization and management (Requirement 1.6)
        self.platform_clients = self._initialize_platform_clients(enabled_platforms)

        # Initialize PublicationManager with configured clients
        self.publication_manager = PublicationManager(self.platform_clients)

        self.logger.info(
            f"PostPublisher initialized with platforms: {list(self.platform_clients.keys())}"
        )

    def _load_configuration(self) -> Dict:
        """
        Load configuration from environment variables.

        Implements Requirement 5.5: Platform configuration handling.

        Returns:
            Dictionary containing configuration settings
        """
        config = {
            "enabled_platforms": os.environ.get(
                "ENABLED_PLATFORMS", "devto,hashnode"
            ).split(","),
            "rate_limit_delay": int(os.environ.get("RATE_LIMIT_DELAY", "5")),
            "markdown_file_pattern": os.environ.get(
                "MARKDOWN_FILE_PATTERN", "blogs/*.md"
            ),
            "exclude_files": os.environ.get("EXCLUDE_FILES", "README.md").split(","),
        }

        # Clean up platform names
        config["enabled_platforms"] = [
            p.strip().lower() for p in config["enabled_platforms"] if p.strip()
        ]

        self.logger.info(f"Configuration loaded: {config}")
        return config

    def _initialize_platform_clients(
        self, enabled_platforms: Optional[List[str]] = None
    ) -> Dict[str, object]:
        """
        Initialize platform clients based on configuration.

        Implements Requirements 1.6, 5.5:
        - Platform client initialization and management
        - Platform configuration handling

        Args:
            enabled_platforms: Override for enabled platforms

        Returns:
            Dictionary mapping platform names to client instances
        """
        clients = {}

        # Use provided platforms or fall back to configuration
        platforms_to_enable = enabled_platforms or self.config["enabled_platforms"]

        for platform in platforms_to_enable:
            platform = platform.strip().lower()

            try:
                if platform == "devto":
                    # Check if DevTo API key is available
                    if os.environ.get("DEVTO_API_KEY"):
                        clients["devto"] = DevToClient()
                        self.logger.info("DevTo client initialized successfully")
                    else:
                        self.error_handler.log_authentication_error(
                            "devto", "DEVTO_API_KEY not found"
                        )

                elif platform == "hashnode":
                    # Check if Hashnode credentials are available
                    if os.environ.get("HASHNODE_API_KEY") and os.environ.get(
                        "HASHNODE_USERNAME"
                    ):
                        clients["hashnode"] = HashnodeClient()
                        self.logger.info("Hashnode client initialized successfully")
                    else:
                        missing_vars = []
                        if not os.environ.get("HASHNODE_API_KEY"):
                            missing_vars.append("HASHNODE_API_KEY")
                        if not os.environ.get("HASHNODE_USERNAME"):
                            missing_vars.append("HASHNODE_USERNAME")
                        self.error_handler.log_authentication_error(
                            "hashnode",
                            f"Missing environment variables: {', '.join(missing_vars)}",
                        )

                else:
                    self.logger.warning(f"Unknown platform: {platform}")

            except AuthenticationError:
                # Authentication errors are already logged
                pass
            except Exception as e:
                self.error_handler.log_api_error(e, platform, None, "initialization")
                self.logger.error(f"Failed to initialize {platform} client: {str(e)}")

        if not clients:
            error_msg = "No platform clients could be initialized. Check your API keys and configuration."
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        return clients

    def publish_to_all_platforms(self) -> None:
        """
        Publish articles to all configured platforms.

        Implements Requirements 1.1, 3.1:
        - Check for existing articles before creating new ones
        - Update existing article detection logic for multiple platforms
        """
        md_files = self._get_list_of_markdown_files()

        if not md_files:
            self.logger.info("No markdown files found to publish")
            return

        self.logger.info(f"Found {len(md_files)} markdown files to process")

        for md_file in md_files:
            try:
                self.logger.info(f"Processing file: {md_file}")

                # Parse markdown file into PostContent model
                post_content = self._parse_markdown_file(md_file)

                if not post_content:
                    self.logger.warning(f"Skipping {md_file} - could not parse content")
                    continue

                # Use PublicationManager to publish to all platforms
                results = self.publication_manager.publish_to_all_platforms(
                    post_content
                )

                # Process results and update tracking
                self._process_publication_results(md_file, post_content, results)

                # Rate limiting between files
                if len(md_files) > 1:  # Only sleep if processing multiple files
                    time.sleep(self.config["rate_limit_delay"])

            except (AuthenticationError, RateLimitError, APIError) as e:
                # Platform-specific errors are already logged by the error handler
                self.logger.error(f"Platform error processing {md_file}: {str(e)}")
                continue
            except Exception as e:
                self.error_handler.log_api_error(
                    e, "system", None, "file_processing", {"file": md_file}
                )
                self.logger.error(
                    f"Unexpected error processing {md_file}: {str(e)}", exc_info=True
                )
                continue

    def _parse_markdown_file(self, md_file: str) -> Optional[PostContent]:
        """
        Parse a markdown file into a PostContent model.

        Args:
            md_file: Path to the markdown file

        Returns:
            PostContent instance or None if parsing fails
        """
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                markdown_text = f.read()

            # Parse frontmatter and content
            post = frontmatter.loads(markdown_text)
            frontmatter_data = post.metadata
            body_markdown = post.content

            # Validate required fields
            if not frontmatter_data.get("title"):
                self.logger.error(f"Missing required 'title' field in {md_file}")
                return None

            # Create PostContent from frontmatter
            post_content = PostContent.from_frontmatter(frontmatter_data, body_markdown)

            self.logger.debug(
                f"Parsed {md_file}: title='{post_content.title}', tags={post_content.tags}"
            )
            return post_content

        except Exception as e:
            self.logger.error(f"Error parsing {md_file}: {str(e)}")
            return None

    def _process_publication_results(
        self, md_file: str, post_content: PostContent, results: List
    ) -> None:
        """
        Process and log publication results.

        Args:
            md_file: The source markdown file
            post_content: The post content that was published
            results: List of PublicationResult objects
        """
        successful_platforms = []
        failed_platforms = []
        skipped_platforms = []

        for result in results:
            if result.success:
                if result.action == "skipped":
                    skipped_platforms.append(result.platform)
                else:
                    successful_platforms.append(f"{result.platform} ({result.action})")
            else:
                failed_platforms.append(f"{result.platform}: {result.error_message}")

        # Log summary for this file
        if successful_platforms:
            self.logger.info(
                f"'{post_content.title}' - Success: {', '.join(successful_platforms)}"
            )

        if skipped_platforms:
            self.logger.info(
                f"'{post_content.title}' - Skipped (no changes): {', '.join(skipped_platforms)}"
            )
            self.non_updated_articles.append(md_file)

        if failed_platforms:
            self.logger.error(
                f"'{post_content.title}' - Failed: {', '.join(failed_platforms)}"
            )

    def _get_list_of_markdown_files(self) -> List[str]:
        """
        Get list of markdown files to process based on configuration.

        Returns:
            List of markdown file paths
        """
        # Use configured pattern or default
        pattern = self.config.get("markdown_file_pattern", "blogs/*.md")
        md_files = glob.glob(pattern)

        # If no files found with pattern, try current directory as fallback
        if not md_files:
            md_files = glob.glob("*.md")

        # Exclude configured files
        exclude_files = self.config.get("exclude_files", ["README.md"])
        md_files = [
            file
            for file in md_files
            if not any(file.endswith(exclude) for exclude in exclude_files)
        ]

        return sorted(md_files)

    def get_platform_status(self, post_title: str) -> Dict:
        """
        Get the status of an article across all platforms.

        Args:
            post_title: Title of the post to check

        Returns:
            Dictionary with platform status information
        """
        # Create a minimal PostContent for status checking
        post_content = PostContent(
            title=post_title,
            subtitle="",
            slug="",
            tags=[],
            cover="",
            domain="",
            save_as_draft=False,
            enable_toc=False,
            body_markdown="",
            canonical_url="",
        )

        return self.publication_manager.get_platform_status(post_content)

    def validate_configuration(self) -> Dict[str, bool]:
        """
        Validate platform configuration and connectivity.

        Returns:
            Dictionary mapping platform names to validation status
        """
        return self.publication_manager.validate_platform_clients()

    # Backward compatibility methods
    def publish_to_devto(self) -> None:
        """
        Backward compatibility method for publishing to DevTo only.

        Deprecated: Use publish_to_all_platforms() instead.
        """
        self.logger.warning(
            "publish_to_devto() is deprecated. Use publish_to_all_platforms() instead."
        )

        # Temporarily restrict to DevTo only
        if "devto" in self.platform_clients:
            original_clients = self.platform_clients.copy()
            self.platform_clients = {"devto": self.platform_clients["devto"]}
            self.publication_manager = PublicationManager(self.platform_clients)

            try:
                self.publish_to_all_platforms()
            finally:
                # Restore original clients
                self.platform_clients = original_clients
                self.publication_manager = PublicationManager(self.platform_clients)
        else:
            self.logger.error("DevTo client not available")

    # Legacy methods for backward compatibility (deprecated)
    def _remove_frontmatter(self, markdown_text: str) -> str:
        """
        Legacy method for removing frontmatter.

        Deprecated: Content processing is now handled by ContentProcessor.
        """
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        return re.sub(frontmatter_pattern, "", markdown_text, flags=re.DOTALL)


def main():
    """Main entry point for the content engine CLI."""
    try:
        # Initialize publisher with all available platforms
        publisher = PostPublisher()

        # Validate configuration
        validation_results = publisher.validate_configuration()

        failed_platforms = [
            platform for platform, valid in validation_results.items() if not valid
        ]
        if failed_platforms:
            logging.warning(f"Some platforms failed validation: {failed_platforms}")

        successful_platforms = [
            platform for platform, valid in validation_results.items() if valid
        ]
        if not successful_platforms:
            logging.error(
                "No platforms are properly configured. Please check your API keys."
            )
            return

        logging.info(f"Publishing to platforms: {successful_platforms}")

        # Publish to all configured platforms
        publisher.publish_to_all_platforms()

        # Log summary
        if publisher.non_updated_articles:
            logging.info(
                f"Articles with no changes: {len(publisher.non_updated_articles)}"
            )

    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

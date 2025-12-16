"""
Comprehensive error handling and logging utilities for multi-platform publishing.

This module implements Requirements 9.1, 9.2, 9.3, 9.4, 9.5:
- Detailed error logging for API failures with platform and article information
- Rate limiting handling with delays and retry mechanisms
- Authentication error handling with clear error messages
- Success logging with article titles and platform names
- Partial failure reporting for mixed success/failure scenarios
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError


class PublishingError(Exception):
    """Base exception for publishing-related errors."""

    def __init__(
        self,
        message: str,
        platform: str = None,
        article_title: str = None,
        error_code: str = None,
        retry_after: int = None,
    ):
        super().__init__(message)
        self.platform = platform
        self.article_title = article_title
        self.error_code = error_code
        self.retry_after = retry_after


class AuthenticationError(PublishingError):
    """Exception raised for authentication-related errors."""

    pass


class RateLimitError(PublishingError):
    """Exception raised when rate limiting occurs."""

    pass


class APIError(PublishingError):
    """Exception raised for general API errors."""

    pass


class ErrorHandler:
    """
    Comprehensive error handler for multi-platform publishing operations.

    Implements Requirements 9.1, 9.2, 9.3, 9.4, 9.5.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the error handler.

        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.retry_delays = [1, 2, 4, 8, 16]  # Exponential backoff delays in seconds
        self.max_retries = 3

    def log_api_error(
        self,
        error: Exception,
        platform: str,
        article_title: str = None,
        operation: str = None,
        additional_context: Dict = None,
    ) -> None:
        """
        Log detailed API error information.

        Implements Requirement 9.1: Log detailed error messages including
        platform and article information.

        Args:
            error: The exception that occurred
            platform: Platform name where error occurred
            article_title: Title of the article being processed (if applicable)
            operation: The operation being performed (publish, update, retrieve, etc.)
            additional_context: Additional context information
        """
        error_details = {
            "platform": platform,
            "article_title": article_title or "Unknown",
            "operation": operation or "Unknown",
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        if additional_context:
            error_details.update(additional_context)

        # Add HTTP-specific details if available
        if hasattr(error, "response") and error.response is not None:
            error_details.update(
                {
                    "status_code": error.response.status_code,
                    "response_text": error.response.text[:500],  # Limit response text
                    "request_url": error.response.url,
                }
            )

        self.logger.error(
            f"API Error on {platform}: {operation} failed for '{article_title}' - {str(error)}",
            extra={"error_details": error_details},
            exc_info=True,
        )

    def log_authentication_error(
        self, platform: str, error_message: str = None
    ) -> None:
        """
        Log authentication errors with clear guidance.

        Implements Requirement 9.3: Provide clear error messages indicating
        authentication issues.

        Args:
            platform: Platform name where authentication failed
            error_message: Optional specific error message
        """
        base_message = f"Authentication failed for {platform}"

        if error_message:
            full_message = f"{base_message}: {error_message}"
        else:
            full_message = base_message

        # Platform-specific guidance
        guidance = self._get_authentication_guidance(platform)

        self.logger.error(f"{full_message}. {guidance}")

    def log_rate_limit_error(
        self, platform: str, retry_after: int = None, article_title: str = None
    ) -> None:
        """
        Log rate limiting errors with retry information.

        Implements Requirement 9.2: Log rate limiting occurrences.

        Args:
            platform: Platform name where rate limiting occurred
            retry_after: Seconds to wait before retrying (if provided by API)
            article_title: Title of the article being processed
        """
        if retry_after:
            message = f"Rate limit exceeded on {platform} for '{article_title}'. Retry after {retry_after} seconds."
        else:
            message = f"Rate limit exceeded on {platform} for '{article_title}'. Using exponential backoff."

        self.logger.warning(message)

    def log_success(
        self,
        platform: str,
        article_title: str,
        action: str,
        article_id: str = None,
        additional_info: Dict = None,
    ) -> None:
        """
        Log successful operations with comprehensive details.

        Implements Requirement 9.4: Log success messages with article titles
        and platform names.

        Args:
            platform: Platform name where operation succeeded
            article_title: Title of the article
            action: Action performed (created, updated, skipped)
            article_id: ID of the article (if available)
            additional_info: Additional information to log
        """
        base_message = f"SUCCESS: {action.capitalize()} '{article_title}' on {platform}"

        if article_id:
            base_message += f" (ID: {article_id})"

        if additional_info:
            details = ", ".join([f"{k}: {v}" for k, v in additional_info.items()])
            base_message += f" - {details}"

        self.logger.info(base_message)

    def log_partial_failure_summary(
        self,
        article_title: str,
        successful_platforms: List[str],
        failed_platforms: List[Tuple[str, str]],
    ) -> None:
        """
        Log summary of partial failures across platforms.

        Implements Requirement 9.5: Report which platforms succeeded and which failed.

        Args:
            article_title: Title of the article being processed
            successful_platforms: List of platforms that succeeded
            failed_platforms: List of tuples (platform, error_message)
        """
        if successful_platforms and failed_platforms:
            self.logger.warning(
                f"PARTIAL SUCCESS for '{article_title}': "
                f"Succeeded on {', '.join(successful_platforms)}; "
                f"Failed on {', '.join([p[0] for p in failed_platforms])}"
            )

            # Log detailed failure information
            for platform, error_msg in failed_platforms:
                self.logger.error(f"  - {platform}: {error_msg}")

        elif failed_platforms and not successful_platforms:
            self.logger.error(
                f"COMPLETE FAILURE for '{article_title}': "
                f"Failed on all platforms: {', '.join([p[0] for p in failed_platforms])}"
            )

    def _get_authentication_guidance(self, platform: str) -> str:
        """
        Get platform-specific authentication guidance.

        Args:
            platform: Platform name

        Returns:
            Guidance message for authentication setup
        """
        guidance_map = {
            "devto": (
                "Please check your DEVTO_API_KEY environment variable. "
                "Get your API key from https://dev.to/settings/extensions"
            ),
            "hashnode": (
                "Please check your HASHNODE_API_KEY and HASHNODE_USERNAME environment variables. "
                "Get your API key from https://hashnode.com/settings/developer"
            ),
        }

        return guidance_map.get(
            platform.lower(), f"Please check your API credentials for {platform}"
        )


def with_retry_and_rate_limiting(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
):
    """
    Decorator for implementing retry logic with exponential backoff and rate limiting.

    Implements Requirement 9.2: Implement appropriate delays and retry mechanisms.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            error_handler = ErrorHandler()
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except (RateLimitError, requests.exceptions.HTTPError) as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Handle rate limiting
                    if isinstance(e, RateLimitError) or (
                        hasattr(e, "response") and e.response.status_code == 429
                    ):
                        # Extract retry-after header if available
                        retry_after = None
                        if hasattr(e, "response") and e.response is not None:
                            retry_after = e.response.headers.get("Retry-After")
                            if retry_after:
                                try:
                                    retry_after = int(retry_after)
                                except ValueError:
                                    retry_after = None

                        # Use retry-after or exponential backoff
                        if retry_after:
                            delay = min(retry_after, max_delay)
                        else:
                            delay = min(
                                base_delay * (backoff_factor**attempt), max_delay
                            )

                        error_handler.logger.info(
                            f"Rate limit hit, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)

                    else:
                        # For other HTTP errors, use exponential backoff
                        delay = min(base_delay * (backoff_factor**attempt), max_delay)
                        error_handler.logger.info(
                            f"Request failed, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)

                except (ConnectionError, Timeout, RequestException) as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    # Network-related errors - use exponential backoff
                    delay = min(base_delay * (backoff_factor**attempt), max_delay)
                    error_handler.logger.info(
                        f"Network error, retrying in {delay} seconds (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
                    )
                    time.sleep(delay)

                except Exception as e:
                    # For other exceptions, don't retry
                    raise e

            # If we get here, all retries failed
            raise last_exception

        return wrapper

    return decorator


def handle_api_response(
    response: requests.Response,
    platform: str,
    operation: str,
    article_title: str = None,
) -> Dict:
    """
    Handle API response and raise appropriate exceptions for errors.

    Implements Requirements 9.1, 9.2, 9.3: Handle various API error conditions
    with appropriate error types and logging.

    Args:
        response: HTTP response object
        platform: Platform name
        operation: Operation being performed
        article_title: Title of article being processed

    Returns:
        Parsed JSON response

    Raises:
        AuthenticationError: For authentication-related errors (401, 403)
        RateLimitError: For rate limiting errors (429)
        APIError: For other API errors
    """
    error_handler = ErrorHandler()

    try:
        response.raise_for_status()
        return response.json()

    except HTTPError as e:
        status_code = response.status_code

        if status_code in [401, 403]:
            error_msg = f"Authentication failed for {platform}"
            if response.text:
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f": {error_data['error']}"
                except:
                    error_msg += f": {response.text[:200]}"

            error_handler.log_authentication_error(platform, error_msg)
            raise AuthenticationError(
                error_msg,
                platform=platform,
                article_title=article_title,
                error_code=str(status_code),
            )

        elif status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = None
            if retry_after:
                try:
                    retry_seconds = int(retry_after)
                except ValueError:
                    pass

            error_handler.log_rate_limit_error(platform, retry_seconds, article_title)
            raise RateLimitError(
                f"Rate limit exceeded on {platform}",
                platform=platform,
                article_title=article_title,
                retry_after=retry_seconds,
            )

        else:
            error_msg = f"API error on {platform}: {status_code}"
            if response.text:
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f" - {error_data['error']}"
                    elif "message" in error_data:
                        error_msg += f" - {error_data['message']}"
                except:
                    error_msg += f" - {response.text[:200]}"

            error_handler.log_api_error(e, platform, article_title, operation)
            raise APIError(
                error_msg,
                platform=platform,
                article_title=article_title,
                error_code=str(status_code),
            )

    except ValueError as e:
        # JSON parsing error
        error_msg = f"Invalid JSON response from {platform}"
        error_handler.log_api_error(e, platform, article_title, operation)
        raise APIError(error_msg, platform=platform, article_title=article_title)

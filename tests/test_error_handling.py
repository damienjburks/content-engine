"""
Tests for comprehensive error handling and logging functionality.
"""

import logging
import pytest
from unittest.mock import Mock, patch
import requests

from src.utils.error_handler import (
    ErrorHandler,
    PublishingError,
    AuthenticationError,
    RateLimitError,
    APIError,
    with_retry_and_rate_limiting,
    handle_api_response,
)


class TestErrorHandler:
    """Test the ErrorHandler class functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)

    def test_log_api_error(self):
        """Test detailed API error logging."""
        error = Exception("Test error")

        self.error_handler.log_api_error(
            error, "devto", "Test Article", "publish", {"additional": "context"}
        )

        # Verify error was logged with correct details
        self.logger.error.assert_called_once()
        call_args = self.logger.error.call_args

        assert "API Error on devto" in call_args[0][0]
        assert "Test Article" in call_args[0][0]
        assert "publish failed" in call_args[0][0]

        # Check extra details were included
        assert "error_details" in call_args[1]["extra"]
        error_details = call_args[1]["extra"]["error_details"]
        assert error_details["platform"] == "devto"
        assert error_details["article_title"] == "Test Article"
        assert error_details["operation"] == "publish"
        assert error_details["additional"] == "context"

    def test_log_authentication_error(self):
        """Test authentication error logging with guidance."""
        self.error_handler.log_authentication_error("devto", "Invalid API key")

        self.logger.error.assert_called_once()
        call_args = self.logger.error.call_args[0][0]

        assert "Authentication failed for devto" in call_args
        assert "Invalid API key" in call_args
        assert "DEVTO_API_KEY" in call_args
        assert "dev.to/settings/extensions" in call_args

    def test_log_rate_limit_error(self):
        """Test rate limiting error logging."""
        self.error_handler.log_rate_limit_error("hashnode", 60, "Test Article")

        self.logger.warning.assert_called_once()
        call_args = self.logger.warning.call_args[0][0]

        assert "Rate limit exceeded on hashnode" in call_args
        assert "Test Article" in call_args
        assert "60 seconds" in call_args

    def test_log_success(self):
        """Test success logging."""
        self.error_handler.log_success(
            "devto", "Test Article", "created", "12345", {"url": "https://dev.to/test"}
        )

        self.logger.debug.assert_called_once()
        call_args = self.logger.debug.call_args[0][0]

        assert "SUCCESS: Created 'Test Article' on devto" in call_args
        assert "ID: 12345" in call_args
        assert "url: https://dev.to/test" in call_args

    def test_log_partial_failure_summary(self):
        """Test partial failure summary logging."""
        successful_platforms = ["devto"]
        failed_platforms = [("hashnode", "Authentication failed")]

        self.error_handler.log_partial_failure_summary(
            "Test Article", successful_platforms, failed_platforms
        )

        # Should log warning for partial success
        self.logger.warning.assert_called_once()
        warning_call = self.logger.warning.call_args[0][0]
        assert "PARTIAL SUCCESS for 'Test Article'" in warning_call
        assert "Succeeded on devto" in warning_call
        assert "Failed on hashnode" in warning_call

        # Should log detailed failure information
        self.logger.error.assert_called_once()
        error_call = self.logger.error.call_args[0][0]
        assert "hashnode: Authentication failed" in error_call


class TestRetryDecorator:
    """Test the retry decorator functionality."""

    def test_successful_execution(self):
        """Test that successful functions execute normally."""

        @with_retry_and_rate_limiting(max_retries=2)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_on_rate_limit(self):
        """Test retry behavior on rate limiting."""
        call_count = 0

        @with_retry_and_rate_limiting(max_retries=2, base_delay=0.01)
        def rate_limited_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limited", platform="test")
            return "success"

        result = rate_limited_function()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that function fails after max retries."""

        @with_retry_and_rate_limiting(max_retries=2, base_delay=0.01)
        def always_fails():
            raise RateLimitError("Always fails", platform="test")

        with pytest.raises(RateLimitError):
            always_fails()


class TestHandleApiResponse:
    """Test the API response handler."""

    def test_successful_response(self):
        """Test handling of successful API response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123", "title": "Test"}
        mock_response.raise_for_status.return_value = None

        result = handle_api_response(mock_response, "devto", "publish", "Test Article")

        assert result == {"id": "123", "title": "Test"}

    def test_authentication_error_response(self):
        """Test handling of authentication error response."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with pytest.raises(AuthenticationError) as exc_info:
            handle_api_response(mock_response, "devto", "publish", "Test Article")

        assert exc_info.value.platform == "devto"
        assert exc_info.value.article_title == "Test Article"
        assert "Invalid API key" in str(exc_info.value)

    def test_rate_limit_error_response(self):
        """Test handling of rate limit error response."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limited"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with pytest.raises(RateLimitError) as exc_info:
            handle_api_response(mock_response, "hashnode", "publish", "Test Article")

        assert exc_info.value.platform == "hashnode"
        assert exc_info.value.article_title == "Test Article"
        assert exc_info.value.retry_after == 60

    def test_general_api_error_response(self):
        """Test handling of general API error response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_response.json.return_value = {"message": "Server error"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with pytest.raises(APIError) as exc_info:
            handle_api_response(mock_response, "devto", "update", "Test Article")

        assert exc_info.value.platform == "devto"
        assert exc_info.value.article_title == "Test Article"
        assert "Server error" in str(exc_info.value)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_publishing_error_base(self):
        """Test base PublishingError exception."""
        error = PublishingError(
            "Test error",
            platform="devto",
            article_title="Test Article",
            error_code="500",
        )

        assert str(error) == "Test error"
        assert error.platform == "devto"
        assert error.article_title == "Test Article"
        assert error.error_code == "500"

    def test_authentication_error(self):
        """Test AuthenticationError exception."""
        error = AuthenticationError(
            "Auth failed", platform="hashnode", article_title="Test Article"
        )

        assert str(error) == "Auth failed"
        assert error.platform == "hashnode"
        assert error.article_title == "Test Article"

    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        error = RateLimitError("Rate limited", platform="devto", retry_after=30)

        assert str(error) == "Rate limited"
        assert error.platform == "devto"
        assert error.retry_after == 30

    def test_api_error(self):
        """Test APIError exception."""
        error = APIError("API error", platform="hashnode", error_code="404")

        assert str(error) == "API error"
        assert error.platform == "hashnode"
        assert error.error_code == "404"

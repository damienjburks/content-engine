"""
Integration tests for error handling functionality.
"""

import os
import pytest
from unittest.mock import Mock, patch

from src.main import PostPublisher
from src.utils.error_handler import AuthenticationError


class TestErrorHandlingIntegration:
    """Test error handling in real integration scenarios."""

    def test_missing_api_keys_handling(self):
        """Test that missing API keys are handled gracefully."""
        # Clear environment variables
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                PostPublisher()

            assert "No platform clients could be initialized" in str(exc_info.value)

    def test_invalid_devto_api_key_handling(self):
        """Test handling of invalid DevTo API key."""
        with patch.dict(
            os.environ,
            {
                "DEVTO_API_KEY": "invalid_key",
                "HASHNODE_API_KEY": "valid_key",
                "HASHNODE_USERNAME": "valid_user",
            },
        ):
            # Mock the DevToClient to raise AuthenticationError, Hashnode to succeed
            with patch("src.main.DevToClient") as mock_devto:
                with patch("src.main.HashnodeClient") as mock_hashnode:
                    mock_devto.side_effect = AuthenticationError(
                        "Invalid API key", platform="devto"
                    )
                    mock_hashnode.return_value = Mock()

                    # Should still initialize but skip DevTo
                    publisher = PostPublisher()
                    assert "devto" not in publisher.platform_clients
                    assert "hashnode" in publisher.platform_clients

    def test_invalid_hashnode_credentials_handling(self):
        """Test handling of invalid Hashnode credentials."""
        with patch.dict(
            os.environ,
            {
                "DEVTO_API_KEY": "valid_key",
                "HASHNODE_API_KEY": "invalid_key",
                "HASHNODE_USERNAME": "invalid_user",
            },
        ):
            # Mock the HashnodeClient to raise AuthenticationError, DevTo to succeed
            with patch("src.main.DevToClient") as mock_devto:
                with patch("src.main.HashnodeClient") as mock_hashnode:
                    mock_devto.return_value = Mock()
                    mock_hashnode.side_effect = AuthenticationError(
                        "Invalid credentials", platform="hashnode"
                    )

                    # Should still initialize but skip Hashnode
                    publisher = PostPublisher()
                    assert "devto" in publisher.platform_clients
                    assert "hashnode" not in publisher.platform_clients

    def test_partial_platform_initialization(self):
        """Test that publisher works with only some platforms available."""
        with patch.dict(os.environ, {"DEVTO_API_KEY": "valid_key"}):
            # Mock successful DevTo client, failed Hashnode
            with patch("src.main.DevToClient") as mock_devto:
                with patch("src.main.HashnodeClient") as mock_hashnode:
                    mock_devto.return_value = Mock()
                    mock_hashnode.side_effect = AuthenticationError(
                        "Invalid credentials", platform="hashnode"
                    )

                    publisher = PostPublisher()

                    # Should have DevTo but not Hashnode
                    assert "devto" in publisher.platform_clients
                    assert "hashnode" not in publisher.platform_clients
                    assert len(publisher.platform_clients) == 1

    def test_validation_with_mixed_platform_status(self):
        """Test platform validation with mixed success/failure."""
        # Create mock clients
        mock_devto = Mock()
        mock_devto.get_articles.return_value = []

        mock_hashnode = Mock()
        mock_hashnode.get_articles.side_effect = AuthenticationError(
            "Auth failed", platform="hashnode"
        )

        publisher = PostPublisher.__new__(PostPublisher)
        publisher.platform_clients = {"devto": mock_devto, "hashnode": mock_hashnode}
        publisher.publication_manager = Mock()
        publisher.publication_manager.validate_platform_clients.return_value = {
            "devto": True,
            "hashnode": False,
        }

        results = publisher.validate_configuration()

        assert results["devto"] is True
        assert results["hashnode"] is False

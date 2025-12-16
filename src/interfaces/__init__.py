"""
Interfaces package for the multi-platform blog publishing system.
"""

from .platform_client import PlatformClient
from .content_processor import ContentProcessor

__all__ = ["PlatformClient", "ContentProcessor"]

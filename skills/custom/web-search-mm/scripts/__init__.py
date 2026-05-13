"""
Multimodal Search Tools Package

Features:
- ImageSearch: Search images by keyword
- VisualSearch: Reverse image search
- Image Description: Use vision model to describe images
- Image Download: Download and save images locally
"""

from .mm_tools import (
    # Classes
    MMSearchTools,
    MMSearchToolsWithVision,
    ImageDescriber,
    # Basic search functions
    image_search,
    visual_search,
    click_image,
    click_visual,
    # Vision-enabled functions
    describe_image,
    image_search_with_description,
    describe_search_result,
    # Image download functions
    download_image,
    get_downloaded_images,
    set_image_save_directory,
)

__all__ = [
    # Classes
    "MMSearchTools",
    "MMSearchToolsWithVision",
    "ImageDescriber",
    # Basic search functions
    "image_search",
    "visual_search",
    "click_image",
    "click_visual",
    # Vision-enabled functions
    "describe_image",
    "image_search_with_description",
    "describe_search_result",
    # Image download functions
    "download_image",
    "get_downloaded_images",
    "set_image_save_directory",
]

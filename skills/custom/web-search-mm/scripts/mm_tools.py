#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multimodal Search Tools - Image Search with Vision Model
Uses Serper for image search and OpenRouter for image understanding
"""

import os
import json
import base64
import hashlib
import requests
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime


class MMSearchTools:
    """Multimodal search tools using Serper API"""

    # Pre-configured API keys
    DEFAULT_SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

    def __init__(
        self,
        serper_api_key: Optional[str] = None
    ):
        """
        Initialize MMSearchTools

        Args:
            serper_api_key: Serper API key (default from env SERPER_API_KEY or built-in)
        """
        self.serper_api_key = serper_api_key or os.environ.get("SERPER_API_KEY") or self.DEFAULT_SERPER_API_KEY

        # Store last search results for click functionality
        self._last_image_results = []
        self._last_visual_results = []

    def image_search(
        self,
        query: str,
        num: int = 10,
        country: str = "cn",
        location: str = None
    ) -> str:
        """
        Search images by keyword using Serper API

        Args:
            query: Search query string
            num: Number of results (default: 10)
            country: Country code for search (default: cn)
            location: Location for search (optional)

        Returns:
            Formatted search results with numbered references
        """
        url = "https://google.serper.dev/images"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num,
            "gl": country
        }
        if location:
            payload["location"] = location

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._format_image_results(data)
        except Exception as e:
            return f"搜索失败: {str(e)}"

    def _format_image_results(self, response: dict) -> str:
        """Format image search results from Serper API"""
        results = []
        self._last_image_results = []

        images = response.get("images", [])

        for i, img in enumerate(images, 1):
            title = img.get("title", "Untitled")
            image_url = img.get("imageUrl", "")
            thumbnail = img.get("thumbnailUrl", "") or image_url
            source_url = img.get("link", "")
            width = img.get("imageWidth", 0)
            height = img.get("imageHeight", 0)

            # Store for click functionality
            self._last_image_results.append({
                "index": i,
                "title": title,
                "url": source_url,
                "image_url": image_url,
                "thumbnail": thumbnail,
                "width": width,
                "height": height,
                "source_page": source_url
            })

            size_str = f"{width}x{height}" if width and height else "unknown"
            result_str = f"【§{i}】Title: {title}。Size: {size_str}。Image: {thumbnail[:100]}...。Source: {source_url[:60]}..."
            results.append(result_str)

        if not results:
            return "No image results found."

        return "\n".join(results)

    def visual_search(
        self,
        image_url: str,
        num: int = 10
    ) -> str:
        """
        Search by image (reverse image search) using Serper API

        Args:
            image_url: URL of the image to search with
            num: Number of results (default: 10)

        Returns:
            Formatted search results with similar images
        """
        url = "https://google.serper.dev/images"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        # Use image URL as query for reverse search
        payload = {
            "q": f"site:* imageurl:{image_url}",
            "num": num
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            return self._format_visual_results(data)
        except Exception as e:
            return f"视觉搜索失败: {str(e)}"

    def _format_visual_results(self, response: dict) -> str:
        """Format visual search results"""
        results = []
        self._last_visual_results = []

        images = response.get("images", [])

        for i, img in enumerate(images, 1):
            title = img.get("title", "Similar Image")
            image_url = img.get("imageUrl", "")
            thumbnail = img.get("thumbnailUrl", "") or image_url
            source_url = img.get("link", "")
            width = img.get("imageWidth", 0)
            height = img.get("imageHeight", 0)

            self._last_visual_results.append({
                "index": i,
                "title": title,
                "url": source_url,
                "image_url": image_url,
                "thumbnail": thumbnail,
                "width": width,
                "height": height,
                "source_page": source_url
            })

            size_str = f"{width}x{height}" if width and height else "unknown"
            result_str = f"【§{i}】Title: {title}。Size: {size_str}。Image: {thumbnail[:100]}...。Source: {source_url[:60]}..."
            results.append(result_str)

        if not results:
            return "No similar images found."

        return "\n".join(results)

    def click_image(self, index: int) -> Dict[str, Any]:
        """
        Get details of an image search result by index

        Args:
            index: The reference number from search results (§1, §2, etc.)

        Returns:
            Dictionary with image details
        """
        if not self._last_image_results:
            return {"error": "No image search results available. Please search first."}

        for item in self._last_image_results:
            if item["index"] == index:
                return item

        return {"error": f"Index {index} not found in results. Valid range: 1-{len(self._last_image_results)}"}

    def click_visual(self, index: int) -> Dict[str, Any]:
        """
        Get details of a visual search result by index

        Args:
            index: The reference number from search results (§1, §2, etc.)

        Returns:
            Dictionary with image details
        """
        if not self._last_visual_results:
            return {"error": "No visual search results available. Please search first."}

        for item in self._last_visual_results:
            if item["index"] == index:
                return item

        return {"error": f"Index {index} not found in results. Valid range: 1-{len(self._last_visual_results)}"}

    def get_image_urls(self, indices: Optional[List[int]] = None) -> List[str]:
        """
        Get image URLs from last search results

        Args:
            indices: List of indices to get (default: all)

        Returns:
            List of image URLs
        """
        results = self._last_image_results or self._last_visual_results
        if not results:
            return []

        if indices is None:
            return [r.get("image_url") or r.get("thumbnail") for r in results]

        return [
            results[i-1].get("image_url") or results[i-1].get("thumbnail")
            for i in indices if 0 < i <= len(results)
        ]


# ===================== Convenience Functions =====================

# Global instance for simple usage
_tools = None

def _get_tools():
    global _tools
    if _tools is None:
        _tools = MMSearchTools()
    return _tools

def image_search(query: str, num: int = 10, **kwargs) -> str:
    """Search images by keyword"""
    return _get_tools().image_search(query, num, **kwargs)

def visual_search(image_url: str, **kwargs) -> str:
    """Search by image (reverse image search)"""
    return _get_tools().visual_search(image_url, **kwargs)

def click_image(index: int) -> Dict[str, Any]:
    """Get details of an image search result"""
    return _get_tools().click_image(index)

def click_visual(index: int) -> Dict[str, Any]:
    """Get details of a visual search result"""
    return _get_tools().click_visual(index)


# ===================== Image Describer =====================

class ImageDescriber:
    """Use vision-language model to describe images"""

    DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
    DEFAULT_VISION_MODEL = "openai/gpt-5.4-mini"

    # Default image save directory
    DEFAULT_IMAGE_DIR = "downloaded_images"

    # Supported image formats
    SUPPORTED_FORMATS = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp'
    }

    # MIME type to extension mapping
    MIME_TO_EXT = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'image/bmp': '.bmp'
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        image_save_dir: Optional[str] = None
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.api_base = api_base or os.environ.get("OPENROUTER_API_BASE", self.DEFAULT_API_BASE)
        self.model = model or os.environ.get("VISION_MODEL", self.DEFAULT_VISION_MODEL)
        self.image_save_dir = image_save_dir or self.DEFAULT_IMAGE_DIR

        # Track downloaded images
        self._downloaded_images: List[Dict[str, str]] = []

    def _get_save_path(self, image_url: str, mime_type: str) -> str:
        """Generate a unique save path for an image"""
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        ext = self.MIME_TO_EXT.get(mime_type, '.jpg')

        parsed = urlparse(image_url)
        original_name = os.path.basename(parsed.path)
        if original_name and '.' in original_name:
            name_part = os.path.splitext(original_name)[0][:20]
            filename = f"{name_part}_{url_hash}{ext}"
        else:
            filename = f"img_{timestamp}_{url_hash}{ext}"

        return os.path.join(self.image_save_dir, filename)

    def _download_image(self, image_url: str, save_to_disk: bool = True) -> Tuple[str, str, Optional[str]]:
        """
        Download image, convert to base64, and optionally save to disk

        Returns:
            Tuple of (base64_data, mime_type, local_path or None)
        """
        try:
            response = requests.get(
                image_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').split(';')[0].strip()

            if not content_type or content_type == 'application/octet-stream':
                parsed = urlparse(image_url)
                path = parsed.path.lower()
                for ext, mime in self.SUPPORTED_FORMATS.items():
                    if path.endswith(ext):
                        content_type = mime
                        break
                else:
                    content_type = 'image/jpeg'

            image_data = base64.b64encode(response.content).decode('utf-8')

            local_path = None
            if save_to_disk:
                local_path = self._save_image(response.content, image_url, content_type)

            return image_data, content_type, local_path

        except Exception as e:
            raise Exception(f"图片下载失败: {str(e)}")

    def _save_image(self, image_bytes: bytes, source_url: str, mime_type: str) -> str:
        """Save image bytes to local disk"""
        os.makedirs(self.image_save_dir, exist_ok=True)
        local_path = self._get_save_path(source_url, mime_type)

        with open(local_path, 'wb') as f:
            f.write(image_bytes)

        self._downloaded_images.append({
            "url": source_url,
            "local_path": os.path.abspath(local_path),
            "mime_type": mime_type,
            "size_bytes": len(image_bytes),
            "timestamp": datetime.now().isoformat()
        })

        return os.path.abspath(local_path)

    def download_image(self, image_url: str, custom_filename: Optional[str] = None) -> Dict[str, str]:
        """Download an image and save to disk (without describing)"""
        try:
            response = requests.get(
                image_url,
                timeout=30,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            response.raise_for_status()

            content_type = response.headers.get('Content-Type', '').split(';')[0].strip()
            if not content_type or content_type == 'application/octet-stream':
                content_type = 'image/jpeg'

            os.makedirs(self.image_save_dir, exist_ok=True)

            if custom_filename:
                local_path = os.path.join(self.image_save_dir, custom_filename)
            else:
                local_path = self._get_save_path(image_url, content_type)

            with open(local_path, 'wb') as f:
                f.write(response.content)

            result = {
                "url": image_url,
                "local_path": os.path.abspath(local_path),
                "mime_type": content_type,
                "size_bytes": len(response.content)
            }

            self._downloaded_images.append({
                **result,
                "timestamp": datetime.now().isoformat()
            })

            return result

        except Exception as e:
            return {"error": f"下载失败: {str(e)}", "url": image_url}

    def get_downloaded_images(self) -> List[Dict[str, str]]:
        """Get list of all downloaded images in this session"""
        return self._downloaded_images.copy()

    def set_save_directory(self, directory: str):
        """Set the directory for saving images"""
        self.image_save_dir = directory
        os.makedirs(directory, exist_ok=True)

    def describe(
        self,
        image_url: str,
        prompt: str = "请详细描述这张图片的内容，包括主要对象、场景、颜色、文字等信息。",
        save_to_disk: bool = True
    ) -> Dict[str, str]:
        """
        Use vision model to describe an image

        Returns:
            Dict with 'description', 'local_path' (if saved), 'url'
        """
        result = {
            "url": image_url,
            "local_path": None,
            "description": None,
            "error": None
        }

        try:
            image_base64, mime_type, local_path = self._download_image(image_url, save_to_disk)
            result["local_path"] = local_path

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data_url = f"data:{mime_type};base64,{image_base64}"

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }

            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            api_result = response.json()

            result["description"] = api_result.get("choices", [{}])[0].get("message", {}).get("content", "无法描述图片")
            return result

        except Exception as e:
            result["error"] = str(e)
            result["description"] = f"图片描述失败: {str(e)}"
            return result

    def describe_from_base64(self, image_base64: str, mime_type: str = "image/jpeg",
                             prompt: str = "请详细描述这张图片的内容，包括主要对象、场景、颜色、文字等信息。") -> str:
        """Describe an image from base64 data (skip download)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data_url = f"data:{mime_type};base64,{image_base64}"

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url}
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }

            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            return result.get("choices", [{}])[0].get("message", {}).get("content", "无法描述图片")

        except Exception as e:
            return f"图片描述失败: {str(e)}"

    def describe_batch(
        self,
        image_urls: List[str],
        prompt: str = None,
        save_to_disk: bool = True
    ) -> List[Dict[str, str]]:
        """Describe multiple images"""
        results = []
        for url in image_urls:
            if prompt:
                result = self.describe(url, prompt, save_to_disk)
            else:
                result = self.describe(url, save_to_disk=save_to_disk)
            results.append(result)
        return results


# ===================== MMSearchToolsWithVision =====================

class MMSearchToolsWithVision(MMSearchTools):
    """MMSearchTools with image description capability"""

    def __init__(self, *args, image_save_dir: str = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.describer = ImageDescriber(image_save_dir=image_save_dir)

    def set_image_save_directory(self, directory: str):
        """Set the directory for saving downloaded images"""
        self.describer.set_save_directory(directory)

    def get_downloaded_images(self) -> List[Dict[str, str]]:
        """Get list of all downloaded images"""
        return self.describer.get_downloaded_images()

    def download_image(self, image_url: str, filename: str = None) -> Dict[str, str]:
        """Download an image without describing it"""
        return self.describer.download_image(image_url, filename)

    def image_search_with_description(
        self,
        query: str,
        num: int = 5,
        describe_top_n: int = 3,
        save_images: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search images and describe top N results

        Returns:
            Dict with 'search_results' text, 'descriptions' list, 'downloaded_images' list
        """
        search_results = self.image_search(query, num, **kwargs)

        output = {
            "search_results": search_results,
            "descriptions": [],
            "downloaded_images": []
        }

        if describe_top_n > 0 and self._last_image_results:
            for i, item in enumerate(self._last_image_results[:describe_top_n], 1):
                img_url = item.get("image_url") or item.get("thumbnail")
                if img_url:
                    result = self.describer.describe(img_url, save_to_disk=save_images)
                    output["descriptions"].append({
                        "index": i,
                        "title": item.get("title", ""),
                        "description": result.get("description", ""),
                        "local_path": result.get("local_path"),
                        "url": img_url
                    })
                    if result.get("local_path"):
                        output["downloaded_images"].append(result["local_path"])

        return output

    def describe_image(
        self,
        image_url: str,
        prompt: str = None,
        save_to_disk: bool = True
    ) -> Dict[str, str]:
        """Describe a single image"""
        if prompt:
            return self.describer.describe(image_url, prompt, save_to_disk)
        return self.describer.describe(image_url, save_to_disk=save_to_disk)

    def describe_search_result(self, index: int, save_to_disk: bool = True) -> Dict[str, str]:
        """Describe an image from the last search results"""
        item = self.click_image(index)
        if "error" in item:
            return {"error": item["error"]}

        img_url = item.get("image_url") or item.get("thumbnail")
        if not img_url:
            return {"error": "无法获取图片URL"}

        result = self.describer.describe(img_url, save_to_disk=save_to_disk)
        result["title"] = item.get("title", "图片")
        return result


# ===================== Convenience Functions for Vision =====================

_vision_tools = None

def _get_vision_tools():
    global _vision_tools
    if _vision_tools is None:
        _vision_tools = MMSearchToolsWithVision()
    return _vision_tools

def set_image_save_directory(directory: str):
    """Set the directory for saving downloaded images"""
    _get_vision_tools().set_image_save_directory(directory)

def describe_image(image_url: str, prompt: str = None, save_to_disk: bool = True) -> Dict[str, str]:
    """Describe an image using vision model and optionally save to disk"""
    return _get_vision_tools().describe_image(image_url, prompt, save_to_disk)

def download_image(image_url: str, filename: str = None) -> Dict[str, str]:
    """Download an image without describing it"""
    return _get_vision_tools().download_image(image_url, filename)

def image_search_with_description(
    query: str,
    num: int = 5,
    describe_top_n: int = 3,
    save_images: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """Search images, describe top results, and save to disk"""
    return _get_vision_tools().image_search_with_description(query, num, describe_top_n, save_images, **kwargs)

def describe_search_result(index: int, save_to_disk: bool = True) -> Dict[str, str]:
    """Describe an image from last search results"""
    return _get_vision_tools().describe_search_result(index, save_to_disk)

def get_downloaded_images() -> List[Dict[str, str]]:
    """Get list of all downloaded images in this session"""
    return _get_vision_tools().get_downloaded_images()


if __name__ == "__main__":
    # Test the tools
    import sys

    test_save_dir = "./test_downloaded_images"
    tools = MMSearchToolsWithVision(image_save_dir=test_save_dir)

    # Test image search
    print("=== Image Search Test ===")
    results = tools.image_search("cute cat", num=5)
    print(results)

    # Test click
    print("\n=== Click Image Test ===")
    detail = tools.click_image(1)
    print(json.dumps(detail, indent=2, ensure_ascii=False))

    # Test describe with download
    print("\n=== Describe Image Test (with download) ===")
    img_url = detail.get("image_url") or detail.get("thumbnail")
    if img_url:
        result = tools.describe_image(img_url, save_to_disk=True)
        print(f"Description: {result.get('description', 'N/A')[:300]}...")
        print(f"Local path: {result.get('local_path', 'N/A')}")

    # Show all downloaded images
    print("\n=== All Downloaded Images ===")
    downloaded = tools.get_downloaded_images()
    for img in downloaded:
        print(f"  - {img.get('local_path')}")

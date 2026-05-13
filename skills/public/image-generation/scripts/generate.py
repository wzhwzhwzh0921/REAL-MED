#!/usr/bin/env python3
"""
Generate images using Gemini image models via OpenRouter (OpenAI-compatible API).

Supports structured JSON prompts and reference images for guided generation.
Used by the ppt-generation skill for slide image creation.

Usage:
    python generate.py --prompt-file prompt.json --output-file output.jpg [--reference-images ref1.jpg ref2.jpg] [--aspect-ratio 16:9]
"""

import argparse
import base64
import os
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image


def validate_image(image_path: str) -> bool:
    """Validate if an image file can be opened and is not corrupted."""
    try:
        with Image.open(image_path) as img:
            img.verify()
        with Image.open(image_path) as img:
            img.load()
        return True
    except Exception as e:
        print(f"Warning: Image '{image_path}' is invalid or corrupted: {e}")
        return False


def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_map.get(suffix, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def extract_image_from_response(content: str) -> bytes | None:
    """Try to extract base64 image data from model response text."""
    b64_patterns = [
        r'data:image/(?:png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)',
        r'!\[.*?\]\(data:image/(?:png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)\)',
    ]
    for pattern in b64_patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            b64_str = match.group(1).replace('\n', '').replace(' ', '').replace('\r', '')
            return base64.b64decode(b64_str)
    return None


def generate_image(
    prompt_file: str,
    reference_images: list[str],
    output_file: str,
    aspect_ratio: str = "16:9",
    model: str = "google/gemini-2.5-flash-preview:thinking",
    base_url: str = "https://openrouter.ai/api/v1",
) -> str:
    from openai import OpenAI

    # Read prompt from JSON file
    with open(prompt_file, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    # Get API key
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Error: No API key. Set OPENROUTER_API_KEY or GEMINI_API_KEY environment variable."

    # Filter valid reference images
    valid_refs = []
    for ref_img in reference_images:
        if validate_image(ref_img):
            valid_refs.append(ref_img)
        else:
            print(f"Skipping invalid reference image: {ref_img}")

    if len(valid_refs) < len(reference_images):
        print(f"Note: {len(reference_images) - len(valid_refs)} reference image(s) skipped due to validation failure.")

    # Initialize OpenRouter client
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Build user message content
    user_content = []

    # Add reference images
    for i, ref_path in enumerate(valid_refs, 1):
        img_b64, mime_type = encode_image_to_base64(ref_path)
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{img_b64}"
            }
        })
        print(f"  Reference image {i}: {ref_path}")

    # Add prompt text with aspect ratio hint
    user_content.append({
        "type": "text",
        "text": (
            f"Generate a high-quality image based on this specification. "
            f"Aspect ratio: {aspect_ratio}. "
            f"Return the image directly.\n\n"
            f"Specification:\n{prompt_text}"
        )
    })

    messages = [
        {
            "role": "system",
            "content": (
                "You are an image generation assistant. Generate the requested image based on the "
                "specification provided. If reference images are provided, use them for style and "
                "composition guidance. Return the image directly in your response."
            )
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

    print(f"Generating image (model={model}, aspect_ratio={aspect_ratio})...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
        )
    except Exception as e:
        return f"Error calling API: {e}"

    # Extract image from response
    choice = response.choices[0]
    content = choice.message.content
    image_saved = False

    if content:
        img_data = extract_image_from_response(content)
        if img_data:
            image = Image.open(BytesIO(img_data))
            # Ensure output directory exists
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)
            # Save as appropriate format
            if output_file.lower().endswith('.png'):
                if image.mode == 'RGBA':
                    image.save(output_file, 'PNG')
                else:
                    image.convert('RGB').save(output_file, 'PNG')
            else:
                image.convert('RGB').save(output_file, 'JPEG', quality=95)
            image_saved = True

    # Also check structured content (some providers return list content)
    if not image_saved and hasattr(choice.message, 'content') and isinstance(choice.message.content, list):
        for part in choice.message.content:
            if isinstance(part, dict):
                if part.get("type") == "image_url":
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        b64_str = url.split(",", 1)[1]
                        img_data = base64.b64decode(b64_str)
                        image = Image.open(BytesIO(img_data))
                        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
                        if output_file.lower().endswith('.png'):
                            image.save(output_file, 'PNG')
                        else:
                            image.convert('RGB').save(output_file, 'JPEG', quality=95)
                        image_saved = True
                        break

    if image_saved:
        return f"Successfully generated image to {output_file}"
    else:
        # Save text response for debugging
        if content:
            debug_path = Path(output_file).with_suffix('.debug.txt')
            debug_path.write_text(content[:2000])
            print(f"Debug: Model text response saved to {debug_path}")
        return (
            f"Error: No image found in model response. "
            f"The model ({model}) may not support image output via this API. "
            f"Try: google/gemini-2.5-flash-preview:thinking or google/gemini-2.5-pro-preview"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate images via OpenRouter (Gemini image models)")
    parser.add_argument(
        "--prompt-file",
        required=True,
        help="Absolute path to JSON prompt file",
    )
    parser.add_argument(
        "--reference-images",
        nargs="*",
        default=[],
        help="Absolute paths to reference images (space-separated)",
    )
    parser.add_argument(
        "--output-file",
        required=True,
        help="Output path for generated image",
    )
    parser.add_argument(
        "--aspect-ratio",
        required=False,
        default="16:9",
        help="Aspect ratio of the generated image (default: 16:9)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (default: google/gemini-2.5-flash-preview:thinking)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="API base URL (default: https://openrouter.ai/api/v1)",
    )

    args = parser.parse_args()

    model = args.model or os.getenv("IMAGE_GEN_MODEL", "google/gemini-2.5-flash-preview:thinking")
    base_url = args.base_url or os.getenv("IMAGE_GEN_BASE_URL", "https://openrouter.ai/api/v1")

    try:
        result = generate_image(
            args.prompt_file,
            args.reference_images,
            args.output_file,
            args.aspect_ratio,
            model=model,
            base_url=base_url,
        )
        print(result)
        if result.startswith("Error"):
            sys.exit(1)
    except Exception as e:
        print(f"Error while generating image: {e}")
        sys.exit(1)

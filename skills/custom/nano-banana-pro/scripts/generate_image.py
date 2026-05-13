#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Generate images using Nano Banana Pro (Gemini 3 Pro Image) via OpenRouter.

Usage:
    uv run generate_image.py --prompt "your image description" --filename "output.png" [--resolution 1K|2K|4K] [--api-key KEY]
"""

import argparse
import base64
import os
import sys
from io import BytesIO
from pathlib import Path


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("OPENROUTER_API_KEY") or os.environ.get("GEMINI_API_KEY")


def encode_image_to_base64(image_path: str) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    from PIL import Image as PILImage

    path = Path(image_path)
    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/png")

    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def main():
    parser = argparse.ArgumentParser(
        description="Generate images using Nano Banana Pro (Gemini 3 Pro Image) via OpenRouter"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="Image description/prompt"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="Output filename (e.g., sunset-mountains.png)"
    )
    parser.add_argument(
        "--input-image", "-i",
        help="Optional input image path for editing/modification"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="1K",
        help="Output resolution: 1K (default), 2K, or 4K"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="OpenRouter API key (overrides OPENROUTER_API_KEY env var)"
    )
    parser.add_argument(
        "--base-url",
        default="https://openrouter.ai/api/v1",
        help="API base URL (default: OpenRouter)"
    )
    parser.add_argument(
        "--model",
        default="google/gemini-2.5-flash-preview:thinking",
        help="Model to use for image generation"
    )

    args = parser.parse_args()

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("Please either:", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set OPENROUTER_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    from openai import OpenAI
    from PIL import Image as PILImage

    # Initialize OpenRouter client
    client = OpenAI(
        api_key=api_key,
        base_url=args.base_url,
    )

    # Set up output path
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolution hint for the prompt
    resolution_map = {"1K": "1024x1024", "2K": "2048x2048", "4K": "4096x4096"}
    resolution_hint = resolution_map.get(args.resolution, "1024x1024")

    # Build messages
    messages = []

    # System message requesting image generation
    messages.append({
        "role": "system",
        "content": (
            "You are an image generation assistant. Generate the requested image. "
            f"Target resolution: {resolution_hint}. "
            "Return the image directly in your response."
        )
    })

    # User message with optional input image
    if args.input_image:
        input_path = Path(args.input_image)
        if not input_path.exists():
            print(f"Error: Input image not found: {args.input_image}", file=sys.stderr)
            sys.exit(1)

        img_b64, mime_type = encode_image_to_base64(args.input_image)
        print(f"Loaded input image: {args.input_image}")

        # Auto-detect resolution
        if args.resolution == "1K":
            img = PILImage.open(args.input_image)
            width, height = img.size
            max_dim = max(width, height)
            if max_dim >= 3000:
                resolution_hint = "4096x4096"
            elif max_dim >= 1500:
                resolution_hint = "2048x2048"
            print(f"Auto-detected resolution from input: {max_dim}px -> {resolution_hint}")

        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{img_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": f"Edit this image: {args.prompt}"
                }
            ]
        })
        print(f"Editing image with resolution {args.resolution}...")
    else:
        messages.append({
            "role": "user",
            "content": f"Generate an image: {args.prompt}"
        })
        print(f"Generating image with resolution {args.resolution}...")

    try:
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            max_tokens=4096,
        )

        # Process response - look for image content
        image_saved = False
        choice = response.choices[0]
        content = choice.message.content

        if content:
            # Check if response contains base64 image data
            # Some models return images as markdown: ![...](data:image/png;base64,...)
            # Or as plain base64 blocks
            import re

            # Try to find base64 image in markdown format
            b64_patterns = [
                r'data:image/(?:png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)',
                r'!\[.*?\]\(data:image/(?:png|jpeg|jpg|webp);base64,([A-Za-z0-9+/=\s]+)\)',
            ]

            for pattern in b64_patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    img_data = base64.b64decode(match.group(1).replace('\n', '').replace(' ', ''))
                    image = PILImage.open(BytesIO(img_data))

                    if image.mode == 'RGBA':
                        rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
                        rgb_image.paste(image, mask=image.split()[3])
                        rgb_image.save(str(output_path), 'PNG')
                    elif image.mode == 'RGB':
                        image.save(str(output_path), 'PNG')
                    else:
                        image.convert('RGB').save(str(output_path), 'PNG')
                    image_saved = True
                    break

            if not image_saved:
                # If no embedded image, print text response
                print(f"Model response: {content}")

        # Also check for multi-part content (some providers return structured content)
        if not image_saved and hasattr(choice.message, 'content') and isinstance(choice.message.content, list):
            for part in choice.message.content:
                if isinstance(part, dict):
                    if part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:"):
                            b64_str = url.split(",", 1)[1]
                            img_data = base64.b64decode(b64_str)
                            image = PILImage.open(BytesIO(img_data))
                            image.save(str(output_path), 'PNG')
                            image_saved = True
                            break

        if image_saved:
            full_path = output_path.resolve()
            print(f"\nImage saved: {full_path}")
        else:
            print("Warning: No image found in model response. The model may not support image generation.", file=sys.stderr)
            print("Try using a model that supports image output (e.g., google/gemini-2.5-flash-preview:thinking).", file=sys.stderr)
            # Save the text response for debugging
            if content:
                text_path = output_path.with_suffix('.txt')
                text_path.write_text(content)
                print(f"Text response saved to: {text_path}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error generating image: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

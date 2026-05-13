"""Render submitted artifacts (pptx / docx / pdf) into PNG images for the
image-rubric vision judge.

Idempotent: caches outputs under `<run_dir>/rendered/` and a `_manifest.json`.
Re-run only if `force=True` or the source file mtime is newer than the manifest.

External deps:
- `soffice` (LibreOffice headless) on PATH    — pptx/docx → pdf
- `pdftoppm` (poppler-utils) on PATH          — pdf → page PNGs
- python: zipfile (stdlib) for docx embedded images

CLI:
    python scripts/render_artifacts.py <run_dir>
    python scripts/render_artifacts.py <run_dir> --force --dpi 144
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

DEFAULT_DPI = 144
SUPPORTED_RENDER = {".pptx", ".docx", ".pdf"}
SUPPORTED_EMBED = {".docx"}


def _which_or_die(binary: str) -> str:
    p = shutil.which(binary)
    if not p:
        raise RuntimeError(
            f"Required binary `{binary}` not found on PATH. "
            f"Install LibreOffice (soffice) and poppler-utils (pdftoppm)."
        )
    return p


def _soffice_to_pdf(src: Path, out_dir: Path) -> Path:
    """Convert pptx/docx → pdf in `out_dir`. Returns pdf path.

    Uses an isolated UserInstallation so concurrent calls don't collide
    on the LibreOffice profile lock.
    """
    soffice = _which_or_die("soffice")
    out_dir.mkdir(parents=True, exist_ok=True)
    user_profile = tempfile.mkdtemp(prefix="lo_")
    try:
        cmd = [
            soffice,
            f"-env:UserInstallation=file://{user_profile}",
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to", "pdf",
            "--outdir", str(out_dir),
            str(src),
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    finally:
        shutil.rmtree(user_profile, ignore_errors=True)
    pdf_path = out_dir / (src.stem + ".pdf")
    if not pdf_path.exists():
        raise RuntimeError(f"soffice did not produce {pdf_path} from {src}")
    return pdf_path


def _pdf_to_pngs(pdf: Path, out_dir: Path, dpi: int, prefix: str) -> list[str]:
    """pdf → page_001.png, page_002.png, ... in out_dir. Returns sorted filenames."""
    pdftoppm = _which_or_die("pdftoppm")
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [pdftoppm, "-png", "-r", str(dpi), str(pdf), str(out_dir / prefix)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=300)
    pngs = sorted(p.name for p in out_dir.glob(f"{prefix}-*.png"))
    # Normalize to zero-padded 3-digit names: page-1.png → page_001.png
    normalized: list[str] = []
    for name in pngs:
        stem = name[len(prefix) + 1 : -4]  # strip prefix- and .png
        idx = int(stem)
        new_name = f"{prefix}_{idx:03d}.png"
        (out_dir / name).rename(out_dir / new_name)
        normalized.append(new_name)
    return sorted(normalized)


def _extract_docx_embedded(docx: Path, out_dir: Path) -> list[str]:
    """Extract `word/media/*` from a docx zip. Returns saved filenames."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    with zipfile.ZipFile(docx) as zf:
        for info in zf.infolist():
            if not info.filename.startswith("word/media/"):
                continue
            name = Path(info.filename).name
            if not name:
                continue
            target = out_dir / name
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
            saved.append(name)
    return sorted(saved)


def _render_pptx(src: Path, dest: Path, dpi: int) -> dict:
    """pptx → slide_001.png, slide_002.png, ..."""
    with tempfile.TemporaryDirectory(prefix="render_pptx_") as td:
        pdf = _soffice_to_pdf(src, Path(td))
        slides = _pdf_to_pngs(pdf, dest, dpi=dpi, prefix="slide")
    return {"slides": slides, "page_count": len(slides)}


def _render_docx(src: Path, dest: Path, dpi: int) -> dict:
    """docx → page_001.png + embedded/ (extracted images)."""
    with tempfile.TemporaryDirectory(prefix="render_docx_") as td:
        pdf = _soffice_to_pdf(src, Path(td))
        pages = _pdf_to_pngs(pdf, dest, dpi=dpi, prefix="page")
    embedded_dir = dest / "embedded"
    embedded = _extract_docx_embedded(src, embedded_dir)
    return {"pages": pages, "embedded": embedded, "page_count": len(pages)}


def _render_pdf(src: Path, dest: Path, dpi: int) -> dict:
    pages = _pdf_to_pngs(src, dest, dpi=dpi, prefix="page")
    return {"pages": pages, "page_count": len(pages)}


_RENDERERS = {
    ".pptx": _render_pptx,
    ".docx": _render_docx,
    ".pdf": _render_pdf,
}


def render_run(run_dir: Path, force: bool = False, dpi: int = DEFAULT_DPI) -> dict:
    """Render every accepted artifact under `<run_dir>/outputs/` to PNGs.

    Returns the manifest dict and writes it to `<run_dir>/rendered/_manifest.json`.

    Manifest schema:
    {
      "dpi": 144,
      "rendered_at": <epoch>,
      "files": {
        "答题.pptx":  {"kind": "pptx", "slides": ["slide_001.png", ...]},
        "综述.docx":  {"kind": "docx", "pages":  ["page_001.png",  ...],
                                       "embedded": ["image1.png", ...]},
        "report.pdf": {"kind": "pdf",  "pages":  ["page_001.png",  ...]}
      }
    }
    """
    outputs_dir = run_dir / "outputs"
    rendered_dir = run_dir / "rendered"
    manifest_path = rendered_dir / "_manifest.json"

    if not outputs_dir.exists():
        return {"dpi": dpi, "files": {}, "note": "no outputs dir"}

    # Check cache
    if manifest_path.exists() and not force:
        try:
            cached = json.loads(manifest_path.read_text(encoding="utf-8"))
            cache_mtime = manifest_path.stat().st_mtime
            stale = any(
                (outputs_dir / fname).exists()
                and (outputs_dir / fname).stat().st_mtime > cache_mtime
                for fname in cached.get("files", {})
            )
            if not stale:
                return cached
        except Exception:
            pass  # fall through and re-render

    rendered_dir.mkdir(parents=True, exist_ok=True)

    files_manifest: dict[str, dict] = {}
    for src in sorted(outputs_dir.iterdir()):
        if not src.is_file():
            continue
        suffix = src.suffix.lower()
        if suffix not in _RENDERERS:
            continue
        dest = rendered_dir / src.stem
        if dest.exists() and force:
            shutil.rmtree(dest)
        try:
            info = _RENDERERS[suffix](src, dest, dpi)
            info["kind"] = suffix.lstrip(".")
            info["source"] = src.name
            files_manifest[src.name] = info
        except Exception as exc:  # keep going on per-file failure
            files_manifest[src.name] = {"kind": suffix.lstrip("."), "error": str(exc)}

    manifest = {
        "dpi": dpi,
        "rendered_at": int(time.time()),
        "files": files_manifest,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return manifest


def collect_images_for_targets(run_dir: Path, image_targets: list[str],
                               max_images: int | None = None) -> list[Path]:
    """Given image_targets like ['pptx_slides'], return absolute PNG paths.

    image_targets vocabulary:
      - pptx_slides            → all slide_*.png from any rendered pptx
      - docx_pages             → all page_*.png from any rendered docx
      - docx_embedded_images   → all files under any docx's embedded/
      - pdf_pages              → all page_*.png from any rendered pdf
      - any_rendered           → union of all above
    """
    rendered_dir = run_dir / "rendered"
    manifest_path = rendered_dir / "_manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    want = set(image_targets)
    if "any_rendered" in want:
        want = {"pptx_slides", "docx_pages", "docx_embedded_images", "pdf_pages"}

    out: list[Path] = []
    for fname, info in manifest.get("files", {}).items():
        kind = info.get("kind")
        base = rendered_dir / Path(fname).stem
        if kind == "pptx" and "pptx_slides" in want:
            out += [base / s for s in info.get("slides", [])]
        elif kind == "docx":
            if "docx_pages" in want:
                out += [base / s for s in info.get("pages", [])]
            if "docx_embedded_images" in want:
                out += [base / "embedded" / s for s in info.get("embedded", [])]
        elif kind == "pdf" and "pdf_pages" in want:
            out += [base / s for s in info.get("pages", [])]

    out = [p for p in out if p.exists()]
    if max_images is not None and len(out) > max_images:
        # Uniform sampling — keep first, last, evenly spaced in between.
        step = (len(out) - 1) / (max_images - 1) if max_images > 1 else 1
        out = [out[round(i * step)] for i in range(max_images)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    args = ap.parse_args()

    manifest = render_run(args.run_dir, force=args.force, dpi=args.dpi)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

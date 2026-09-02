"""Responsive image processing for uploads.

Best-effort: images PIL cannot decode are left untouched and only get the
base metadata, so uploads never hard-fail because of an exotic container.
"""

import os

from PIL import Image

#: variant name -> longest edge in pixels
VARIANTS = {"lg": 1280, "md": 640, "sm": 320, "thumb": 128}

#: formats we understand well enough to re-encode into variants
_RASTER_FORMATS = {"JPEG", "PNG", "WEBP", "BMP", "TIFF"}


def _variant_url(stored_name: str, variant: str, ext: str) -> str:
    stem = os.path.splitext(stored_name)[0]
    return f"/uploads/{stem}.{variant}.{ext}"


def generate_variants(upload_dir: str, stored_name: str) -> dict:
    """Return ``{"width", "height", "dimensions", "variants"}`` for an image.

    Variants are written next to the original as ``<stem>.<variant>.<ext>``
    (``.jpg`` unless the source has transparency, then ``.png``). The original
    is re-encoded without its EXIF block when it is a JPEG. Any failure for a
    specific image degrades to the base metadata with no variants.
    """
    path = os.path.join(upload_dir, stored_name)
    result = {"width": None, "height": None, "dimensions": "", "variants": {}}
    try:
        with Image.open(path) as im:
            im.load()
            fmt = (im.format or "").upper()
            if fmt not in _RASTER_FORMATS:
                return result
            width, height = im.size
            result["width"] = width
            result["height"] = height
            result["dimensions"] = f"{width}x{height}"
            has_alpha = "A" in im.getbands() or fmt in ("PNG",)
            variant_ext = "png" if has_alpha else "jpg"
            stem = os.path.splitext(stored_name)[0]
            for name, longest_edge in VARIANTS.items():
                canvas = im.copy()
                canvas.thumbnail((longest_edge, longest_edge), Image.LANCZOS)
                target = os.path.join(upload_dir, f"{stem}.{name}.{variant_ext}")
                if variant_ext == "png":
                    canvas.save(target, format="PNG", optimize=True)
                else:
                    canvas.convert("RGB").save(
                        target,
                        format="JPEG",
                        quality=82,
                        optimize=True,
                        progressive=True,
                    )
                result["variants"][name] = _variant_url(stored_name, name, variant_ext)
            if fmt == "JPEG":
                # Rewrite the stored original without EXIF.
                im.convert("RGB").save(
                    path, format="JPEG", quality=85, optimize=True, progressive=True
                )
    except Exception:
        # Unsupported / truncated / fake test payloads: keep the raw file.
        result["width"] = None
        result["height"] = None
        result["dimensions"] = ""
        result["variants"] = {}
    return result


def resolve_variant_media(upload_dir: str, filename: str, size: str | None) -> str:
    """Map ``filename?size=lg|md|sm|thumb`` onto a generated variant file.

    Returns the original path when the requested variant does not exist so
    legacy uploads and unknown sizes degrade gracefully.
    """
    original = os.path.join(upload_dir, filename)
    if size not in VARIANTS:
        return original
    stem, _ext = os.path.splitext(filename)
    for ext in ("jpg", "png"):
        candidate = os.path.join(upload_dir, f"{stem}.{size}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return original
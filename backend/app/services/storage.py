"""Image upload handling with content-type and magic-byte checks."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile

from .. import config

ALLOWED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAGIC = {
    ".jpg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
}


def _looks_right(data: bytes, ext: str) -> bool:
    if ext == ".webp":
        return len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return any(data.startswith(prefix) for prefix in MAGIC.get(ext, ()))


def save_image(upload: UploadFile | None) -> str | None:
    if upload is None or not upload.filename:
        return None

    content_type = (upload.content_type or "").lower()
    ext = ALLOWED.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG or WebP images are allowed.",
        )

    data = upload.file.read(config.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image is too large (max {config.MAX_UPLOAD_MB} MB).",
        )
    if not _looks_right(data, ext):
        raise HTTPException(status_code=400, detail="File contents are not a valid image.")

    name = f"{uuid4().hex}{ext}"
    (config.UPLOAD_DIR / name).write_bytes(data)
    return f"/uploads/{name}"


def delete_image(image_url: str | None) -> None:
    if not image_url or not image_url.startswith("/uploads/"):
        return
    name = Path(image_url).name
    target = (config.UPLOAD_DIR / name).resolve()
    if target.parent != config.UPLOAD_DIR.resolve():
        return
    target.unlink(missing_ok=True)

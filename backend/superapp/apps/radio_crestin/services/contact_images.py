"""Turns an uploaded file into a safe image, or says why it can't.

Only JPEG, PNG and WebP are read, and the pixels are always re-encoded: the
stored file never holds the uploaded bytes, so no metadata (GPS), scripts or
polyglot payloads survive. Header sizes are checked before decoding, so a
decompression bomb is refused without being loaded.
"""
import io
from dataclasses import dataclass

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 40_000_000
MAX_SIDE = 2000
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class ImageRejected(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass
class CleanImage:
    content: ContentFile
    width: int
    height: int


def clean_image(upload) -> CleanImage:
    if upload.size > MAX_UPLOAD_BYTES:
        raise ImageRejected('file_too_large')
    _check_header(upload)
    return _reencode(upload)


def _check_header(upload):
    try:
        upload.seek(0)
        with Image.open(upload) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise ImageRejected('unsupported_image')
            width, height = probe.size
            if width * height > MAX_PIXELS:
                raise ImageRejected('image_too_large_dimensions')
            probe.verify()
    except ImageRejected:
        raise
    except Exception:  # Pillow raises many types for a broken file.
        raise ImageRejected('unsupported_image')


def _reencode(upload) -> CleanImage:
    try:
        upload.seek(0)
        with Image.open(upload) as image:
            image.load()
            image = ImageOps.exif_transpose(image)
            has_alpha = image.mode in ('RGBA', 'LA', 'PA') or 'transparency' in image.info
            image = image.convert('RGBA' if has_alpha else 'RGB')
            image.thumbnail((MAX_SIDE, MAX_SIDE))
            buffer = io.BytesIO()
            if has_alpha:
                image.save(buffer, format='PNG', optimize=True)
                extension = 'png'
            else:
                image.save(buffer, format='JPEG', quality=88, optimize=True)
                extension = 'jpg'
            return CleanImage(ContentFile(buffer.getvalue(), name=f'upload.{extension}'), *image.size)
    except Exception:
        raise ImageRejected('unsupported_image')

"""Strict inspection for the small raster formats accepted by the publisher."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from .errors import ValidationError

MAX_IMAGE_BYTES = 1_500_000
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = 12_000_000


@dataclass(frozen=True)
class RasterInfo:
    media_type: str
    extension: str
    width: int
    height: int


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    position = 2
    while position + 4 <= len(data):
        if data[position] != 0xFF:
            raise ValidationError("JPEG marker stream is invalid")
        while position < len(data) and data[position] == 0xFF:
            position += 1
        if position >= len(data):
            break
        marker = data[position]
        position += 1
        if marker in {0xD8, 0xD9}:
            continue
        if position + 2 > len(data):
            break
        length = int.from_bytes(data[position : position + 2], "big")
        if length < 2 or position + length > len(data):
            raise ValidationError("JPEG segment is invalid")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if length < 7:
                raise ValidationError("JPEG frame is invalid")
            return (
                int.from_bytes(data[position + 5 : position + 7], "big"),
                int.from_bytes(data[position + 3 : position + 5], "big"),
            )
        position += length
    raise ValidationError("JPEG has no supported frame header")


def _webp_dimensions(data: bytes) -> tuple[int, int]:
    position = 12
    dimensions: tuple[int, int] | None = None
    canvas: tuple[int, int] | None = None
    image_chunks = 0
    while position + 8 <= len(data):
        chunk = data[position : position + 4]
        length = int.from_bytes(data[position + 4 : position + 8], "little")
        payload_start = position + 8
        payload_end = payload_start + length
        padded_end = payload_end + (length % 2)
        if payload_end > len(data) or padded_end > len(data):
            raise ValidationError("WebP chunk is invalid")
        payload = data[payload_start:payload_end]
        if chunk in {b"ANIM", b"ANMF"}:
            raise ValidationError("animated WebP is not accepted")
        if chunk == b"VP8X":
            if length == 10 and payload[0] & 0x02:
                raise ValidationError("animated WebP is not accepted")
            if length != 10 or canvas is not None:
                raise ValidationError("WebP extended header is invalid")
            canvas = (
                1 + int.from_bytes(payload[4:7], "little"),
                1 + int.from_bytes(payload[7:10], "little"),
            )
        elif chunk == b"VP8 ":
            if length < 10 or payload[3:6] != b"\x9d\x01\x2a":
                raise ValidationError("WebP lossy frame is invalid")
            dimensions = (
                int.from_bytes(payload[6:8], "little") & 0x3FFF,
                int.from_bytes(payload[8:10], "little") & 0x3FFF,
            )
            image_chunks += 1
        elif chunk == b"VP8L":
            if length < 5 or payload[0] != 0x2F:
                raise ValidationError("WebP lossless frame is invalid")
            bits = int.from_bytes(payload[1:5], "little")
            dimensions = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
            image_chunks += 1
        position = padded_end
    if position != len(data) or image_chunks != 1 or dimensions is None:
        raise ValidationError("WebP structure is incomplete")
    if canvas is not None and canvas != dimensions:
        raise ValidationError("WebP canvas and frame dimensions differ")
    return canvas or dimensions


def _png_dimensions(data: bytes) -> tuple[int, int]:
    position = 8
    chunks = 0
    dimensions: tuple[int, int] | None = None
    saw_end = False
    while position + 12 <= len(data) and chunks < 4096:
        length = int.from_bytes(data[position : position + 4], "big")
        chunk_type = data[position + 4 : position + 8]
        end = position + 12 + length
        if length > MAX_IMAGE_BYTES or end > len(data):
            raise ValidationError("PNG chunk is invalid")
        payload = data[position + 8 : position + 8 + length]
        expected_crc = int.from_bytes(data[position + 8 + length : end], "big")
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise ValidationError("PNG chunk checksum is invalid")
        if chunks == 0:
            if chunk_type != b"IHDR" or length != 13:
                raise ValidationError("PNG IHDR is invalid")
            dimensions = struct.unpack(">II", payload[:8])
        if chunk_type == b"acTL":
            raise ValidationError("animated PNG is not accepted")
        if chunk_type == b"IEND":
            if length != 0 or end != len(data):
                raise ValidationError("PNG ending is invalid")
            saw_end = True
            break
        position = end
        chunks += 1
    if dimensions is None or not saw_end:
        raise ValidationError("PNG structure is incomplete")
    return dimensions


def inspect_raster(data: bytes, content_type: str) -> RasterInfo:
    if not 1 <= len(data) <= MAX_IMAGE_BYTES:
        raise ValidationError("image size is outside its bound")
    declared = content_type.split(";", 1)[0].strip().lower()
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        info = RasterInfo("image/png", "png", *_png_dimensions(data))
    elif data.startswith(b"\xff\xd8"):
        if not data.endswith(b"\xff\xd9"):
            raise ValidationError("JPEG ending is invalid")
        info = RasterInfo("image/jpeg", "jpg", *_jpeg_dimensions(data))
    elif len(data) >= 30 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        declared_size = int.from_bytes(data[4:8], "little") + 8
        if declared_size != len(data):
            raise ValidationError("WebP RIFF size is invalid")
        info = RasterInfo("image/webp", "webp", *_webp_dimensions(data))
    else:
        raise ValidationError("image format is unsupported")
    if declared != info.media_type:
        raise ValidationError("image Content-Type does not match its bytes")
    if not 1 <= info.width <= MAX_IMAGE_DIMENSION or not 1 <= info.height <= MAX_IMAGE_DIMENSION:
        raise ValidationError("image dimensions are outside their bound")
    if info.width * info.height > MAX_IMAGE_PIXELS:
        raise ValidationError("image pixel count exceeds its bound")
    return info

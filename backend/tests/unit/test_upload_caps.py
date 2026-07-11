# =============================================================================
# Stratum AI - Upload size cap tests (API-001)
# =============================================================================
"""
Uploads must be bounded so a large body can't OOM the process. read_upload_capped
streams and aborts with 413 past the cap; enforce_content_length rejects early on
the declared header.
"""

import io

import pytest
from fastapi import HTTPException

from app.core.uploads import (
    MAX_CSV_UPLOAD_BYTES,
    enforce_content_length,
    read_upload_capped,
)

pytestmark = pytest.mark.unit


class _FakeUpload:
    """Minimal UploadFile stand-in with an async chunked read()."""

    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    async def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)


@pytest.mark.asyncio
async def test_reads_small_upload_fully():
    data = b"x" * 1000
    out = await read_upload_capped(_FakeUpload(data), max_bytes=1_000_000)
    assert out == data


@pytest.mark.asyncio
async def test_rejects_upload_over_cap():
    data = b"y" * (2 * 1024 * 1024)  # 2 MiB
    with pytest.raises(HTTPException) as exc:
        await read_upload_capped(_FakeUpload(data), max_bytes=1024 * 1024)  # 1 MiB
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_reads_exactly_at_cap():
    data = b"z" * 1024
    out = await read_upload_capped(_FakeUpload(data), max_bytes=1024)
    assert out == data


def test_enforce_content_length_rejects_declared_oversize():
    with pytest.raises(HTTPException) as exc:
        enforce_content_length(str(MAX_CSV_UPLOAD_BYTES + 1), MAX_CSV_UPLOAD_BYTES)
    assert exc.value.status_code == 413


def test_enforce_content_length_allows_under_and_missing():
    enforce_content_length(str(MAX_CSV_UPLOAD_BYTES - 1), MAX_CSV_UPLOAD_BYTES)
    enforce_content_length(None, MAX_CSV_UPLOAD_BYTES)
    enforce_content_length("not-a-number", MAX_CSV_UPLOAD_BYTES)  # ignored

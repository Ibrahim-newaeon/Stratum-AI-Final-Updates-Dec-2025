# =============================================================================
# Stratum AI - Upload size guards (API-001)
# =============================================================================
"""
Helpers to bound request-body size on file-upload endpoints.

Reading an UploadFile with ``await file.read()`` loads the WHOLE body into
memory before any size check runs, so a large (or malicious) upload can OOM the
process before the cap is enforced. ``read_upload_capped`` streams in chunks and
aborts with 413 the moment the cap is exceeded, and ``enforce_content_length``
rejects early on the declared header.
"""

from fastapi import HTTPException, UploadFile, status

UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MiB

# Default cap for CSV data imports (products / COGS / training data).
MAX_CSV_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MiB


def _too_large(max_bytes: int) -> str:
    return f"File too large. Maximum size is {max_bytes // (1024 * 1024)}MB."


def enforce_content_length(content_length: str | None, max_bytes: int) -> None:
    """Reject early (413) when the declared Content-Length exceeds max_bytes.

    A cheap pre-check before touching the body. The streaming cap in
    read_upload_capped is the real guard (a client can lie about Content-Length).
    """
    if not content_length:
        return
    try:
        declared = int(content_length)
    except ValueError:
        return
    if declared > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=_too_large(max_bytes),
        )


async def read_upload_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read an UploadFile fully, but abort with 413 once max_bytes is exceeded.

    Streams in UPLOAD_CHUNK_SIZE chunks so an oversized upload is rejected
    without ever holding more than max_bytes (+one chunk) in memory.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=_too_large(max_bytes),
            )
        chunks.append(chunk)
    return b"".join(chunks)

# =============================================================================
# Stratum AI - Object Storage Abstraction (INF-001)
# =============================================================================
"""
Pluggable object storage for uploaded assets.

The container filesystem on Railway is ephemeral — anything written to local
disk is wiped on every redeploy/restart, so asset files vanish while their DB
records (and file_url) survive, leaving broken links. This module abstracts
persistence behind ``ObjectStorage.save`` with two backends:

- ``LocalObjectStorage`` — writes under ``settings.asset_upload_dir`` and returns
  a ``/uploads/assets/...`` path served by the static mount. Durable ONLY when
  that path is a mounted persistent volume.
- ``S3ObjectStorage`` — streams to an S3-compatible bucket (AWS S3 or Cloudflare
  R2) via aioboto3. Durable across restarts; the natural production choice.

Select the backend with ``settings.asset_storage_backend`` ("local" | "s3").
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageError(Exception):
    """Raised when an object cannot be persisted to the configured backend."""


class ObjectStorage(ABC):
    """Backend-agnostic object storage interface."""

    @abstractmethod
    async def save(self, key: str, data: bytes, content_type: str) -> str:
        """Persist ``data`` under ``key`` and return a URL to retrieve it.

        ``key`` is a relative, forward-slash path such as
        ``"assets/<tenant>/<uuid>.png"``. Implementations must treat it as
        untrusted and refuse to escape their root.
        """
        raise NotImplementedError


def _reject_traversal(key: str) -> None:
    """Guard against path traversal in an object key."""
    if not key or key.startswith("/") or "\\" in key:
        raise StorageError(f"Invalid object key: {key!r}")
    parts = key.split("/")
    if any(p in ("", ".", "..") for p in parts) or any("\x00" in p for p in parts):
        raise StorageError(f"Invalid object key: {key!r}")


class LocalObjectStorage(ObjectStorage):
    """Filesystem-backed storage (dev default / Railway volume)."""

    # Public URL prefix — the static mount in main.py serves asset_upload_dir here.
    URL_PREFIX = "/uploads/assets"

    def __init__(self, base_dir: Optional[str] = None):
        self._base = Path(base_dir or settings.asset_upload_dir)

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        _reject_traversal(key)
        dest = self._base / key
        base_resolved = self._base.resolve()
        dest_resolved = dest.resolve()
        # Defense in depth: the resolved path must stay within the base dir.
        if os.path.commonpath([str(base_resolved), str(dest_resolved)]) != str(
            base_resolved
        ):
            raise StorageError(f"Resolved path escapes storage root: {key!r}")

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return f"{self.URL_PREFIX}/{key}"


class S3ObjectStorage(ObjectStorage):
    """S3-compatible storage (AWS S3 or Cloudflare R2) via aioboto3."""

    # Presigned-URL lifetime when no public base URL is configured.
    PRESIGN_EXPIRY_SECONDS = 86400 * 7  # 7 days

    def __init__(self):
        if not settings.asset_s3_bucket:
            raise StorageError(
                "asset_storage_backend='s3' requires asset_s3_bucket to be set"
            )
        self._bucket = settings.asset_s3_bucket

    def _session(self):
        import aioboto3

        return aioboto3.Session(
            aws_access_key_id=settings.asset_s3_access_key,
            aws_secret_access_key=settings.asset_s3_secret_key,
            region_name=settings.asset_s3_region,
        )

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        _reject_traversal(key)
        try:
            session = self._session()
            async with session.client(
                "s3", endpoint_url=settings.asset_s3_endpoint_url
            ) as s3:
                await s3.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
                # Prefer a stable public URL (CDN / R2 public domain) when
                # configured; otherwise hand back a time-limited presigned URL.
                if settings.asset_s3_public_base_url:
                    base = settings.asset_s3_public_base_url.rstrip("/")
                    return f"{base}/{key}"
                return await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": key},
                    ExpiresIn=self.PRESIGN_EXPIRY_SECONDS,
                )
        except ImportError as exc:  # pragma: no cover - aioboto3 is a hard dep
            raise StorageError("aioboto3 is required for the s3 backend") from exc
        except (ConnectionError, TimeoutError, OSError, ValueError, KeyError) as exc:
            logger.error("asset_s3_upload_failed", key=key, error=str(exc))
            raise StorageError(f"Failed to upload object to S3: {exc}") from exc


def get_object_storage() -> ObjectStorage:
    """Return the storage backend selected by settings.asset_storage_backend."""
    backend = (settings.asset_storage_backend or "local").lower()
    if backend == "s3":
        return S3ObjectStorage()
    return LocalObjectStorage()

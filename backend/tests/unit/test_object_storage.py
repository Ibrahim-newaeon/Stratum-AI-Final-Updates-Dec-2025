# =============================================================================
# Stratum AI - Object storage abstraction tests (INF-001)
# =============================================================================
"""
Uploaded assets must persist through a backend abstraction rather than a hard
local-disk write, so production can point at S3/R2 (durable across Railway
redeploys) while dev keeps a local dir. Covers the local backend, the traversal
guard, backend selection, and the S3 put/URL path.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.storage import (
    LocalObjectStorage,
    S3ObjectStorage,
    StorageError,
    get_object_storage,
)


@pytest.mark.asyncio
async def test_local_save_writes_file_and_returns_url(tmp_path):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    url = await storage.save("7/abc123.png", b"binarydata", "image/png")

    assert url == "/uploads/assets/7/abc123.png"
    written = tmp_path / "7" / "abc123.png"
    assert written.read_bytes() == b"binarydata"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_key",
    ["../evil.png", "/abs/evil.png", "7/../../etc/passwd", "a\\b.png", ""],
)
async def test_local_save_rejects_traversal(tmp_path, bad_key):
    storage = LocalObjectStorage(base_dir=str(tmp_path))
    with pytest.raises(StorageError):
        await storage.save(bad_key, b"x", "image/png")


def test_get_object_storage_defaults_to_local():
    with patch("app.services.storage.settings") as s:
        s.asset_storage_backend = "local"
        s.asset_upload_dir = "uploads/assets"
        assert isinstance(get_object_storage(), LocalObjectStorage)


def test_get_object_storage_selects_s3_when_configured():
    with patch("app.services.storage.settings") as s:
        s.asset_storage_backend = "s3"
        s.asset_s3_bucket = "my-bucket"
        assert isinstance(get_object_storage(), S3ObjectStorage)


def test_s3_backend_requires_bucket():
    with patch("app.services.storage.settings") as s:
        s.asset_storage_backend = "s3"
        s.asset_s3_bucket = None
        with pytest.raises(StorageError):
            S3ObjectStorage()


@pytest.mark.asyncio
async def test_s3_save_returns_public_url_when_configured():
    fake_s3 = MagicMock()
    fake_s3.put_object = AsyncMock()
    fake_s3.generate_presigned_url = AsyncMock(return_value="https://presigned/never")

    @asynccontextmanager
    async def _client(*args, **kwargs):
        yield fake_s3

    fake_session = MagicMock()
    fake_session.client = _client

    with patch("app.services.storage.settings") as s:
        s.asset_storage_backend = "s3"
        s.asset_s3_bucket = "assets"
        s.asset_s3_endpoint_url = "https://r2.example.com"
        s.asset_s3_region = "auto"
        s.asset_s3_access_key = "k"
        s.asset_s3_secret_key = "sec"
        s.asset_s3_public_base_url = "https://cdn.example.com"

        storage = S3ObjectStorage()
        with patch.object(storage, "_session", return_value=fake_session):
            url = await storage.save("7/abc.png", b"data", "image/png")

    fake_s3.put_object.assert_awaited_once()
    kwargs = fake_s3.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "assets"
    assert kwargs["Key"] == "7/abc.png"
    assert kwargs["ContentType"] == "image/png"
    # Stable public URL preferred over a presigned one.
    assert url == "https://cdn.example.com/7/abc.png"
    fake_s3.generate_presigned_url.assert_not_awaited()


@pytest.mark.asyncio
async def test_s3_save_returns_presigned_url_without_public_base():
    fake_s3 = MagicMock()
    fake_s3.put_object = AsyncMock()
    fake_s3.generate_presigned_url = AsyncMock(return_value="https://presigned/url")

    @asynccontextmanager
    async def _client(*args, **kwargs):
        yield fake_s3

    fake_session = MagicMock()
    fake_session.client = _client

    with patch("app.services.storage.settings") as s:
        s.asset_storage_backend = "s3"
        s.asset_s3_bucket = "assets"
        s.asset_s3_endpoint_url = None
        s.asset_s3_region = "us-east-1"
        s.asset_s3_access_key = "k"
        s.asset_s3_secret_key = "sec"
        s.asset_s3_public_base_url = None

        storage = S3ObjectStorage()
        with patch.object(storage, "_session", return_value=fake_session):
            url = await storage.save("7/abc.png", b"data", "image/png")

    assert url == "https://presigned/url"
    fake_s3.generate_presigned_url.assert_awaited_once()

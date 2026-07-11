# =============================================================================
# Stratum AI - ML Model Integrity (ML-002)
# =============================================================================
"""
Checksum-based integrity verification for model .pkl files.

joblib.load deserializes (unpickles) whatever bytes are on disk — arbitrary-code
execution if the file is attacker-controlled. Uploads are already gated to
super admins (ML-003); this adds defense-in-depth on the LOAD path: each model
is written with a sidecar ``<file>.sha256`` at train/promote time, and the
loader verifies the file against it. A mismatch means the model was tampered
with or corrupted and is refused; a missing sidecar (e.g. a legacy model) is
loaded but logged as unverified so it can't be a silent bypass.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

CHECKSUM_SUFFIX = ".sha256"
_CHUNK = 65536


def sha256_file(path: Path) -> str:
    """Streaming SHA-256 of a file (chunked so large models don't load to RAM)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def checksum_path(model_path: Path) -> Path:
    """Sidecar path for a model file: ``model.pkl`` -> ``model.pkl.sha256``."""
    return model_path.parent / (model_path.name + CHECKSUM_SUFFIX)


def write_checksum(model_path: Path) -> None:
    """Write the sidecar checksum for ``model_path``. Best-effort at call sites."""
    checksum_path(model_path).write_text(sha256_file(model_path), encoding="utf-8")


def verify_checksum(model_path: Path) -> Optional[bool]:
    """Verify a model file against its sidecar checksum.

    Returns:
        True  — sidecar present and matches.
        False — sidecar present and does NOT match (tampered/corrupt; refuse).
        None  — no sidecar (unverifiable; caller decides, default is to load).
    """
    sidecar = checksum_path(model_path)
    if not sidecar.exists():
        return None
    try:
        expected = sidecar.read_text(encoding="utf-8").strip()
        actual = sha256_file(model_path)
    except OSError as exc:
        logger.warning(
            "model_checksum_read_failed", path=str(model_path), error=str(exc)
        )
        return None
    return hmac.compare_digest(expected, actual)

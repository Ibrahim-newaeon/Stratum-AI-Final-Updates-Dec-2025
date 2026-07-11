# =============================================================================
# Stratum AI - ML model integrity tests (ML-002)
# =============================================================================
"""
Models are verified against a sidecar SHA-256 before joblib.load (which
unpickles = executes arbitrary code). A tampered/corrupt model is refused; a
model with no sidecar loads but is flagged unverified.
"""

import joblib
import pytest

from app.ml.inference import LocalInferenceStrategy
from app.ml.integrity import (
    checksum_path,
    sha256_file,
    verify_checksum,
    write_checksum,
)

pytestmark = pytest.mark.unit


# ---- integrity helpers ------------------------------------------------------


def test_sha256_file_matches_hashlib(tmp_path):
    import hashlib

    f = tmp_path / "m.pkl"
    f.write_bytes(b"model-bytes")
    assert sha256_file(f) == hashlib.sha256(b"model-bytes").hexdigest()


def test_write_then_verify_matches(tmp_path):
    f = tmp_path / "m.pkl"
    f.write_bytes(b"abc")
    write_checksum(f)
    assert checksum_path(f).exists()
    assert verify_checksum(f) is True


def test_verify_false_when_file_tampered(tmp_path):
    f = tmp_path / "m.pkl"
    f.write_bytes(b"abc")
    write_checksum(f)
    f.write_bytes(b"tampered-after-checksum")
    assert verify_checksum(f) is False


def test_verify_none_without_sidecar(tmp_path):
    f = tmp_path / "m.pkl"
    f.write_bytes(b"abc")
    assert verify_checksum(f) is None


# ---- loader integration -----------------------------------------------------


def test_load_ok_with_matching_sidecar(tmp_path):
    strat = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)
    write_checksum(f)
    assert strat._load_model("m") == {"v": 1}


def test_load_refuses_on_checksum_mismatch(tmp_path):
    strat = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)
    checksum_path(f).write_text("0" * 64, encoding="utf-8")  # wrong digest
    assert strat._load_model("m") is None


def test_load_allows_missing_sidecar(tmp_path):
    strat = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)  # no sidecar written
    assert strat._load_model("m") == {"v": 1}

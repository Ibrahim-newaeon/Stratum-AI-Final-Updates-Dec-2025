# =============================================================================
# Stratum AI - Atomic model promotion tests (ML-004)
# =============================================================================
"""
Model promotion/rollback copies a new .pkl over the path inference workers
joblib.load from. The copy must be atomic (temp file + os.replace) so a
concurrent reader never observes a half-written file.
"""

from unittest.mock import patch

import pytest

from app.ml.retraining_pipeline import _atomic_copy

pytestmark = pytest.mark.unit


def test_copies_content(tmp_path):
    src = tmp_path / "src.pkl"
    dst = tmp_path / "prod.pkl"
    src.write_bytes(b"model-bytes")

    _atomic_copy(src, dst)

    assert dst.read_bytes() == b"model-bytes"


def test_overwrites_existing_destination(tmp_path):
    src = tmp_path / "src.pkl"
    dst = tmp_path / "prod.pkl"
    src.write_bytes(b"new")
    dst.write_bytes(b"old")

    _atomic_copy(src, dst)

    assert dst.read_bytes() == b"new"


def test_leaves_no_temp_file(tmp_path):
    src = tmp_path / "src.pkl"
    dst = tmp_path / "prod.pkl"
    src.write_bytes(b"x")

    _atomic_copy(src, dst)

    assert not (tmp_path / "prod.pkl.tmp").exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_uses_os_replace_for_atomicity(tmp_path):
    src = tmp_path / "src.pkl"
    dst = tmp_path / "prod.pkl"
    src.write_bytes(b"x")

    with patch("app.ml.retraining_pipeline.os.replace") as replace:
        _atomic_copy(src, dst)

    # The final swap must go through os.replace (atomic rename), not a direct
    # write to the destination.
    replace.assert_called_once()
    args = replace.call_args.args
    assert str(args[1]) == str(dst)

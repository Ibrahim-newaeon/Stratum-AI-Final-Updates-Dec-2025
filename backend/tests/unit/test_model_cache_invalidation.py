# =============================================================================
# Stratum AI - Model cache invalidation tests (ML-005)
# =============================================================================
"""
ModelRegistry is a process-wide singleton, so a model cached in memory was
served for the life of the process even after a retrain promoted a new .pkl to
disk. _load_model now reloads when the file's mtime changes.
"""

import os

import joblib
import pytest

from app.ml.inference import LocalInferenceStrategy

pytestmark = pytest.mark.unit


def test_serves_cache_when_file_unchanged(tmp_path):
    reg = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)

    first = reg._load_model("m")
    assert first == {"v": 1}
    # Same object returned from cache (no reload) while the file is unchanged.
    assert reg._load_model("m") is first


def test_reloads_when_file_mtime_changes(tmp_path):
    reg = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)
    assert reg._load_model("m") == {"v": 1}

    # Simulate a retrain promoting a new model with a newer mtime.
    joblib.dump({"v": 2}, f)
    st = f.stat()
    os.utime(f, (st.st_atime, st.st_mtime + 10))

    assert reg._load_model("m") == {"v": 2}


def test_missing_file_keeps_previous_copy(tmp_path):
    reg = LocalInferenceStrategy(models_path=str(tmp_path))
    f = tmp_path / "m.pkl"
    joblib.dump({"v": 1}, f)
    first = reg._load_model("m")

    f.unlink()  # file vanishes mid-run
    # Still serves the previously loaded copy rather than returning None.
    assert reg._load_model("m") is first

#!/usr/bin/env python
"""
Build-time ML model trainer.

Runs during `docker build` so models are baked into the image layer.
Eliminates the ~9.5 GB / 5-minute training step at every container start.

Mirrors the runtime auto-train block in app/main.py — keep them in sync.
"""

import os
import sys
from pathlib import Path

# Ensure the backend package is importable when invoked from /app during build.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__ + "/..")))

from app.ml.data_loader import TrainingDataLoader  # noqa: E402
from app.ml.train import ModelTrainer  # noqa: E402


def main() -> int:
    models_path = Path(os.environ.get("ML_MODELS_PATH", "/app/ml_service/models"))
    models_path.mkdir(parents=True, exist_ok=True)

    print(f"[build_ml_models] target dir: {models_path}", flush=True)
    print("[build_ml_models] generating sample data (100 campaigns x 30 days)...", flush=True)
    df = TrainingDataLoader.generate_sample_data(num_campaigns=100, days_per_campaign=30)
    print(f"[build_ml_models] data prepared: {len(df)} rows x {len(df.columns)} columns", flush=True)

    trainer = ModelTrainer(str(models_path))
    trainer.train_all(df, include_platform_models=False)

    pkls = sorted(p.name for p in models_path.glob("*.pkl"))
    if not pkls:
        print("[build_ml_models] ERROR: no .pkl files produced", flush=True)
        return 1

    print(f"[build_ml_models] done. {len(pkls)} files baked into image: {pkls}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

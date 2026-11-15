"""Read Person 2's exported score table through one shared loader."""

from __future__ import annotations

from pathlib import Path
import warnings

import pandas as pd


SCORE_BASENAMES = ("scores_all.parquet", "scores_all.csv")


def load_scores(path: str | Path) -> pd.DataFrame:
    """Load scores_all parquet or CSV and validate its shared columns."""
    source = Path(path)
    if source.is_dir():
        matches = [source / name for name in SCORE_BASENAMES if (source / name).is_file()]
        if not matches:
            raise FileNotFoundError(
                f"No scores_all.parquet or scores_all.csv found in {source}"
            )
        source = matches[0]
    if not source.is_file():
        raise FileNotFoundError(f"Score file not found: {source}")
    suffix = source.suffix.lower()
    if suffix == ".parquet":
        frame = pd.read_parquet(source)
    elif suffix == ".csv":
        frame = pd.read_csv(source)
    else:
        raise ValueError(f"Unsupported score file extension: {source.suffix}")

    required = {"cell_id", "target_id", "score"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Score file missing required columns: {sorted(missing)}")
    frame = frame.copy()
    frame["cell_id"] = frame["cell_id"].astype("string")
    frame["target_id"] = frame["target_id"].astype("string")
    if "engine_region_id" in frame.columns:
        frame["engine_region_id"] = frame["engine_region_id"].astype("string")
        missing_engine_ids = frame["engine_region_id"].isna()
        if missing_engine_ids.any():
            raise ValueError("engine_region_id must be present for every score row")
    frame["score"] = pd.to_numeric(frame["score"], errors="coerce")
    finite = frame["score"].dropna()
    if not finite.between(0, 1).all():
        raise ValueError("Non-null score values must be in [0, 1]")
    duplicate_columns = ["cell_id", "target_id"]
    if "grid_source" in frame.columns:
        frame["grid_source"] = frame["grid_source"].astype("string")
        duplicate_columns.append("grid_source")
    duplicate_mask = frame.duplicated(duplicate_columns, keep="first")
    if duplicate_mask.any():
        warnings.warn(
            f"Dropping {int(duplicate_mask.sum())} duplicate (cell_id, target_id) score rows; keeping first",
            RuntimeWarning,
            stacklevel=2,
        )
        frame = frame.loc[~duplicate_mask].copy()
    return frame.reset_index(drop=True)

"""Shared grid loading, cell-key joins, scope and score helpers."""

from __future__ import annotations

import math
import warnings
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .analog_mapping import cell_id
from .grid_utils import parse_cell_id


SCORING_FEATURES = (
    "slope_median_deg", "slope_p90_deg", "flat_fraction", "tri_median_m",
    "relief_m", "elevation_std_m",
)
TARGET_ENGINE_IDS = {
    "T-01": "mars_jezero_regional",
    "T-02": "moon_shackleton_regional",
    "T-03": "moon_marius_hills_regional",
    "mars_phoenix_regional": "mars_phoenix_regional",
    "mars_arcadia_regional": "mars_arcadia_regional",
}
TARGET_IDS = tuple(TARGET_ENGINE_IDS)
UNSCORABLE_TARGETS = {
    "T-01": "unscorable",
    "T-03": "unscorable",
}
SCOPE_NOTE = "Kapsam küresel değildir; sonuçlar yalnızca işlenmiş hücreler için geçerlidir."
SOURCE_FILE = Path(__file__).resolve().parent / "data" / "inputs" / "SOURCE.txt"


def load_grid(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Load one or more parquet grids; match and deduplicate by coordinate key."""
    sources = [Path(p) for p in paths]
    if not sources:
        raise ValueError("At least one --grid parquet path is required")
    frames = []
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(f"Grid parquet not found: {source}")
        frame = pd.read_parquet(source)
        for col in ("lat", "lon"):
            if col not in frame.columns:
                raise ValueError(f"Grid {source} is missing coordinate column {col!r}")
        frame = frame.copy()
        frame["cell_key"] = [cell_id(float(lat), float(lon)) for lat, lon in zip(frame.lat, frame.lon)]
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True, sort=False)
    duplicate_mask = combined.duplicated("cell_key", keep="first")
    if duplicate_mask.any():
        warnings.warn(
            f"Found {int(duplicate_mask.sum())} duplicate coordinate cell_key rows across grids; keeping first",
            RuntimeWarning,
            stacklevel=2,
        )
        combined = combined.loc[~duplicate_mask].copy()
    return combined.reset_index(drop=True)


def comparable_mask(frame: pd.DataFrame) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for feature in SCORING_FEATURES:
        value_col = feature
        flag_col = f"{feature}__comparable"
        if value_col not in frame or flag_col not in frame:
            return pd.Series(False, index=frame.index)
        mask &= frame[flag_col].fillna(False).astype(bool)
        mask &= pd.to_numeric(frame[value_col], errors="coerce").notna()
    return mask


def validation_mask(frame: pd.DataFrame) -> pd.Series:
    """Rows with six comparable features and, if supplied, land fraction >= 0.5."""
    mask = comparable_mask(frame)
    if "land_fraction" in frame.columns:
        mask &= pd.to_numeric(frame["land_fraction"], errors="coerce").ge(0.5)
    return mask


def source_metadata(path: str | Path = SOURCE_FILE) -> dict[str, str | None]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Grid source file not found: {source}")
    values: dict[str, str | None] = {"branch": None, "commit": None}
    for line in source.read_text(encoding="utf-8").splitlines():
        if line.startswith("Source branch:"):
            values["branch"] = line.split(":", 1)[1].strip()
        elif line.startswith("Source commit:"):
            values["commit"] = line.split(":", 1)[1].strip()
    return values


def scope_block(frame: pd.DataFrame, source_path: str | Path = SOURCE_FILE) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("Cannot construct scope for an empty grid")
    lats = pd.to_numeric(frame.lat, errors="coerce").dropna().astype(float)
    lons = pd.to_numeric(frame.lon, errors="coerce").dropna().astype(float)
    if lats.empty or lons.empty:
        raise ValueError("Grid has no valid lat/lon coordinates")
    counts: Counter[tuple[int, int]] = Counter()
    for lat, lon in zip(frame.lat, frame.lon):
        counts[(math.floor(float(lat) / 5) * 5, math.floor(float(lon) / 5) * 5)] += 1
    bins = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    source = source_metadata(source_path)
    return {
        "processed_cell_count": int(frame.cell_key.nunique()),
        "valid_cell_count": int(comparable_mask(frame).sum()),
        "latitude_range": [float(lats.min()), float(lats.max())],
        "longitude_range": [float(lons.min()), float(lons.max())],
        "five_degree_bins_top_10": [
            {"lat_min": lat0, "lat_max": lat0 + 5, "lon_min": lon0,
             "lon_max": lon0 + 5, "cell_count": count}
            for (lat0, lon0), count in bins
        ],
        "source_branch": source["branch"],
        "source_commit": source["commit"],
        "note": SCOPE_NOTE,
    }


def cell_key_aliases(frame: pd.DataFrame) -> dict[str, str]:
    """Map external score IDs to coordinate-derived cell_key values."""
    aliases: dict[str, str] = {}
    for row in frame.to_dict(orient="records"):
        key = str(row["cell_key"])
        aliases[key] = key
        for col in ("cell_id", "region_id"):
            value = row.get(col)
            if value is not None and not pd.isna(value):
                aliases[str(value)] = key
    return aliases


def scores_by_key(scores: pd.DataFrame, grid: pd.DataFrame) -> pd.DataFrame:
    aliases = cell_key_aliases(grid)
    mapped = scores.copy()
    mapped["cell_key"] = mapped["cell_id"].astype(str).map(aliases)
    direct = mapped["cell_key"].isna() & mapped["cell_id"].astype(str).str.startswith("g_")
    mapped.loc[direct, "cell_key"] = mapped.loc[direct, "cell_id"].astype(str)
    return mapped


def rank_percentiles(scores: pd.Series) -> pd.Series:
    """Return ascending average-rank percentiles, with the maximum at 100."""
    from scipy.stats import rankdata

    values = pd.to_numeric(scores, errors="coerce")
    valid = values.notna()
    result = pd.Series(np.nan, index=scores.index, dtype=float)
    n = int(valid.sum())
    if n:
        result.loc[valid] = rankdata(values.loc[valid].to_numpy(), method="average") / n * 100.0
    return result


def safe_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): safe_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_json_value(v) for v in value]
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def timestamp_iso() -> str:
    return datetime.now(timezone(timedelta(hours=3))).isoformat(timespec="seconds")


def non_overwriting_path(path: Path) -> Path:
    if not path.exists():
        return path
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    candidate = path.with_name(f"{path.stem}_{stamp}{path.suffix}")
    index = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{stamp}_{index}{path.suffix}")
        index += 1
    return candidate

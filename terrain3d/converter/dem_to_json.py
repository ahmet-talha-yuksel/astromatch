"""Convert a single-band projected DEM GeoTIFF to AstroMatch terrain JSON.
Requires: pip install rasterio numpy
Use a projected DEM with meter-based pixels. Reproject/crop upstream.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.enums import Resampling

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument("--name", required=True)
    parser.add_argument("--body", choices=["Earth", "Mars", "Moon"], required=True)
    parser.add_argument("--size", type=int, default=128)
    args = parser.parse_args()
    if args.size < 2:
        parser.error("--size must be >= 2")
    with rasterio.open(args.input) as ds:
        if ds.crs is None or not ds.crs.is_projected:
            raise ValueError("Input DEM must be projected to a metric CRS first")
        units = ds.crs.linear_units
        if not units or units.lower() not in ("metre", "meter", "metres", "meters", "m"):
            raise ValueError(f"DEM must use meters, got {units}")
        if abs(ds.res[0] - ds.res[1]) / max(ds.res) > 0.001:
            raise ValueError("Pixel width/height must be approximately equal")
        arr = ds.read(1, out_shape=(args.size, args.size),
                      resampling=Resampling.bilinear, masked=True)
        if np.ma.is_masked(arr) and np.any(np.ma.getmaskarray(arr)):
            raise ValueError("NoData detected: crop or fill appropriately before conversion")
        values = np.asarray(arr, dtype=np.float64)
        if not np.isfinite(values).all():
            raise ValueError("Non-finite DEM values")
        cell = float(ds.res[0]) * (ds.width - 1) / (args.size - 1)
        data = {"id": Path(args.output).stem, "name": args.name, "body": args.body,
                "width": args.size, "height": args.size,
                "cellSizeMeters": cell, "elevationsMeters": values.ravel().tolist(),
                "source": f"{Path(args.input).name}; original CRS {ds.crs}",
                "verticalExaggeration": 1}
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(data), encoding="utf-8")
    print(f"Saved {args.output}")

if __name__ == "__main__":
    main()

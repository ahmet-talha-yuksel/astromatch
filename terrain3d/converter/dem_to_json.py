"""Convert a prepared metric GeoTIFF DEM to canonical TerrainDataJSON.

Requires rasterio and numpy. This tool prepares visualization windows only; it does
not download data, infer planetary datums, or reproject geographic rasters.
"""
from __future__ import annotations
import argparse, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import Window
except ImportError:
    np = None  # type: ignore[assignment]
    rasterio = None  # type: ignore[assignment]
    Resampling = None  # type: ignore[assignment]
    Window = None  # type: ignore[assignment]

RESAMPLING = {n: getattr(Resampling, n) for n in ("nearest", "bilinear", "cubic", "average", "mode")} if Resampling else {}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Convert a prepared metric GeoTIFF DEM into TerrainDataJSON.")
    p.add_argument("input_pos", nargs="?", help=argparse.SUPPRESS); p.add_argument("output_pos", nargs="?", help=argparse.SUPPRESS)
    p.add_argument("--input", dest="input_path"); p.add_argument("--output", dest="output_path")
    p.add_argument("--id"); p.add_argument("--name", required=True); p.add_argument("--body", choices=("Earth", "Mars", "Moon"), required=True)
    p.add_argument("--data-type", choices=("real", "synthetic"), default="real")
    p.add_argument("--dataset"); p.add_argument("--product-id"); p.add_argument("--version"); p.add_argument("--source-url")
    p.add_argument("--vertical-datum", required=True); p.add_argument("--vertical-units", default="meters", choices=("m", "meter", "meters", "metre", "metres"))
    p.add_argument("--target-size", type=int); p.add_argument("--target-width", type=int); p.add_argument("--target-height", type=int)
    p.add_argument("--resampling", choices=tuple(RESAMPLING), default="bilinear"); p.add_argument("--vertical-exaggeration", type=float, default=1.0)
    p.add_argument("--window", nargs=4, type=float, metavar=("COL", "ROW", "WIDTH", "HEIGHT")); p.add_argument("--window-meters", nargs=4, type=float, metavar=("X", "Y", "WIDTH", "HEIGHT"))
    p.add_argument("--allow-upsampling", action="store_true", help="Allow interpolation finer than source samples (creates no new measurements).")
    p.add_argument("--processing-note", action="append", default=[]); return p


def resolve_args(p: argparse.ArgumentParser, ns: argparse.Namespace) -> tuple[Path, Path]:
    inp, out = ns.input_path or ns.input_pos, ns.output_path or ns.output_pos
    if not inp or not out: p.error("--input and --output are required (positional input output are also accepted)")
    if ns.target_size is not None and (ns.target_width is not None or ns.target_height is not None): p.error("use --target-size or target width/height, not both")
    if (ns.target_width is None) != (ns.target_height is None): p.error("--target-width and --target-height must be supplied together")
    if ns.target_size is not None and ns.target_size < 2: p.error("--target-size must be >= 2")
    if ns.target_width is not None and (ns.target_width < 2 or ns.target_height < 2): p.error("target dimensions must be >= 2")
    if not math.isfinite(ns.vertical_exaggeration) or ns.vertical_exaggeration <= 0: p.error("vertical exaggeration must be finite and > 0")
    if ns.data_type == "real" and not all((ns.dataset, ns.product_id, ns.version, ns.source_url)): p.error("real data requires dataset, product-id, version and source-url")
    if ns.source_url and not ns.source_url.startswith(("http://", "https://")): p.error("source-url must be HTTP(S)")
    return Path(inp), Path(out)


def validate_raster(ds: Any, body: str, vertical_units: str) -> None:
    if ds.count < 1 or ds.width < 2 or ds.height < 2: raise ValueError("raster must have a band and dimensions >= 2x2")
    t = ds.transform
    if t.a <= 0 or t.e >= 0 or t.b != 0 or t.d != 0: raise ValueError("rotated, skewed, south-up, or zero-scale transforms are unsupported")
    if ds.crs is None: raise ValueError("input CRS is missing; provide a verified projected CRS upstream")
    if not ds.crs.is_projected: raise ValueError("geographic CRS in degrees is unsupported; prepare a body-appropriate projected metric raster")
    if (ds.crs.linear_units or "").lower() not in {"m", "meter", "meters", "metre", "metres"}: raise ValueError(f"CRS units {ds.crs.linear_units!r} are not meters")
    if vertical_units not in {"m", "meter", "meters", "metre", "metres"}: raise ValueError("vertical units must be meters")
    if ds.nodata is None and not np.isfinite(ds.read(1, masked=False)).all(): raise ValueError("non-finite values exist without identifiable NoData")
    if body in ("Mars", "Moon") and not ds.crs.is_projected: raise ValueError(f"{body} geographic CRS lacks verified body-specific conversion")


def select_window(ds: Any, ns: argparse.Namespace) -> Window:
    if ns.window and ns.window_meters: raise ValueError("use window or window-meters, not both")
    if ns.window: w = Window(*ns.window)
    elif ns.window_meters:
        x, y, width, height = ns.window_meters
        if width <= 0 or height <= 0: raise ValueError("window-meters dimensions must be positive")
        w = Window((x - ds.transform.c) / ds.transform.a, (ds.transform.f - y - height) / abs(ds.transform.e), width / ds.transform.a, height / abs(ds.transform.e))
    else: w = Window(0, 0, ds.width, ds.height)
    if w.col_off < 0 or w.row_off < 0 or w.col_off + w.width > ds.width or w.row_off + w.height > ds.height: raise ValueError("selected window does not overlap raster")
    if w.width < 2 or w.height < 2: raise ValueError("selected window must be at least 2x2")
    return w


def convert(ns: argparse.Namespace, inp: Path, out: Path) -> dict[str, Any]:
    if np is None or rasterio is None:
        raise ValueError("rasterio and numpy are required; install with: python -m pip install rasterio numpy")
    if not inp.is_file(): raise ValueError(f"input file does not exist or is not readable: {inp}")
    with rasterio.open(inp) as ds:
        validate_raster(ds, ns.body, ns.vertical_units); window = select_window(ds, ns)
        width = ns.target_size or ns.target_width or int(round(window.width)); height = ns.target_size or ns.target_height or int(round(window.height))
        sx, sy = abs(ds.transform.a), abs(ds.transform.e)
        out_sx, out_sy = window.width * sx / width, window.height * sy / height
        if (out_sx < sx or out_sy < sy) and not ns.allow_upsampling: raise ValueError("output is finer than source; use --allow-upsampling explicitly")
        arr = ds.read(1, window=window, out_shape=(height, width), resampling=RESAMPLING[ns.resampling], masked=True)
        raw, mask = np.ma.getdata(arr).astype(float), np.ma.getmaskarray(arr) | ~np.isfinite(np.ma.getdata(arr))
        valid = ~mask
        if not valid.any(): raise ValueError("selected output contains no valid samples")
        heights = [float(v) if valid.flat[i] else None for i, v in enumerate(raw.ravel())]
        valid_mask = valid.ravel().tolist()
        steps = [f"resampling={ns.resampling}", f"original_dimensions={ds.width}x{ds.height}", f"output_dimensions={width}x{height}"] + list(ns.processing_note)
        if out_sx < sx or out_sy < sy: steps.append("WARNING: upsampling interpolation creates no new measurements")
        metadata: dict[str, Any] = {"steps": steps, "processedAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"), "software": "AstroMatch Terrain3D dem_to_json.py"}
        if ns.data_type == "real": metadata["provenance"] = {"dataset": ns.dataset, "productId": ns.product_id, "version": ns.version, "url": ns.source_url}
        return {"id": ns.id or out.stem, "name": ns.name, "body": ns.body, "width": width, "height": height, "heights": heights,
                "cellSizeMeters": {"x": out_sx, "y": out_sy}, "source": ns.dataset or f"Synthetic generated from {inp.name}", "resolutionMeters": {"x": sx, "y": sy},
                "verticalExaggeration": ns.vertical_exaggeration, "dataType": ns.data_type, "validMask": valid_mask,
                "horizontalWindowMeters": {"width": (width - 1) * out_sx, "height": (height - 1) * out_sy}, "verticalDatum": ns.vertical_datum,
                "coordinateReferenceSystem": ds.crs.to_string(), "processingMetadata": metadata}


def main(argv: list[str] | None = None) -> int:
    p = build_parser()
    try:
        ns = p.parse_args(argv); inp, out = resolve_args(p, ns); data = convert(ns, inp, out)
        out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(data, allow_nan=False, indent=2) + "\n", encoding="utf-8")
        invalid = sum(not x for x in data["validMask"]); print(f"Saved {out} ({data['width']}x{data['height']}, valid {100 * (1 - invalid / len(data['validMask'])):.2f}%, invalid {invalid})"); return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())

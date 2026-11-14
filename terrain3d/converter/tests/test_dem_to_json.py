"""Focused offline converter tests; skipped when rasterio is not installed."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import Affine

SCRIPT = Path(__file__).parents[1] / "dem_to_json.py"


def raster(tmp_path, *, crs="EPSG:3857", nodata=-9999, transform=None, data=None):
    data = np.asarray(data if data is not None else [[1, 2, 3], [4, nodata, 6], [7, 8, 9]], dtype="float32")
    path = tmp_path / "input.tif"
    with rasterio.open(path, "w", driver="GTiff", width=data.shape[1], height=data.shape[0], count=1, dtype="float32", crs=crs, transform=transform or Affine(10, 0, 0, 0, -20, 60), nodata=nodata) as dst:
        dst.write(data, 1)
    return path


def run(tmp_path, source, *extra):
    output = tmp_path / "out.json"
    command = [sys.executable, str(SCRIPT), "--input", str(source), "--output", str(output), "--id", "test", "--name", "Test", "--body", "Mars", "--data-type", "real", "--dataset", "Dataset", "--product-id", "P1", "--version", "1", "--source-url", "https://example.org/p1", "--vertical-datum", "test datum", *extra]
    result = subprocess.run(command, capture_output=True, text=True)
    return result, output


def test_metric_nodata_order_spacing_and_contract(tmp_path):
    result, output = run(tmp_path, raster(tmp_path))
    assert result.returncode == 0, result.stderr
    data = json.loads(output.read_text())
    assert data["heights"] == [1, 2, 3, 4, None, 6, 7, 8, 9]
    assert data["validMask"][4] is False
    assert data["cellSizeMeters"] == {"x": 10.0, "y": 20.0}
    assert data["horizontalWindowMeters"] == {"width": 20.0, "height": 40.0}
    assert data["processingMetadata"]["provenance"]["productId"] == "P1"
    assert "NaN" not in output.read_text() and "Infinity" not in output.read_text()


@pytest.mark.parametrize("size", [128, 256])
def test_target_sizes(tmp_path, size):
    result, output = run(tmp_path, raster(tmp_path, data=np.arange(25, dtype="float32").reshape(5, 5), nodata=-9999), "--target-size", str(size), "--allow-upsampling")
    assert result.returncode == 0, result.stderr
    data = json.loads(output.read_text()); assert (data["width"], data["height"]) == (size, size)


def test_rejects_geographic_rotated_and_missing_provenance(tmp_path):
    result, _ = run(tmp_path, raster(tmp_path, crs="EPSG:4326")); assert result.returncode != 0 and "degrees" in result.stderr
    result, _ = run(tmp_path, raster(tmp_path, transform=Affine(10, 1, 0, 0, -20, 60))); assert result.returncode != 0 and "rotated" in result.stderr
    source = raster(tmp_path); result, _ = run(tmp_path, source, "--data-type", "synthetic")
    assert result.returncode == 0

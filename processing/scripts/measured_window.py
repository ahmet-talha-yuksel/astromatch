"""Project a counts-masked source DEM onto an already specified metric window."""
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject
from rasterio.windows import Window


def measured_window(path, counts_path, *, crs, transform, shape, vertical_unit):
    with rasterio.open(path) as src, rasterio.open(counts_path) as counts:
        if (src.crs != counts.crs or not np.isclose(src.transform.a, counts.transform.a)
                or not np.isclose(src.transform.e, counts.transform.e)
                or src.transform.b != 0 or src.transform.d != 0 or counts.transform.b != 0 or counts.transform.d != 0):
            raise ValueError('Elevation/count grids must have the same native CRS, pixel spacing and orientation')
        col = (counts.transform.c - src.transform.c) / src.transform.a
        row = (counts.transform.f - src.transform.f) / src.transform.e
        if not np.isclose(col, round(col), atol=1e-6, rtol=0) or not np.isclose(row, round(row), atol=1e-6, rtol=0):
            raise ValueError('Counts crop must align exactly to elevation pixel centers')
        if counts.width * counts.height > 1_000_000:
            raise ValueError('Provide a cropped counts raster (<=1 million pixels)')
        # A counts crop may cover just the analysis neighborhood of a larger DEM.
        # Read the identical native pixels; unknown support outside that crop stays NoData.
        window = Window(round(col), round(row), counts.width, counts.height)
        heights = src.read(1, window=window, boundless=True, masked=True).astype('float64').filled(np.nan)
        observed = counts.read(1, masked=True).astype('float64').filled(np.nan)
        heights[~np.isfinite(observed) | (observed <= 0)] = np.nan
        heights = (heights * src.scales[0] + src.offsets[0]) * (1000 if vertical_unit == 'km' else 1)
        result = np.full(shape, np.nan, dtype='float64')
        reproject(heights, result, src_transform=counts.transform, src_crs=src.crs,
                  src_nodata=np.nan, dst_transform=transform, dst_crs=crs,
                  dst_nodata=np.nan, resampling=Resampling.average)
    return result

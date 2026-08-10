from pathlib import Path
import re

import numpy as np
import pandas as pd
import rasterio
import xarray as xr


DATE_PATTERN = re.compile(r"(\d{6})")


def extract_month(path: Path) -> pd.Timestamp:
    """Extract a YYYYMM timestamp from a DWD raster filename."""
    match = DATE_PATTERN.search(path.name)
    if match is None:
        raise ValueError(f"No YYYYMM date found in filename: {path.name}")

    try:
        return pd.to_datetime(match.group(1), format="%Y%m")
    except ValueError as exc:
        raise ValueError(f"Invalid YYYYMM date in filename: {path.name}") from exc


def calculate_regional_mean(raster_path: Path) -> float:
    """Calculate the mean of valid pixels inside a clipped raster."""
    with rasterio.open(raster_path) as src:
        data = src.read(1, masked=True)

        # gdalwarp -dstalpha creates an alpha band as the last band.
        # Pixels outside the study-area polygon have alpha = 0.
        if src.count > 1:
            alpha = src.read(src.count)
            data = np.ma.masked_where(alpha == 0, data)

        if data.count() == 0:
            raise ValueError(f"Raster contains no valid study-area pixels: {raster_path}")

        return float(data.mean())


def build_regional_timeseries(
    raster_paths: list[Path],
    value_column: str,
    value_unit: str,
) -> pd.DataFrame:
    """Convert monthly clipped rasters into a sorted regional time series."""
    records = []

    for raster_path in sorted(raster_paths):
        records.append(
            {
                "date": extract_month(raster_path),
                "filename": raster_path.name,
                value_column: calculate_regional_mean(raster_path),
                "unit": value_unit,
            }
        )

    return (
        pd.DataFrame(records)
        .sort_values("date")
        .reset_index(drop=True)
    )


def export_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def export_netcdf(
    df: pd.DataFrame,
    value_column: str,
    value_unit: str,
    output_path: Path,
) -> Path:
    """Export the regional time series as a simple NetCDF dataset."""
    dataset = xr.Dataset(
        data_vars={
            value_column: (
                "time",
                df[value_column].to_numpy(),
                {"units": value_unit},
            )
        },
        coords={"time": pd.to_datetime(df["date"]).to_numpy()},
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_netcdf(output_path)
    return output_path

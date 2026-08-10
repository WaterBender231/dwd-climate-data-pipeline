from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

from .aggregate import extract_month


def require_file(path: Path, label: str = "File") -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")


def validate_raster(
    raster_path: Path,
    expected_crs: str | None = None,
    expected_resolution: tuple[float, float] | None = None,
) -> dict:
    """Run basic metadata and data-quality checks on one raster."""
    require_file(raster_path, "Raster")

    with rasterio.open(raster_path) as src:
        if src.crs is None:
            raise ValueError(f"Raster has no CRS: {raster_path}")
        if src.width <= 0 or src.height <= 0:
            raise ValueError(f"Raster has invalid dimensions: {raster_path}")

        if expected_crs and src.crs.to_string() != expected_crs:
            raise ValueError(
                f"Unexpected CRS for {raster_path.name}: "
                f"{src.crs} != {expected_crs}"
            )

        resolution = (abs(src.res[0]), abs(src.res[1]))
        if expected_resolution and not np.allclose(resolution, expected_resolution):
            raise ValueError(
                f"Unexpected resolution for {raster_path.name}: "
                f"{resolution} != {expected_resolution}"
            )

        data = src.read(1, masked=True)
        valid_pixel_count = int(data.count())
        if valid_pixel_count == 0:
            raise ValueError(f"Raster has no valid pixels: {raster_path}")

        valid_values = data.compressed()
        if not np.isfinite(valid_values).all():
            raise ValueError(f"Raster contains non-finite values: {raster_path}")

        return {
            "path": raster_path,
            "crs": src.crs.to_string(),
            "resolution": resolution,
            "width": src.width,
            "height": src.height,
            "bands": src.count,
            "nodata": src.nodata,
            "valid_pixels": valid_pixel_count,
            "min": float(valid_values.min()),
            "max": float(valid_values.max()),
        }


def validate_raster_collection(
    raster_paths: list[Path],
    expected_crs: str | None = None,
    expected_resolution: tuple[float, float] | None = None,
) -> list[dict]:
    """Validate each raster and check collection-level consistency."""
    if not raster_paths:
        raise ValueError("Raster collection is empty.")

    reports = [
        validate_raster(path, expected_crs, expected_resolution)
        for path in raster_paths
    ]

    crs_values = {report["crs"] for report in reports}
    resolutions = {report["resolution"] for report in reports}

    if len(crs_values) != 1:
        raise ValueError(f"Raster collection contains multiple CRS values: {crs_values}")
    if len(resolutions) != 1:
        raise ValueError(
            f"Raster collection contains multiple resolutions: {resolutions}"
        )

    months = [extract_month(path) for path in raster_paths]
    duplicates = pd.Series(months).duplicated(keep=False)
    if duplicates.any():
        duplicate_months = sorted(set(pd.Series(months)[duplicates]))
        raise ValueError(f"Duplicate raster months found: {duplicate_months}")

    return reports


def expected_months(start_year: int, end_year: int) -> pd.DatetimeIndex:
    return pd.date_range(
        f"{start_year}-01-01",
        f"{end_year}-12-01",
        freq="MS",
    )


def find_missing_months(
    dates: pd.Series,
    start_year: int,
    end_year: int,
) -> pd.DatetimeIndex:
    actual = pd.DatetimeIndex(pd.to_datetime(dates)).normalize()
    expected = expected_months(start_year, end_year)
    return expected.difference(actual)


def validate_time_series(
    df: pd.DataFrame,
    value_column: str,
    value_unit: str,
    start_year: int,
    end_year: int,
    min_value: float | None = None,
    max_value: float | None = None,
) -> dict:
    """Validate monthly coverage, duplicates, missing values and optional ranges."""
    required_columns = {"date", value_column, "unit"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(f"Missing output columns: {sorted(missing_columns)}")

    dates = pd.to_datetime(df["date"])

    if dates.duplicated().any():
        duplicate_dates = dates[dates.duplicated(keep=False)].tolist()
        raise ValueError(f"Duplicate dates in time series: {duplicate_dates}")

    missing = find_missing_months(dates, start_year, end_year)
    if len(missing) > 0:
        formatted = [date.strftime("%Y-%m") for date in missing]
        raise ValueError(f"Missing monthly observations: {formatted}")

    values = pd.to_numeric(df[value_column], errors="coerce")
    if values.isna().any():
        raise ValueError(f"Missing or non-numeric values found in {value_column}")
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(f"Non-finite values found in {value_column}")

    units = set(df["unit"].dropna().astype(str))
    if units != {value_unit}:
        raise ValueError(f"Unexpected units: {units}; expected {value_unit!r}")

    if min_value is not None and (values < min_value).any():
        raise ValueError(f"Values below expected minimum {min_value}")
    if max_value is not None and (values > max_value).any():
        raise ValueError(f"Values above expected maximum {max_value}")

    if not dates.is_monotonic_increasing:
        raise ValueError("Time series is not sorted chronologically.")

    return {
        "rows": len(df),
        "start": dates.min(),
        "end": dates.max(),
        "missing_months": 0,
        "duplicate_months": 0,
        "min": float(values.min()),
        "max": float(values.max()),
        "unit": value_unit,
    }

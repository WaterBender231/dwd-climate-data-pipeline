from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import rasterio
from rasterio.transform import from_origin

from src.aggregate import calculate_regional_mean, extract_month
from src.validation import (
    find_missing_months,
    validate_raster,
    validate_time_series,
)


def write_test_raster(path: Path, with_alpha: bool = False) -> None:
    data = np.array([[1, 2], [3, 4]], dtype="float32")
    count = 2 if with_alpha else 1

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=2,
        height=2,
        count=count,
        dtype="float32",
        crs="EPSG:31467",
        transform=from_origin(0, 2000, 1000, 1000),
        nodata=-9999,
    ) as dst:
        dst.write(data, 1)
        if with_alpha:
            alpha = np.array([[255, 0], [255, 255]], dtype="float32")
            dst.write(alpha, 2)


def test_extract_month_from_dwd_filename():
    path = Path("cropped_grids_germany_monthly_soil_moist_199101.tif")
    assert extract_month(path) == pd.Timestamp("1991-01-01")


def test_validate_raster_checks_crs_and_resolution(tmp_path):
    raster_path = tmp_path / "sample_199101.tif"
    write_test_raster(raster_path)

    report = validate_raster(
        raster_path,
        expected_crs="EPSG:31467",
        expected_resolution=(1000.0, 1000.0),
    )

    assert report["valid_pixels"] == 4
    assert report["min"] == 1.0
    assert report["max"] == 4.0


def test_regional_mean_excludes_alpha_masked_pixel(tmp_path):
    raster_path = tmp_path / "sample_199101.tif"
    write_test_raster(raster_path, with_alpha=True)

    # The value 2 is masked by alpha=0, so mean = (1 + 3 + 4) / 3.
    assert calculate_regional_mean(raster_path) == pytest.approx(8 / 3)


def test_find_missing_months():
    dates = pd.Series(pd.to_datetime(["2020-01-01", "2020-03-01"]))
    missing = find_missing_months(dates, 2020, 2020)

    assert pd.Timestamp("2020-02-01") in missing
    assert len(missing) == 10


def test_time_series_validation_passes_complete_year():
    dates = pd.date_range("2020-01-01", "2020-12-01", freq="MS")
    df = pd.DataFrame(
        {
            "date": dates,
            "value": np.arange(12, dtype=float),
            "unit": "test-unit",
        }
    )

    report = validate_time_series(
        df,
        value_column="value",
        value_unit="test-unit",
        start_year=2020,
        end_year=2020,
    )

    assert report["rows"] == 12
    assert report["missing_months"] == 0


def test_time_series_validation_fails_on_missing_month():
    dates = pd.date_range("2020-01-01", "2020-12-01", freq="MS").delete(5)
    df = pd.DataFrame(
        {
            "date": dates,
            "value": np.arange(len(dates), dtype=float),
            "unit": "test-unit",
        }
    )

    with pytest.raises(ValueError, match="Missing monthly observations"):
        validate_time_series(
            df,
            value_column="value",
            value_unit="test-unit",
            start_year=2020,
            end_year=2020,
        )

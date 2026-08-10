from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .aggregate import build_regional_timeseries, export_csv, export_netcdf, extract_month
from .clip import clip_rasters, reproject_study_area
from .download import decompress_gzip_files, download_dataset
from .preprocess import convert_asc_to_geotiff, find_geotiffs, remove_ascii_files
from .validation import (
    require_file,
    validate_raster_collection,
    validate_time_series,
)


@dataclass
class PipelineConfig:
    region_name: str
    start_year: int
    end_year: int
    dwd_dataset_folder: str
    value_column: str
    value_unit: str
    source_crs: str
    work_dir: Path
    study_area: Path
    expected_resolution: tuple[float, float] | None = None
    min_value: float | None = None
    max_value: float | None = None

    @property
    def dwd_url(self) -> str:
        return (
            "https://opendata.dwd.de/climate_environment/CDC/"
            f"grids_germany/monthly/{self.dwd_dataset_folder}/"
        )

    @property
    def data_dir(self) -> Path:
        return (
            self.work_dir
            / "opendata.dwd.de"
            / "climate_environment"
            / "CDC"
            / "grids_germany"
            / "monthly"
            / self.dwd_dataset_folder
        )

    @property
    def output_dir(self) -> Path:
        return self.work_dir / "outputs"


def run_pipeline(config: PipelineConfig, download: bool = True) -> pd.DataFrame:
    """Run the DWD raster-to-regional-time-series workflow."""
    require_file(config.study_area, "Study-area vector")

    if download:
        print("1/7 Downloading DWD data")
        download_dataset(config.dwd_url, config.work_dir)

    if not config.data_dir.exists():
        raise FileNotFoundError(f"DWD data directory not found: {config.data_dir}")

    print("2/7 Decompressing downloaded rasters")
    decompress_gzip_files(config.data_dir)

    existing_geotiffs = find_geotiffs(config.data_dir)
    asc_files = list(config.data_dir.rglob("*.asc"))

    print("3/7 Converting ASCII grids to GeoTIFF")
    if asc_files:
        converted = convert_asc_to_geotiff(config.data_dir, config.source_crs)
        remove_ascii_files(config.data_dir)
        geotiffs = sorted(set(existing_geotiffs + converted))
    else:
        geotiffs = existing_geotiffs

    if not geotiffs:
        raise FileNotFoundError("No GeoTIFF rasters are available for processing.")

    # DWD directories can contain years outside the requested analysis period.
    # Keep only the configured months before validation, clipping and aggregation.
    start_date = pd.Timestamp(f"{config.start_year}-01-01")
    end_date = pd.Timestamp(f"{config.end_year}-12-01")
    geotiffs = [
        path for path in geotiffs
        if start_date <= extract_month(path) <= end_date
    ]

    if not geotiffs:
        raise ValueError(
            f"No rasters found between {config.start_year} and {config.end_year}."
        )

    print("4/7 Validating source rasters")
    validate_raster_collection(
        geotiffs,
        expected_crs=config.source_crs,
        expected_resolution=config.expected_resolution,
    )

    print("5/7 Reprojecting study area and clipping rasters")
    vector_dir = config.work_dir / "study_area_reprojected"
    reprojected_shape = vector_dir / "study_area.shp"
    reproject_study_area(config.study_area, config.source_crs, reprojected_shape)

    cropped_dir = config.work_dir / "cropped"
    clipped = clip_rasters(geotiffs, reprojected_shape, cropped_dir)

    # Clipped rasters retain the source CRS and resolution.
    validate_raster_collection(
        clipped,
        expected_crs=config.source_crs,
        expected_resolution=config.expected_resolution,
    )

    print("6/7 Aggregating regional monthly means")
    df = build_regional_timeseries(
        clipped,
        value_column=config.value_column,
        value_unit=config.value_unit,
    )

    print("7/7 Validating and exporting time series")
    qa = validate_time_series(
        df,
        value_column=config.value_column,
        value_unit=config.value_unit,
        start_year=config.start_year,
        end_year=config.end_year,
        min_value=config.min_value,
        max_value=config.max_value,
    )

    basename = (
        f"{config.value_column}_{config.region_name}_"
        f"{config.start_year}_{config.end_year}"
    )
    export_csv(df[["date", config.value_column, "unit"]], config.output_dir / f"{basename}.csv")
    export_netcdf(
        df,
        config.value_column,
        config.value_unit,
        config.output_dir / f"{basename}.nc",
    )

    print("QA passed:", qa)
    return df


if __name__ == "__main__":
    # Default runnable example based on the original Kerpen soil-moisture workflow.
    # Update the study_area path if your shapefile is stored somewhere else.
    config = PipelineConfig(
        region_name="Kerpen",
        start_year=1991,
        end_year=2025,
        dwd_dataset_folder="soil_moist",
        value_column="soil_moisture_nfk_percent",
        value_unit="% nFK",
        source_crs="EPSG:31467",
        work_dir=Path("data"),
        study_area=Path("data/shapefiles/kerpen/kerpen.shp"),
        expected_resolution=(1000.0, 1000.0),
    )

    result = run_pipeline(config, download=True)
    print(result)

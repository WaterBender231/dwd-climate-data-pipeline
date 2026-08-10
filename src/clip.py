from pathlib import Path
import subprocess

import geopandas as gpd


def reproject_study_area(
    study_area_path: Path,
    target_crs: str,
    output_path: Path,
) -> Path:
    """Reproject the study-area vector to the raster CRS."""
    study_area = gpd.read_file(study_area_path)

    if study_area.empty:
        raise ValueError(f"Study-area file contains no features: {study_area_path}")
    if study_area.crs is None:
        raise ValueError(f"Study-area file has no CRS: {study_area_path}")

    reprojected = study_area.to_crs(target_crs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    reprojected.to_file(output_path)

    return output_path


def clip_rasters(
    raster_paths: list[Path],
    cutline_path: Path,
    output_dir: Path,
) -> list[Path]:
    """Clip GeoTIFFs to the study area using GDAL gdalwarp."""
    if not raster_paths:
        raise ValueError("No rasters supplied for clipping.")

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    for raster_path in raster_paths:
        output_path = output_dir / f"cropped_{raster_path.name}"

        command = [
            "gdalwarp",
            "-q",
            "-cutline",
            str(cutline_path),
            "-crop_to_cutline",
            "-dstalpha",
            str(raster_path),
            str(output_path),
        ]
        subprocess.run(command, check=True)
        outputs.append(output_path)

    return outputs

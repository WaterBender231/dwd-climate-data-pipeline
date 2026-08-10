from pathlib import Path
import subprocess


def convert_asc_to_geotiff(data_dir: Path, source_crs: str) -> list[Path]:
    """Convert all DWD ASCII grids below data_dir to GeoTIFF."""
    asc_files = sorted(data_dir.rglob("*.asc"))
    outputs = []

    if not asc_files:
        raise FileNotFoundError(f"No .asc files found in {data_dir}")

    for asc_path in asc_files:
        tif_path = asc_path.with_suffix(".tif")

        command = [
            "gdal_translate",
            "-q",
            "-a_srs",
            source_crs,
            str(asc_path),
            str(tif_path),
        ]
        subprocess.run(command, check=True)
        outputs.append(tif_path)

    return outputs


def remove_ascii_files(data_dir: Path) -> int:
    """Delete decompressed ASCII grids after successful conversion."""
    asc_files = list(data_dir.rglob("*.asc"))

    for path in asc_files:
        path.unlink()

    return len(asc_files)


def find_geotiffs(data_dir: Path) -> list[Path]:
    return sorted(data_dir.rglob("*.tif"))

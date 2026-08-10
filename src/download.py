from pathlib import Path
import gzip
import shutil
import subprocess


def download_dataset(url: str, work_dir: Path) -> None:
    """Download a DWD directory recursively with wget."""
    work_dir.mkdir(parents=True, exist_ok=True)

    command = [
        "wget",
        "-r",
        "-np",
        "-R",
        "index.html*",
        url,
    ]
    subprocess.run(command, cwd=work_dir, check=True)


def decompress_gzip_files(data_dir: Path) -> list[Path]:
    """Decompress all .gz files recursively and return the created files."""
    gz_files = sorted(data_dir.rglob("*.gz"))
    created = []

    for gz_path in gz_files:
        output_path = gz_path.with_suffix("")

        with gzip.open(gz_path, "rb") as source, output_path.open("wb") as target:
            shutil.copyfileobj(source, target)

        gz_path.unlink()
        created.append(output_path)

    return created

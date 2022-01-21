import tarfile
from io import UnsupportedOperation
from pathlib import Path
from zipfile import ZipFile


def extract_archive(archive_path: Path, target_directory: Path):
    target_directory.mkdir(exist_ok=True, parents=True)

    if archive_path.name.endswith(".zip"):
        with ZipFile(archive_path) as z:
            z.extractall(target_directory)
    elif archive_path.name.endswith('.tar.gz'):
        with tarfile.open(archive_path) as tar:
            tar.extractall(target_directory)
    else:
        raise UnsupportedOperation(f"does not support archive {archive_path.name}")

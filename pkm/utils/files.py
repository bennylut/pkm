from pathlib import Path


def is_empty_directory(path: Path) -> bool:
    """
    check if the given `path` is a directory and is empty
    :param path: the path to check
    :return: if `path` is empty directory
    """

    return path.is_dir() and next(path.iterdir(), None) is None

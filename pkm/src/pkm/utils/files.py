import os
from pathlib import Path
from typing import Optional, Callable


def is_empty_directory(path: Path) -> bool:
    """
    check if the given `path` is a directory and is empty
    :param path: the path to check
    :return: if `path` is empty directory
    """

    return path.is_dir() and next(path.iterdir(), None) is None


def ensure_exists(path: Path, error_msg: Optional[Callable[[], str]] = None) -> Path:
    """
    :param path: the path to check if exists
    :param error_msg: the error message to use in case that the path does not exist
    :return: the given `path` if it exists, otherwise raise `FileNotFoundError`
    """
    if path.exists():
        return path
    raise FileNotFoundError(f"no such file or directory: {path}" if error_msg is None else error_msg())


def resolve_relativity(path: Path, parent: Path) -> Path:
    """
    :param path: the path to resolve
    :param parent: the potential parent of the path (if the path is relative)
    :return: if `path` is absolute, return `path` otherwise return `parent / path`
    """

    return path if path.is_absolute() else parent / path


def path_to(source: Path, destination: Path) -> Path:
    """
    creates a relative path from `source` to `destination`, allowing back stepping ('..')
    :param source: the path to start from
    :param destination: the path to end at
    :return: the relative path from `source` to `destination`
    """
    source = source.absolute()
    destination = destination.absolute()

    destination_parents = set(destination.parents)
    p = source
    back = 0
    while p not in destination_parents:
        p = p.parent
        back += 1
    return Path((f'..{os.sep}' * back) + str(destination.relative_to(p)))

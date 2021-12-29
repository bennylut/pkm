import os
from pathlib import Path


def is_empty_directory(path: Path) -> bool:
    """
    check if the given `path` is a directory and is empty
    :param path: the path to check
    :return: if `path` is empty directory
    """

    return path.is_dir() and next(path.iterdir(), None) is None


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

import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, Callable, ContextManager


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


@contextmanager
def temp_dir() -> ContextManager[Path]:
    """
    creates a temporary directory and return a context manager, which, when closing, deletes it
    :return:
    """

    with TemporaryDirectory() as tdir:
        yield Path(tdir)


def name_without_ext(path: Path) -> str:
    """
    extract the given path name without extensions, unlike `path.stem` this will remove all composed extensions
    like `.tar.gz`
    :param path: a path to a file, its name you want to get
    :return: the file name without any extension (read: until the first '.')
    """

    name = path.name
    try:
        return name[:name.index('.')]
    except ValueError:
        return name

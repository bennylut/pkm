from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp
from typing import Optional, Callable, ContextManager, Iterator, List, Set

from pkm.utils.commons import UnsupportedOperationException


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


class CopyTransaction:
    """
    a context manager for copy transactions,
    this keep track on a transaction of copy operations which may also overwrite existing files,
    if an uncaught exception was raised during this transaction execution, the operations are rollback
    and any overwritten file is restored
    """

    def __init__(self):
        self._copied_files: Set[Path] = set()
        self._overwritten_files: List[Path] = []  # source overwrite, temp location
        self._temp_dir: Optional[Path] = None

    def copy_tree(self, source: Path, target: Path,
                  accept: Callable[[Path], bool] = lambda _: True,
                  file_copy: Optional[Callable[[Path, Path], None]] = None):
        """
        copy the given source directory files into the target directory (creating it if necessary)
        :param source: a directory to copy files from
        :param target: a directory to copy files to
        :param accept: a predicate that is called before each copy operation, if it returns False,
                       the copy will not be made
        :param file_copy: the function that will be used to copy a file
        """

        if file_copy:
            def cp(s, d):
                file_copy(s, d)
                self.touch(d)
        else:
            cp = self.copy

        self.mkdir(target)
        for file in source.iterdir():
            if not accept(file):
                continue

            if file.is_dir():
                self.copy_tree(file, target / file.name, accept)
            else:
                cp(file, target / file.name)

    def mkdir(self, target: Path):
        """
        creates a directory in the given `target` path
        :param target: the directory path to create
        """
        if not target.exists():
            if not target.parent.exists():
                self.mkdir(target.parent)
            target.mkdir()
            self._copied_files.add(target)

    def copy(self, source: Path, target: Path):
        """
        copies the `source` file into the `target` path, if the `target` already exists, overwrite it
        :param source: the source file to copy
        :param target: the target path to copy into
        """
        if source.is_dir():
            raise UnsupportedOperationException("copy should not work with directories, use copy_tree or mkdir instead")

        if target.exists():
            self.rm(target)

        if not target.parent.exists():
            self.mkdir(target.parent)

        shutil.copy(source, target)
        self._copied_files.add(target)

    @property
    def copied_files(self) -> Iterator[Path]:
        """
        :return: list of all the files (including directories) that was created as a result of this transaction
        """
        return iter(self._copied_files)

    def touch(self, path: Path):
        """
        mark the given `path` as copied in this transaction
        :param path: the path to mark
        """
        self._copied_files.add(path)

    def rm(self, path: Path):
        temp = self._temp_dir / str(len(self._overwritten_files))
        shutil.move(path, temp)
        self._overwritten_files.append(path)

    def __enter__(self) -> CopyTransaction:
        self._temp_dir = Path(mkdtemp())
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:  # rollback
            import traceback
            traceback.print_exc()
            self._rollback()
        else:
            self._commit()

    def _commit(self):
        shutil.rmtree(self._temp_dir)
        self._temp_dir = None

    def _rollback(self):
        for file in self._copied_files:
            if not file.is_dir():
                file.unlink(missing_ok=True)

        for file in self._copied_files:
            if file.is_dir() and is_empty_directory(file):
                file.rmdir()

        for i, path in enumerate(self._overwritten_files):
            restore_path = self._temp_dir / str(i)
            shutil.move(restore_path, path)

        self._commit()

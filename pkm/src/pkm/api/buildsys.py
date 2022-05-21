"""
an implementation of pep517 & pep660 build system
"""
from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager

from pkm.api.pkm import Pkm, pkm_home, pkm
from pkm.api.projects.project import Project
from pkm.utils.files import temp_dir


# import sys
# sys.stdout = open(Path("/Users/bennyl/pkm-build.log").resolve(), "w")
# sys.stderr = open(Path("/Users/bennyl/pkm-build-err.log").resolve(), "w")


@contextmanager
def buildsys_pkm() -> ContextManager:
    if pkm_home.exists():
        yield
    else:
        import pkm.api as pkm_api
        old_pkm = pkm
        try:
            with temp_dir() as tdir:
                pkm_api.pkm = Pkm(tdir)
                yield
        finally:
            pkm_api.pkm = old_pkm


# noinspection PyUnusedLocal
def build_wheel(wheel_directory: str, config_settings=None, metadata_directory=None):
    with buildsys_pkm():
        return Project.load(Path(".")).build_wheel(Path(wheel_directory)).name


# noinspection PyUnusedLocal
def build_sdist(sdist_directory: str, config_settings=None):
    with buildsys_pkm():
        return Project.load(Path(".")).build_sdist(Path(sdist_directory)).name


# noinspection PyUnusedLocal
def get_requires_for_build_wheel(config_settings=None):
    return []


# noinspection PyUnusedLocal
def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None):
    with buildsys_pkm():
        return Project.load(Path(".")).build_wheel(Path(metadata_directory), only_meta=True).name


# noinspection PyUnusedLocal
def get_requires_for_build_sdist(config_settings=None):
    return []


# noinspection PyUnusedLocal
def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return Project.load(Path(".")).build_wheel(Path(wheel_directory), editable=True).name


# noinspection PyUnusedLocal
def get_requires_for_build_editable(config_settings=None):
    return []


# noinspection PyUnusedLocal
def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    with buildsys_pkm():
        return Project.load(Path(".")).build_wheel(Path(metadata_directory), only_meta=True, editable=True).name

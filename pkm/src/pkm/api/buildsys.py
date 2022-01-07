"""
an implementation of pep517 & pep660 build system
"""

from pathlib import Path

from pkm.api.projects.project import Project


def build_wheel(wheel_directory: str, config_settings=None, metadata_directory=None):
    return Project.load(Path(".")).build_wheel(Path(wheel_directory)).name


def build_sdist(sdist_directory: str, config_settings=None):
    return Project.load(Path(".")).build_sdist(Path(sdist_directory)).name


def get_requires_for_build_wheel(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None):
    return Project.load(Path(".")).build_wheel(Path(metadata_directory), only_meta=True).name


def get_requires_for_build_sdist(config_settings=None):
    return []


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return Project.load(Path(".")).build_wheel(Path(wheel_directory), editable=True).name


def get_requires_for_build_editable(config_settings=None):
    return []


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return Project.load(Path(".")).build_wheel(Path(metadata_directory), only_meta=True, editable=True).name

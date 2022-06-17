from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Union, Dict, Mapping, Any, Iterator, Type

from pkm.api.dependencies.dependency import Dependency
from pkm.api.dependencies.env_markers import EnvironmentMarker
from pkm.api.distributions.distinfo import EntryPoint, ObjectReference
from pkm.api.packages.package import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier, AllowAllVersions
from pkm.config.configclass import config, config_field, ConfigFieldCodec, ConfigCodec, ConfigFile
from pkm.config.configfiles import TomlConfigIO
from pkm.utils.properties import cached_property


@dataclass(eq=True)
@config
class BuildSystemConfig:
    requirements: List[Dependency] = config_field(
        key='requires',
        default_factory=lambda: [Dependency.parse('setuptools'), Dependency.parse('wheel'), Dependency.parse('pip')])
    build_backend: str = config_field(key='build-backend', default='setuptools.build_meta:__legacy__')
    backend_path: List[str] = config_field(key='backend-path')


@dataclass(eq=True)
@config
class ContactInfo:
    name: str = None
    email: str = None


def _entrypoints_from_config(group: str, ep: Dict[str, str]) -> List[EntryPoint]:
    return [EntryPoint(group, ep_name, ObjectReference.parse(ep_oref)) for ep_name, ep_oref in ep.items()]


def _entrypoints_to_config(entries: List[EntryPoint]) -> Dict[str, str]:
    return {e.name: str(e.ref) for e in entries}


PKM_DIST_CFG_TYPE_LIB = "lib"
PKM_DIST_CFG_TYPE_CAPP = "cnt-app"
PKM_DIST_CFG_TYPE_NONE = "none"


@dataclass(eq=True)
@config
class PkmDistributionConfig:
    type: str  # lib, cnt-app


@dataclass(eq=True)
@config
class PkmApplicationConfig:
    containerized: bool
    dependencies: List[Dependency]
    dependency_overwrites: Dict[str, Dependency] = config_field(key='dependency-overwrites')
    exposed_packages: List[str] = config_field(key='exposed-packages')


@dataclass(eq=True)
@config
class PkmProjectConfig:
    packages: Optional[List[str]] = None
    group: Optional[str] = None  # TODO: remove group and use conventions only?


class _TextOrFileConfigFieldCodec(ConfigFieldCodec):

    def __init__(self, allows_raw_text: bool):
        self._allows_raw_text = allows_raw_text

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> Union[Path, str, None]:
        if self._allows_raw_text and isinstance(v, str):
            return v

        if not isinstance(v, Mapping):
            raise ValueError(f"malformed value: {v}")

        if 'text' in v:
            return v['text']
        else:
            return Path(v['file'])

    def unparse(self, parent: ConfigCodec, type_: Type, v: Union[Path, str, None]) -> Any:
        if isinstance(v, Path):
            return {'file': str(v)}
        elif self._allows_raw_text:
            return v
        else:
            return {'text': v}


@dataclass(eq=True)
@config
class ProjectConfig:
    """
    the project config as described in
    https://www.python.org/dev/peps/pep-0621/, https://www.python.org/dev/peps/pep-0631/
    """

    # The name of the project.
    name: str
    # The version of the project as supported by PEP 440.
    version: Version
    # The summary description of the project.
    description: str = None
    # The people or organizations considered to be the "authors" of the project.
    authors: List[ContactInfo] = None
    # similar to "authors", exact meaning is open to interpretation.
    maintainers: List[ContactInfo] = None
    # The keywords for the project.
    keywords: List[str] = None
    # Trove classifiers (https://pypi.org/classifiers/) which apply to the project.
    classifiers: List[str] = None
    # A mapping of URLs where the key is the URL label and the value is the URL itself.
    urls: Dict[str, str] = None
    # a list of field names (from the above fields), each field name that appears in this list means that the absense of
    # data in the corresponding field means that a user tool provides it dynamically
    dynamic: List[str] = None
    # The Python version requirements of the project.
    requires_python: VersionSpecifier = config_field(key="requires-python", default=AllowAllVersions)
    # The dependencies of the project.
    dependencies: List[Dependency] = config_field(default_factory=list)
    # The optional dependencies of the project, grouped by the 'extra' name that provides them.
    optional_dependencies: Dict[str, List[Dependency]] = config_field(key="optional-dependencies", default_factory=dict)
    # The actual text or Path to a text file containing the full description of this project.
    readme: Union[Path, str, None] = config_field(codec=_TextOrFileConfigFieldCodec(True))
    # The project licence identifier or path to the actual licence file
    license: Union[str, Path, None] = config_field(codec=_TextOrFileConfigFieldCodec(False))
    # list of entry points, following https://packaging.python.org/en/latest/specifications/entry-points/.
    _entry_points: Dict[str, Dict[str, str]] = config_field(key="entry-points", default_factory=dict)
    _scripts: Dict[str, str] = config_field(key="scripts", default_factory=dict)
    _gui_scripts: Dict[str, str] = config_field(key="gui-scripts", default_factory=dict)

    leftovers = config_field(leftover=True)

    # all_fields: Dict[str, Any]

    @cached_property
    def entry_points(self) -> Mapping[str, List[EntryPoint]]:
        result: Dict[str, List[EntryPoint]] = defaultdict(list)
        if self._entry_points:
            result.update({g: _entrypoints_from_config(g, eps) for g, eps in self.entry_points.values()})
        if self._scripts:
            result[EntryPoint.G_CONSOLE_SCRIPTS] \
                .extend(_entrypoints_from_config(EntryPoint.G_CONSOLE_SCRIPTS, self._scripts))
        if self._gui_scripts:
            result[EntryPoint.G_GUI_SCRIPTS] \
                .extend(_entrypoints_from_config(EntryPoint.G_CONSOLE_SCRIPTS, self._gui_scripts))

        return result

    def all_entrypoints(self) -> List[EntryPoint]:
        if not self.entry_points:
            return []

        return [e for points in self.entry_points.values() for e in points]

    def is_dynamic(self, field: str) -> bool:
        """
        :param field: the field name (as in the configuration, e.g.,
                      optional-dependencies and not optional_dependencies)
        :return: True if the field is marked as dynamic, False otherwise
        """
        return (d := self.dynamic) and field in d  # noqa

    @cached_property
    def all_dependencies(self) -> List[Dependency]:
        all_deps = [d for d in (self.dependencies or [])]
        optional_deps = self.optional_dependencies or {}
        for od_group, deps in optional_deps.items():
            extra_rx = re.compile(f'extra\\s*==\\s*(\'{od_group}\'|"{od_group}")')
            for dep in deps:
                if not dep.env_marker or not extra_rx.match(str(dep.env_marker)):
                    new_marker = (str(dep.env_marker).rstrip(';') + ';') if dep.env_marker else ''
                    new_marker = f"{new_marker}extra==\'{od_group}\'"
                    all_deps.append(replace(dep, env_marker=EnvironmentMarker.parse_pep508(new_marker)))
                else:
                    all_deps.append(dep)
        return all_deps

    def package_descriptor(self) -> PackageDescriptor:
        return PackageDescriptor(self.name, self.version)

    def readme_content(self) -> str:
        if not self.readme:
            return ""

        if isinstance(self.readme, str):
            return self.readme

        if self.readme.exists():
            return self.readme.read_text()

        return ""

    def script_entrypoints(self) -> Iterator[EntryPoint]:
        """
        :return: iterator over the scripts (and gui scripts) entrypoints
        """
        if scripts := self.entry_points.get(EntryPoint.G_CONSOLE_SCRIPTS):
            yield from scripts

        if gui_scripts := self.entry_points.get(EntryPoint.G_GUI_SCRIPTS):
            yield from gui_scripts

    def readme_content_type(self) -> str:
        if self.readme and isinstance(self.readme, Path):
            readme_suffix = self.readme.suffix
            if readme_suffix == '.md':
                return 'text/markdown'
            elif readme_suffix == '.rst':
                return 'text/x-rst'

        return 'text/plain'

    def license_content(self) -> str:
        if not self.license:
            return ""

        if isinstance(self.license, str):
            return self.license

        return self.license.read_text()


_LEGACY_PROJECT_DYNAMIC = [
    'description', 'readme', 'requires-python', 'license', 'authors', 'maintainers', 'keywords',
    'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']


@config(io=TomlConfigIO())
class PyProjectConfiguration(ConfigFile):
    project: ProjectConfig
    pkm_project: PkmProjectConfig = config_field(key="tool.pkm.project", default_factory=PkmProjectConfig)
    build_system: BuildSystemConfig = config_field(key="build-system", default_factory=BuildSystemConfig)
    pkm_application: PkmApplicationConfig = config_field(key="tool.pkm.application")
    pkm_distribution: PkmDistributionConfig = config_field(
        key="tool.pkm.distribution", default_factory=lambda: PkmDistributionConfig(PKM_DIST_CFG_TYPE_LIB))
    _leftovers = config_field(leftover=True)

    @classmethod
    def load_effective(cls, pyproject_file: Path,
                       package: Optional[PackageDescriptor] = None) -> "PyProjectConfiguration":
        """
        load the effective pyproject file (with missing essential values filled with their legacy values)
        for example, if no build-system is available, this method will fill in the legacy build-system
        :param pyproject_file: the pyproject.toml to load
        :param package: the package that this pyproject belongs to, if given,
                        it will be used in case of missing name and version values
        :return: the loaded pyproject
        """
        pyproject = PyProjectConfiguration.load(pyproject_file)
        source_tree = pyproject_file.parent

        # ensure project:
        if not pyproject.project:
            pyproject.project = ProjectConfig(
                dynamic=_LEGACY_PROJECT_DYNAMIC, name=(package or source_tree).name,
                version=package.version if package else Version.parse('unknown_version'))

        pyproject.project.name = PackageDescriptor.normalize_name(pyproject.project.name)
        return pyproject

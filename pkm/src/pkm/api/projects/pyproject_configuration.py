from copy import copy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Union, Dict, Mapping, Any
import re

from pkm.api.dependencies.dependency import Dependency
from pkm.api.dependencies.env_markers import EnvironmentMarker
from pkm.api.distributions.distinfo import EntryPoint, ObjectReference
from pkm.api.packages.package import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion
from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.resolution.pubgrub import MalformedPackageException
from pkm.utils.dicts import remove_none_values, without_keys
from pkm.utils.files import path_to
from pkm.utils.properties import cached_property


@dataclass(frozen=True, eq=True)
class BuildSystemConfig:
    requirements: List[Dependency]
    build_backend: str
    backend_path: Optional[List[str]]


@dataclass(frozen=True, eq=True)
class ContactInfo:
    name: Optional[str] = None
    email: Optional[str] = None

    @classmethod
    def from_config(cls, contact: Dict[str, Any]) -> "ContactInfo":
        return cls(**contact)

    def to_config(self) -> Dict[str, Any]:
        return remove_none_values({
            'name': self.name, 'email': self.email
        })


def _entrypoints_from_config(group: str, ep: Dict[str, str]) -> List[EntryPoint]:
    return [EntryPoint(group, ep_name, ObjectReference.parse(ep_oref)) for ep_name, ep_oref in ep.items()]


def _entrypoints_to_config(entries: List[EntryPoint]) -> Dict[str, str]:
    return {e.name: str(e.ref) for e in entries}


@dataclass(frozen=True, eq=True)
class PkmProjectConfig:
    packages: Optional[List[str]] = None
    group: Optional[str] = None

    def to_config(self) -> Dict[str, Any]:
        return remove_none_values({
            'packages': self.packages,
            'group': self.group
        })

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> Optional["PkmProjectConfig"]:
        if not config:
            return PkmProjectConfig()

        return PkmProjectConfig(**config)


@dataclass(frozen=True, eq=True)
class PkmRepositoryInstanceConfig:
    type: str
    packages: Dict[str, Any]
    name: Optional[str]
    args: Dict[str, Any]

    def to_config(self) -> Dict[str, Any]:
        return remove_none_values({
            **self.args,
            'type': self.type,
            'packages': self.packages,
            'name': self.name
        })

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "PkmRepositoryInstanceConfig":
        config = copy(config)
        type_ = config.pop('type')
        name = config.pop('name', None)
        packages: List[Union[str, Dict]] = config.pop('packages')

        packages_dict = {}

        if packages == "*":
            packages_dict['*'] = {}
        else:
            for package in packages:
                if isinstance(package, str):
                    packages_dict[package] = {}
                else:
                    packages_dict[package['name']] = package

        args = config
        return PkmRepositoryInstanceConfig(type_, packages_dict, name, args)


@dataclass(frozen=True, eq=True)
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
    description: Optional[str]
    # The actual text or Path to a text file containing the full description of this project.
    readme: Union[Path, str, None]
    # The Python version requirements of the project.
    requires_python: Optional[VersionSpecifier]
    # The project licence identifier or path to the actual licence file
    license: Union[str, Path, None]
    # The people or organizations considered to be the "authors" of the project.
    authors: Optional[List[ContactInfo]]
    # similar to "authors", exact meaning is open to interpretation.
    maintainers: Optional[List[ContactInfo]]
    # The keywords for the project.
    keywords: Optional[List[str]]
    # Trove classifiers (https://pypi.org/classifiers/) which apply to the project.
    classifiers: Optional[List[str]]
    # A mapping of URLs where the key is the URL label and the value is the URL itself.
    urls: Optional[Dict[str, str]]
    # list of entry points, following https://packaging.python.org/en/latest/specifications/entry-points/.
    entry_points: Optional[Dict[str, List[EntryPoint]]]
    # The dependencies of the project.
    dependencies: Optional[List[Dependency]]
    # The optional dependencies of the project, grouped by the 'extra' name that provides them.
    optional_dependencies: Dict[str, List[Dependency]]
    # a list of field names (from the above fields), each field name that appears in this list means that the absense of
    # data in the corresponding field means that a user tool provides it dynamically
    dynamic: Optional[List[str]]

    all_fields: Dict[str, Any]

    @cached_property
    def all_dependencies(self) -> List[Dependency]:
        all_deps = [d for d in (self.dependencies or [])]
        optional_deps = self.optional_dependencies or {}
        for od_group, deps in optional_deps.items():
            extra_rx = re.compile(f'extra\\s*==\\s*(\'{od_group}\'|"{od_group}")')
            for dep in deps:
                if not extra_rx.match(str(dep.env_marker)):
                    new_marker = f"{str(dep.env_marker).rstrip(';')};extra=\'{od_group}\'"
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

    def to_config(self, project_path: Path) -> Dict[str, Any]:
        readme_value = None
        if self.readme:
            readme_value = self.readme if isinstance(self.readme, str) \
                else {'file': str(path_to(project_path, self.readme))}

        ep: Dict[str, List[EntryPoint]] = self.entry_points or {}
        ep_no_scripts: Dict[str, List[EntryPoint]] = without_keys(ep, 'scripts', 'gui-scripts')
        optional_dependencies = {
            extra: [str(d) for d in deps]
            for extra, deps in self.optional_dependencies.items()
        } if self.optional_dependencies else None

        license_ = None
        if self.license:
            license_ = {'file': self.license} if isinstance(self.license, Path) else {'text': self.license}

        project = {
            **self.all_fields,
            'name': self.name, 'version': str(self.version), 'description': self.description,
            'readme': readme_value, 'requires-python': str(self.requires_python) if self.requires_python else None,
            'license': license_, 'authors': [c.to_config() for c in self.authors] if self.authors is not None else None,
            'maintainers': [c.to_config() for c in self.maintainers] if self.maintainers is not None else None,
            'keywords': self.keywords, 'classifiers': self.classifiers, 'urls': self.urls,
            'scripts': _entrypoints_to_config(ep['scripts']) if 'scripts' in ep else None,
            'gui-scripts': _entrypoints_to_config(ep['gui-scripts']) if 'gui-scripts' in ep else None,
            'entry-points': {group: _entrypoints_to_config(entries)
                             for group, entries in ep_no_scripts.items()} if ep_no_scripts else None,
            'dependencies': [str(d) for d in self.dependencies] if self.dependencies else None,
            'optional-dependencies': optional_dependencies, 'dynamic': self.dynamic
        }

        return remove_none_values(project)

    @classmethod
    def from_config(cls, project_path: Path, project: Dict[str, Any]) -> "ProjectConfig":
        version = Version.parse(project['version'])

        # decide the readme value
        readme = None
        if readme_entry := project.get('readme'):
            if isinstance(readme_entry, Mapping):
                if readme_file := readme_entry.get('file'):
                    readme = project_path / readme_file
                else:
                    readme = str(readme_entry['text'])
            else:
                readme = str(readme_entry)

        requires_python = VersionSpecifier.parse(project['requires-python']) \
            if 'requires-python' in project else AnyVersion

        license_ = None
        if license_table := project.get('license'):
            license_ = (project_path / license_table['file']) if 'file' in license_table else str(license_table['text'])

        authors = None
        if authors_array := project.get('authors'):
            authors = [ContactInfo.from_config(a) for a in authors_array]

        maintainers = None
        if maintainers_array := project.get('maintainers'):
            maintainers = [ContactInfo.from_config(a) for a in maintainers_array]

        entry_points = {}
        if scripts_table := project.get('scripts'):
            entry_points['scripts'] = _entrypoints_from_config(EntryPoint.G_CONSOLE_SCRIPTS, scripts_table)

        if gui_scripts_table := project.get('gui-scripts'):
            entry_points['gui-scripts'] = _entrypoints_from_config(EntryPoint.G_GUI_SCRIPTS, gui_scripts_table)

        if entry_points_tables := project.get('entry-points'):
            entry_points.update({
                group: _entrypoints_from_config(group, entries)
                for group, entries in entry_points_tables
            })

        dependencies = None
        if dependencies_array := project.get('dependencies'):
            dependencies = [Dependency.parse_pep508(it) for it in dependencies_array]

        optional_dependencies = None
        if optional_dependencies_table := project.get('optional-dependencies'):
            optional_dependencies = {
                extra: [Dependency.parse_pep508(it) for it in deps]
                for extra, deps in optional_dependencies_table.items()
            }

        return ProjectConfig(
            name=project['name'], version=version, description=project.get('description'), readme=readme,
            requires_python=requires_python, license=license_, authors=authors, maintainers=maintainers,
            keywords=project.get('keywords'), classifiers=project.get('classifiers'), urls=project.get('urls'),
            entry_points=entry_points, dependencies=dependencies, optional_dependencies=optional_dependencies,
            dynamic=project.get('dynamic'), all_fields=project)


_LEGACY_BUILDSYS = {
    'requires': ['setuptools', 'wheel', 'pip'],
    'build-backend': 'setuptools.build_meta:__legacy__'
}

_LEGACY_PROJECT = {
    'dynamic': [
        'description', 'readme', 'requires-python', 'license', 'authors', 'maintainers', 'keywords',
        'classifiers', 'urls', 'scripts', 'gui-scripts', 'entry-points', 'dependencies', 'optional-dependencies']}


class PyProjectConfiguration(TomlFileConfiguration):
    # here due to pycharm bug https://youtrack.jetbrains.com/issue/PY-47698
    project: ProjectConfig
    pkm_project: PkmProjectConfig
    pkm_repositories: List[PkmRepositoryInstanceConfig]

    @computed_based_on("tool.pkm.project")
    def pkm_project(self) -> PkmProjectConfig:
        return PkmProjectConfig.from_config(self['tool.pkm.project'])

    @computed_based_on("tool.pkm.repositories")
    def pkm_repositories(self) -> List[PkmRepositoryInstanceConfig]:
        return [PkmRepositoryInstanceConfig.from_config(it) for it in (self["tool.pkm.repositories"] or [])]

    @computed_based_on("project")
    def project(self) -> ProjectConfig:
        project_path = self._path.parent
        project: Dict[str, Any] = self['project']
        return ProjectConfig.from_config(project_path, project)

    @project.modifier
    def set_project(self, value: ProjectConfig):
        project_path = self.path.parent
        self['project'] = value.to_config(project_path)

    @computed_based_on("build-system")
    def build_system(self) -> BuildSystemConfig:
        build_system = self['build-system']
        requirements = [Dependency.parse_pep508(dep) for dep in build_system['requires']]
        build_backend = build_system.get('build-backend')
        backend_path = build_system.get('backend-path')

        return BuildSystemConfig(requirements, build_backend, backend_path)

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

        # ensure build-system:
        if pyproject['build-system'] is None:
            if not (source_tree / 'setup.py').exists():
                raise MalformedPackageException(f"cannot infer project settings for project: {pyproject_file.parent}")

            pyproject['build-system'] = _LEGACY_BUILDSYS

        if pyproject['build-system.requires'] is None:
            pyproject['build-system.requires'] = []

        if pyproject['build-system.build-backend'] is None:
            pyproject['build-system.build-backend'] = _LEGACY_BUILDSYS['build-backend']
            pyproject['build-system.requires'] = list(
                {*_LEGACY_BUILDSYS['requires'], *pyproject['build-system.requires']})

        # ensure project:
        if not pyproject['project']:
            pyproject['project'] = {
                **_LEGACY_PROJECT,
                'name': (package or source_tree).name,
                'version': str(package.version) if package else '1.0.0'}

        pyproject['project.name'] = PackageDescriptor.normalize_name(pyproject['project.name'])
        return pyproject

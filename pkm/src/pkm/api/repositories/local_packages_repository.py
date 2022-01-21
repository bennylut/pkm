from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Dict, Optional, Any

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.repositories.repository import Repository, RepositoryBuilder
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor
from pkm.api.repositories.source_builds_repository import SourceBuildsRepository
from pkm.api.versions.version import Version
from pkm.utils.files import is_empty_directory
from pkm.utils.monitors import no_monitor


@dataclass
class LocalPackageSettings:
    name: str
    location: Path
    version: Version
    editable: bool

    def to_package_descriptor(self):
        return PackageDescriptor(self.name, self.version)

    @classmethod
    def from_config(cls, package_name: str, settings: Any):
        if not isinstance(settings, Dict):
            raise ValueError(f"illegal setting for local package repository in package: {package_name}")

        try:
            return LocalPackageSettings(
                package_name, Path(settings['path']), Version.parse(settings['version']),
                settings.get('editable', True) is True)
        except Exception as e:
            raise ValueError(f"illegal setting for local package repository in package: {package_name}") from e


class LocalPackagesRepository(Repository):

    def __init__(self, name: str, workspace: Path, build_packages_repo: Repository,
                 package_settings: Dict[str, LocalPackageSettings]):
        super().__init__(name)
        self._package_settings = package_settings
        self._packages_cache: Dict[str, Package] = {}

        workspace.mkdir(parents=True, exist_ok=True)
        if not is_empty_directory(workspace):
            raise ValueError("received workspace must be an empty directory")

        self._build_repo = SourceBuildsRepository(workspace, build_packages_repo)

    def accepts(self, dependency: Dependency) -> bool:
        return dependency.package_name in self._package_settings

    def _do_match(self, dependency: Dependency, *, monitor: RepositoryOperationsMonitor) -> List[Package]:
        monitor.on_dependency_match(dependency)

        if cache := self._packages_cache.get(dependency.package_name):
            return [cache]

        if not (settings := self._package_settings.get(dependency.package_name)):
            raise KeyError(f"no settings are provided to find local package {dependency.package_name}")

        package = LocalPackage(settings, self._build_repo)
        self._packages_cache[dependency.package_name] = package
        return [package]


class LocalPackage(Package):

    def __init__(self, settings: LocalPackageSettings, builds_repo: SourceBuildsRepository):
        self._desc = settings.to_package_descriptor()
        self._settings = settings
        self._builds_repo = builds_repo
        self._build_cache: Dict[str, Package] = {}

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def _get_or_create_delegate(self, env: Environment) -> Package:
        key = str(env.interpreter_path.resolve())
        if cache := self._build_cache.get(key):
            return cache

        package = self._builds_repo.build(
            self.descriptor, self._settings.location, env, self._settings.editable, self._builds_repo)
        self._build_cache[key] = package
        return package

    def _all_dependencies(self, environment: "Environment", monitor: PackageOperationsMonitor) -> List["Dependency"]:
        return self._get_or_create_delegate(environment)._all_dependencies(environment, monitor)

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._get_or_create_delegate(env).is_compatible_with(env)

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None,
                   *, monitor: PackageOperationsMonitor = no_monitor(),
                   build_packages_repo: Optional["Repository"] = None):
        self._get_or_create_delegate(env).install_to(
            env, user_request, monitor=monitor,
            build_packages_repo=build_packages_repo)


class LocalPackagesRepositoryBuilder(RepositoryBuilder):

    def __init__(self, build_packages_repo: Repository):
        super().__init__('local')
        self._build_packages_repo = build_packages_repo

    def build(self, name: Optional[str], package_settings: Dict[str, Any], **kwargs: Any) -> Repository:
        parsed_settings = {
            package: LocalPackageSettings.from_config(package, settings)
            for package, settings in package_settings.items()
        }

        return LocalPackagesRepository(
            name or 'local-packages', Path(TemporaryDirectory().name),
            self._build_packages_repo, parsed_settings)

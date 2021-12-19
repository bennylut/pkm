import hashlib
from abc import abstractmethod, ABC
from dataclasses import dataclass
from io import UnsupportedOperation
from pathlib import Path
from typing import List, Set, Dict, Optional, Union

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.site_packages import SitePackages, InstalledPackage
from pkm.api.repositories import Repository, DelegatingRepository
from pkm.api.versions.version import Version, NamedVersion
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.resolution.dependency_resolver import resolve_dependencies
from pkm.utils.properties import cached_property

_DEPENDENCIES_T = Union[Dependency, str, List[Union[Dependency, str]]]
_PACKAGE_NAMES_T = Union[str, List[str]]


@dataclass(frozen=True)
class CompatibilityTag:
    interpreter: str
    abi: str
    platform: str

    @classmethod
    def parse_tags(cls, tag: str) -> "Set[CompatibilityTag]":
        tags = set()
        interpreters, abis, platforms = tag.split("-")
        for interpreter in interpreters.split("."):
            for abi in abis.split("."):
                for platform_ in platforms.split("."):
                    tags.add(cls(interpreter, abi, platform_))
        return tags

    def __str__(self):
        return f'{self.interpreter}-{self.abi}-{self.platform}'


class Environment(ABC):

    @property
    @abstractmethod
    def path(self) -> Path:
        """
        :return: the path for this environment root directory
        """

    @abstractmethod
    def sysconfig_path(self, type: str) -> Optional[Path]:
        """
        :param type: the type of path to return (purelib, platlib, scripts, data)
        :return: the path to site packages
        """

    @property
    def name(self) -> str:
        return self.path.name

    def __repr__(self):
        return f"Environment({self.path})"

    @property
    @abstractmethod
    def interpreter_version(self) -> Version:
        """
        :return: the version of the environment's python interpreter
        """

    @property
    @abstractmethod
    def interpreter_path(self) -> Path:
        """
        :return: the path for the environment's python interpreter
        """

    @property
    @abstractmethod
    def compatibility_tags(self) -> Set[str]:
        """
        :return: pep425 compatibility tags
        """

    @property
    @abstractmethod
    def markers(self) -> Dict[str, str]:
        """
        :return: pep508 environment markers  
        """

    @cached_property
    def site_packages(self) -> SitePackages:
        return SitePackages({self.sysconfig_path('platlib'), self.sysconfig_path('purelib')})

    @cached_property
    def markers_hash(self) -> str:
        """
        :return: a hash built from the environment's markers, can be used to identify instances of this environment
        """
        sorted_markers = sorted(self.markers.items(), key=lambda item: item[0])
        marker_str = ';'.join(f"{k}={v}" for k, v in sorted_markers)
        return hashlib.md5(marker_str).hexdigest()

    @abstractmethod
    def reload(self):
        """
        reload volatile information about this environment (like the installed packages)
        """

    def install(self, dependencies: _DEPENDENCIES_T, repository: Repository, user_requested: bool = True):
        """
        retrieve the `dependencies` from the `repository` together with all their dependencies and install them inside
        this environment, making sure to not break any pre-installed "user-requested" packages
        (but may upgrade their dependencies if it needs to)

        :param dependencies: the dependency to install
        :param repository: the repository to fetch this dependency from
        :param user_requested: indicator that the user requested this dependency themselves
            (this will be marked on the installation as per pep376)
        """

        self.reload()

        preinstalled_packages = list(self.site_packages.installed_packages())
        pre_requested_deps = {p: p.user_request for p in preinstalled_packages if p.user_request}
        new_deps = {d.package_name: d for d in _coerce_dependencies(dependencies)}

        all_deps = {**pre_requested_deps, **new_deps}
        user_request = _UserRequestPackage(list(all_deps.values()))
        installation_repo = _InstallationRepository(repository, preinstalled_packages, user_request)

        installation = self._compute_clean_install(user_request.to_dependency(), installation_repo)
        _sync_package(self, installation)

        self.reload()

        for package, dep in new_deps.items():
            self.site_packages.installed_package(package).mark_user_requested(dep)

    def remove(self, packages: _PACKAGE_NAMES_T) -> Set[str]:
        """
        attempt to remove the required packages from this env together will all the dependencies that may become orphan
        as a result of this step.

        if a package `p in packages` is a dependency (directly or indirectly) of another
        "user requested" package `q not in packages` then `p` will be kept in the environment but its
        "user requested" flag will be removed (if it was existed)

        :param packages: the package names to remove
        :return the set of package names that were successfully removed from the environment
        """

        self.reload()

        preinstalled_packages = list(self.site_packages.installed_packages())
        requested_deps = {p: p.user_request for p in preinstalled_packages if p.user_request}
        for package_name in packages:
            requested_deps.pop(package_name)

        user_request = _UserRequestPackage(list(requested_deps.values()))
        installation_repo = _RemovalRepository(preinstalled_packages, user_request)

        installation = self._compute_clean_install(user_request.to_dependency(), installation_repo)
        _sync_package(self, installation)

        kept = {p.name for p in installation}

        for p in packages:
            if p in kept:
                self.site_packages.installed_package(p).unmark_user_requested()

        self.reload()
        return {p for p in packages if p not in kept}

    def _compute_clean_install(self, dependency: Dependency, repository: Repository) -> List[Package]:
        """
        compute the list of packages from the given `repository` that should be installed in this
        environment in order to have the given `dependency` fulfilled.
        while computing this list, you should not take into consideration any packages that are already in this environment
        :param dependency: the dependency to fulfil
        :param repository: the repository contains the packages
        :return: the computed list of packages
        """

        return resolve_dependencies(dependency, self, repository)


def _sync_package(env: Environment, packages: List[Package]):
    preinstalled: Dict[str, InstalledPackage] = {p.name: p for p in env.site_packages.installed_packages()}
    toinstall: Dict[str, Package] = {p.name: p for p in packages}

    for package_to_install in toinstall.values():
        if preinstalled_package := preinstalled.pop(package_to_install.name, None):
            if preinstalled_package.version == package_to_install.version:
                continue
            preinstalled_package.uninstall()
        package_to_install.install_to(env)

    for package_to_remove in preinstalled.values():
        package_to_remove.uninstall()


class UninitializedEnvironment(Environment):
    """
    defines an uninitialized (= empty/non-existing directory) virtual environment
    use this together with a package from the local-pythons repository to install a specific python version
    into this environment, then you can call the [to_initialized] method to get a virtual-env instance.
    """

    def __init__(self, path: Path):
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    @property
    def interpreter_version(self) -> Version:
        raise UnsupportedOperation('uninitialized environment')

    @property
    def interpreter_path(self) -> Path:
        raise UnsupportedOperation('uninitialized environment')

    def install(self, dependency: Dependency, repository: Repository, requested: bool = True):
        raise UnsupportedOperation('uninitialized environment')

    @property
    def compatibility_tags(self) -> Set[str]:
        return set()

    def sysconfig_path(self, type: str) -> Optional[Path]:
        return None

    @property
    def markers(self) -> Dict[str, str]:
        return dict()

    def reload(self):
        pass


class _UserRequestPackage(Package):
    def __init__(self, request: List[Dependency]):
        self._desc = PackageDescriptor("installation request", NamedVersion(""))
        self._request = request

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        return self._request

    def is_compatible_with(self, env: "Environment") -> bool: return True

    def install_to(self, env: "Environment", user_request: Optional[Dependency] = None): pass

    def to_dependency(self) -> Dependency:
        return Dependency(self.name, SpecificVersion(self.version))


class _RemovalRepository(Repository):

    def __init__(self, preinstalled: List[InstalledPackage], user_request: Package):
        super().__init__('removal repository')
        self._preinstalled: Dict[str, InstalledPackage] = {p.name: p for p in preinstalled}
        self._user_request = user_request

    def accepts(self, dependency: Dependency) -> bool:
        return True

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if dependency.package_name == self._user_request.name:
            return [self._user_request]

        return [self._preinstalled[dependency.package_name]]


class _InstallationRepository(DelegatingRepository):
    def __init__(self, repo: Repository, installed_packages: List[InstalledPackage], user_request: Package):
        super().__init__(repo)
        self._user_request = user_request
        self._installed_packages: Dict[str, InstalledPackage] = {p.name: p for p in installed_packages}

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if dependency.package_name == self._user_request.name:
            return [self._user_request]

        return self._repo._do_match(dependency)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        packages = self._repo._sort_by_priority(dependency, packages)

        if installed := self._installed_packages.get(dependency.package_name):
            packages.sort(key=lambda it: 0 if installed.version == it.version else 1)

        return packages


def _coerce_dependencies(dependencies: _DEPENDENCIES_T) -> List[Dependency]:
    if isinstance(dependencies, str):
        return [Dependency.parse_pep508(dependencies)]
    if isinstance(dependencies, Dependency):
        return [dependencies]
    return [d for deps in dependencies for d in deps]


def _coerce_package_names(package_names: _PACKAGE_NAMES_T) -> List[str]:
    if isinstance(package_names, str):
        return [package_names]
    return package_names

import hashlib
import os
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import List, Set, Dict, Optional, Union, TypeVar

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment_introspection import EnvironmentIntrospection
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.site_packages import SitePackages, InstalledPackage
from pkm.api.repositories.repository import Repository, DelegatingRepository
from pkm.api.versions.version import NamedVersion, StandardVersion
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.resolution.dependency_resolver import resolve_dependencies
from pkm.utils.commons import SupportsLessThanEq
from pkm.utils.iterators import find_first
from pkm.utils.properties import cached_property, clear_cached_properties

_DEPENDENCIES_T = Union[Dependency, str, List[Union[Dependency, str]]]
_PACKAGE_NAMES_T = Union[str, List[str]]
_T = TypeVar("_T")


class Environment:

    def __init__(self, env_path: Path, interpreter_path: Optional[Path] = None, readonly: bool = False):
        self._env_path = env_path
        self._interpreter_path = interpreter_path
        self._readonly = readonly

    @property
    def path(self) -> Path:
        """
        :return: the path for this environment root directory
        """
        return self._env_path

    @cached_property
    def _introspection(self) -> EnvironmentIntrospection:
        if self._readonly:
            return EnvironmentIntrospection.compute(self.interpreter_path)
        return EnvironmentIntrospection.load_or_compute(
            self._env_path / 'etc/pkm/env_introspection.json', self.interpreter_path, True)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def paths(self) -> Dict[str, str]:
        """
        :return: environment paths as returned by `sysconfig.getpaths()`
        """
        return self._introspection.paths

    def __repr__(self):
        return f"Environment({self.path})"

    @cached_property
    def interpreter_version(self) -> StandardVersion:
        """
        :return: the version of the environment's python interpreter
        """
        return StandardVersion(release=tuple(self._introspection.interpreter_version))

    @cached_property
    def interpreter_path(self) -> Path:
        """
        :return: the path for the environment's python interpreter
        """
        if self._interpreter_path is None:
            self._interpreter_path = _find_interpreter(self._env_path)
            if not self._interpreter_path:
                raise ValueError("could not determine the environment interpreter path")
        return self._interpreter_path

    def compatibility_tag_score(self, tag: str) -> Optional[SupportsLessThanEq]:
        """
        compute the compatibility score for the given pep425 compatibility tag
        :param tag: the pep425 compatibility tag
        :return: an opaque score object that support __le__ and __eq__ operations (read: comparable)
                 which can be treated as a score (read: higher is better)
        """
        return self._introspection.compatibility_score(tag)

    @cached_property
    def markers(self) -> Dict[str, str]:
        """
        :return: pep508 environment markers  
        """
        return self._introspection.compute_markers()

    @cached_property
    def site_packages(self) -> SitePackages:
        return self._introspection.create_site_packages(False)

    @cached_property
    def markers_hash(self) -> str:
        """
        :return: a hash built from the environment's markers, can be used to identify instances of this environment
        """
        sorted_markers = sorted(self.markers.items(), key=lambda item: item[0])
        marker_str = ';'.join(f"{k}={v}" for k, v in sorted_markers)
        return hashlib.md5(marker_str).hexdigest()

    def run_proc(self, args: List[str], **subprocess_run_kwargs) -> CompletedProcess:
        """
        execute the given command in a new process, the process will be executed with its path adjusted to include this
        venv binaries and scripts

        :param args: the command to execute
        :param subprocess_run_kwargs: any argument that is accepted by `subprocess.run` (aside from args)
        :return: a `CompletedProcess` instance describing the completion of the requested process
        """
        env = {}
        if extra_env := subprocess_run_kwargs.get('env'):
            env.update(extra_env)
        else:
            env.update(os.environ)

        bin_name = 'Scripts' if self._introspection.is_windows_env() else 'bin'
        path_addition = str(self._env_path / bin_name)

        if 'PATH' not in env:
            env['PATH'] = path_addition
        else:
            env['PATH'] = f"{path_addition}{os.pathsep}{env['PATH']}"

        subprocess_run_kwargs['env'] = env
        return subprocess.run(args, **subprocess_run_kwargs)

    def reload(self):
        """
        reload volatile information about this environment (like the installed packages)
        """
        clear_cached_properties(self)

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

        installation = resolve_dependencies(user_request.to_dependency(), self, installation_repo)
        _sync_package(self, installation, repository)

        self.reload()

        if user_requested:
            for package, dep in new_deps.items():
                if installed_package := self.site_packages.installed_package(package):
                    # note that the package may not get installed if the dependency is not required for our specific environment
                    installed_package.mark_user_requested(dep)

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

        installation = resolve_dependencies(user_request.to_dependency(), self, installation_repo)
        _sync_package(self, installation, None)

        kept = {p.name for p in installation}

        for p in packages:
            if p in kept:
                self.site_packages.installed_package(p).unmark_user_requested()

        self.reload()
        return {p for p in packages if p not in kept}

    @staticmethod
    def is_valid(path: Path) -> bool:
        """
        :param path: a path that may contain a python environment
        :return: true if this path contains a python environment
        """
        return (path / "pyvenv.cfg").exists() and _find_interpreter(path) is not None


def _sync_package(env: Environment, packages: List[Package], build_packages_repo: Optional[Repository]):
    preinstalled: Dict[str, InstalledPackage] = {p.name: p for p in env.site_packages.installed_packages()}
    toinstall: Dict[str, Package] = {p.name: p for p in packages}
    
    if toinstall and not build_packages_repo:
        raise ValueError("sync requires installation but no build-packages repository was provided")
    
    for package_to_install in toinstall.values():
        if preinstalled_package := preinstalled.pop(package_to_install.name, None):
            if preinstalled_package.version == package_to_install.version:
                continue

            preinstalled_package.uninstall()

            
        package_to_install.install_to(env, build_packages_repo)

    for package_to_remove in preinstalled.values():
        package_to_remove.uninstall()


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

    def install_to(self, env: "Environment", build_packages_repo: Repository, user_request: Optional[Dependency] = None): pass

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
    return [cd for dep in dependencies for cd in _coerce_dependencies(dep)]


def _coerce_package_names(package_names: _PACKAGE_NAMES_T) -> List[str]:
    if isinstance(package_names, str):
        return [package_names]
    return package_names


def _find_interpreter(env_root: Path) -> Optional[Path]:
    return find_first((env_root / "bin/python", env_root / "bin/python.exe"), lambda it: it.exists())

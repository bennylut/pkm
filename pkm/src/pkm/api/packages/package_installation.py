from __future__ import annotations

from _ast import Set
from abc import ABC
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Union, Set, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package_installation_info import StoreMode
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_monitors import PackageOperationMonitoredOp
from pkm.api.packages.site_packages import InstalledPackage
from pkm.api.packages.site_packages import SitePackages
from pkm.api.repositories.repository import Repository, AbstractRepository
from pkm.api.versions.version import StandardVersion
from pkm.api.versions.version_specifiers import VersionMatch, StandardVersionRange, AllowAllVersions
from pkm.resolution.dependency_resolver import resolve_dependencies
from pkm.resolution.pubgrub import UnsolvableProblemException
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.delegations import delegate
from pkm.utils.ipc import IPCPackable
from pkm.utils.iterators import first_or_none
from pkm.utils.multiproc import ProcessPoolExecutor
from pkm.utils.promises import Promise, await_all_promises_or_cancel
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.environments.package_containers import PackageContainers


@dataclass
class PackageInstallationTarget:  # TODO: maybe rename into package installation site?
    env: "Environment"
    stdlib: str
    platstdlib: str
    platinclude: str
    purelib: str
    platlib: str
    include: str
    data: str
    scripts: str

    @cached_property
    def site_packages(self) -> "SitePackages":
        from pkm.api.packages.site_packages import SitePackages
        return SitePackages(self.env, Path(self.purelib), Path(self.platlib))

    @cached_property
    def package_containers(self) -> "PackageContainers":
        from pkm.api.environments.package_containers import PackageContainers
        return PackageContainers(self)

    def reload(self):
        clear_cached_properties(self)

    def uninstall(self, packages_to_remove: List[str]) -> Set[str]:
        """
        attempt to remove the required packages from this target together will all the dependencies
        that may become orphan as a result of this step.

        if a package `p in packages` is a dependency (directly or indirectly) of another
        "user requested" package `q not in packages` then `p` will be kept in the target but its
        "user requested" flag will be removed (if it was existed)

        :param packages_to_remove: the package names to remove
        :return the set of package names that were successfully removed from the environment
        """

        self.reload()

        preinstalled_packages = list(self.site_packages.installed_packages())
        requested_deps = {p.name: p.user_request for p in preinstalled_packages if p.user_request}
        for package_name in packages_to_remove:
            requested_deps.pop(package_name, None)

        user_request = _UserRequestPackage(list(requested_deps.values()))
        installation_repo = _RemovalRepository(preinstalled_packages, user_request)

        installation = resolve_dependencies(user_request.to_dependency(), self, installation_repo)
        InstallationPlan(self, installation, {}).execute()

        kept = {p.name for p in installation}

        for p in packages_to_remove:
            if p in kept:
                self.site_packages.installed_package(p).dist_info.unmark_as_user_requested()

        self.reload()
        return {p for p in packages_to_remove if p not in kept}

    def install(
            self, dependencies: List[Dependency], repository: Optional[Repository] = None, user_requested: bool = True,
            dependencies_override: Optional[Dict[str, Dependency]] = None,
            store_mode: Optional[Dict[str, StoreMode]] = None, updates: Optional[List[str]] = None):
        """
        installs the given set of dependencies into this target.
        see: `prepare_installation` and `PreparedInstallation:install` for more information about this method arguments
        """
        if not dependencies:
            return  # nothing to do...

        repository = repository or self.env.attached_repository
        plan = self.plan_installation(
            dependencies, repository, user_requested, dependencies_override, updates
        )
        plan.store_modes = store_mode
        plan.execute()

    def force_remove(self, package: str) -> bool:
        """
        forcefully remove the required package, will not remove its dependencies and will not check if other packages
        depends on it - use this method with care (or don't use it at all :) )
        :param package: the name of the package to be removed
        :return: True if the package was found and removed, False otherwise
        """
        if installed := self.site_packages.installed_package(package):
            installed.uninstall()
            return True
        return False

    def plan_installation(
            self, dependencies: List[Dependency], repository: Repository,
            user_requested: bool = True, dependencies_override: Optional[Dict[str, Dependency]] = None,
            updates: Optional[List[str]] = None, unspecified_spec_packages: Optional[List[str]] = None
    ) -> InstallationPlan:
        """
        plan but does not install an installation for the given dependencies.
        resolve the `dependencies` using the given `repository`, making sure to not break any pre-installed
        "user-requested" packages (but may upgrade their dependencies if it needs to)

        :param dependencies: the dependency to install
        :param repository: the repository to fetch this dependency from, if not given will use the attached repository
        :param user_requested: indicator that the user requested this dependency themselves
            (this will be marked on the installation as per pep376)
        :param dependencies_override: mapping from package name into dependency that should be "forcefully"
            used for this package
        :param unspecified_spec_packages: when installing, the user may give some packages with unspecified version spec
                so that the system should attempt to find the best version to install for these packages,
                you can and should provide these here, the planner uses this information to better plan the installation
        :param updates: If given, the packages listed will be updated if required and already installed
        """

        self.reload()

        updates = set(updates or ())
        preinstalled_packages = [p for p in self.site_packages.installed_packages() if p.name_key not in updates]
        pre_requested_deps = {p.name_key: p.user_request for p in preinstalled_packages if p.user_request}
        unspecified_spec_packages = \
            unspecified_spec_packages or [
                d.package_name_key
                for d in dependencies if d.version_spec is AllowAllVersions]

        unspecified_spec_packages = set(unspecified_spec_packages)

        new_deps = {d.package_name_key: d for d in dependencies}
        all_deps = {**pre_requested_deps, **new_deps}

        run_slow_path = False
        installation = None

        try:
            # first we try the fast path: only adding packages without updating
            # but requiring latest matching versions of new user requested packages
            user_request = _UserRequestPackage(list(new_deps.values()))
            installation_repo = _InstallationRepository(
                repository, preinstalled_packages, user_request, unspecified_spec_packages, True)

            installation = resolve_dependencies(
                user_request.to_dependency(), self, installation_repo, dependencies_override)

            installation_names = {i.name_key for i in installation}
            for preinstalled in preinstalled_packages:
                if preinstalled.name_key not in installation_names:
                    installation.append(preinstalled)

        except UnsolvableProblemException:
            # don't execute the slow path code here so that the stacktrace will be cleaner if exception will happen
            run_slow_path = True

        if run_slow_path:
            # if we cannot we try the slow path in which we allow preinstalled packages dependencies to be updated
            user_request = _UserRequestPackage(list(all_deps.values()))
            installation_repo = _InstallationRepository(
                repository, preinstalled_packages, user_request, unspecified_spec_packages, False)
            installation = resolve_dependencies(
                user_request.to_dependency(), self, installation_repo)

        user_requests = {**pre_requested_deps}
        if user_requested:
            user_requests.update(new_deps)

        return InstallationPlan(self, installation, user_requests)


class PackageOperation(Enum):
    INSTALL = "install"
    UPDATE = "update"
    REMOVE = "remove"
    SKIP = "skip"


class InstallationPlan:
    def __init__(self, target: PackageInstallationTarget, packages: List[Package],
                 user_requests: Dict[str, "Dependency"]):
        self.default_target = target
        self.packages = packages
        self.user_requests = user_requests
        self.store_modes: Optional[Dict[str, StoreMode]] = None

    def selected_package(self, name: str) -> Optional[Package]:
        return first_or_none(it for it in self.packages if it.name == name)

    def compute_operations_for_target(
            self, target: Optional[PackageInstallationTarget] = None) -> Dict[Package, PackageOperation]:

        operations: Dict[Package, PackageOperation] = {}

        target = target or self.default_target

        preinstalled: Dict[str, InstalledPackage] = {
            p.name_key: p
            for p in target.site_packages.installed_packages()}

        toinstall: Dict[str, Package] = {
            p.name_key: p
            for p in self.packages
            if not isinstance(p, _UserRequestPackage)}

        store_modes = {name: value for name, value in (self.store_modes or {}).items()}

        for name_key, package_to_install in toinstall.items():

            if preinstalled_package := preinstalled.pop(name_key, None):
                if preinstalled_package.version == package_to_install.version:
                    prev_store_mode = preinstalled_package.installation_info.store_mode
                    store_mode = store_modes.get(name_key, StoreMode.AUTO)
                    store_mode_matching = (store_mode == StoreMode.AUTO or store_mode == prev_store_mode)
                    new_user_request = self.user_requests.get(preinstalled_package.name_key)
                    user_request_matching = \
                        (not new_user_request) or preinstalled_package.user_request == new_user_request

                    if store_mode_matching and user_request_matching:
                        operations[package_to_install] = PackageOperation.SKIP
                        continue
                    if store_mode_matching and not user_request_matching:
                        # note that i am attaching the operation to the preinstalled package instead of the real package
                        # this is for performance reasons - no need to really reinstall the package, only change the
                        # user request flag
                        operations[preinstalled_package] = PackageOperation.UPDATE
                        continue

                operations[package_to_install] = PackageOperation.UPDATE
            else:
                operations[package_to_install] = PackageOperation.INSTALL

        for package_to_remove in preinstalled.values():
            operations[package_to_remove] = PackageOperation.REMOVE

        return operations

    def execute(self, target: Optional[PackageInstallationTarget] = None):
        """
        executes the prepared installation inside the given `target`
        :param target: the site in which to execute this installation
        """

        from pkm.api.pkm import pkm

        target = target or self.default_target
        operations = self.compute_operations_for_target(target)
        store_modes = self.store_modes or {}
        site = target.site_packages

        tasks: List[_PackageOperationTask] = []

        for package, operation in operations.items():
            if operation == PackageOperation.SKIP:
                continue

            store_mode = store_modes.get(package.name_key, StoreMode.AUTO)
            user_request = self.user_requests.get(package.name_key)
            tasks.append(_PackageOperationTask(package, operation, store_mode, user_request, target))

        parallelism = pkm.config.concurrency_mode
        threads = pkm.threads if parallelism != "none" else None

        if parallelism == "proc" and sum(1 for it in tasks if it.can_be_multiprocessesd()) > 1:
            procpool = pkm.processes
            await_all_promises_or_cancel([task.execute(threads, procpool) for task in tasks])

        else:
            await_all_promises_or_cancel([task.execute(threads, None) for task in tasks])

        site.reload()


class _PackageOperationTask:
    def __init__(self, package: Package, operation: PackageOperation, store_mode: StoreMode,
                 user_request: Optional[Dependency], target: PackageInstallationTarget):
        self._package = package
        self._operation = operation
        self._store_mode = store_mode
        self._user_request = user_request
        self._target = target

    def can_be_multiprocessesd(self):
        return isinstance(self._package, IPCPackable)

    def execute(self, threadpool: ThreadPoolExecutor, procpool: Optional[ProcessPoolExecutor]) -> Promise:
        operation, store_mode, user_request, package, target = \
            self._operation, self._store_mode, self._user_request, self._package, self._target

        executor = procpool if self.can_be_multiprocessesd() and procpool else threadpool

        promise = None
        if operation == PackageOperation.INSTALL:
            promise = Promise.execute(
                executor, _po_execute, package, "install_to", target, store_mode=store_mode, user_request=user_request)

        elif operation == PackageOperation.UPDATE:
            promise = Promise.execute(
                executor, _po_execute, package, "update_at", target, store_mode=store_mode, user_request=user_request)
        elif operation == PackageOperation.REMOVE:
            promise = Promise.execute(executor, _po_execute, package, "uninstall")

        if not promise:
            raise UnsupportedOperationException(f"unsupported package operation {self._operation}")

        return PackageOperationMonitoredOp(package.descriptor, operation).with_async(promise)


def _po_execute(package: Package, mtd: str, *args, **kwargs):
    getattr(package, mtd)(*args, **kwargs)


class _UserRequestPackage(Package):
    def __init__(self, request: List["Dependency"]):
        self._desc = PackageDescriptor("installation request", StandardVersion(release=(0,)))
        self._request = request

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def dependencies(
            self, target: "PackageInstallationTarget", extras: Optional[List[str]] = None) -> List["Dependency"]:
        return self._request

    def is_compatible_with(self, env: "Environment") -> bool: return True

    def install_to(self, *args, **kwargs): pass

    def to_dependency(self) -> "Dependency":
        return Dependency(self.name, VersionMatch(self.version))


class _RemovalRepository(AbstractRepository):

    def __init__(self, preinstalled: List[InstalledPackage], user_request: Package):
        super().__init__('removal repository')
        self._preinstalled: Dict[str, InstalledPackage] = {
            p.name_key: p
            for p in preinstalled
        }

        self._user_request = user_request

    def _do_match(self, dependency: "Dependency", env: Environment) -> List[Package]:
        if dependency.package_name == self._user_request.name:
            return [self._user_request]

        match = self._preinstalled.get(dependency.package_name_key)
        return [_RemovalPackage(match)] if match else []


class _RemovalPackage(Package, IPCPackable):

    def __init__(self, p: InstalledPackage):
        self.package = p

    def __getstate__(self):
        return [self.package]

    def __setstate__(self, state):
        self.__init__(*state)

    @property
    def descriptor(self) -> PackageDescriptor:
        return self.package.descriptor

    def dependencies(
            self, target: "PackageInstallationTarget", extras: Optional[List[str]] = None) -> List["Dependency"]:
        sitep = target.site_packages
        return [d for d in self.package.dependencies(target, extras) if sitep.installed_package(d.package_name)]

    def is_compatible_with(self, env: "Environment") -> bool:
        return self.package.is_compatible_with(env)

    def install_to(self, target: "PackageInstallationTarget", user_request: Optional["Dependency"] = None,
                   store_mode: StoreMode = StoreMode.AUTO):
        raise UnsupportedOperationException()

    def update_at(self, target: "PackageInstallationTarget", user_request: Optional["Dependency"] = None,
                  store_mode: StoreMode = StoreMode.AUTO):
        self.package.update_at(target, user_request, store_mode)


@delegate(Repository, '_repo')
class _InstallationRepository(Repository, ABC):
    def __init__(
            self, repo: Repository, installed_packages: List[InstalledPackage], user_request: Package,
            unspecified_spec_packages: Set[str], fast_plan_mode: bool):

        assert repo, "no repository provided"
        self._user_request = user_request
        self._installed_packages: Dict[str, InstalledPackage] = {p.name_key: p for p in installed_packages}
        self._fast_plan_mode = fast_plan_mode
        self._unspecified_spec_packages = unspecified_spec_packages
        self._repo = repo

    def match(self, dependency: Union["Dependency", str], env: Environment) -> List[Package]:
        if isinstance(dependency, str):
            dependency = Dependency.parse(dependency)

        if dependency.package_name_key == self._user_request.name_key:
            return [self._user_request]

        if installed := self._installed_packages.get(dependency.package_name_key):
            # installed = _UpdatableInstalledPackage(installed, self._repo)
            if self._fast_plan_mode:
                return [installed]

        packages = self._repo.match(dependency, env)
        if installed:
            packages.sort(key=lambda it: 0 if installed.version == it.version else 1)
        elif self._fast_plan_mode and dependency.package_name_key in self._unspecified_spec_packages:
            max_version_package = max(packages, key=lambda it: it.version)
            if not isinstance(max_version_package.version, StandardVersion):
                unspecified_limit = VersionMatch(max_version_package.version)
            else:
                unspecified_limit = StandardVersionRange.create_range(
                    min_=max_version_package.version.without_patch(), includes_min=True)
            packages = [p for p in packages if unspecified_limit.allows_version(p.version)]

        return packages

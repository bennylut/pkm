from typing import List, Dict, Tuple, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages import Package, PackageDescriptor
from pkm.api.repositories import Repository
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.utils.commons import unone

from pkm_main.installation.packages_lock import PackagesLock
from pkm_main.utils.http.http_client import HttpException
from pkm_main.versions.pubgrub import Problem, Term, Solver, MalformedPackageException


class PackageInstallationPlan:

    def __init__(self, env: Environment, install: List[Package], remove: List[str]):
        self._env = env
        self._install = install
        self._remove = remove

    def execute(self, env: Optional[Environment]):
        env = unone(env, lambda: self.environment)
        print("PACKAGE INSTALLATION PLAN EXECUTION IS NOT IMPLEMENTED YET")

    @property
    def environment(self) -> Environment:
        """
        :return: the environment that this plan was generated for
        """
        return self._env

    @property
    def packages_to_remove(self) -> List[str]:
        """
        :return: list of package names to remove from the environment
        """

        return self._remove

    @property
    def packages_to_install(self) -> List[Package]:
        """
        :return: list of packages to install to the environment
        """

        return self._install

    @classmethod
    def create(cls, root: Dependency, env: Environment, repo: Repository,
               lock: Optional[PackagesLock] = None) -> "PackageInstallationPlan":
        """
        creates an installation plan to install [root] on [env] using packages from [repo]
        while considering the given [lock]

        :param root: the package to install
        :param env: the environment to install into
        :param repo: the repository to use in order to retrieve packages
        :param lock: the lock to consider
        :return: the result installation plan
        """

        lock = unone(lock, lambda: PackagesLock())
        problem = _PkmPackageInstallationProblem(env, lock, repo, root)
        solver = Solver(problem, root.package_name)
        solution = solver.solve()

        already_installed_packages: Dict[str, PackageDescriptor] = {p.name: p for p in env.installed_packages}

        to_install: List[Package] = []
        to_remove: List[str] = []

        for package_with_extras, version in solution.items():

            package, extras = _decode_package_and_extras(package_with_extras)
            if extras:
                continue

            if package in already_installed_packages:
                if already_installed_packages[package] != version:
                    to_install.append(problem.opened_packages[PackageDescriptor(package, version)])
                    to_remove.append(package)
            else:
                to_install.append(problem.opened_packages[PackageDescriptor(package, version)])

        for pd in already_installed_packages.values():
            if pd.name not in solution:
                to_remove.append(pd.name)

        return PackageInstallationPlan(env, to_install, to_remove)


class _PkmPackageInstallationProblem(Problem):

    def __init__(self, env: Environment, lock: PackagesLock, repo: Repository, root: Dependency):
        self._env = env
        self._lock = lock
        self._repo = repo
        self._root = root

        self.opened_packages: Dict[PackageDescriptor, Package] = {}

    def get_dependencies(self, package: str, version: Version) -> List[Term]:
        package_name, extras = _decode_package_and_extras(package)
        descriptor = PackageDescriptor(package_name, version)

        try:
            dependencies = self.opened_packages[descriptor].dependencies(self._env, extras)
        except (ValueError, HttpException) as e:
            raise MalformedPackageException(str(descriptor)) from e

        result: List[Term] = []
        if extras:
            result.append(Term(package_name, SpecificVersion(version)))

        for d in dependencies:
            if d.is_applicable_for(self._env, extras):
                term_package = _encode_package_and_extras(d.package_name, d.extras)
                term_spec = d.version_spec

                result.append(Term(term_package, term_spec))

        return result

    def get_versions(self, package: str) -> List[Version]:

        package_name, extras = _decode_package_and_extras(package)

        if package_name == self._root.package_name:
            package_by_version = {p.version: p for p in self._repo.match(self._root)
                                  if p.is_compatible_with(self._env)}
        else:
            package_by_version = {p.version: p for p in self._repo.list(package_name)
                                  if p.is_compatible_with(self._env)}

        for package in package_by_version.values():
            self.opened_packages[package.descriptor] = package

        result: List[Version] = []

        installed = self._env.installed_version(package_name)
        if installed:
            pd = package_by_version.pop(installed, None)
            if pd:
                result.append(pd.version)

        locked_packages: List[PackageDescriptor] = self._lock.locked_versions(self._env, package_name)
        for locked_package in locked_packages:
            pd = package_by_version.pop(locked_package.version)
            if pd:
                result.append(pd.version)

        sorted_packages_left = sorted((p.version for p in package_by_version.values()), reverse=True)
        result.extend(sorted_packages_left)

        return result


def _decode_package_and_extras(package: str) -> Tuple[str, Optional[List[str]]]:
    if '[' not in package:
        return package, None

    package_name, extras = package.split('[')
    extras = extras[:-1].split(',')

    return package_name, extras


def _encode_package_and_extras(package_name: str, extras: Optional[List[str]]) -> str:
    if not extras:
        return package_name

    return f"{package_name}[{','.join(extras)}]"

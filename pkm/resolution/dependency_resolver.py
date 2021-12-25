from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.repositories import Repository
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.resolution.pubgrub import Problem, MalformedPackageException, Term, Solver
from pkm_main.utils.http.http_client import HttpException

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


def resolve_dependencies(root: Dependency, env: "Environment", repo: Repository) -> List[Package]:
    problem = _PkmPackageInstallationProblem(env, repo, root)
    solver = Solver(problem, root.package_name)
    solution: Dict[str, Version] = solver.solve()

    result: List[Package] = []

    for package_with_extras, version in solution.items():
        package, extras = _decode_package_and_extras(package_with_extras)
        if extras:
            continue

        result.append(problem.opened_packages[PackageDescriptor(package, version)])

    return result


class _PkmPackageInstallationProblem(Problem):

    def __init__(self, env: "Environment", repo: Repository, root: Dependency):
        self._env = env
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
        pacakges = [p for p in self._repo.list(package_name) if p.is_compatible_with(self._env)]

        for package in pacakges:
            self.opened_packages[package.descriptor] = package

        return [p.version for p in pacakges]


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

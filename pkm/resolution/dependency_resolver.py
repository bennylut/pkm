from typing import List, Dict, Tuple, Optional, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.resolution.pubgrub import Problem, MalformedPackageException, Term, Solver
from pkm.utils.dicts import get_or_put
from pkm.utils.promises import Promise

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.repositories.repository import Repository


def resolve_dependencies(root: Dependency, env: "Environment", repo: "Repository") -> List[Package]:
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

    def __init__(self, env: "Environment", repo: "Repository", root: Dependency):
        self._env = env
        self._repo = repo
        self._root = root

        from pkm.api.pkm import pkm
        self._threads = pkm.threads

        self.opened_packages: Dict[PackageDescriptor, Package] = {}
        self._prefetched_packages: Dict[str, Promise[List[Package]]] = {}

    def _prefetch(self, package_name: str) -> Promise[List[Package]]:
        return get_or_put(self._prefetched_packages, package_name,
                          lambda: Promise.execute(self._threads, self._repo.list, package_name))

    def get_dependencies(self, package: str, version: Version) -> List[Term]:
        package_name, extras = _decode_package_and_extras(package)
        descriptor = PackageDescriptor(package_name, version)

        try:
            dependencies = self.opened_packages[descriptor].dependencies(self._env, extras)

            for d in dependencies:
                self._prefetch(d.package_name)

        except (ValueError, IOError) as e:
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

        all_packages = self._prefetch(package_name).result()
        pacakges = [p for p in all_packages if p.is_compatible_with(self._env)]

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

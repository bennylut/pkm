from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Dict, Optional, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.repositories.source_builds_repository import BuildError
from pkm.api.versions.version import Version, UrlVersion
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.resolution.pubgrub import Problem, MalformedPackageException, Term, Solver
from pkm.utils.dicts import get_or_put
from pkm.utils.promises import Promise
from pkm.utils.sequences import single_or_raise

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.repositories.repository import Repository


def resolve_dependencies(root: Dependency, env: "Environment", repo: "Repository") -> List[Package]:
    problem = _PkmPackageInstallationProblem(env, repo, root)
    solver = Solver(problem, _Pkg.of(root))
    solution: Dict[_Pkg, Version] = solver.solve()

    result: List[Package] = []

    for pkg, version in solution.items():
        if pkg.extras:
            continue

        result.append(problem.opened_packages[PackageDescriptor(pkg.name, version)])

    return result


class _PkmPackageInstallationProblem(Problem):

    def __init__(self, env: "Environment", repo: "Repository", root: Dependency):
        self._env = env
        self._repo = repo
        self._root = root

        from pkm.api.pkm import pkm
        self._threads = pkm.threads

        self.opened_packages: Dict[PackageDescriptor, Package] = {}
        self._prefetched_packages: Dict[_Pkg, Promise[List[Package]]] = {}

    def _prefetch(self, package: _Pkg) -> Promise[List[Package]]:
        print(f"prefetching {package}")
        return get_or_put(self._prefetched_packages, package,
                          lambda: Promise.execute(self._threads, self._repo.list, package.name))

    def get_dependencies(self, package: _Pkg, version: Version) -> List[Term]:
        print(f"get dependencies for {package}")
        descriptor = PackageDescriptor(package.name, version)

        try:
            if isinstance(version, UrlVersion) and descriptor not in self.opened_packages:
                self.opened_packages[descriptor] = single_or_raise(self._repo.match(f"{package} @ {version}"))

            dependencies = self.opened_packages[descriptor] \
                .dependencies(self._env, package.extras)

            for d in dependencies:
                if not d.version_spec.specific_url():
                    self._prefetch(_Pkg.of(d))

        except (ValueError, IOError, BuildError) as e:
            raise MalformedPackageException(str(descriptor)) from e

        result: List[Term] = []

        if package.extras:  # add the package itself together with its extras
            result.append(Term(replace(package, extras=None), SpecificVersion(version)))

        for d in dependencies:
            if d.is_applicable_for(self._env, package.extras):
                result.append(Term(_Pkg.of(d), d.version_spec))

        return result

    def get_versions(self, package: _Pkg) -> List[Version]:
        print(f"get versions for {package}")
        all_packages = self._prefetch(package).result()
        packages = [p for p in all_packages if p.is_compatible_with(self._env)]

        for package in packages:
            self.opened_packages[package.descriptor] = package

        print(f"done get versions for {package}")
        return [p.version for p in packages]


@dataclass(frozen=True, eq=True)
class _Pkg:
    name: str
    extras: Optional[List[str]]

    def __str__(self):
        result = self.name
        if self.extras:
            result += "[" + ', '.join(self.extras) + "]"
        return result

    def __repr__(self):
        return self.__str__()

    @classmethod
    def of(cls, d: Dependency) -> _Pkg:
        return _Pkg(d.package_name, d.extras)

from typing import List, Dict, Optional
from unittest import TestCase

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.repositories.repository import AbstractRepository
from pkm.api.versions.version import Version


class TestRepository(TestCase):
    def test_filter_prereleases(self):
        repo = DummyRepository({
            'x': ['1.2a', '1.2'],
            'y': ['1.1a', '1.1.7a']
        })

        ecurrent = Environment.current()

        def match(dep: str):
            return repo.match(dep, ecurrent)

        assert_match(match('x ==1.2a'), '1.2a')
        assert_match(match('x ==1.2'), '1.2')
        assert_match(match('x >=1.2'), '1.2')
        assert_match(match('x <1.3'), '1.2')
        assert_match(match('x *'), '1.2')
        assert_match(match('x < 1.3a'), '1.2a', '1.2')

        assert_match(match('y *'), '1.1a', '1.1.7a')
        assert_match(match('y < 1.1'), '1.1a')
        assert_match(match('y > 1'), '1.1a', '1.1.7a')
        assert_match(match('y == 1.1'))


def assert_match(packages: List[Package], *expected_versions: str):
    assert len(packages) == len(
        expected_versions), f'expecting {len(expected_versions)} packages but got {len(packages)}'
    parsed_expected_versions = [Version.parse(v) for v in expected_versions]
    for package in packages:
        assert package.version in parsed_expected_versions, f'unexpected version: {package.version}'


class DummyRepository(AbstractRepository):

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        # monitor.on_dependency_match(dependency)
        packages: List[Package] = self._packages[dependency.package_name] or []
        return self._sorted_by_version([p for p in packages if dependency.version_spec.allows_version(p.version)])

    def __init__(self, packages: Dict[str, List[str]]):
        super().__init__('dummy')
        self._packages: Dict[str, List[Package]] = {
            package_name: [DummyPackage(package_name, version) for version in versions]
            for package_name, versions in packages.items()
        }


class DummyPackage(Package):

    def __init__(self, name: str, version: str):
        self._desc = PackageDescriptor(name, Version.parse(version))

    def dependencies(
            self, target: "PackageInstallationTarget",
            extras: Optional[List[str]] = None) -> List["Dependency"]:
        return []

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def is_compatible_with(self, env: Environment):
        return True

    def install_to(self, *args, **kwargs): pass

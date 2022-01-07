from typing import List, Optional, Dict
from unittest import TestCase

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.repositories.repository import Repository

from pkm.api.versions.version import Version
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import no_monitor


class TestRepository(TestCase):
    def test_filter_prereleases(self):
        repo = DummyRepository({
            'x': ['1.2a', '1.2'],
            'y': ['1.1a', '1.1.7a']
        })

        assert_match(repo.match('x ==1.2a'), '1.2a')
        assert_match(repo.match('x ==1.2'), '1.2')
        assert_match(repo.match('x >=1.2'), '1.2')
        assert_match(repo.match('x <1.3'), '1.2')
        assert_match(repo.match('x *'), '1.2')
        assert_match(repo.match('x < 1.3a'), '1.2a', '1.2')

        assert_match(repo.match('y *'), '1.1a', '1.1.7a')
        assert_match(repo.match('y < 1.1'), '1.1a')
        assert_match(repo.match('y > 1'), '1.1a', '1.1.7a')
        assert_match(repo.match('y == 1.1'))


def assert_match(packages: List[Package], *expected_versions: str):
    assert len(packages) == len(
        expected_versions), f'expecting {len(expected_versions)} packages but got {len(packages)}'
    parsed_expected_versions = [Version.parse(v) for v in expected_versions]
    for package in packages:
        assert package.version in parsed_expected_versions, f'unexpected version: {package.version}'


class DummyRepository(Repository):

    def _do_match(self, dependency: Dependency) -> List[Package]:
        packages: List[Package] = self._packages[dependency.package_name] or []
        return [p for p in packages if dependency.version_spec.allows_version(p.version)]

    def __init__(self, packages: Dict[str, List[str]]):
        super().__init__('dummy')
        self._packages: Dict[str, List[Package]] = {
            package_name: [DummyPackage(package_name, version) for version in versions]
            for package_name, versions in packages.items()
        }

    def accepts(self, dependency: Dependency) -> bool:
        return True


class DummyPackage(Package):

    def _all_dependencies(self, environment: "Environment", monitor: FetchResourceMonitor) -> List["Dependency"]:
        return []

    def __init__(self, name: str, version: str):
        self._desc = PackageDescriptor(name, Version.parse(version))

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def is_compatible_with(self, env: Environment):
        return True

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None,
                   *, monitor: FetchResourceMonitor = no_monitor()):
        pass

from pathlib import Path
from typing import List, Dict, Any, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.standard_package import AbstractPackage, StandardPackageArtifact
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.utils.http.cache_directive import CacheDirective
from pkm.utils.http.http_client import HttpClient


class PyPiRepository(Repository):

    def __init__(self, http: HttpClient):
        super().__init__('pypi')
        self._http = http

    def accepts(self, dependency: Dependency) -> bool:
        return not dependency.is_url_dependency

    def _do_match(self, dependency: Dependency) -> List[Package]:
        json: Dict[str, Any] = self._http \
            .fetch_resource(f'https://pypi.org/pypi/{dependency.package_name}/json', cache=CacheDirective.ask_for_update()) \
            .read_data_as_json()

        package_info: Dict[str, Any] = json['info']
        packages: List[PypiPackage] = []
        releases: Dict[str, Any] = json['releases']
        for version_str, release in releases.items():

            relevant_artifacts = []
            for a in release:
                if not a.get('yanked') and a.get("packagetype") in ("sdist", "bdist_wheel"):
                    if sa := _create_artifact_from_pypi_release(a):
                        relevant_artifacts.append(sa)

            if relevant_artifacts:
                version = Version.parse(version_str)
                if dependency.version_spec.allows_version(version):
                    packages.append(PypiPackage(
                        PackageDescriptor(dependency.package_name, version),
                        relevant_artifacts, self
                    ))

        return packages


# noinspection PyProtectedMember
class PypiPackage(AbstractPackage):

    def __init__(self, descriptor: PackageDescriptor, artifacts: List[StandardPackageArtifact], repo: PyPiRepository):
        super().__init__(descriptor, artifacts)
        self._repo = repo

    def _retrieve_artifact(self, artifact: StandardPackageArtifact) -> Path:
        url = artifact.other_info.get('url')
        if not url:
            raise KeyError(f'could not find url in given artifact info: {artifact}')

        resource = self._repo._http.fetch_resource(url)
        if not resource:
            raise FileNotFoundError(f'cannot find requested artifact: {artifact.file_name}')

        return resource.data

    def _all_dependencies(self, environment: "Environment", build_packages_repo: Repository) -> List[Dependency]:
        json: Dict[str, Any] = self._repo._http \
            .fetch_resource(f'https://pypi.org/pypi/{self.name}/{self.version}/json') \
            .read_data_as_json()

        requires_dist = json['info'].get('requires_dist')
        if requires_dist is None:
            return super(PypiPackage, self)._all_dependencies(environment, build_packages_repo)

        return [Dependency.parse_pep508(dstr) for dstr in requires_dist]


def _create_artifact_from_pypi_release(release: Dict[str, Any]) -> Optional[StandardPackageArtifact]:
    requires_python = release.get('requires_python')
    package_type = release.get('packagetype')
    python_version: Optional[str] = release.get('python_version')

    file_name: str = release.get('filename')
    is_binary = package_type == 'bdist_wheel' or file_name.endswith('.whl')

    if not file_name:
        return None

    return StandardPackageArtifact(
        file_name, 'bdist_wheel' if is_binary else 'sdist',
        VersionSpecifier.parse(requires_python) if requires_python else None,
        python_version,
        release
    )

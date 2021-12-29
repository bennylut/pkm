from io import UnsupportedOperation
from pathlib import Path
from typing import List, Dict, Any, Optional

import pkginfo
from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.standard_package import AbstractPackage, StandardPackageArtifact
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier

from pkm_main.utils.http.cache_directive import CacheDirective
from pkm_main.utils.http.http_client import HttpClient


class PyPiRepository(Repository):

    def __init__(self, http: HttpClient):
        super().__init__('pypi')
        self._http = http

    def accepts(self, dependency: Dependency) -> bool:
        return not dependency.is_url_dependency

    def _do_match(self, dependency: Dependency) -> List[Package]:
        json: Dict[str, Any] = self._http \
            .get(f'https://pypi.org/pypi/{dependency.package_name}/json', cache=CacheDirective.ask_for_update()) \
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

        resource = self._repo._http.get(url)
        if not resource:
            raise FileNotFoundError(f'cannot find requested artifact: {artifact.file_name}')

        return resource.data

    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        json: Dict[str, Any] = self._repo._http \
            .get(f'https://pypi.org/pypi/{self.name}/{self.version}/json') \
            .read_data_as_json()

        requires_dist = json['info'].get('requires_dist')
        if requires_dist is None:
            # we cannot know if that means that we dont have dependencies or that a tool choose to not specify them
            # so we must download it..
            artifact = self._best_artifact_for(environment)
            if not artifact:
                raise UnsupportedOperation(
                    "attempting to compute dependencies for environment that is not supported by this package")

            resource = self._retrieve_artifact(artifact)
            filename = artifact.file_name
            if filename.endswith('.whl'):
                info = pkginfo.Wheel(str(resource))
            else:
                info = pkginfo.SDist(str(resource))

            requires_dist = info.requires_dist

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
#
#
# _ArtifactInfo = Dict[str, Any]
#
#
# class _PyPiPackage(Package):
#
#     def __init__(
#             self, pypi: PyPiRepository, desc: PackageDescriptor,
#             package_info: Dict[str, Any], artifacts: List[_ArtifactInfo]):
#         self._desc = desc
#         self._pypi = pypi
#         self._package_info = package_info
#         self._artifacts = artifacts
#
#     def __str__(self):
#         return f"PyPiPackage({self.name} {self.version})"
#
#     def __repr__(self):
#         return str(self)
#
#     def _download_artifact(self, artifact: _ArtifactInfo) -> FetchedResource:
#         url = artifact.get('url')
#         if not url:
#             raise KeyError(f'could not find url in given artifact info: {artifact}')
#
#         resource = self._http.get(url)
#         filename: str = artifact['filename']
#         if not resource:
#             raise FileNotFoundError(f'cannot find requested artifact: {filename}')
#
#         return resource
#
#     def _best_artifact_for(self, env: Environment) -> Optional[_ArtifactInfo]:
#         env_interpreter = env.interpreter_version
#         env_ctags = env.compatibility_tags
#
#         # we prefer binary distributions, so if we found a matching source dist we store it until
#         # we see that there is binary option
#         best_source_dist: Optional[_ArtifactInfo] = None
#
#         for artifact in self._artifacts:
#             requires_python = artifact.get('requires_python')
#             package_type = artifact.get('packagetype')
#             python_version: Optional[str] = artifact.get('python_version')
#
#             if python_version and not python_version.startswith(('cp', 'py')):
#                 python_version = None  # guard from malformed python versions
#
#             file_name: str = artifact.get('filename')
#             is_binary = package_type == 'bdist_wheel' or file_name.endswith('.whl')
#
#             if requires_python:
#                 try:
#                     requires_python_spec = VersionSpecifier.parse(requires_python)
#                     if not requires_python_spec.allows_version(env_interpreter):
#                         continue
#                 except ValueError:
#                     console.log(
#                         'could not parse python requirements for artifact:'
#                         f' {file_name} of {self.name}=={self.version}, skipping it')
#                     continue
#
#             if is_binary:
#                 ctags_unparsed = '-'.join(without_suffix(file_name, '.whl').split('-')[-3:])
#                 ctags = set(str(it) for it in CompatibilityTag.parse_tags(ctags_unparsed))
#                 if ctags.isdisjoint(env_ctags):
#                     continue
#             elif python_version:
#                 if f'{python_version}-none-any' not in env_ctags:
#                     continue
#
#             if is_binary:
#                 return artifact
#             else:
#                 best_source_dist = best_source_dist or artifact
#
#         return best_source_dist
#
#     @property
#     def descriptor(self) -> PackageDescriptor:
#         return self._desc
#
#     @property
#     def _http(self) -> HttpClient:
#         # noinspection PyProtectedMember
#         return self._pypi._http
#
#     def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
#         json: Dict[str, Any] = self._http \
#             .get(f'https://pypi.org/pypi/{self.name}/{self.version}/json') \
#             .read_data_as_json()
#
#         requires_dist = json['info'].get('requires_dist')
#         if requires_dist is None:
#             # we cannot know if that means that we dont have dependencies or that a tool choose to not specify them
#             # so we must download it..
#             artifact = self._best_artifact_for(environment)
#             if not artifact:
#                 raise UnsupportedOperation(
#                     "attempting to compute dependencies for environment that is not supported by this package")
#
#             resource = self._download_artifact(artifact)
#             filename = artifact['filename']
#             if filename.endswith('.whl'):
#                 info = pkginfo.Wheel(str(resource.data))
#             else:
#                 info = pkginfo.SDist(str(resource.data))
#
#             requires_dist = info.requires_dist
#
#         return [Dependency.parse_pep508(dstr) for dstr in requires_dist]
#
#     def is_compatible_with(self, env: Environment):
#         return self._best_artifact_for(env) is not None
#
#     def install_to(self, env: Environment):
#         pass

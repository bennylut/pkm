from abc import abstractmethod
from dataclasses import dataclass, field
from io import UnsupportedOperation
from pathlib import Path
from typing import Optional, Any, Dict, List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.api.distributions.source_distribution import SourceDistribution
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import no_monitor
from pkm.utils.strings import without_suffix
from pkm.utils.types import SupportsLessThanEq


@dataclass(frozen=True, eq=True)
class StandardPackageArtifact:
    file_name: str
    requires_python: Optional[VersionSpecifier] = None
    other_info: Dict[str, Any] = field(default_factory=dict)

    def is_wheel(self):
        return self.file_name.endswith(".whl")


class AbstractPackage(Package):

    def __init__(self, descriptor: PackageDescriptor, artifacts: List[StandardPackageArtifact]):
        self._descriptor = descriptor
        self._artifacts = artifacts
        self._dependencies_per_artifact_id: Dict[int, List["Dependency"]] = {}
        self._path_per_artifact_id: Dict[int, Path] = {}

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._descriptor

    def _best_artifact_for(self, env: Environment) -> Optional[StandardPackageArtifact]:

        env_interpreter = env.interpreter_version

        source_dist: Optional[StandardPackageArtifact] = None
        best_binary_dist: Optional[StandardPackageArtifact] = None
        best_binary_dist_score: Optional[SupportsLessThanEq] = None

        for artifact in self._artifacts:
            requires_python = artifact.requires_python

            file_name: str = artifact.file_name
            is_binary = artifact.is_wheel()

            if requires_python:
                try:
                    if not requires_python.allows_version(env_interpreter):
                        continue
                except ValueError:
                    print(
                        'could not parse python requirements for artifact:'
                        f' {file_name} of {self.name}=={self.version}, skipping it')
                    continue

            if is_binary:
                ctag = '-'.join(without_suffix(file_name, '.whl').split('-')[-3:])
                if (score := env.compatibility_tag_score(ctag)) is not None:
                    if best_binary_dist_score is None or best_binary_dist_score < score:
                        best_binary_dist = artifact
                        best_binary_dist_score = score

            else:
                source_dist = artifact

        return best_binary_dist or source_dist

    def is_compatible_with(self, env: Environment):
        return self._best_artifact_for(env) is not None

    @abstractmethod
    def _retrieve_artifact(self, artifact: StandardPackageArtifact, monitor: FetchResourceMonitor) -> Path:
        """
        retrieve the given artifact, storing it to the file system and returning it
        :param artifact: the artifact to retrieve
        :param monitor: in case where the artifact needs to be fetched, this should be used as the monitor
        :return: the stored artifact
        """

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None,
                   *, monitor: PackageOperationsMonitor = no_monitor(),
                   build_packages_repo: Optional["Repository"] = None):

        monitor.on_install(self, env)

        artifact = self._best_artifact_for(env)
        artifact_path = self._get_or_retrieve_artifact_path(artifact, monitor)

        if artifact.is_wheel():
            WheelDistribution(self.descriptor, artifact_path).install_to(env, user_request)
        else:
            SourceDistribution(self.descriptor, artifact_path, build_packages_repo).install_to(env, user_request)

    def _get_or_retrieve_artifact_path(self, artifact, monitor):
        if not (artifact_path := self._path_per_artifact_id.get(id(artifact))):
            with monitor.on_fetch(self.descriptor) as fetch_monitor:
                artifact_path = self._retrieve_artifact(artifact, monitor=fetch_monitor)
                self._path_per_artifact_id[id(artifact)] = artifact_path
        return artifact_path

    def _all_dependencies(self, environment: "Environment", monitor: PackageOperationsMonitor) -> List["Dependency"]:
        artifact = self._best_artifact_for(environment)
        if not artifact:
            raise UnsupportedOperation(
                "attempting to compute dependencies for environment that is not supported by this package")

        if deps := self._dependencies_per_artifact_id.get(id(artifact)):
            return deps
        resource = self._get_or_retrieve_artifact_path(artifact, monitor)
        filename = artifact.file_name
        if filename.endswith('.whl'):
            info = WheelDistribution(self.descriptor, resource) \
                .extract_metadata(environment, monitor=monitor)
        else:
            info = SourceDistribution(self.descriptor, resource) \
                .extract_metadata(environment, monitor=monitor)

        self._dependencies_per_artifact_id[id(artifact)] = info.dependencies
        return info.dependencies

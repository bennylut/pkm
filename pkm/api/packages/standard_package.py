from abc import abstractmethod
from dataclasses import dataclass, field
from io import UnsupportedOperation
from pathlib import Path
from typing import Optional, Any, Dict, List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.environments.environment import Environment, CompatibilityTag
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.logging.console import console
from pkm.utils.strings import without_suffix


@dataclass
class StandardPackageArtifact:
    file_name: str  # in pypi: 'filename'
    distribution: str # Literal['bdist_wheel', 'sdist']  # in pypi: 'packagetype'
    python_version_spec: Optional[VersionSpecifier] = None  # in pypi: 'requires_python'
    python_implementation_spec: Optional[str] = None  # in pypi: 'python_version'
    other_info: Dict[str, Any] = field(default_factory=dict)


class StandardPackage(Package):

    def __init__(self, descriptor: PackageDescriptor, artifacts: List[StandardPackageArtifact]):
        self._descriptor = descriptor
        self._artifacts = artifacts

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._descriptor

    def _best_artifact_for(self, env: Environment) -> Optional[StandardPackageArtifact]:
        env_interpreter = env.interpreter_version
        env_ctags = env.compatibility_tags

        # we prefer binary distributions, so if we found a matching source dist we store it until
        # we see that there is binary option
        best_source_dist: Optional[StandardPackageArtifact] = None

        for artifact in self._artifacts:
            requires_python = artifact.python_version_spec
            package_type = artifact.distribution
            python_version = artifact.python_implementation_spec

            if python_version and not python_version.startswith(('cp', 'py')):
                python_version = None  # guard from malformed python versions

            file_name: str = artifact.file_name
            is_binary = package_type == 'bdist_wheel'

            if requires_python:
                try:
                    if not requires_python.allows_version(env_interpreter):
                        continue
                except ValueError:
                    console.log(
                        'could not parse python requirements for artifact:'
                        f' {file_name} of {self.name}=={self.version}, skipping it')
                    continue

            if is_binary:
                ctags_unparsed = '-'.join(without_suffix(file_name, '.whl').split('-')[-3:])
                ctags = set(str(it) for it in CompatibilityTag.parse_tags(ctags_unparsed))
                if ctags.isdisjoint(env_ctags):
                    continue
            elif python_version:
                if f'{python_version}-none-any' not in env_ctags:
                    continue

            if is_binary:
                return artifact
            else:
                best_source_dist = best_source_dist or artifact

        return best_source_dist

    def is_compatible_with(self, env: Environment):
        return self._best_artifact_for(env) is not None

    @abstractmethod
    def _retrieve_artifact(self, artifact: StandardPackageArtifact) -> Path:
        """
        retrieve the given artifact, storing it to the file system and returning it
        :param artifact: the artifact to retrieve
        :return: the stored artifact
        """

    def install_to(self, env: Environment, user_request: Optional[Dependency] = None):
        artifact = self._best_artifact_for(env)
        with self._retrieve_artifact(artifact) as artifact_path:
            if artifact.distribution == 'bdist_wheel':
                WheelDistribution(artifact_path).install(env, user_request)
            else:
                raise UnsupportedOperation("installing non-wheel packages is not supported yet")

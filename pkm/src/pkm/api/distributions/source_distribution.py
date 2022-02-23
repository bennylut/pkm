from pathlib import Path
from typing import Optional, TYPE_CHECKING

from pkm.api.distributions.distribution import Distribution
from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.pkm import pkm

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class SourceDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, archive: Path):
        self._package = package
        self.archive = archive

    @property
    def owner_package(self) -> PackageDescriptor:
        return self._package

    def extract_metadata(self, env: "Environment") -> PackageMetadata:
        return pkm.source_build_cache.get_or_build_meta(env, self)

    def install_to(self, env: "Environment", user_request: Optional[Dependency] = None, editable: bool = False):
        WheelDistribution(self.owner_package, pkm.source_build_cache.get_or_build_wheel(env, self)) \
            .install_to(env, user_request)

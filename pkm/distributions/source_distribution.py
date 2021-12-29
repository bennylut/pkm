from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.repositories.repository import Repository
from pkm.distributions.distribution import Distribution
from pkm.utils.archives import extract_archive


class SourceDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, archive: Path):
        self._package = package
        self._archive = archive

    @property
    def owner_package(self) -> PackageDescriptor:
        return self._package

    def install_to(self, env: Environment, build_packages_repo: Repository, user_request: Optional[Dependency] = None):
        from pkm.api import pkm
        builds = pkm.repositories.source_builds

        prebuilt = builds.match(self.owner_package.to_dependency())
        if prebuilt and prebuilt[0].is_compatible_with(env):
            return prebuilt[0].install_to(env, build_packages_repo, user_request)

        with TemporaryDirectory() as source_tree:
            source_tree = Path(source_tree)
            extract_archive(self._archive, source_tree)

            # attempt to resolve nested source trees
            while True:
                itd = source_tree.iterdir()
                maybe_source_tree = next(itd, None)
                if maybe_source_tree and maybe_source_tree.is_dir() and next(itd, None) is None:
                    source_tree = maybe_source_tree
                else:
                    break

            builds\
                .build(self.owner_package, source_tree, env, build_packages_repo)\
                .install_to(env, build_packages_repo, user_request)



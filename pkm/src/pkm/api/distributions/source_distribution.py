from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, ContextManager, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distribution import Distribution
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.pkm import pkm
from pkm.api.repositories.repository import Repository
from pkm.utils.archives import extract_archive

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class SourceDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, archive_or_source_tree: Path,
                 build_requirements_repository: Optional[Repository] = None):
        self._build_requirements_repository = build_requirements_repository
        self._package = package
        if archive_or_source_tree.is_dir():
            self._source_tree_path = archive_or_source_tree
            self._archive_path = None
        else:
            self._archive_path = archive_or_source_tree
            self._source_tree_path = None

    @property
    def owner_package(self) -> PackageDescriptor:
        return self._package

    def extract_metadata(self, env: "Environment") -> PackageMetadata:
        builds = pkm.repositories.source_builds

        with self._source_tree() as source_tree:
            return builds.build_or_get_metadata(self.owner_package, source_tree, env,
                                                self._build_requirements_repository)

    @contextmanager
    def _source_tree(self) -> ContextManager[Path]:
        if self._source_tree_path:
            yield self._source_tree_path
            return

        with TemporaryDirectory() as source_tree:
            source_tree = Path(source_tree)
            extract_archive(self._archive_path, source_tree)

            # attempt to resolve nested source trees
            while True:
                itd = source_tree.iterdir()
                maybe_source_tree = next(itd, None)
                if maybe_source_tree and maybe_source_tree.is_dir() and next(itd, None) is None:
                    source_tree = maybe_source_tree
                else:
                    break

            yield source_tree

    def install_to(self, env: "Environment", user_request: Optional[Dependency] = None, editable: bool = False):

        from pkm.api.pkm import pkm
        builds = pkm.repositories.source_builds
        prebuilt = builds.match(self.owner_package.to_dependency())
        if prebuilt and prebuilt[0].is_compatible_with(env):
            return prebuilt[0].install_to(env, user_request)

        with self._source_tree() as source_tree:
            builds \
                .build(self.owner_package, source_tree, env, editable, self._build_requirements_repository) \
                .install_to(env, user_request)

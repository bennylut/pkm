from typing import List, cast, Any, Tuple, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package
from pkm.api.pkm import pkm
from pkm.api.repositories.repository import AbstractRepository, RepositoryBuilder, Repository
from pkm.repositories.simple_repository import SimpleRepository
from pkm.api.versions.version import StandardVersion
from pkm.utils.commons import unone
from pkm.utils.properties import cached_property
from download_torch_pkm_repo.cuda_compatibility import CudaCompatibilityTable


class DownloadTorchRepository(AbstractRepository):

    def __init__(
            self, name: str, allow_cpu: bool,
            compatible_cuda_versions: List[StandardVersion]):
        super().__init__(name)
        self._simple_repo = SimpleRepository('torch', pkm.httpclient, "https://download.pytorch.org/whl")

        self._compatible_locals = {
            f"cu{''.join(str(r) for r in v.release)}"
            for v in compatible_cuda_versions
        }

        self._allow_cpu = allow_cpu

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        all_packages = self._simple_repo.match(dependency, env)
        matches = []

        for package in all_packages:
            version = cast(StandardVersion, package.version)
            if (local := version.local_label) == 'cpu' or not local:
                if self._allow_cpu:
                    matches.append(package)
            elif local.startswith("cu"):
                if local in self._compatible_locals:
                    matches.append(package)

        return matches

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        def key(p: Package) -> Tuple:
            version = cast(StandardVersion, p.version)
            ll = version.local_label

            arch = 0 if not ll or ll == 'cpu' else 1
            cuda = int(ll[len('cu'):]) if ll and ll.startswith("cu") else 0

            return arch, p.version, cuda

        packages.sort(key=key, reverse=True)
        return packages


class DownloadTorchRepositoryBuilder(RepositoryBuilder):

    def __init__(self):
        super().__init__('download-torch')

    @cached_property
    def _cuda_compatibility(self) -> CudaCompatibilityTable:
        return CudaCompatibilityTable.load()

    def build(self, name: Optional[str], packages_limit: Optional[List[str]], **kwargs: Any) -> Repository:
        allow_cpu = unone(kwargs.get('allow-cpu'), lambda: True)

        return DownloadTorchRepository(name, allow_cpu, self._cuda_compatibility.compatible_cuda_versions())

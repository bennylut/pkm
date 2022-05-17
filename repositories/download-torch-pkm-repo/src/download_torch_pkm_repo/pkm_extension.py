from download_torch_pkm_repo.torch_repository import DownloadTorchRepositoryBuilder
from pkm.api.repositories.repository_loader import RepositoriesExtension


def install() -> RepositoriesExtension:
    return RepositoriesExtension(
        builders=[DownloadTorchRepositoryBuilder()],
    )

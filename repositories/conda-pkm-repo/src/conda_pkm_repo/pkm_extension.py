from weakref import WeakValueDictionary

from typing import Dict

from conda_pkm_repo.conda_repo import CondaRepository
from pkm.api.repositories.repository import RepositoryBuilder, Repository
from pkm.api.repositories.repository_loader import RepositoriesExtension


def install() -> RepositoriesExtension:
    return RepositoriesExtension(
        builders=[CondaRepositoryBuilder()],
        instances=[CondaRepository("conda-main")]
    )


_prebuilt_repositories = WeakValueDictionary()


class CondaRepositoryBuilder(RepositoryBuilder):
    def __init__(self):
        super().__init__("conda")

    def build(self, name: str, channel: str) -> Repository:
        if not (result := _prebuilt_repositories.get(channel)):
            _prebuilt_repositories[channel] = result = CondaRepository(name, channel)

        return result

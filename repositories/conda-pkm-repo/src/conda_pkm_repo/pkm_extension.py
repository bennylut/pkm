from typing import Optional, List, Any

from pkm.api.repositories.repository import RepositoryBuilder, Repository
from pkm.api.repositories.repository_loader import RepositoriesExtension
from src.conda_pkm_repo.conda_repo import CondaRepository


def install() -> RepositoriesExtension:
    return RepositoriesExtension(
        builders=[CondaRepositoryBuilder()],
        instances=[CondaRepository("conda-main")]
    )


class CondaRepositoryBuilder(RepositoryBuilder):
    def __init__(self):
        super().__init__("conda")

    def build(self, name: str, packages_limit: Optional[List[str]], **kwargs: Any) -> Repository:
        if not isinstance(channel := kwargs.get('channel'), str):
            raise ValueError("expecting channel argument with type string")

        return CondaRepository(name, channel)

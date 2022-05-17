from __future__ import annotations
from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any, Dict, List

from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.utils.dicts import remove_none_values
from pkm.utils.hashes import HashBuilder


class RepositoriesConfigInheritanceMode(Enum):
    INHERIT_CONTEXT = 0,
    INHERIT_MAIN = 1,
    NO_INHERITANCE = 2


class RepositoriesConfiguration(TomlFileConfiguration):
    repositories: List[RepositoryInstanceConfig]
    inheritance_mode: RepositoriesConfigInheritanceMode

    @computed_based_on("inheritance")
    def inheritance_mode(self) -> RepositoriesConfigInheritanceMode:
        value = self["inheritance"]
        if value is not None:
            if value == "main":
                return RepositoriesConfigInheritanceMode.INHERIT_MAIN
            if not value:
                return RepositoriesConfigInheritanceMode.NO_INHERITANCE
        return RepositoriesConfigInheritanceMode.INHERIT_CONTEXT

    @computed_based_on("")
    def repositories(self) -> List[RepositoryInstanceConfig]:
        return [
            RepositoryInstanceConfig.from_config(name, repo) for name, repo in self.items()
            if isinstance(repo, Dict)]

    @repositories.modifier
    def set_repositories(self, repos: List[RepositoryInstanceConfig]):
        for k, v in list(self.items()):
            if isinstance(v, Dict):
                del self[k]
        for repo in repos:
            self[repo.name] = repo.to_config()


@dataclass(frozen=True, eq=True)
class RepositoryInstanceConfig:
    type: str
    packages: Optional[List[str]]  # use to limit to the repository to only the given packages
    name: Optional[str]
    args: Dict[str, str]

    def __hash__(self):
        return HashBuilder() \
            .regulars(self.type, self.name) \
            .unordered_mapping(self.args) \
            .unordered_seq(self.packages) \
            .build()

    def to_config(self) -> Dict[str, Any]:
        return remove_none_values({
            **self.args,
            'type': self.type,
            'packages': self.packages,
        })

    @classmethod
    def from_config(cls, name: str, config: Dict[str, Any]) -> "RepositoryInstanceConfig":
        config = copy(config)
        type_ = config.pop('type')
        packages: Optional[List[str]] = config.pop('packages', None)
        args = config
        return RepositoryInstanceConfig(type_, packages, name, args)

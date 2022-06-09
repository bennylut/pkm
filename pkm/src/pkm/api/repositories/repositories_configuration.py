from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping

from pkm.config.configclass import config, config_field, ConfigFile
from pkm.config.configfiles import TomlConfigIO
from pkm.utils.hashes import HashBuilder
from pkm.utils.properties import cached_property


class RepositoriesConfigInheritanceMode(Enum):
    INHERIT_CONTEXT = 0,
    INHERIT_GLOBAL = 1,
    NO_INHERITANCE = 2


@dataclass(eq=True)
@config
class RepositoryInstanceConfig:
    type: str
    bind_only: bool = config_field(key="bind-only")
    args: Dict[str, str] = config_field(leftover=True)

    def __hash__(self):
        return HashBuilder() \
            .regulars(self.type, self.bind_only) \
            .unordered_mapping(self.args) \
            .build()


@config(io=TomlConfigIO())
class RepositoriesConfiguration(ConfigFile):
    repos: Dict[str, RepositoryInstanceConfig]
    inheritance: str = "context"
    package_bindings: Mapping[str, Any] = config_field(key="package-bindings", default_factory=dict)

    @cached_property
    def inheritance_mode(self) -> RepositoriesConfigInheritanceMode:
        value = self.inheritance
        if value is not None:
            if value == "global":
                return RepositoriesConfigInheritanceMode.INHERIT_GLOBAL
            if not value:
                return RepositoriesConfigInheritanceMode.NO_INHERITANCE
        return RepositoriesConfigInheritanceMode.INHERIT_CONTEXT

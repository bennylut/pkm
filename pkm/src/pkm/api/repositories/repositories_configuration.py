from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Mapping

from pkm.config.configclass import config, config_field, ConfigFile
from pkm.config.configfiles import TomlConfigIO
from pkm.utils.enums import enum_by_value
from pkm.utils.hashes import HashBuilder
from pkm.utils.properties import cached_property


class RepositoriesConfigInheritanceMode(Enum):
    INHERIT_CONTEXT = "context"
    INHERIT_GLOBAL = "global"
    NO_INHERITANCE = "none"


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
    repos: Dict[str, RepositoryInstanceConfig] = config_field(default_factory=dict)
    inheritance: str = "context"
    package_bindings: Mapping[str, Any] = config_field(key="package-bindings", default_factory=dict)

    @cached_property
    def inheritance_mode(self) -> RepositoriesConfigInheritanceMode:
        return enum_by_value(RepositoriesConfigInheritanceMode, self.inheritance)

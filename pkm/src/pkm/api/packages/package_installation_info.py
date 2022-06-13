from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pkm.config.configclass import config_field, ConfigFile, config
from pkm.config.configfiles import JsonConfigIO


class StoreMode(Enum):
    EDITABLE = "editable"
    COPY = "copy"
    #: auto = editable if package installed from source otherwise false
    AUTO = "auto"

    @classmethod
    def from_editable_flag(cls, editable: bool) -> StoreMode:
        return cls.EDITABLE if editable else cls.COPY


@dataclass
@config(io=JsonConfigIO())
class PackageInstallationInfo(ConfigFile):
    containerized: bool = config_field(default=False)
    store_mode: StoreMode = config_field(default=StoreMode.COPY)
    compatibility_tag: str = config_field(default="")

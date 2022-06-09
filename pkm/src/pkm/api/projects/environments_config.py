from dataclasses import dataclass
from pathlib import Path

from pkm.config.configclass import config, ConfigFile, config_field
from pkm.config.configfiles import TomlConfigIO

ENVIRONMENT_CONFIGURATION_PATH = "etc/pkm/environments.toml"


@dataclass(eq=True)
@config
class AttachedEnvironmentConfig:
    path: Path = None
    zoo: Path = None


@config(io=TomlConfigIO())
class EnvironmentsConfiguration(ConfigFile):
    attached_env: AttachedEnvironmentConfig = config_field(key="attached-env")

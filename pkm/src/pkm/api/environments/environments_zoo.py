from __future__ import annotations

import os
import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Dict, TYPE_CHECKING

from pkm.api.environments.environment import Environment
from pkm.api.environments.environment_builder import EnvironmentBuilder
from pkm.api.pkm import HasAttachedRepository
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.config.configclass import config, config_field, ConfigFile
from pkm.config.configfiles import TomlConfigIO
from pkm.repositories.shared_pacakges_repo import SharedPackagesRepository
from pkm.utils.commons import NoSuchElementException
from pkm.utils.files import is_relative_to
from pkm.utils.ipc import IPCPackable
from pkm.utils.properties import cached_property

if TYPE_CHECKING:
    from pkm.api.repositories.repository_management import RepositoryManagement


class EnvironmentsZoo(HasAttachedRepository, IPCPackable):

    def __init__(self, cfg: EnvironmentZooConfiguration):
        self.config = cfg
        self.path = cfg.path.parent

    def __getstate__(self):
        return [self.config.path]

    def __setstate__(self, state):
        self.__init__(EnvironmentZooConfiguration.load(state[0]))

    @property
    def _bin_path(self) -> Path:
        return self.path / ".zoo/bin"

    @cached_property
    def repository_management(self) -> "RepositoryManagement":
        from pkm.api.repositories.repository_management import ZooRepositoryManagement
        return ZooRepositoryManagement(self)

    def create_environment(self, name: str, python: VersionSpecifier) -> Environment:

        if (env_path := self.path / name).exists():
            raise FileExistsError(f"environment with name: {name} already exists in the zoo")

        return EnvironmentBuilder.create_matching(env_path, python)

    def delete_environment(self, name: str):
        # shared repository gc
        shutil.rmtree(self.path / name)

    def clean_unused_shared(self):
        repo = self.attached_repository
        if isinstance(repo, SharedPackagesRepository):
            repo.remove_unused_packages(self.list())

    @contextmanager
    def activate(self, env: Dict[str, str] = os.environ):
        prev_path = env.get("PATH")
        new_path_component = str(self._bin_path)
        new_path = f"{new_path_component}{os.pathsep}{prev_path}" if prev_path else new_path_component

        env["PATH"] = new_path
        try:
            yield
        finally:
            if prev_path:
                env["PATH"] = prev_path
            else:
                del env["PATH"]

    def list(self) -> Iterator[Environment]:
        """
        :return: iterator iterating over the requested environments that exists in this zoo
        """
        for e_path in self.path.iterdir():
            if Environment.is_venv_path(e_path):
                yield Environment(e_path, zoo=self)

    def load_environment(self, name: str) -> Environment:
        if not (e_path := self.path / name).exists():
            raise NoSuchElementException(f"environment named {name} could not be found in this zoo")

        if not Environment.is_venv_path(e_path):
            raise ValueError(f"directory {e_path} does not contains a valid environment")

        return Environment(e_path, zoo=self)

    def export_script(self, env_name: str, script_name: str):
        env = self.load_environment(env_name)
        env_scripts = Path(env.installation_target.scripts)
        if not (script_file := env_scripts / script_name).exists() \
                and not (script_file := env_scripts / f"{script_name}.exe").exists():
            raise NoSuchElementException(f"script {script_name} could not be find in environment {env_name}")

        shutil.copy(script_file, self._bin_path / script_file.name)

    def export_all_scripts(self, env_name: str, package: str):
        env = self.load_environment(env_name)
        env_scripts = env.installation_target.scripts
        bin_path = self._bin_path

        for file in env.site_packages.installed_package(package).dist_info.installed_files():
            if is_relative_to(file, Path(env_scripts)):
                shutil.copy(file, bin_path / file.name)

    @classmethod
    def load(cls, path: Path) -> EnvironmentsZoo:
        if (cfg_path := path / "env-zoo.toml").exists():
            return EnvironmentsZoo(EnvironmentZooConfiguration.load(cfg_path))

        cfg = EnvironmentZooConfiguration.load(cfg_path)
        cfg.save()

        (path / ".zoo/bin").mkdir(exist_ok=True, parents=True)
        (path / ".zoo/shared").mkdir(exist_ok=True, parents=True)

        return EnvironmentsZoo(cfg)

    @classmethod
    def is_valid(cls, path: Path) -> bool:
        return (path / "env-zoo.toml").exists()


@dataclass(eq=True)
@config
class PackageSharingConfig:
    enabled: bool = True
    exclude: List[str] = config_field(default_factory=list)


@config(io=TomlConfigIO())
class EnvironmentZooConfiguration(ConfigFile):
    package_sharing: PackageSharingConfig

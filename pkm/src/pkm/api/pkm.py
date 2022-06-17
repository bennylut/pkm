import os
import shutil
import sys
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List

from pkm.config.configclass import config, config_field, ConfigFile
from pkm.config.configfiles import TomlConfigIO
from pkm.utils.files import mkdir
from pkm.utils.http.http_client import HttpClient
from pkm.utils.multiproc import ProcessPoolExecutor
from pkm.utils.properties import cached_property, clear_cached_properties
from pkm.utils.resources import ResourcePath

if TYPE_CHECKING:
    from pkm.api.environments.installed_pythons_locator import InstalledPythonsLocator
    from pkm.api.repositories.repository import Repository
    from pkm.api.repositories.repository_loader import RepositoryLoader
    from pkm.distributions.source_build_cache import SourceBuildCache
    from pkm.api.repositories.repository_management import RepositoryManagement

ENV_PKM_HOME = "PKM_HOME"


@dataclass
class _PkmRepositories:
    pypi: "Repository"
    main: "Repository"


# @dataclass
# @config(io=TomlConfigIO())
# class PkmGlobalFlags(ConfigFile):
#     : can be: "proc", "thread", "none"
# package_installation_parallelizm: str = config_field(key="package-installation-parallelism", default="proc")


@dataclass
@config(io=TomlConfigIO())
class PkmGeneralConfiguration(ConfigFile):
    #: can be: "proc", "thread", "none"
    concurrency_mode: str = config_field(key="concurrency.mode", default="proc")
    interpreters_search_paths: List[str] = config_field(key='interpreters.search-paths', default_factory=list)


class HasAttachedRepository(ABC):

    @property
    @abstractmethod
    def repository_management(self) -> "RepositoryManagement":
        ...

    @property
    def attached_repository(self) -> "Repository":
        """
        :return: the repository that is attached to this artifact
        """
        return self.repository_management.attached_repo


class Pkm(HasAttachedRepository):
    repositories: _PkmRepositories

    def __init__(self, home: Path):
        self.threads = ThreadPoolExecutor()
        self.processes = ProcessPoolExecutor()
        self._home = home

    @cached_property
    def config(self) -> PkmGeneralConfiguration:
        general_config = self.home / 'etc/pkm/general.toml'
        if not general_config.exists():
            mkdir(general_config.parent)
            with ResourcePath('pkm.resources', 'default_pkm_general.toml').use() as default_pkm_general_cfg:
                shutil.copy(default_pkm_general_cfg, general_config)

        return PkmGeneralConfiguration.load(general_config)

    @cached_property
    def installed_pythons(self) -> "InstalledPythonsLocator":
        from pkm.api.environments.installed_pythons_locator import InstalledPythonsLocator
        return InstalledPythonsLocator(self.config.interpreters_search_paths)

    @cached_property
    def home(self) -> Path:
        return mkdir(self._home)

    @cached_property
    def httpclient(self) -> HttpClient:
        return HttpClient(self.home / 'resources/http')

    @cached_property
    def repository_management(self) -> "RepositoryManagement":
        from pkm.api.repositories.repository_management import PkmRepositoryManagement
        return PkmRepositoryManagement(self)

    @cached_property
    def source_build_cache(self) -> "SourceBuildCache":
        from pkm.distributions.source_build_cache import SourceBuildCache
        return SourceBuildCache(self.home / 'build-cache')

    @cached_property
    def repository_loader(self) -> "RepositoryLoader":
        from pkm.api.repositories.repository_loader import RepositoryLoader, REPOSITORIES_CONFIGURATION_PATH

        repo_config = self.home / REPOSITORIES_CONFIGURATION_PATH
        if not repo_config.exists():
            mkdir(repo_config.parent)
            with ResourcePath('pkm.resources', 'default_pkm_repositories.toml').use() as default_pkm_repo_cfg:
                shutil.copy(default_pkm_repo_cfg, repo_config)

        return RepositoryLoader(
            repo_config,
            self.home / 'repos')

    @cached_property
    def repositories(self) -> _PkmRepositories:
        return _PkmRepositories(
            self.repository_loader.pypi,
            self.repository_loader.global_repo,
        )

    def clean_cache(self):
        shutil.rmtree(self.repository_loader.workspace, ignore_errors=True)
        shutil.rmtree(self.source_build_cache.workspace, ignore_errors=True)
        shutil.rmtree(self.httpclient.workspace, ignore_errors=True)

        clear_cached_properties(self)


# the methods used for finding the default data directory were adapted from the appdirs library

def _get_win_folder() -> str:
    import ctypes

    csidl_const = 28  # "CSIDL_LOCAL_APPDATA"
    buf = ctypes.create_unicode_buffer(1024)
    ctypes.windll.shell32.SHGetFolderPathW(None, csidl_const, None, 0, buf)

    # Downgrade to short path name if have highbit chars. See
    # <http://bugs.activestate.com/show_bug.cgi?id=85099>.
    if any(ord(c) > 255 for c in buf):
        buf2 = ctypes.create_unicode_buffer(1024)
        if ctypes.windll.kernel32.GetShortPathNameW(buf.value, buf2, 1024):
            buf = buf2

    return buf.value


def _default_home_directory():
    system = sys.platform
    if system == "win32":
        path = Path(_get_win_folder())
    elif system == 'darwin':
        path = Path('~/Library/Application Support/')
    else:
        path = Path(os.getenv('XDG_DATA_HOME', "~/.local/share"))

    return (path / 'pkm').expanduser().resolve()


pkm_home = os.environ.get(ENV_PKM_HOME) or _default_home_directory()
pkm: Pkm = Pkm(pkm_home)

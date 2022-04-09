import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pkm.utils.http.http_client import HttpClient
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.repositories.local_pythons_repository import InstalledPythonsRepository
    from pkm.api.repositories.repository import Repository
    from pkm.api.repositories.repository_loader import RepositoryLoader
    from pkm.distributions.source_build_cache import SourceBuildCache

ENV_PKM_HOME = "PKM_HOME"


@dataclass
class _PkmRepositories:
    pypi: "Repository"
    main: "Repository"
    installed_pythons: "InstalledPythonsRepository"


class _Pkm:
    repositories: _PkmRepositories

    def __init__(self):
        self.workspace = workspace = os.environ.get(ENV_PKM_HOME) or _default_home_directory()
        workspace.mkdir(exist_ok=True, parents=True)
        self.httpclient = HttpClient(workspace / 'resources/http')
        self.threads = ThreadPoolExecutor()

    @cached_property
    def source_build_cache(self) -> "SourceBuildCache":
        from pkm.distributions.source_build_cache import SourceBuildCache
        return SourceBuildCache(self.workspace / 'build-cache')

    @cached_property
    def repository_loader(self) -> "RepositoryLoader":
        from pkm.api.repositories.repository_loader import RepositoryLoader, REPOSITORIES_CONFIGURATION_PATH
        return RepositoryLoader(
            self.workspace / REPOSITORIES_CONFIGURATION_PATH,
            self.httpclient,
            self.workspace / 'repos')

    @cached_property
    def repositories(self) -> _PkmRepositories:
        from pkm.repositories.local_pythons_repository import InstalledPythonsRepository

        return _PkmRepositories(
            self.repository_loader.pypi,
            self.repository_loader.main,
            InstalledPythonsRepository(),
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


pkm = _Pkm()

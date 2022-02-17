import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pkm.config.etc_chain import EtcChain
from pkm.utils.http.http_client import HttpClient
from pkm.utils.properties import cached_property

if TYPE_CHECKING:
    from pkm.api.repositories.local_pythons_repository import InstalledPythonsRepository
    from pkm.api.repositories.source_builds_repository import SourceBuildsRepository
    from pkm.api.repositories.repository import Repository
    from pkm.api.repositories.repository_loader import RepositoryLoader

ENV_PKM_HOME = "PKM_HOME"


@dataclass
class _PkmRepositories:
    pypi: "Repository"
    source_builds: "SourceBuildsRepository"
    main: "Repository"
    installed_pythons: "InstalledPythonsRepository"


class _Pkm:
    repositories: _PkmRepositories

    def __init__(self):
        self.workspace = workspace = os.environ.get(ENV_PKM_HOME) or _default_home_directory()
        workspace.mkdir(exist_ok=True, parents=True)
        self.etc_chain = EtcChain(workspace/'etc', 'pkm')
        self.httpclient = HttpClient(workspace / 'resources/http')
        self.threads = ThreadPoolExecutor()

    @cached_property
    def repository_loader(self) -> "RepositoryLoader":
        from pkm.api.repositories.repository_loader import RepositoryLoader
        return RepositoryLoader(self.etc_chain, self.httpclient, self.workspace / 'repos')

    @cached_property
    def repositories(self) -> _PkmRepositories:
        from pkm.api.repositories.local_pythons_repository import InstalledPythonsRepository
        from pkm.api.repositories.source_builds_repository import SourceBuildsRepository

        return _PkmRepositories(
            self.repository_loader.pypi,
            SourceBuildsRepository(self.workspace / 'source-builds'),
            self.repository_loader.main,
            InstalledPythonsRepository(),
        )


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

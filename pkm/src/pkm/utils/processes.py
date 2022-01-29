import os
import platform
import subprocess
import sys
from typing import List, Dict, NoReturn

_IS_WINDOWS = platform.system() == 'Windows'


def execvpe(cmd: str, args: List[str], env: Dict[str, str]) -> NoReturn:
    if _IS_WINDOWS:
        sys.exit(subprocess.run([cmd, *args], env=env).returncode)

    os.execvpe(cmd, [cmd, *args], env)

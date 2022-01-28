import os
from pathlib import Path
import platform
import subprocess
import sys
from subprocess import CompletedProcess
from typing import List, Dict, NoReturn, Optional

from pkm.utils.commons import unone

_IS_WINDOWS = platform.system() == 'Windows'


def execvpe(cmd: str, args: List[str], env: Dict[str, str]) -> NoReturn:
    if _IS_WINDOWS:
        sys.exit(run_proc(cmd, args, env=env).returncode)

    os.execvpe(cmd, [cmd, *args], env)


def run_proc(cmd: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None) -> CompletedProcess:
    args = unone(args, list)

    if _IS_WINDOWS:
        if not (cmd_path := Path(cmd)).exists():
            for path in env.get('PATH', os.environ['PATH']).split(os.pathsep):
                if (cmd_path := Path(path) / f"{cmd}.exe").exists:
                    break

            if not cmd_path.exists():
                raise ValueError(f'could not find {cmd} in PATH')

        def _w(a: str) -> str:
            a = a.replace("\"", "\\\"")
            return f'"{a}"'

        return subprocess.run([str(cmd_path), *map(_w, args)], env=env, shell=True)

    return subprocess.run([cmd, *args], env=env)

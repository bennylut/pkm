import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import List, Dict, NoReturn


def execvpe(cmd: str, args: List[str], env: Dict[str, str]) -> NoReturn:
    if platform.system() == 'Windows':
        cmd_path = Path(cmd)
        if not cmd_path.exists():
            for path in env.get('PATH', os.environ['PATH']).split(os.pathsep):
                if (cmd_path := Path(path) / f"{cmd}.exe").exists:
                    break

            if not cmd_path.exists():
                raise ValueError(f'could not find {cmd} in PATH')

        sys.exit(subprocess.run([str(cmd_path), *args], env=env, shell=True).returncode)

    os.execvpe(cmd, [cmd, *args], env)

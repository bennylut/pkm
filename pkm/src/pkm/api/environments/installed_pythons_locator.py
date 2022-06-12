from __future__ import annotations

import os.path
import platform
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, Optional, Set

from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.utils.properties import cached_property
from pkm.utils.systems import is_executable


class InstalledPythonsLocator:

    @cached_property
    def all_installed(self) -> List[InstalledInterpreter]:
        result: List[InstalledInterpreter] = []
        executeables_matched: Set[Path] = set()

        # add current interpreter
        current_interpreter_path = Path(sys.executable)
        current_interpreter = InstalledInterpreter(
            current_interpreter_path, PackageDescriptor("python", Version.parse(platform.python_version())))
        executeables_matched.add(current_interpreter_path)
        result.append(current_interpreter)

        # add interpreters in path
        interpreters_in_path = _interpreters_in_path()
        for interpreter_path in interpreters_in_path:
            try:
                cmdout = subprocess.run(
                    [str(interpreter_path), "-c",
                     "import platform;import sys;print(platform.python_version());print(sys.executable)"],
                    capture_output=True)
                cmdout.check_returncode()

                version_str, executable = cmdout.stdout.decode().strip().splitlines(keepends=False)
                executable = Path(executable.strip()).resolve()

                if executable in executeables_matched:
                    continue

                executeables_matched.add(executable)

                result.append(InstalledInterpreter(
                    executable,
                    PackageDescriptor("python", Version.parse(version_str.strip()))))

            except (ChildProcessError, CalledProcessError):
                # import traceback
                # traceback.print_exc()
                pass  # skip this interpreter

        return sorted(result, key=lambda p: p.version, reverse=True)

    def match(self, version_spec: VersionSpecifier) -> List[InstalledInterpreter]:
        result = [
            p for p in self.all_installed
            if version_spec.allows_version(p.version)]

        result.sort(key=lambda v: v.version, reverse=True)
        return result


@dataclass
class InstalledInterpreter:

    def __init__(self, interpreter: Path, desc: PackageDescriptor):
        self.interpreter = interpreter
        self.descriptor = desc

    @property
    def version(self) -> Version:
        return self.descriptor.version

    def to_environment(self) -> Environment:
        return Environment(env_path=self.interpreter.parent, interpreter_path=self.interpreter)


_OS = platform.system()
_PYTHON_EXEC_RX = re.compile(r"python-?[\d.]*(.exe)?")


def _interpreters_in_path() -> Set[Path]:
    path_parts = [path for it in (os.environ.get("PATH") or "").split(os.pathsep) if (path := Path(it)).exists()]

    def as_python_executeable(file: Path) -> Optional[Path]:
        if _PYTHON_EXEC_RX.fullmatch(file.name.lower()) and is_executable(file):
            try:
                return file.resolve()
            except:  # noqa
                pass
        return None

    return {
        executable
        for path in path_parts
        for file in path.iterdir()
        if (executable := as_python_executeable(file))}

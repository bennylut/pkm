import os.path
import platform
import re
import subprocess
import sys
from pathlib import Path
from subprocess import CalledProcessError
from typing import List, Optional, Set, Union

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.environment_builder import EnvironmentBuilder
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.repositories.repository import AbstractRepository
from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property
from pkm.utils.systems import is_executable


class InstalledPythonsRepository(AbstractRepository):

    def __init__(self):
        super().__init__('local-pythons')

    def list(self, package_name: str = 'python', env: Environment = None) -> List[Package]:
        return super().list(package_name, env)

    @cached_property
    def _interpreters(self) -> List["LocalInterpreterPackage"]:
        result: List[LocalInterpreterPackage] = []
        executeables_matched: Set[Path] = set()

        # add current interpreter
        current_interpreter_path = Path(sys.executable)
        current_interpreter = LocalInterpreterPackage(
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

                result.append(LocalInterpreterPackage(
                    executable,
                    PackageDescriptor("python", Version.parse(version_str.strip()))))

            except (ChildProcessError, CalledProcessError):
                # import traceback
                # traceback.print_exc()
                pass  # skip this interpreter

        return sorted(result, key=lambda p: p.version, reverse=True)

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        return [
            p
            for p in self._interpreters
            if dependency.version_spec.allows_version(p.version)]


class LocalInterpreterPackage(Package):

    def __init__(self, interpreter: Path, desc: PackageDescriptor):
        self._interpreter = interpreter
        self._desc = desc

    def dependencies(
            self, target: "PackageInstallationTarget", extras: Optional[List[str]] = None) -> List["Dependency"]:
        return []

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def is_compatible_with(self, env: Environment):
        return True

    def to_environment(self) -> Environment:
        return Environment(env_path=self._interpreter.parent, interpreter_path=self._interpreter)

    def install_to(
            self, target: Union["PackageInstallationTarget", Environment], user_request: Optional["Dependency"] = None,
            editable: bool = False):
        env_dir = target.path if isinstance(target, Environment) else target.env.path
        EnvironmentBuilder.create(env_dir, self._interpreter.absolute())


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

import os.path
import platform
import re
from io import UnsupportedOperation
from pathlib import Path
from typing import List, Optional, Set

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages import Package, PackageDescriptor
from pkm.api.repositories import Repository
from pkm.api.versions.version import Version
from pkm.utils.properties import cached_property
from pkm.utils.systems import is_executable

from pkm_main.environments.interpreter_introspection import InterpreterIntrospection
from pkm_main.environments.virtual_environment import UninitializedVirtualEnvironment, VirtualEnvironment

_DEFAULT_PKG_EXTRAS = {'pip', 'wheel', 'setuptools'}


class LocalPythonsRepository(Repository):
    _INSTANCE: Optional["LocalPythonsRepository"] = None

    def __init__(self):
        super().__init__('local-pythons')

    @cached_property
    def _interpreters(self) -> List["LocalInterpreterPackage"]:
        result: List[LocalInterpreterPackage] = []
        interpreters_in_path = _interpreters_in_path()
        for interpreter_path in interpreters_in_path:
            try:
                introspection = InterpreterIntrospection.remote(interpreter_path)
                result.append(LocalInterpreterPackage(
                    interpreter_path,
                    PackageDescriptor("python", Version.parse(introspection.version)),
                    _DEFAULT_PKG_EXTRAS))

            except UnsupportedOperation:
                ...  # skip this interpreter

        return result

    def accepts(self, dependency: Dependency) -> bool:
        return dependency.package_name == 'python'

    def _do_match(self, dependency: Dependency) -> List[Package]:
        extras = set(dependency.extras) if dependency.extras is not None else _DEFAULT_PKG_EXTRAS

        return [
            p.with_extras(extras)
            for p in self._interpreters
            if dependency.version_spec.allows_version(p.version)]

    @classmethod
    def instance(cls) -> "LocalPythonsRepository":
        if not cls._INSTANCE:
            cls._INSTANCE = LocalPythonsRepository()

        return cls._INSTANCE


class LocalInterpreterPackage(Package):

    def __init__(self, interpreter: Path, desc: PackageDescriptor, extras: Set[str]):
        self._interpreter = interpreter
        self._desc = desc
        self._extras = extras

    def with_extras(self, extras: Set[str]) -> "LocalInterpreterPackage":
        if self._extras == extras:
            return self
        return LocalInterpreterPackage(self._interpreter, self._desc, extras)

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    def dependencies(self, environment: Environment, extras: Optional[List[str]] = None) -> List[Dependency]:
        return []

    def is_compatible_with(self, env: Environment):
        return isinstance(env, UninitializedVirtualEnvironment)

    def to_environment(self) -> Environment:
        return VirtualEnvironment(path=self._interpreter.parent, interpreter_path=self._interpreter)

    def install_to(self, env: Environment):
        from virtualenv import cli_run

        args = [
            "--python", str(self._interpreter.absolute())
        ]

        if 'pip' not in self._extras:
            args.append('--no-pip')

        if 'wheel' not in self._extras:
            args.append('--no-wheel')

        if 'setuptools' not in self._extras:
            args.append('--no-setuptools')

        args.append(str(env.path.absolute()))

        cli_run(args)


_OS = platform.system()
_PYTHON_EXEC_RX = re.compile(r"python-?[0-9.]*(.exe)?")


def _interpreters_in_path() -> Set[Path]:
    path_parts = [Path(it) for it in (os.environ.get("PATH") or "").split(os.pathsep)]
    return {
        file.resolve()
        for path in path_parts
        for file in path.iterdir()
        if _PYTHON_EXEC_RX.fullmatch(file.name.lower()) and is_executable(file)}

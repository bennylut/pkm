import shutil
from io import UnsupportedOperation
from pathlib import Path
from typing import Literal, Optional, Iterator, Union

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.environments.environments_zoo import ManagedEnvironment
from pkm.api.environments.lightweight_environment_builder import LightweightEnvironments
from pkm.api.packages.package import PackageDescriptor
from pkm.api.pkm import pkm
from pkm.api.repositories.repository import Repository
from pkm.config.configuration import TomlFileConfiguration
from pkm.resolution.pubgrub import UnsolvableProblemException
from pkm.utils.commons import unone, unone_raise, UnsupportedOperationException
from pkm.utils.iterators import without_nones
from pkm.utils.properties import cached_property, clear_cached_properties

_PKM_ENV_INFO_SUFFIX = "etc/pkm/zoo-info.toml"


class StandardEnvironmentsZoo(EnvironmentsZoo):

    def __init__(self, path: Path, allow_applications: bool = True):
        self._path = path
        self._with_applications = allow_applications

        if not self._path.exists():
            self._path.mkdir(parents=True)
            if allow_applications:
                (self._path / "apps").mkdir()
                (self._path / "envs").mkdir()

    def create_environment(self, name: str, python: Union[Dependency, str]) -> "ManagedEnvironment":
        python = Dependency.parse_pep508(python) if isinstance(python, str) else python

        path = (self._path / "envs" / name) if self._with_applications else (self._path / name)
        if path.exists():
            raise FileExistsError(f"environment named {name} already exists")

        env = Environment(path)
        interpreters = pkm.repositories.installed_pythons.match(python)
        interpreter = max(
            (i for i in interpreters if i.is_compatible_with(env)),
            key=lambda it: it.version, default=None)

        if not interpreter:
            raise FileNotFoundError(f"could not find locally installed interpreter matching {python}")

        interpreter.install_to(env)
        return StandardManagedEnvironment(Environment(env.path))

    def create_application_environment(
            self, application: Union[str, Dependency], repository: Repository, name: Optional[str] = None,
            python: Optional[Union[str, Dependency]] = None) -> "ManagedEnvironment":

        if not self._with_applications:
            raise UnsupportedOperationException("this environment zoo does not support applications")

        application = Dependency.parse_pep508(application) if isinstance(application, str) else application
        name = unone(name, lambda: application.package_name)
        path = self._path / "apps" / name
        if path.exists():
            raise FileExistsError(f"application environment named {name} already exists")

        python = unone(python, lambda: 'python *')
        python = Dependency.parse_pep508(python) if isinstance(python, str) else python

        interpreters = sorted(pkm.repositories.installed_pythons.match(python), key=lambda it: it.version, reverse=True)

        for interpreter in interpreters:
            try:
                env = LightweightEnvironments.create(path, interpreter)
                env.install(application, repository, True)
            except (UnsupportedOperation, UnsolvableProblemException):
                shutil.rmtree(path)
                continue

            env_info = TomlFileConfiguration.load(env.path / _PKM_ENV_INFO_SUFFIX)
            env_info['application'] = str(application)
            env_info.save()

            return StandardManagedEnvironment(env)

        raise FileNotFoundError(f"could not find locally installed interpreter matching {python}")

    def list(self, match: Literal['applications', 'general', 'all'] = 'all') -> Iterator["ManagedEnvironment"]:
        if not self._with_applications:
            yield from without_nones(self._try_load(p) for p in self._path.iterdir())
        else:
            if match in ('applications', 'all'):
                yield from without_nones(self._try_load(p) for p in (self._path / 'apps').iterdir())

            if match in ('general', 'all'):
                yield from without_nones(self._try_load(p) for p in (self._path / 'envs').iterdir())
    
    def _try_load(self, path: Path) -> Optional["ManagedEnvironment"]:
        if Environment.is_valid(path):
            return StandardManagedEnvironment(Environment(path))
        return None

    def load_environment(self, name: str, application: bool) -> "ManagedEnvironment":
        path = self._path / name
        if self._with_applications:
            path = (self._path / 'apps' / name) if application else (self._path / 'envs' / name)

        return unone_raise(self._try_load(path), lambda: KeyError('no such environment found'))


class StandardManagedEnvironment(ManagedEnvironment):

    def __init__(self, env: Environment):
        self._env = env

    @cached_property
    def _env_info(self) -> TomlFileConfiguration:
        return TomlFileConfiguration.load(self.environment.path / _PKM_ENV_INFO_SUFFIX)

    @property
    def environment(self) -> Environment:
        return self._env

    @property
    def application(self) -> Optional[PackageDescriptor]:
        return self._env_info['application'] is not None

    def delete(self):
        shutil.rmtree(self._env.path)
        self._env.reload()
        clear_cached_properties(self)

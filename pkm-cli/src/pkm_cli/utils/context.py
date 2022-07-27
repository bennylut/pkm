from __future__ import annotations
from dataclasses import dataclass

from pathlib import Path

from typing import Optional, Callable

from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.pkm import HasAttachedRepository
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.symbol import Symbol
from pkm.utils.types import Consumer
from pkm_cli.api.dynamic_cli.command_parser import Command
from pkm_cli.display.display import Display

_CONTEXT_SYM = Symbol("context")


def _lookup_project_group(path: Path) -> Optional[ProjectGroup]:
    if (path / 'pyproject-group.toml').exists():
        return ProjectGroup.load(path)


def _lookup_project(path: Path) -> Optional[Project]:
    if (path / 'pyproject.toml').exists():
        return Project.load(path)


def _lookup_env(path: Path) -> Optional[Environment]:
    if (path / 'pyvenv.cfg').exists():
        return Environment(path)
    if prj := _lookup_project(path):
        return prj.attached_environment


def _lookup_env_zoo(path: Path) -> Optional[EnvironmentsZoo]:
    if EnvironmentsZoo.is_valid(path):
        return EnvironmentsZoo.load(path)


@dataclass
class _ContextualCommand:
    on_project: Optional[Callable[[Project], None]] = None,
    on_project_group: Optional[Callable[[ProjectGroup], None]] = None,
    on_environment: Optional[Callable[[Environment], None]] = None,
    on_env_zoo: Optional[Callable[[EnvironmentsZoo], None]] = None,

    # noinspection PyCallingNonCallable
    def execute(self, path: Path, print_: Callable[[str], None]):
        path = path.resolve()

        if (on_project := self.on_project) and (project := _lookup_project(path)):
            print_(f"using [gold1 on grey19]project[/] context: {project.path}")
            on_project(project)
        elif (on_project_group := self.on_project_group) and (project_group := _lookup_project_group(path)):
            print_(f"using project-group context: {project_group.path}")
            on_project_group(project_group)
        elif (on_environment := self.on_environment) and (env := _lookup_env(path)):
            print_(f"using virtual-env context: {env.path}")
            on_environment(env)
        elif (on_env_zoo := self.on_env_zoo) and (env_zoo := _lookup_env_zoo(path)):
            print_(f"using env-zoo context: {env_zoo.path}")
            on_env_zoo(env_zoo)
        else:
            return False
        return True


class _ContextCollector:
    def __init__(self):
        self.context = None

    def __call__(self, context=None):
        self.context = context


# noinspection PyShadowingBuiltins
class Context:
    # add listeners/? to context so that we can add tasks when project is applied
    def __init__(self, path: Path, lookup: bool, use_global: bool, site: Optional[str]):
        self._path = path
        self._lookup = lookup
        self._use_global = use_global
        self._site = site

    def lookup_project(self) -> Optional[Project]:
        collector = _ContextCollector()
        self.run(on_project=collector, on_missing=collector)
        return collector.context

    def lookup_has_attached_repository(self) -> Optional[HasAttachedRepository]:

        collector = _ContextCollector()

        # noinspection PyTypeChecker
        self.run(
            on_project=collector, on_project_group=collector, on_environment=collector,
            on_env_zoo=collector, on_missing=collector)
        return collector.context

    # noinspection PyUnusedLocal
    def run(self,
            on_project: Optional[Consumer[Project]] = None,
            on_project_group: Optional[Consumer[ProjectGroup]] = None,
            on_environment: Optional[Consumer[Environment]] = None,
            on_free_context: Optional[Callable[[], None]] = None,
            on_env_zoo: Optional[Consumer[EnvironmentsZoo]] = None,
            on_missing: Optional[Callable[[], None]] = None,
            silent: bool = False,
            **_):

        if silent:
            def print(_):
                ...
        else:
            def print(msg):
                Display.print(msg)

        if self._use_global:
            env = Environment.current(site=self._site or 'user')
            print(f"using global context: {env.interpreter_path}")
            if on_environment:
                on_environment(env)
            elif on_missing:
                on_missing()
            else:
                raise UnsupportedOperationException("could not execute operation")
            return

        path = self._path
        cmd = _ContextualCommand(
            on_project=on_project, on_project_group=on_project_group,
            on_environment=on_environment, on_env_zoo=on_env_zoo
        )

        executed = cmd.execute(path, print)

        if not executed and self._lookup:
            for parent in path.parents:
                if executed := cmd.execute(parent, print):
                    break
        if not executed:
            if on_free_context:
                on_free_context()
            elif on_missing:
                on_missing()
            else:
                raise UnsupportedOperationException("could not execute operation on current context")

    @classmethod
    def of(cls, command: Command) -> Context:
        command = command.parent_by_path("pkm")
        if prec := _CONTEXT_SYM.getattr(command, None):
            return prec

        cwd = Path.cwd()
        if context := command.context:
            result = cls(Path(context), False, False, None)
        elif command.global_context:
            result = cls(cwd, False, True, getattr(command, 'site', None))
        else:
            result = cls(cwd, True, False, None)

        _CONTEXT_SYM.setattr(command, result)
        return result

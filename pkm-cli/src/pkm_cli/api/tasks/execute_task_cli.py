import ast
import importlib.resources as ir
import importlib.util as iu
from pathlib import Path
from types import ModuleType
from typing import List, Optional

from pkm.api.projects.project import Project
from pkm.utils.commons import UnsupportedOperationException
from pkm_cli.api.dynamic_cli.method_parser import command_definition_from_method, _doc_to_short_desc
from pkm_cli.api.dynamic_cli.command_parser import dynamic_commands, ArgumentsBuffer, CommandDef, option, command, Command, \
    DynamicCommandLine, command_definitions_from

project: Optional[Project] = None


def _load_task(name: str) -> ModuleType:
    name = name.replace('-', '_')
    try:
        task_spec = iu.find_spec(name) or iu.find_spec(f"pkm_tasks.{name}")
    except ModuleNotFoundError:
        task_spec = None

    if not task_spec:
        raise FileNotFoundError(f"no such task: {name}")

    task = iu.module_from_spec(task_spec)

    # extend builtins
    task.run_task = _run_task
    task.project = project

    task_spec.loader.exec_module(task)
    if not callable(getattr(task, 'run', None)):
        raise ValueError(f"not a task: {name} (missing run function)")

    return task


def _run_task(name, *args, **kwargs):
    task = _load_task(name)
    task.run(*args, **kwargs)


def _as_task_preview_command(name: str, source: str) -> Optional[CommandDef]:
    for stmt in ast.parse(source).body:
        if isinstance(stmt, ast.FunctionDef) and stmt.name == "run":
            def execute(_: Command):
                raise UnsupportedOperationException("task preview")

            doc = ast.get_docstring(stmt) or ""  # noqa
            short_desc = _doc_to_short_desc(doc)
            return CommandDef([name], execute, help=doc, short_desc=short_desc)
    return None


def _load_all_tasks() -> List[CommandDef]:
    def find_in_namespace(namespace: str) -> List[CommandDef]:
        result = []
        for r in ir.contents(namespace):
            if r.endswith(".py"):
                task_command = _as_task_preview_command(
                    f"{namespace[len('pkm_tasks.'):]}.{r[:-(len('.py'))]}", ir.read_text(namespace, r))
                if task_command:
                    result.append(task_command)
            elif not ir.is_resource(namespace, r):
                result.extend(find_in_namespace(f"{namespace}.{r}"))
        return result

    tasks_dir = project.path / "tasks"

    def find_in_directory(directory: Path) -> List[CommandDef]:
        result = []
        for r in directory.iterdir():
            if r.suffix == ".py":
                task_command = _as_task_preview_command(
                    '.'.join(r.relative_to(tasks_dir).with_suffix("").parts), r.read_text())
                if task_command:
                    result.append(task_command)
            elif r.is_dir():
                result.extend(find_in_directory(r))
        return result

    return find_in_namespace('pkm_tasks') + find_in_directory(tasks_dir)


@command("pkm", option("-p,--project", reader=Path))
def pkm_(cmd: Command):
    global project
    project = Project.load(cmd.project)


@dynamic_commands("pkm run")
def pkm_run(_: Command, next_args: ArgumentsBuffer) -> List[CommandDef]:
    if next_ := next_args.peek_or_none():
        task = _load_task(next_.lstrip('@')).run
        return [command_definition_from_method(task, next_)]

    return _load_all_tasks()


def main(args: List[str]):
    cmd = DynamicCommandLine.create(command_definitions_from(globals())).parse()
    if cmd.help or cmd.parse_error:
        cmd.print_help()
    else:
        cmd.execute()

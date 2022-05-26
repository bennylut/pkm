import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, cast

from jinja2.utils import Namespace

from pkm.api.projects.project import Project
from pkm.utils.commons import NoSuchElementException, UnsupportedOperationException
from pkm.utils.files import temp_dir
from pkm_cli.utils.clis import Command

_EXECUTE_TASK = """
import inspect
import typing
import json
import sys
from pathlib import Path
import importlib.util as iu

insn = json.loads(Path('insn.json').read_text())
if parent_path := insn.get('parent_path'):
    sys.path.insert(1, parent_path)
    
sys.path.insert(1, insn['path'])

def load_task(name):
    task_spec = iu.find_spec(name)
    task = iu.module_from_spec(task_spec)
    
    # extend builtins
    task.run_task = run_task
    task.project_info = insn['project_info']
        
    task_spec.loader.exec_module(task)
    return task

def run_task(name, *args, **kwargs):
    task = load_task(name.replace('-','_'))
    task.run(*args, **kwargs)

task = load_task(insn['task'])
run_function = task.run
arg_types = typing.get_type_hints(run_function)

arg_names = inspect.getfullargspec(task.run).args
named_args = zip(insn['args'], arg_names)

def identity(x):
    return x

def typeof(name: str):
    result = arg_types.get(name, identity)
    if isinstance(result, str):
        result = identity
    return result

parsed_args = [typeof(name)(arg) for arg, name in named_args]
parsed_kwargs = {k: typeof(k)(v) for k, v in insn['kwargs'].items()}

task.run(*parsed_args, **parsed_kwargs)
"""


class TasksRunner:
    def __init__(self, project: Project):
        self._project = project

    def run(self, task_name: str, args: List[str]) -> int:
        a, k = [], {}
        for arg in args:
            name, sep, value = arg.partition('=')
            if sep:
                k[name] = value
            elif k:
                raise UnsupportedOperationException(
                    f"positional arguments are not supported after named arguments: {arg}")
            else:
                a.append(arg)

        if not (task := _locate_task(task_name, self._project)):
            raise NoSuchElementException(f"no such task: {task_name}")

        return task.execute(*a, **k)

    @contextmanager
    def run_attached(self, command: Command, command_args: Namespace):
        command_args_dict = dict(vars(command_args))
        del command_args_dict['func']
        task_prefix = f"commands.{'.'.join(command.path.split()[1:])}"
        if before := _locate_task(f"{task_prefix}.before", self._project):
            before.execute(command_args_dict)
        yield
        if after := _locate_task(f"{task_prefix}.after", self._project):
            after.execute(command_args_dict)

    def describe(self, task_name: str) -> str:
        if not (task := _locate_task(task_name, self._project)):
            raise NoSuchElementException(f"no such task: {task_name}")

        return task.describe()


class _Task:
    def __init__(self, task: str, path: Path, project: Project):
        self.task = task
        self.path = path
        self.project = project

    def execute(self, *args, **kwargs) -> int:
        project = self.project
        group = project.group
        insn = {
            'path': str((project.path / 'tasks').resolve()),
            'parent_path': str((group.path / 'tasks').resolve()) if group else None,
            'task': self.task,
            'args': args,
            'kwargs': kwargs,
            'project_info': {
                'name': project.name,
                'version': str(project.version),
                'path': str(project.path.resolve()),
                'group_path': str(group.path.resolve()) if group else None
            }
        }

        with temp_dir() as tdir:
            execute_py = tdir / "execute.py"
            (tdir / "insn.json").write_text(json.dumps(insn))
            execute_py.write_text(_EXECUTE_TASK)
            return subprocess.run([str(self.project.attached_environment.interpreter_path), "execute.py"],
                                  cwd=tdir).returncode

    def describe(self) -> str:
        import ast
        t = cast(ast.Module, ast.parse(self.path.read_text()))
        for stmt in t.body:
            if isinstance(stmt, ast.FunctionDef) and stmt.name == 'run':
                return ast.get_docstring(stmt, True)  # noqa

        return ""


def _locate_task(task_name: str, project: Project) -> Optional[_Task]:
    task_name = task_name.replace('-', '_')
    name_parts = task_name.split(".")

    def _task_path(base_path: Path) -> Path:
        return base_path.joinpath("tasks", *name_parts[:-1], name_parts[-1] + ".py")

    if (path := _task_path(project.path)).exists():
        return _Task(task_name, path, project)
    if (group := project.group) and (path := _task_path(group.path)).exists():
        return _Task(task_name, path, project)
    return None

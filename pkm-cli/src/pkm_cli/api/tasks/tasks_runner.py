import inspect
import json
import os
import subprocess
from contextlib import contextmanager
from typing import List, Optional, Union, Any

from jinja2.utils import Namespace

from pkm.api.projects.project import Project
from pkm.utils.files import temp_dir
from pkm_cli.utils.clis import Command

_EXECUTE_TASK = """
import importlib.util as iu
import json
from pathlib import Path
from mc import MethodCliArgs # noqa

insn = json.loads(Path('insn.json').read_text())

def load_task(name):
    name = name.replace('-','_')
    try:
        task_spec = iu.find_spec(name) or iu.find_spec(f"pkm_tasks.{name}")
    except ModuleNotFoundError:
        task_spec = None
        
    if not task_spec:
        raise FileNotFoundError(f"no such task: {name}")
    
    task = iu.module_from_spec(task_spec)
    
    # extend builtins
    task.run_task = run_task
    task.project_info = insn['project_info']
        
    task_spec.loader.exec_module(task)
    if not callable(getattr(task, 'run', None)):
        raise ValueError(f"not a task: {name} (missing run function)")
        
    return task

def run_task(name, *args, **kwargs):
    task = load_task(name)
    task.run(*args, **kwargs)

main_task = load_task(insn['task'])
run_function = main_task.run

if insn['mode'] == 'describe':
    print(run_function.__doc__ or "No Description Provided")
elif insn['mode'] == 'run-attached':
    run_function(insn['args'])
else:
    MethodCliArgs.parse(insn['args']).execute(run_function)
"""


class TasksRunner:
    def __init__(self, project: Project):
        self._project = project

    def run(self, task_name: str, args: List[str]) -> int:
        return _Task(task_name, self._project).execute(args)

    @contextmanager
    def run_attached(self, command: Command, command_args: Namespace):
        command_args_dict = dict(vars(command_args))
        del command_args_dict['func']

        if before := _get_attached_name('before', command.path, self._project):
            _Task(before, self._project).execute_attached(command_args_dict)
        yield
        if after := _get_attached_name('after', command.path, self._project):
            _Task(after, self._project).execute_attached(command_args_dict)

    def describe(self, task_name: str) -> str:
        return _Task(task_name, self._project).describe()


class _Task:
    def __init__(self, task: str, project: Project):
        self.task = task
        self.project = project

    def execute(self, args: List[str]) -> int:
        return self._execute('run', args)

    def execute_attached(self, args: dict) -> int:
        return self._execute('run-attached', args)

    def describe(self) -> str:
        return self._execute('describe', [])

    def _execute(self, mode: str, args: Any) -> Union[int, str]:
        project = self.project
        group = project.group
        insn = {
            'task': self.task,
            'args': args,
            'mode': mode,
            'project_info': {
                'name': project.name,
                'version': str(project.version),
                'path': str(project.path.resolve()),
                'group_path': str(group.path.resolve()) if group else None
            }
        }

        with temp_dir() as tdir:
            import pkm_cli.utils.method_clis as mc
            (tdir / "mc.py").write_text(inspect.getsource(mc))

            execute_py = tdir / "execute.py"
            (tdir / "insn.json").write_text(json.dumps(insn))
            execute_py.write_text(_EXECUTE_TASK)
            with self.project.attached_environment.activate():
                pythonpath = str((project.path / 'tasks').resolve())
                if old_pythonpath := os.environ.get("PYTHONPATH", ""):
                    pythonpath = pythonpath + os.pathsep + old_pythonpath

                os.environ["PYTHONPATH"] = pythonpath
                try:
                    capture = mode == 'describe'
                    result = subprocess.run([
                        str(self.project.attached_environment.interpreter_path), "execute.py"], cwd=tdir,
                        capture_output=capture, text=capture)

                    if capture:
                        return result.stdout.strip()
                    return result.returncode
                finally:
                    os.environ["PYTHONPATH"] = old_pythonpath


def _get_attached_name(phase: str, command: str, project: Project) -> Optional[str]:
    cmd = command.replace("-", "_").split(" ")[1:]
    task_path = project.path.joinpath("tasks", "commands", *cmd, phase + ".py")
    if task_path.exists():
        return f"commands.{'.'.join(cmd)}.{phase}"
    return None

from __future__ import annotations

import importlib.util as iu
import importlib.resources as ir
import inspect
import shutil
from contextlib import contextmanager
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import List, Any, Optional, ContextManager, Set, Mapping, Dict

import questionary as q
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

from pkm.utils.commons import UnsupportedOperationException, IllegalStateException
from pkm.utils.files import temp_dir
from pkm.utils.properties import cached_property
from pkm_cli.api.dynamic_cli.method_parser import command_definition_from_method
from pkm_cli.api.dynamic_cli.command_parser import CommandDef, flag, Command
from pkm_cli.display.display import Display


class TemplateRunner:

    def __init__(self):
        self.jinja_context = SandboxedEnvironment(loader=FileSystemLoader("/"))

    @staticmethod
    def templates_in_namespace() -> List[str]:

        def find(namespace: str) -> List[str]:
            result = []
            for c in ir.contents(namespace):
                if c == "render.py":
                    return [namespace]
                elif not ir.is_resource(namespace, c):
                    result.extend(find(f"{namespace}.{c}"))

            return result

        l = len("pkm_templates.")
        return [it[l:] for it in find("pkm_templates")]

    @contextmanager
    def load_template(self, name: str) -> ContextManager[Template]:
        name = name.replace('-', '_')
        renderer_name = f"{name}.render"

        local_template_file = Path(*name.split("."), "render.py")
        if local_template_file.exists():
            yield Template(iu.spec_from_file_location(str(local_template_file.resolve())), self)
            return

        try:
            if template_spec := iu.find_spec(f"pkm_templates.{renderer_name}"):
                yield Template(template_spec, self)
                return
        except ModuleNotFoundError:
            ...

        raise FileNotFoundError(f"No such template: {name}")


# noinspection PyMethodMayBeStatic
class Template:

    def __init__(self, render_spec: ModuleSpec, runner: TemplateRunner):
        self._render_spec = render_spec
        self._runner = runner
        self._builtins = _TemplateExtendedBuiltins(self._runner)
        self._template_dir = Path(self._render_spec.origin).parent

    def describe(self) -> str:
        module = self._module
        return module.__doc__ or f"No Description Provided for template '{self._template_dir.name}'"

    def as_command(self, command_path: str, target_dir: Optional[Path] = None) -> CommandDef:
        target_dir = target_dir or Path.cwd()
        result = command_definition_from_method(self._module.setup, command_path)

        allowed_args = {a.field_name for a in result.arguments_def}

        overwrite_flag_names = "-o, --overwrite"
        if any("-o" in it.defined_names for it in result.arguments_def):
            overwrite_flag_names = "--overwrite"

        result.arguments_def = [*result.arguments_def, flag(overwrite_flag_names)]

        def execute(cmd: Command):
            self.execute(target_dir, {k: v for k, v in cmd.arguments.items() if k in allowed_args}, cmd.overwrite)

        result.execution = execute
        return result

    def execute(self, target_dir: Path, args: Dict[str, Any], allow_overwrite: bool = False):
        module = self._module
        self._builtins.install_execution(module, target_dir, allow_overwrite)

        context = self._setup(args, module)
        ignored_files = self._load_ignored_files(self._template_dir)
        if allow_overwrite:
            self._render(self._template_dir, target_dir, context, ignored_files)
        else:
            with temp_dir() as tdir:
                self._render(self._template_dir, tdir, context, ignored_files)
                for file in tdir.rglob("*"):
                    relative_file = file.relative_to(tdir)
                    if (target_file := target_dir / relative_file).exists() and not target_file.is_dir():
                        raise IOError(f"file already exists: {target_file}")

                shutil.copytree(tdir, target_dir, dirs_exist_ok=True)
        if callable(post_render := getattr(module, "post_render", None)):
            post_render(context)

    def _load_ignored_files(self, template_root: Path) -> Set[Path]:
        result = {self._template_dir / file for file in ("render.py", "__pycache__", ".templateignore")}

        ignore_file = self._template_dir / ".templateignore"

        if ignore_file.exists():
            lines = ignore_file.read_text().splitlines()
            result = {f.resolve() for line in lines if line.strip() for f in template_root.glob(line)}

        for sub_dir in template_root.iterdir():
            if sub_dir.is_dir():
                result.update(self._load_ignored_files(sub_dir))

        return result

    def _render(self, template_dir: Path, target_dir: Path, context: Mapping, ignored_files: Set[Path]):

        jinja = self._runner.jinja_context

        for template_child in template_dir.iterdir():
            if template_child in ignored_files:
                continue

            name = jinja.from_string(template_child.name).render(context)

            if not name:  # empty names indicate unneeded files
                continue

            target_child = (target_dir / name).resolve()

            if not target_child.parent.exists():
                target_child.parent.mkdir(parents=True)

            if template_child.is_dir():
                if (template_child / ".templatepreserve").exists():
                    shutil.copytree(str(template_child.absolute()), str(target_child.absolute()))
                    return

                target_child.mkdir(exist_ok=True)
                self._render(template_child, target_child, context, ignored_files)
            elif target_child.suffix == ".tmpl":
                with target_child.with_suffix("").open("w") as f:
                    jinja.from_string(template_child.read_text()).stream(context).dump(f)
            else:
                shutil.copy(template_child, target_child)

    def _setup(self, args: Dict[str, Any], module: ModuleType) -> Mapping:
        result = module.setup(**args)
        if not isinstance(result, Mapping):
            raise IllegalStateException(
                f"invalid return value from template setup function (dict is required, got {type(result)})")
        return result

    @cached_property
    def _module(self) -> ModuleType:
        module = iu.module_from_spec(self._render_spec)

        # noinspection PyProtectedMember
        self._builtins.install_base(module)

        self._render_spec.loader.exec_module(module)

        if not callable(getattr(module, 'setup', None)):
            raise UnsupportedOperationException(f"illegal template, no setup function defined")

        return module


# noinspection PyMethodMayBeStatic
class _TemplateExtendedBuiltins:

    def __init__(self, runner: TemplateRunner):
        self._runner = runner
        self._target_dir = None
        self._allow_overwrite = None

    def render_template(self, name: str, **kwargs):
        # noinspection PyProtectedMember
        with self._runner._load_template(name) as t:
            t.execute(self._target_dir, kwargs, self._allow_overwrite)

    def confirm(self, prompt: str, default: bool = True) -> bool:
        """
        ask the user a yes/no question
        :param prompt: the prompt to show to the user
        :param default: the default to show to the user
        :return: True if the user enter yes, False otherwise
        """
        r = q.confirm(prompt, default=default).unsafe_ask()
        return r if isinstance(r, bool) else str(r).lower() in ('y', 'yes')

    def ask(self, prompt: str, default: Any = "", options: Optional[List[str]] = None,
            secret: bool = False, autocomplete: bool = False, multiselect: bool = False,
            path: bool = False):

        """
        ask the user using the given `prompt`, limiting its answers using the different arguments of this function
        :param prompt: the prompt to show to the user
        :param default: the default value to show to the user
        :param options: limited options for the user to select from
        :param secret: if True, the caracters the user insert will not be visible
        :param autocomplete: use in combination with `options`, will autocomplete the user answers using the options
        :param multiselect: use in combination with `options`, allow to select several options
        :param path: if True, limit the user to entering a filesystem path
        :return: the response of the user
        """

        if options:
            options = list(options)  # ensure we have a list
            default = default or options[0]
            if multiselect:
                return q.checkbox(prompt, choices=options, default=default).unsafe_ask()
            elif autocomplete:
                return q.autocomplete(prompt, choices=options, default=default).unsafe_ask()
            else:
                return q.select(prompt, choices=options, default=default).unsafe_ask()
        else:
            if secret:
                return q.password(prompt, default=default).unsafe_ask()
            elif path:
                return q.path(prompt, default=default).unsafe_ask()
            else:
                return q.text(prompt, default=default).unsafe_ask()

    def install_base(self, module: ModuleType):
        module.ask = self.ask
        module.confirm = self.confirm
        module.print = Display.print

    def install_execution(self, module: ModuleType, target_dir: Path, allow_overwrite: bool):
        self._target_dir = target_dir
        self._allow_overwrite = allow_overwrite

        module.render_template = self.render_template
        module.target_dir = target_dir

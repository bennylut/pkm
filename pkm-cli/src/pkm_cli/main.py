import cProfile
import os
import pstats
from pathlib import Path
from pstats import SortKey
from typing import Optional, Any, List, Iterable

import sys

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.packages.package_installation_info import StoreMode
from pkm.api.pkm import pkm, HasAttachedRepository
from pkm.api.projects.project import Project
from pkm.api.repositories.repositories_configuration import RepositoryInstanceConfig
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.ctxman import with_gc_context
from pkm.utils.enums import enum_by_name
from pkm.utils.processes import execvpe
from pkm.utils.sequences import startswith
from pkm_cli import cli_monitors
from pkm_cli.api.dynamic_cli.command_parser import DynamicCommandLine, command_definitions_from, command, flag, option, \
    Command, \
    ChoicesReader, ArgumentReader, ArgumentDef, ArgumentsBuffer, ArgumentFieldsProvider, OptionDef, positional, \
    dynamic_commands, CommandDef
from pkm_cli.api.dynamic_cli.method_parser import fields_from_method
from pkm_cli.api.tasks.tasks_executor import TasksExecutor
from pkm_cli.api.tasks.tasks_runner import TasksRunner
from pkm_cli.api.templates.template_runner import TemplateRunner
from pkm_cli.controllers.prj_controller import PrjController
from pkm_cli.display.display import restore_cursor
from pkm_cli.utils.context import Context

tasks: Optional[TasksRunner] = None


class RepositoryInstanceFieldsProvider(ArgumentFieldsProvider):

    def provide(self, cmd: Command, arg: ArgumentDef, value: Any) -> Iterable[OptionDef]:
        for rtype in pkm.repository_loader.available_repository_types():
            if rtype.type_name == value:
                fields = fields_from_method(rtype.builder.build)
                return fields[2:]  # without the self and name field
        raise UnsupportedOperationException(f"unknown repository type: {value}")


class AvailableRepositorySelectionReader(ArgumentReader):

    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        if not (har := Context.of(cmd).lookup_has_attached_repository()):
            raise UnsupportedOperationException("context does not support attached repositories")

        name = buf.next_or_raise("expecting repository name")
        repos_by_name = dict(har.repository_management.all_repositories())
        if not (repo := repos_by_name.get(name, None)):
            raise ValueError(f"undefined repository: {name} given for {argument.display_name}")
        return repo


@command(
    "pkm",
    flag("-v, --verbose", help="run with verbose output"),
    option("-c, --context", help="path to the context to run this command under", default=None,
           mutex_group="context", reader=Path),
    flag('-g, --global-context', help="use the global environment context", mutex_group="context"),
    flag("-T, --without-tasks", help="dont run command-attached tasks"),
    flag("-p, --profiler", help="run with cprofiler and print results")
)
def pkm_(cmd: Command):
    cli_monitors.listen(cmd.verbose)
    if cmd.profiler:
        with cProfile.Profile() as pr:
            yield
            pstats.Stats(pr).strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)


@dynamic_commands("pkm run")
def pkm_run(cmd: Command, next_args: ArgumentsBuffer) -> List[CommandDef]:
    next_ = next_args.peek_or_none()
    context = Context.of(cmd)

    @command("", positional("cmd-and-args", n_values="*"))
    def os_exec(cmd: Command):
        if not (caa := cmd.cmd_and_args):
            raise UnsupportedOperationException("command is required to be executed")

        def on_environment(env: Environment):
            with env.activate():
                restore_cursor()
                sys.exit(execvpe(caa[0], caa[1:], os.environ))

        def on_project(project_: Project):
            on_environment(project_.attached_environment)

        context.run(**locals())

    if next_ is None or not next_.startswith("@"):
        return command_definitions_from([os_exec])

    if not (project := context.lookup_project()):
        raise UnsupportedOperationException("tasks can only be executed in project context")

    @command("", positional("task"), positional("args", n_values="*", default=[]))
    def task_exec(cmd: Command):
        TasksExecutor.execute(project, cmd.task, cmd.args)

    return command_definitions_from([task_exec])


@dynamic_commands('pkm new')
def pkm_new(_: Command, next_args: ArgumentsBuffer) -> List[CommandDef]:
    tr = TemplateRunner()
    if template_name := next_args.peek_or_none():
        try:
            return [with_gc_context(tr.load_template(template_name)).as_command(template_name)]
        except:
            ...

    names = tr.templates_in_namespace()
    if template_name and (filtered := [it for it in names if it.startswith(template_name)]):
        names = filtered

    return [with_gc_context(tr.load_template(it)).as_command(it) for it in names]


@command(
    'pkm install',
    option("-o, --optional", default=None, help="optional group to use (only for projects)"),
    flag("-f, --force", help="forcefully remove and reinstall the given pacakges"),
    flag("-a, --app", help="install package in containerized application mode"),
    flag("-u, --update", help="update the given packages if already installed"),
    option("-m, --mode", default='auto', reader=ChoicesReader(['editable', 'copy', 'auto']),
           help="choose the installation mode for the requested packages."),
    option('-s, --site', default='user', reader=ChoicesReader(['user', 'system']),
           help="applicable for global-context, which site to use - defaults to 'user'"),
    option('-r, --repo', default=None, reader=AvailableRepositorySelectionReader(),
           help="bind the given packages to a specific repository by name"),
    option('-R, --unnamed-repo', fields_provider=RepositoryInstanceFieldsProvider(), default=None,
           help="bind the given packages to a new unnamed repositry given its configuration"),
    positional('packages', n_values="*", help="the packages to install (support pep508 dependency syntax)"))
def pkm_install(cmd: Command):
    """
    install packages under the current context
    """

    dependencies = [Dependency.parse(it) for it in cmd.packages]
    store_mode = enum_by_name(StoreMode, cmd.mode.upper())

    def register_repo_bindings(contex: HasAttachedRepository):
        if repo := cmd.repo:
            if any(contex.repository_management.configuration.package_bindings.get(d.package_name) != repo
                   for d in dependencies):
                contex.repository_management.register_bindings([d.package_name for d in dependencies], repo)
                cmd.force = True
        elif repo_type := cmd.unnamed_repo:
            instance_config = RepositoryInstanceConfig(repo_type, True, getattr(args, 'unnamed_repo_extras', {}))
            contex.repository_management.register_bindings([d.package_name for d in dependencies], instance_config)
            cmd.force = True

    def force(target: PackageInstallationTarget):
        if cmd.force:
            for d in dependencies:
                target.force_remove(d.package_name)

    def on_project(project: Project):
        register_repo_bindings(project)
        if cmd.app:
            raise UnsupportedOperationException("application install as project dependency is not supported")

        force(project.attached_environment.installation_target)
        ctrl = PrjController(project)
        if dependencies:
            ctrl.install_dependencies(
                dependencies, optional_group=cmd.optional, update=cmd.update, store_mode=store_mode)
        else:
            ctrl.install_project(optional_group=cmd.optional)

    def on_environment(env: Environment):
        nonlocal dependencies
        register_repo_bindings(env)
        if cmd.optional:
            raise UnsupportedOperationException("optional dependencies are only supported inside projects")

        if dependencies:
            target = env.installation_target
            if cmd.app:
                target = env.package_containers.install(
                    dependencies[0], store_mode=store_mode,
                    update=cmd.update and len(dependencies) == 1).installation_target
                dependencies = dependencies[1:]

            if dependencies:
                force(target)
                updates = [d.package_name for d in dependencies] if args.update else None
                store_modes = {d.package_name: store_mode for d in dependencies}
                target.install(dependencies, updates=updates, store_mode=store_modes)

    context.run(**locals())


def parse(args: List[str]) -> Command:
    args[0] = "pkm"
    return DynamicCommandLine.create(command_definitions_from(globals()), args).parse()


def main(args: Optional[List[str]] = None):
    args = args if args is not None else sys.argv
    cmd = parse(args)

    if cmd.parse_error or cmd.help:
        cmd.print_help()
        if getattr(cmd, 'verbose', True) and cmd.parse_error:
            raise cmd.parse_error
    else:
        global context
        context = Context.of(cmd)

        def with_tasks(p: Project):
            global tasks
            tasks = TasksRunner(p)
            with tasks.run_attached(cmd):
                cmd.execute()

        context.run(on_project=with_tasks, on_missing=cmd.execute, silent=True)


if __name__ == '__main__':
    main(sys.argv)

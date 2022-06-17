import argparse
import cProfile
import os
import pstats
from argparse import Namespace, ArgumentParser
from contextlib import contextmanager
from pathlib import Path
from pstats import SortKey
from typing import List, Optional, Dict

import sys

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package_installation_info import StoreMode
from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.pkm import pkm, HasAttachedRepository
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repositories_configuration import RepositoryInstanceConfig
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.enums import enum_by_name
from pkm.utils.processes import execvpe
from pkm_cli import cli_monitors
from pkm_cli.api.tasks.tasks_runner import TasksRunner
from pkm_cli.api.templates.template_runner import TemplateRunner
from pkm_cli.controllers.env_controller import EnvController
from pkm_cli.controllers.prj_controller import PrjController
from pkm_cli.controllers.self_controller import SelfController
from pkm_cli.display.display import Display
from pkm_cli.reports.added_repositories_report import AddedRepositoriesReport
from pkm_cli.reports.environment_report import EnvironmentReport
from pkm_cli.reports.installed_repositories_report import InstalledRepositoriesReport
from pkm_cli.reports.package_report import PackageReport
from pkm_cli.reports.pkm_report import PkmReport
from pkm_cli.reports.project_report import ProjectReport
from pkm_cli.reports.report import Report
from pkm_cli.utils.clis import command, Arg, create_args_parser, Command, with_extras
from pkm_cli.utils.context import Context

context: Optional[Context] = None
tasks: Optional[TasksRunner] = None


def _cli_container() -> PackageInstallationTarget:
    global_env = Environment.current()
    if pkm_container := global_env.package_containers.container_of('pkm-cli'):
        return pkm_container.installation_target
    return global_env.installation_target


def status_command(path: str):
    return command(
        path, Arg(['-l', '--list-options'], action='store_true'), Arg(['-i', '--include'], nargs='*'),
        Arg(['-x', '--exclude'], nargs='*'))


def _show_status(report: Report, args: Namespace):
    Display.print()

    if args.list_options:
        report.display_options()
        return

    options = {}
    options.update({s: True for s in args.include or []})
    options.update({s: False for s in args.exclude or []})

    report.display(options)


# noinspection PyUnusedLocal
@status_command('pkm self status')
def self_version(args: Namespace):
    _show_status(PkmReport(), args)


@command('pkm self update', Arg(["-s", "--version-spec"], default="*"))
def self_update(args: Namespace):
    SelfController().update(VersionSpecifier.parse(args.version_spec))


@command(
    'pkm self install',
    Arg(["-u", "--update"], action='store_true', help="update the given packages if already installed"),
    Arg(["-m", "--mode"], required=False, default='editable', choices=['editable', 'copy'],
        help="choose the installation mode for the requested packages."),
    Arg('packages', nargs=argparse.REMAINDER, help="the packages to install (support pep508 dependency syntax)"))
def self_install(args: Namespace):
    dependencies = [Dependency.parse(d) for d in args.packages]
    store_mode = enum_by_name(StoreMode, args.mode.upper())
    SelfController().install_plugins(dependencies, store_mode=store_mode, update=args.update)


@command(
    'pkm self uninstall',
    Arg(["-f", "--force"], action="store_true",
        help="remove the requested packages even if they are dependant of other packages, "
             "will not remove any other packages or update pyproject"),
    Arg('package_names', nargs=argparse.REMAINDER, help="the packages to remove"))
def self_uninstall(args: Namespace):
    SelfController().uninstall_plugin(args.package_names, force=args.force)


@command('pkm repos install', Arg(["-u", "--update"], action="store_true"), Arg('names', nargs=argparse.REMAINDER))
def install_repos(args: Namespace):
    if not args.global_context:
        raise UnsupportedOperationException("repository installation is only supported in global context (add -g)")

    updates = args.names if args.update else []
    _cli_container().install([Dependency.parse(it) for it in args.names], updates=updates)


@command('pkm repos uninstall', Arg('names', nargs=argparse.REMAINDER))
def uninstall_repo(args: Namespace):
    if not args.global_context:
        raise UnsupportedOperationException("repository uninstallation is only supported in global context (add -g)")

    _cli_container().uninstall(args.names)


@command('pkm repos show installed')
def show_installed_repositories(_: Namespace):
    InstalledRepositoriesReport().display()


@command(
    'pkm repos add',
    Arg("repo_name"),
    Arg("type", action=with_extras()),
    Arg(['-b', '--bind-only'], action="store_true", required=False))
def add_repo(args: Namespace):
    def add(with_repo: HasAttachedRepository):
        with_repo.repository_management.add_repository(
            args.repo_name, args.type, getattr(args, 'type_extras', {}), args.bind_only)

    on_environment, on_project, on_project_group, = add, add, add
    context.run(**locals())


@command('pkm repos remove', Arg("name"))
def remove_repo(args: Namespace):
    def rm(with_repo: HasAttachedRepository):
        with_repo.repository_management.remove_repository(args.name)

    on_environment, on_project, on_project_group, = rm, rm, rm
    context.run(**locals())


@command('pkm repos show added')
def show_added_repositories(args: Namespace):
    def show(with_repo: HasAttachedRepository):
        AddedRepositoriesReport(with_repo).display()

    on_environment, on_project, on_project_group, = show, show, show
    context.run(**locals())


@command('pkm run', Arg('cmd', nargs=argparse.REMAINDER))
def run(args: Namespace):
    if not args.cmd:
        raise UnsupportedOperationException("command is required to be executed")

    def on_environment(env: Environment):
        with env.activate():
            sys.exit(execvpe(args.cmd[0], args.cmd[1:], os.environ))

    def on_project(project: Project):
        if args.cmd[0].startswith("@"):
            task_name = args.cmd[0][1:]
            task_args = args.cmd[1:]
            if '-h' in task_args:
                Display.print(tasks.describe(task_name))
            else:
                sys.exit(tasks.run(task_name, task_args))
        else:
            on_environment(project.attached_environment)

    context.run(**locals())


# noinspection PyUnusedLocal
@command('pkm build')
def build(args: Namespace):
    def on_project(project: Project):
        if any((u := d.required_url()) and u.protocol == 'file'
               for d in (project.config.project.dependencies or [])):
            Display.print("[orange1]Warning[/] you are building a project that depends on packages located in your "
                          "file system, [red]publishing this project will result in unusable package[/]")
        project.build()

    def on_project_group(project_group: ProjectGroup):
        project_group.build_all()

    context.run(**locals())


@command(
    'pkm vbump',
    Arg('particle', choices=['major', 'minor', 'patch', 'a', 'b', 'rc'], nargs='?', default='patch'))
def vbump(args: Namespace):
    def on_project(project: Project):
        new_version = project.bump_version(args.particle)
        Display.print(f"Version bumped to: {new_version}")

    context.run(**locals())


@command(
    'pkm install',
    Arg(["-o", "--optional"], help="optional group to use (only for projects)"),
    Arg(["-f", "--force"], action='store_true', help="forcefully remove and reinstall the given pacakges"),
    Arg(["-a", "--app"], action='store_true', help="install package in containerized application mode"),
    Arg(["-u", "--update"], action='store_true', help="update the given packages if already installed"),
    Arg(["-m", "--mode"], required=False, default='auto', choices=['editable', 'copy', 'auto'],
        help="choose the installation mode for the requested packages."),
    Arg(['-s', '--site'], required=False, choices=['user', 'system'],
        help="applicable for global-context, which site to use - defaults to 'user'"),
    Arg(['-r', '--repo'], required=False,
        help="bind the given packages to a specific repositry by name, use 'default' to remove previous binding"),
    Arg(['-R', '--unnamed-repo'], required=False, action=with_extras(),
        help="bind the given packages to a new unnamed repositry given its configuration"),
    Arg('packages', nargs=argparse.REMAINDER, help="the packages to install (support pep508 dependency syntax)"))
def install(args: Namespace):
    """
    install packages under the current context
    """

    dependencies = [Dependency.parse(it) for it in args.packages]
    store_mode = enum_by_name(StoreMode, args.mode.upper())

    def register_repo_bindings(contex: HasAttachedRepository):
        if repo := args.repo:
            repo = None if repo == 'default' else repo
            if any(contex.repository_management.configuration.package_bindings.get(d.package_name) != repo
                   for d in dependencies):
                contex.repository_management.register_bindings([d.package_name for d in dependencies], repo)
                args.force = True
        elif repo_type := args.unnamed_repo:
            instance_config = RepositoryInstanceConfig(repo_type, True, getattr(args, 'unnamed_repo_extras', {}))
            contex.repository_management.register_bindings([d.package_name for d in dependencies], instance_config)
            args.force = True

    def force(target: PackageInstallationTarget):
        if args.force:
            for d in dependencies:
                target.force_remove(d.package_name)

    def on_project(project: Project):
        register_repo_bindings(project)
        if args.app:
            raise UnsupportedOperationException("application install as project dependency is not supported")

        force(project.attached_environment.installation_target)
        ctrl = PrjController(project)
        if dependencies:
            ctrl.install_dependencies(
                dependencies, optional_group=args.optional, update=args.update, store_mode=store_mode)
        else:
            ctrl.install_project(optional_group=args.optional)

    def on_environment(env: Environment):
        nonlocal dependencies
        register_repo_bindings(env)
        if args.optional:
            raise UnsupportedOperationException("optional dependencies are only supported inside projects")

        if dependencies:
            target = env.installation_target
            if args.app:
                target = env.package_containers.install(
                    dependencies[0], store_mode=store_mode,
                    update=args.update and len(dependencies) == 1).installation_target
                dependencies = dependencies[1:]

            if dependencies:
                force(target)
                updates = [d.package_name for d in dependencies] if args.update else None
                store_modes = {d.package_name: store_mode for d in dependencies}
                target.install(dependencies, updates=updates, store_mode=store_modes)

    context.run(**locals())


@command(
    "pkm uninstall-orphans",
    Arg(["-a", "--app"], action='store_true', help="uninstall orphans in containerized package"))
def uninstall_orphans(args: Namespace):
    def on_environment(env: Environment):
        EnvController(env).uninstall_orphans(args.app)

    def on_project(prj: Project):
        on_environment(prj.attached_environment)

    context.run(**locals())


@command('pkm uninstall', Arg(["-a", "--app"], action='store_true', help="remove containerized packages"),
         Arg(["-f", "--force"], action="store_true",
             help="remove the requested packages even if they are dependant of other packages, "
                  "will not remove any other packages or update pyproject"),
         Arg('package_names', nargs=argparse.REMAINDER, help="the packages to remove"))
def uninstall(args: Namespace):
    """
    remove packages from the current context
    """

    if not args.package_names:
        raise ValueError("no package names are provided to be removed")

    def on_project(project: Project):
        if args.app:
            raise UnsupportedOperationException("application install/remove as project dependency is not supported")
        PrjController(project).uninstall_dependencies(args.package_names, args.force)

    def on_environment(env: Environment):
        app = args.package_names[0] if args.app else None
        package_names = args.package_names[1:] if args.app else args.package_names
        EnvController(env).uninstall(package_names, args.force, app)

    context.run(**locals())


@command('pkm publish', Arg('repo', action=with_extras()), Arg(['-s', '--save'], action='store_true'))
def publish(args: Namespace):
    try:
        from pkm_cli.auth.publish_auth_store import PublishAuthenticationStore
        publish_auth = PublishAuthenticationStore()
    except Exception as e:
        Display.print(f"[red]Could not load publish authentication store: {e}[/red]")
        publish_auth = None

    def on_project(project: Project):
        if not project.is_built_in_default_location():
            project.build()

        if not (publisher := project.repository_management.publisher_for(args.repo)):
            raise UnsupportedOperationException(f"repository: {args.repo} does not support publishing")

        auth_args: Dict[str, str] = {}
        if hasattr(args, 'repo_extras'):
            auth_args = args.repo_extras
        elif publisher.requires_authentication():
            if not publish_auth or not publish_auth.is_configuration_exists() \
                    or not (auth_args := publish_auth.auth_args_for(args.repo)):
                raise UnsupportedOperationException("authentication required")

        project.publish(publisher, auth_args)
        if args.save and publish_auth:
            publish_auth.add_auth_args(args.repo, auth_args)

    context.run(**locals())


@command(
    'pkm new',
    Arg('template'), Arg(["-o", "--overwrite"], action="store_true"),
    Arg('template_args', nargs=argparse.REMAINDER))
def new(args: Namespace):
    tr = TemplateRunner()
    if "-h" in args.template_args:
        Display.print(tr.describe(args.template))
    else:
        tr.run(args.template, Path.cwd(), args.template_args, bool(args.overwrite))
        Display.print("Template Execution Completed Successfully.")


@status_command('pkm status')
def status(args: Namespace):
    def on_project(project: Project):
        _show_status(ProjectReport(project), args)

    def on_environment(env: Environment):
        _show_status(EnvironmentReport(env), args)

    context.run(**locals())


@command('pkm show package', Arg('dependency'))
def show_package(args: Namespace):
    def on_project(project: Project):
        PackageReport(project, args.dependency).display()

    def on_environment(env: Environment):
        PackageReport(env, args.dependency).display()

    context.run(**locals())


# noinspection PyUnusedLocal
@command('pkm clean cache')
def clean_cache(args: Namespace):
    pkm.clean_cache()


# noinspection PyUnusedLocal
@command('pkm clean shared')
def clean_shared(args: Namespace):
    def on_env_zoo(env_zoo: EnvironmentsZoo):
        env_zoo.clean_unused_shared()

    context.run(**locals())


@command('pkm clean dist', Arg(["--all", "-a"], action="store_true"))
def clean_dist(args: Namespace):
    def on_project(project: Project):
        keep_versions = [project.version] if not args.all else None
        project.directories.clean_dist(keep_versions)

    context.run(**locals())


def prepare_parser() -> ArgumentParser:
    pkm_parser = create_args_parser(
        "pkm - python package management for busy developers", globals().values())

    pkm_parser.add_argument('-v', '--verbose', action='store_true', help="run with verbose output")
    pkm_parser.add_argument('-c', '--context', help="path to the context to run this command under")
    pkm_parser.add_argument('-g', '--global-context', action='store_true', help="use the global environment context")
    pkm_parser.add_argument('-nt', '--no-tasks', action='store_true', help="dont run command-attached tasks")
    pkm_parser.add_argument('-p', '--profile', action='store_true', help="run with cprofiler and print results")

    return pkm_parser


@contextmanager
def profile(args: Namespace):
    if args.profile:
        with cProfile.Profile() as pr:
            yield
            pstats.Stats(pr).strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats(20)
    else:
        yield


def main(args: Optional[List[str]] = None):
    global context
    args = args or sys.argv[1:]

    pkm_parser = prepare_parser()

    pargs = pkm_parser.parse_args(args)
    with profile(pargs):

        cli_monitors.listen('verbose' in pargs and pargs.verbose)
        context = Context.of(pargs)

        if 'func' in pargs:
            def with_tasks(p: Project):
                global tasks
                tasks = TasksRunner(p)
                with tasks.run_attached(Command.of(pargs.func), pargs):
                    pargs.func(pargs)

            def without_tasks():
                pargs.func(pargs)

            if pargs.no_tasks:
                without_tasks()
            else:
                context.run(on_project=with_tasks, on_missing=without_tasks, silent=True)
        else:
            pkm_parser.print_help()

    Display.print("", newline=False)


if __name__ == "__main__":
    main()

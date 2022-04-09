import argparse
import os
import shutil
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import Authentication
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.processes import execvpe
from pkm.utils.resources import ResourcePath
from pkm_cli import cli_monitors
from pkm_cli.context import Context
from pkm_cli.display.display import Display
from pkm_cli.reports.environment_report import EnvironmentReport
from pkm_cli.reports.package_report import PackageReport
from pkm_cli.reports.project_report import ProjectReport
from pkm_cli.scaffold.engine import ScaffoldingEngine
from pkm_cli.utils.clis import command, Arg, create_args_parser, Command


@command('pkm run', Arg('cmd', nargs=argparse.REMAINDER))
def py(args: Namespace):
    def on_environment(env: Environment):
        if not args.cmd:
            raise UnsupportedOperationException("command is required to be executed")

        with env.activate():
            sys.exit(execvpe(args.cmd[0], args.cmd[1:], os.environ))

    Context.of(args).run(**locals())


# noinspection PyUnusedLocal
@command('pkm shell', Arg(["-e", '--execute'], required=False, nargs=argparse.REMAINDER))
def shell(args: Namespace):
    def on_environment(env: Environment):
        with env.activate():
            if execution := args.execute:
                sys.exit(execvpe(execution[0], execution[1:], os.environ))

            import xonsh.main
            sys.exit(xonsh.main.main([]))

    def on_project(project: Project):
        on_environment(project.attached_environment)

    def on_free_context():
        on_environment(Environment.current())

    Context.of(args).run(**locals())


# noinspection PyUnusedLocal
@command('pkm build')
def build(args: Namespace):
    def on_project(project: Project):
        project.build()

    def on_project_group(project_group: ProjectGroup):
        project_group.build_all()

    Context.of(args).run(**locals())


@command(
    'pkm vbump',
    Arg('particle', choices=['major', 'minor', 'patch', 'a', 'b', 'rc'], nargs='?', default='patch'))
def vbump(args: Namespace):
    def on_project(project: Project):
        new_version = project.bump_version(args.particle)
        Display.print(f"Version bumped to: {new_version}")

    Context.of(args).run(**locals())


@command('pkm install', Arg(["-o", "--optional"]), Arg('dependencies', nargs=argparse.REMAINDER))
def install(args: Namespace):
    dependencies = [Dependency.parse(it) for it in args.dependencies]
    optional_group = getattr(args, "optional", None)

    def on_project(project: Project):
        Display.print(f"Adding dependencies into project: {project.path}")
        project.install_with_dependencies(dependencies, optional_group=optional_group)

    def on_project_group(project_group: ProjectGroup):
        if dependencies:
            raise UnsupportedOperationException("could not install dependencies in project group")

        Display.print(f"Installing all projects in group")
        project_group.install_all()

    def on_environment(env: Environment):
        if optional_group:
            raise UnsupportedOperationException("optional dependencies are only supported inside projects")
        env.install(dependencies)

    Context.of(args).run(**locals())


@command('pkm remove', Arg('package_names', nargs=argparse.REMAINDER))
def remove(args: Namespace):
    if not (package_names := args.package_names):
        raise ValueError("no package names are provided to be removed")

    def on_project(project: Project):
        Display.print(f"Removing packages from project: {project.path}")
        project.remove_dependencies(package_names)

    def on_environment(env: Environment):
        env.uninstall(package_names)

    Context.of(args).run(**locals())


@command('pkm publish', Arg('user'), Arg('password'))
def publish(args: Namespace):
    if not (uname := args.user):
        raise ValueError("missing user name")

    if not (password := args.password):
        raise ValueError("missing password")

    def on_project(project: Project):
        if not project.is_built_in_default_location():
            project.build()

        project.publish(pkm.repositories.pypi, Authentication(uname, password))

    def on_project_group(project_group: ProjectGroup):
        project_group.publish_all(pkm.repositories.pypi, Authentication(uname, password))

    Context.of(args).run(**locals())


@command('pkm new', Arg('template'), Arg('template_args', nargs=argparse.REMAINDER))
def new(args: Namespace):
    ScaffoldingEngine().render(
        ResourcePath('pkm_cli.scaffold', f"new_{args.template}.tar.gz"), Path.cwd(), args.template_args)


@command('pkm show context')
def show_context(args: Namespace):
    def on_project(project: Project):
        ProjectReport(project).display()

    def on_environment(env: Environment):
        EnvironmentReport(env).display()

    Context.of(args).run(**locals())


@command('pkm show package', Arg('dependency'))
def show_package(args: Namespace):
    def on_project(project: Project):
        PackageReport(project, args.dependency).display()

    def on_environment(env: Environment):
        PackageReport(env, args.dependency).display()

    Context.of(args).run(**locals())


# noinspection PyUnusedLocal
@command('pkm clean cache')
def clean_cache(args: Namespace):
    pkm.clean_cache()


# noinspection PyUnusedLocal
@command('pkm clean shared')
def clean_shared(args: Namespace):
    def on_env_zoo(env_zoo: EnvironmentsZoo):
        env_zoo.clean_unused_shared()

    Context.of(args).run(**locals())


@command('pkm clean dist')
def clean_dist(args: Namespace):
    def on_project(project: Project):
        if (dist := project.directories.dist).exists():
            shutil.rmtree(dist)

    Context.of(args).run(**locals())


def main(args: Optional[List[str]] = None):
    args = args or sys.argv[1:]

    def customize_command(cmd: ArgumentParser, _: Command):
        cmd.add_argument('-v', '--verbose', action='store_true')
        cmd.add_argument('-c', '--context')
        cmd.add_argument('-g', '--global-context', action='store_true')

    pkm_parser = create_args_parser(
        "pkm - python package management for busy developers", globals().values(), customize_command)

    pargs = pkm_parser.parse_args(args)
    cli_monitors.listen('verbose' in pargs and pargs.verbose)
    if 'func' in pargs:
        pargs.func(pargs)
    else:
        pkm_parser.print_help()

    Display.print("")


if __name__ == "__main__":
    main()

import xonsh.main
from prompt_toolkit.patch_stdout import patch_stdout
from typing import List, Optional, Callable

import sys

import argparse
from argparse import ArgumentParser, Namespace
from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import Authentication
from pkm.utils.archives import extract_archive
from pkm.utils.commons import NoSuchElementException, UnsupportedOperationException
from pkm.utils.files import temp_dir
from pkm_cli.display.display import Display
from pkm_cli.monitors.environment_monitors import ConsoleEnvironmentOperationsMonitor
from pkm_cli.monitors.project_monitors import ConsoleProjectOperationsMonitor
from pkm_cli.scaffold.engine import ScaffoldingEngine


def _lookup_project_group() -> ProjectGroup:
    return ProjectGroup.load(Path.cwd())


def _lookup_project() -> Project:
    return Project.load(Path.cwd())


def _lookup_env() -> Environment:
    env_path = Path.cwd() / '.venv'
    return Environment(env_path)


# noinspection PyUnusedLocal
def _run_contextual(
        on_project: Optional[Callable[[Project], None]] = None,
        on_project_group: Optional[Callable[[ProjectGroup], None]] = None,
        on_environment: Optional[Callable[[Environment], None]] = None,
        on_free_context: Optional[Callable[[], None]] = None,
        on_missing: Optional[Callable[[], None]] = None,
        **junk
):
    if on_project and (project := _lookup_project()).config.exists():
        on_project(project)
    elif on_project_group and (project_group := _lookup_project_group()).config.exists():
        on_project_group(project_group)
    elif on_environment and (env := _lookup_env()).path.exists():
        on_environment(env)
    elif on_free_context:
        on_free_context()
    elif on_missing:
        on_missing()
    else:
        raise UnsupportedOperationException("could not execute operation")


# noinspection PyUnusedLocal
def shell(args: Namespace):
    def on_environment(env: Environment):
        Display.print(f"Using environment: {env.path}")
        env.exec_proc('python', ['-c', 'import sys;import xonsh.main;sys.exit(xonsh.main.main())'])

    def on_project(project: Project):
        on_environment(project.default_environment)

    def on_free_context():
        on_environment(Environment.current())

    _run_contextual(**locals())


# noinspection PyUnusedLocal
def build(args: Namespace):
    def on_project(project: Project):
        project.build()

    def on_project_group(project_group: ProjectGroup):
        project_group.build_all()

    _run_contextual(**locals())


def project_bump(args: Namespace):
    def on_project(project: Project):
        Display.print(f"Using Project: {project}")
        new_version = project.bump_version(args.particle)
        Display.print(f"Version bumped to: {new_version}")

    _run_contextual(**locals())


def install(args: Namespace):
    dependencies = [Dependency.parse_pep508(it) for it in args.dependencies]

    def on_project(project: Project):
        print(f"Adding dependencies into project: {project.path}")
        project.install_with_dependencies(dependencies, monitor=ConsoleProjectOperationsMonitor())

    def on_project_group(project_group: ProjectGroup):
        if dependencies:
            raise UnsupportedOperationException("could not install dependencies in project group")

        print(f"Installing all projects in group")
        project_group.install_all()

    def on_environment(env: Environment):
        print(f"Adding dependencies into environment: {env.path}")
        env.install(dependencies, pkm.repositories.pypi, monitor=ConsoleEnvironmentOperationsMonitor())

    _run_contextual(**locals())


def remove(args: Namespace):
    if not (package_names := args.package_names):
        raise ValueError("no package names are provided to be removed")

    def on_project(project: Project):
        print(f"Removing packages from project: {project.path}")
        project.remove_dependencies(package_names)

    def on_environment(env: Environment):
        print(f"Removing packages from environment: {env.path}")
        env.uninstall(package_names)

    _run_contextual(**locals())


def publish(args: Namespace):
    if not (uname := args.user):
        raise ValueError("missing user name")

    if not (password := args.password):
        raise ValueError("missing password")

    def on_project(project: Project):
        project.publish(pkm.repositories.pypi, Authentication(uname, password))

    def on_project_group(project_group: ProjectGroup):
        project_group.publish_all(pkm.repositories.pypi, Authentication(uname, password))

    _run_contextual(**locals())


def new(args: Namespace):
    from importlib.resources import path
    with path('pkm_cli.scaffold', f"new_{args.template}.tar.gz") as template_path:
        with temp_dir() as tdir:
            extract_archive(template_path, tdir)
            ScaffoldingEngine().render(tdir, Path.cwd(), args.template_args)


def main(args: Optional[List[str]] = None):
    args = args or sys.argv[1:]

    pkm_parser = ArgumentParser(description="pkm - python package management for busy developers")
    pkm_subparsers = pkm_parser.add_subparsers()

    pkm_build_parser = pkm_subparsers.add_parser('build')
    pkm_build_parser.set_defaults(func=build)

    pkm_shell_parser = pkm_subparsers.add_parser('shell')
    pkm_shell_parser.set_defaults(func=shell)

    pkm_install_parser = pkm_subparsers.add_parser('install')
    pkm_install_parser.add_argument('dependencies', nargs=argparse.REMAINDER)
    pkm_install_parser.set_defaults(func=install)

    pkm_remove_parser = pkm_subparsers.add_parser('remove')
    pkm_remove_parser.add_argument('package_names', nargs=argparse.REMAINDER)
    pkm_remove_parser.set_defaults(func=remove)

    pkm_new_parser = pkm_subparsers.add_parser('new')
    pkm_new_parser.add_argument('template')
    pkm_new_parser.add_argument('template_args', nargs=argparse.REMAINDER)
    pkm_new_parser.set_defaults(func=new)

    pkm_publish_parser = pkm_subparsers.add_parser('publish')
    pkm_publish_parser.add_argument('user')
    pkm_publish_parser.add_argument('password')
    pkm_publish_parser.set_defaults(func=publish)

    pkm_project_parser = pkm_subparsers.add_parser('project')
    pkm_project_subparsers = pkm_project_parser.add_subparsers()
    pkm_project_bump_parser = pkm_project_subparsers.add_parser('bump')
    pkm_project_bump_parser.add_argument('particle', choices=['major', 'minor', 'patch', 'a', 'b', 'rc'], nargs='?')
    pkm_project_bump_parser.set_defaults(func=project_bump, particle='patch')

    (pargs := pkm_parser.parse_args(args)).func(pargs)


if __name__ == "__main__":
    main()

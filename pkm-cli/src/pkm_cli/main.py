import argparse
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import List, Optional, Callable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import Authentication
from pkm.utils.archives import extract_archive
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.files import temp_dir
from pkm_cli.context import Context
from pkm_cli.display.display import Display
from pkm_cli.monitors.environment_monitors import ConsoleEnvironmentOperationsMonitor
from pkm_cli.monitors.project_monitors import ConsoleProjectOperationsMonitor
from pkm_cli.scaffold.engine import ScaffoldingEngine


# noinspection PyUnusedLocal
def shell(args: Namespace):
    def on_environment(env: Environment):
        Display.print(f"Using environment: {env.path}")
        env.exec_proc('python', ['-c', 'import sys;import xonsh.main;sys.exit(xonsh.main.main())'])

    def on_project(project: Project):
        on_environment(project.default_environment)

    def on_free_context():
        on_environment(Environment.current())

    Context.of(args).run(**locals())


# noinspection PyUnusedLocal
def build(args: Namespace):
    def on_project(project: Project):
        project.build()

    def on_project_group(project_group: ProjectGroup):
        project_group.build_all()

    Context.of(args).run(**locals())


def vbump(args: Namespace):
    def on_project(project: Project):
        Display.print(f"Using Project: {project}")
        new_version = project.bump_version(args.particle)
        Display.print(f"Version bumped to: {new_version}")

    Context.of(args).run(**locals())


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

    Context.of(args).run(**locals())


def remove(args: Namespace):
    if not (package_names := args.package_names):
        raise ValueError("no package names are provided to be removed")

    def on_project(project: Project):
        print(f"Removing packages from project: {project.path}")
        project.remove_dependencies(package_names)

    def on_environment(env: Environment):
        print(f"Removing packages from environment: {env.path}")
        env.uninstall(package_names)

    Context.of(args).run(**locals())


def publish(args: Namespace):
    if not (uname := args.user):
        raise ValueError("missing user name")

    if not (password := args.password):
        raise ValueError("missing password")

    def on_project(project: Project):
        project.publish(pkm.repositories.pypi, Authentication(uname, password))

    def on_project_group(project_group: ProjectGroup):
        project_group.publish_all(pkm.repositories.pypi, Authentication(uname, password))

    Context.of(args).run(**locals())


def new(args: Namespace):
    from importlib.resources import path
    with path('pkm_cli.scaffold', f"new_{args.template}.tar.gz") as template_path:
        with temp_dir() as tdir:
            extract_archive(template_path, tdir)
            ScaffoldingEngine().render(tdir, Path.cwd(), args.template_args)

def test(args: Namespace):
    def on_project(project: Project):
        print("project context")

    def on_project_group(project_group: ProjectGroup):
        print("project group")

    def on_environment(env: Environment):
        print("environment")

    def on_free_context():
        print("free context")

    Context.of(args).run(**locals())

def main(args: Optional[List[str]] = None):
    args = args or sys.argv[1:]

    pkm_parser = ArgumentParser(description="pkm - python package management for busy developers")
    pkm_subparsers = pkm_parser.add_subparsers()
    all_subparsers = []

    def create_command(name: str, func: Callable[[Namespace], None], **defaults) -> ArgumentParser:
        result = pkm_subparsers.add_parser(name)
        result.set_defaults(func=func, **defaults)
        all_subparsers.append(result)

        return result


    # pkm build
    create_command('build', build)

    # pkm shell
    create_command('shell', shell)

    # pkm install
    pkm_install_parser = create_command('install', install)
    pkm_install_parser.add_argument('dependencies', nargs=argparse.REMAINDER)

    # pkm remove
    pkm_remove_parser = create_command('remove', remove)
    pkm_remove_parser.add_argument('package_names', nargs=argparse.REMAINDER)

    # pkm new
    pkm_new_parser = create_command('new', new)
    pkm_new_parser.add_argument('template')
    pkm_new_parser.add_argument('template_args', nargs=argparse.REMAINDER)

    # pkm publish
    pkm_publish_parser = create_command('publish', publish)
    pkm_publish_parser.add_argument('user')
    pkm_publish_parser.add_argument('password')

    # pkm vbump
    pkm_vbump_parser = create_command('vbump', vbump, particle='patch')
    pkm_vbump_parser.add_argument('particle', choices=['major', 'minor', 'patch', 'a', 'b', 'rc'], nargs='?')

    # pkm test
    pkm_vbump_parser = create_command('test', test)

    # context altering flags
    for subparser in all_subparsers:
        subparser.add_argument('-c', '--context')
        subparser.add_argument('-g', '--global-context', action='store_true')

    (pargs := pkm_parser.parse_args(args)).func(pargs)


if __name__ == "__main__":
    main()
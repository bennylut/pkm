import xonsh.main
from prompt_toolkit.patch_stdout import patch_stdout
from typing import List, Optional

import sys

import argparse
from argparse import ArgumentParser, Namespace
from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.repositories.repository import Authentication
from pkm.utils.archives import extract_archive
from pkm.utils.commons import NoSuchElementException
from pkm.utils.files import temp_dir
from pkm_cli.monitors.environment_monitors import ConsoleEnvironmentOperationsMonitor
from pkm_cli.monitors.project_monitors import ConsoleProjectOperationsMonitor
from pkm_cli.scaffold.engine import ScaffoldingEngine


def _current_project(allow_missing: bool = False) -> Project:
    pyproject = (cwd := Path.cwd()) / 'pyproject.toml'
    if not allow_missing and not pyproject.exists():
        raise NoSuchElementException("could not find project in current directory")

    return Project.load(cwd)


def _current_env(allow_missing: bool = False) -> Environment:
    env_path = Path.cwd() / '.venv'
    if not allow_missing and not env_path.exists():
        raise NoSuchElementException("could not find virtual environment (.venv) in current directory")

    return Environment(env_path)


# noinspection PyUnusedLocal
def build(args: Namespace):
    _current_project().build()


# noinspection PyUnusedLocal
def shell(args: Namespace):
    env = _current_env()
    print(f"Using environment: {env.path}")
    env.exec_proc('python', ['-c', 'import sys;import xonsh.main;sys.exit(xonsh.main.main())'])


def install(args: Namespace):
    dependencies = [Dependency.parse_pep508(it) for it in args.dependencies]

    if (project := _current_project(True)).config.exists():
        print(f"Adding dependencies into project: {project.path}")
        project.install_with_dependencies(dependencies, monitor=ConsoleProjectOperationsMonitor())
    elif (env := _current_env(True)).path.exists():
        print(f"Adding dependencies into environment: {env.path}")
        env.install(dependencies, pkm.repositories.pypi, monitor=ConsoleEnvironmentOperationsMonitor())


def remove(args: Namespace):
    if not (package_names := args.package_names):
        raise ValueError("no package names are provided to be removed")

    if (project := _current_project(True)).config.exists():
        print(f"Removing packages from project: {project.path}")
        project.remove_dependencies(package_names)
    elif (env := _current_env(True)).path.exists():
        print(f"Removing packages from environment: {env.path}")
        env.uninstall(package_names)


def publish(args: Namespace):
    if not (uname := args.user):
        raise ValueError("missing user name")

    if not (password := args.password):
        raise ValueError("missing password")

    _current_project().publish(pkm.repositories.pypi, Authentication(uname, password))


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

    with patch_stdout():
        (pargs := pkm_parser.parse_args(args)).func(pargs)


if __name__ == "__main__":
    main()

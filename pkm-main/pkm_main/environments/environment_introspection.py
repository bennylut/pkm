import argparse
import json
import os
import platform
import site
import subprocess
import sys
from argparse import Namespace
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Dict

import pkg_resources
from packaging.tags import sys_tags

parser = argparse.ArgumentParser()
parser.add_argument('output', type=str)


class EnvironmentIntrospection:
    def __init__(self, compatibility_tags: List[str], installed_packages: Dict[str, str],
                 python_version: str, env_markers: Dict[str, str]):
        self.compatibility_tags = compatibility_tags
        self.installed_packages = installed_packages
        self.python_version = python_version

        # as defined in https://www.python.org/dev/peps/pep-0508/
        self.env_markers = env_markers

    def write(self, out: Path):
        out.parent.mkdir(exist_ok=True)
        with out.open('w') as out_fd:
            json.dump(self.__dict__, out_fd, indent=4, sort_keys=True)

    @classmethod
    def read(cls, path: Path) -> "EnvironmentIntrospection":
        with path.open('r') as path_fd:
            return cls(**json.load(path_fd))

    @classmethod
    def local(cls) -> "EnvironmentIntrospection":
        compatibility_tags = [str(tag) for tag in sys_tags(warn=True)]
        installed_packages = {d.project_name: str(d.version) for d in pkg_resources.working_set}
        python_version = platform.python_version()
        markers = {
            "os_name": os.name,
            "sys_platform": sys.platform,
            "platform_machine": platform.machine(),
            "platform_python_implementation": platform.python_implementation(),
            "platform_release": platform.release(),
            "platform_system": platform.system(),
            "platform_version": platform.version(),
            "python_version": '.'.join(platform.python_version_tuple()[:2]),
            "python_full_version": platform.python_version(),
            "implementation_name": sys.implementation.name,
            "implementation_version": _compute_implementation_version()
        }

        return cls(compatibility_tags, installed_packages, python_version, markers)

    @classmethod
    def remote(cls, interpreter_path: Path) -> "EnvironmentIntrospection":
        with NamedTemporaryFile() as tmp:
            subprocess.run(
                [str(interpreter_path.absolute()), __file__, tmp.name],
                env={"PYTHONPATH": os.pathsep.join(site.getsitepackages())}
            ).check_returncode()

            return cls.read(Path(tmp.name))


def _compute_implementation_version():
    if hasattr(sys, 'implementation'):
        info = sys.implementation.version
        version = '{0.major}.{0.minor}.{0.micro}'.format(info)
        kind = info.releaselevel
        if kind != 'final':
            version += kind[0] + str(info.serial)

        return version
    return "0"


if __name__ == '__main__':
    args: Namespace = parser.parse_args()

    EnvironmentIntrospection.local().write(Path(args.output))

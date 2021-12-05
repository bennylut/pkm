import json
import argparse
import subprocess
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryFile
import os
import site
from typing import List, Dict
import pkg_resources

from packaging.tags import sys_tags

parser = argparse.ArgumentParser()
parser.add_argument('output', type=str)


class EnvironmentIntrospection:
    def __init__(self, compatibility_tags: List[str], installed_packages: Dict[int, str]):
        self.compatibility_tags = compatibility_tags
        self.installed_packages = installed_packages

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
        return cls(compatibility_tags, installed_packages)

    @classmethod
    def remote(cls, interpreter_path: Path) -> "EnvironmentIntrospection":
        with TemporaryFile() as tmp:
            subprocess.run(
                [str(interpreter_path.absolute()), __file__, tmp],
                env={"PYTHONPATH": os.pathsep.join(site.getsitepackages())}
            ).check_returncode()

            return cls.read(tmp)


if __name__ == '__main__':
    args: Namespace = parser.parse_args()

    EnvironmentIntrospection.local().write(Path(args.output))

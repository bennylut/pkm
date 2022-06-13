import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from pkm.api.environments.environment import Environment
from pkm.api.environments.environment_introspection import EnvironmentIntrospection
from pkm.api.pkm import pkm
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.config.configclass import ConfigFile, config, config_field
from pkm.config.configfiles import WheelFileConfigIO
from pkm.utils.commons import NoSuchElementException

_INTERPRETER_INTROSPECTIONS: Dict[str, EnvironmentIntrospection] = {}
_PYVENV_SEP_RX = re.compile("\\s*=\\s*")


class EnvironmentBuilder:

    @staticmethod
    def create_matching(env_path: Path, spec: VersionSpecifier) -> Environment:
        """
        attempt to find the best installed python intepreter that match the given `spec` and creates an environment
        based on it
        :param env_path: the path to create the environment at
        :param spec: the required interpreter spec
        :return: the created environment
        """
        python_versions = pkm.installed_pythons.match(spec)
        if not python_versions:
            raise NoSuchElementException("could not find installed python interpreter "
                                         f"that match the given spec: {spec}")

        return EnvironmentBuilder.create(env_path, python_versions[0].interpreter)

    @staticmethod
    def create(env_path: Path, interpreter_path: Path = Path(sys.executable)) -> Environment:
        """
        creates a new virtual-environment in the given `env_path` based on the given `interpreter_path`
        :param env_path: the path where the create the new environment
        :param interpreter_path: the interpreter to use for the environment
        :return: the created environment
        """
        interpreter_path = interpreter_path.absolute()

        if env_path.exists():
            raise FileExistsError(f"{env_path} already exists")

        ispc = _introspection_for(interpreter_path)
        sys_platform = ispc['sys']['platform']
        is_windows = ispc.is_windows_env()
        sys_vinfo = ispc['sys']['version_info']

        env_path.mkdir(parents=True, exist_ok=True)

        # prepare pyvenv.cfg
        pyvenvcfg = PyVEnvConfiguration.load(env_path / 'pyvenv.cfg')

        pyvenvcfg.home = interpreter_path.parent
        pyvenvcfg.version = Version.parse('.'.join(str(it) for it in sys_vinfo[:3]))
        pyvenvcfg.include_system_site_packages = False
        pyvenvcfg.save()

        # build relevant directories
        if is_windows:
            bin_path = env_path / 'Scripts'
            include_path = env_path / 'Include'
            site_packages_path = env_path / 'Lib' / 'site-packages'
        else:
            bin_path = env_path / 'bin'
            include_path = env_path / 'include'
            site_packages_path = env_path / 'lib' / f'python{sys_vinfo[0]}.{sys_vinfo[1]}' / 'site-packages'

        for path in (bin_path, include_path, site_packages_path):
            path.mkdir(exist_ok=True, parents=True)

        if not ispc.is_32bit_interpreter and ispc['os']['name'] == 'posix' and sys_platform != 'darwin':
            (env_path / 'lib64').symlink_to(env_path / 'lib')

        # copy needed files
        if is_windows:
            file_names_to_copy = ['python.exe', 'python_d.exe', 'pythonw.exe', 'pythonw_d.exe']
            python_dir = interpreter_path.parent
            for file_name in file_names_to_copy:
                if (python_file := python_dir / file_name).exists():
                    shutil.copy(python_file, bin_path / file_name)

            if ispc['sysconfig']['is_python_build']:
                # copy init.tcl
                if init_tcl := next(python_dir.rglob("**/init.tcl"), None):
                    target_init_tcl = env_path / str(init_tcl.relative_to(python_dir))
                    target_init_tcl.parent.mkdir(exist_ok=True, parents=True)
                    shutil.copy(init_tcl, target_init_tcl)
        else:
            for i in range(3):
                executable_name = f"python{'.'.join(str(it) for it in sys_vinfo[:i])}"
                executable_path = bin_path / executable_name
                if not executable_path.exists():
                    executable_path.symlink_to(interpreter_path)

        return Environment(env_path)


def _introspection_for(interpreter_path: Path) -> EnvironmentIntrospection:
    interpreter_key = str(interpreter_path.absolute())
    if (intro := _INTERPRETER_INTROSPECTIONS.get(interpreter_key)) is None:
        _INTERPRETER_INTROSPECTIONS[interpreter_key] = intro = EnvironmentIntrospection.compute(interpreter_path)

    return intro


@dataclass
@config(io=WheelFileConfigIO())
class PyVEnvConfiguration(ConfigFile):
    home: Path
    version: Version
    include_system_site_packages: bool = config_field(key="include-system-site-packages")
    _leftovers = config_field(leftover=True)

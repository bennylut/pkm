"""
launchers are taken from:
https://bitbucket.org/vinay.sajip/simple_launcher
"""
import importlib.resources as resources
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from zipfile import ZipFile

from pkm.api.distributions.distinfo import EntryPoint

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


def build_windows_script_launcher(
        env: "Environment", entrypoint: EntryPoint, target_dir: Path,
        script: Optional[str] = None) -> Path:
    """
    creates windows launcher for the given `script` that is suitable to the os of the given environment.
    the launcher will be written into a file named `script_name` under the given `dir`

    :param env: the environment that the created launcher should be suitable for
    :param entrypoint: the entrypoint to create a script for
    :param target_dir: the directory where to put the launcher in
    :param script: in case this argument is given it will be used as the script for the entrypoint,
           otherwise the script will be generated from the entrypoint object reference
    :return: path to the created launcher
    """

    op_plat = env.operating_platform
    arch_suffix = '-arm' if op_plat.has_arm_cpu() else ''
    launcher_kind = 't' if entrypoint.group == EntryPoint.G_CONSOLE_SCRIPTS else 'w'
    launcher_name = f"{launcher_kind}{arch_suffix}{op_plat.os_bits}.exe"

    launcher_data = resources.read_binary('pkm.launchers', launcher_name)
    script_content = script or entrypoint.ref.execution_script_snippet()

    result_file = target_dir / f"{entrypoint.name}.exe"
    with result_file.open('wb') as result_fd:
        result_fd.write(launcher_data)
        result_fd.write(f"#!{env.interpreter_path.absolute()}\r\n".encode())
        with ZipFile(result_fd) as result_zip_fd:
            result_zip_fd.writestr("__main__.py", script_content.encode())

    return result_file

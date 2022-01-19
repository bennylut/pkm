import os
import stat
import sys
from pathlib import Path

from pkm.api.distributions.distinfo import EntryPoint
from pkm.api.environments.environment import Environment
from pkm.launchers import build_windows_script_launcher


class Executables:

    @staticmethod
    def patch_shabang_for_env(source: Path, target: Path, env: Environment):
        """
        copy the `source` script to the `target` path, patching the shabng line so that it will be executable
        under the given `env`
        :param source: path to the source script
        :param target: path to put the patched script
        :param env: the environment where the patched script should be executeable with
        """
        with source.open('rb') as script_fd, target.open('wb+') as target_fd:
            first_line = script_fd.readline()
            if first_line.startswith(b"#!python"):
                w = 'w' if first_line.startswith(b"#!pythonw") else ''
                target_fd.write(
                    f"#!{env.interpreter_path.absolute()}{w}{os.linesep}".encode(sys.getfilesystemencoding()))
            else:
                target_fd.write(first_line)

            target_fd.write(script_fd.read())

        st = os.stat(source)
        os.chmod(target, st.st_mode | stat.S_IEXEC)

    @staticmethod
    def generate_for_entrypoint(entrypoint: EntryPoint, env: Environment, target_dir: Path) -> Path:
        """
        generates executable for the given entrypoint that is runnable under the given environment
        :param entrypoint: the entrypoint to generate the executable for
        :param env: environment that the created executable should be runnable in
        :param target_dir: where to put the executable
        :return: path to the created executable
        """

        if env.operating_platform.has_windows_os():
            return build_windows_script_launcher(env, entrypoint, target_dir)
        else:
            source = f"#!{env.interpreter_path.absolute()}\n{entrypoint.ref.execution_script_snippet()}"

            result_script_path = target_dir / entrypoint.name
            result_script_path.write_text(source)

            st = os.stat(result_script_path)
            os.chmod(result_script_path, st.st_mode | stat.S_IEXEC)
            return result_script_path

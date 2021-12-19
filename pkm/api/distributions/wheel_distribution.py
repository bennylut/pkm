import compileall
import csv
import os
import re
import shutil
import stat
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Callable, Dict, Set, Optional
from zipfile import ZipFile

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.versions.version import Version, StandardVersion
from pkm.config.configuration import FileConfiguration
from pkm.logging.console import console
from pkm.utils.hashes import HashSignature
from pkm.utils.iterators import first_or_none


class InstallationException(IOError):
    ...


class WheelFileConfiguration(FileConfiguration):

    def generate_content(self) -> str:
        return os.linesep.join(f'{k}: {v}' for k, v in self._data.items())

    def validate_supported_version(self):
        wv = Version.parse(self['Wheel-Version'] or 'unprovided')
        if not isinstance(wv, StandardVersion):
            raise InstallationException(f"unknown wheel version: {wv}")

        if wv.release[0] != 1:
            raise InstallationException(f"unsupported wheel version: {wv}")
        if wv.release[1] != 0:
            console.log(f'advanced wheel version: {wv} detected, will be treated as version 1.0')

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            raise InstallationException(f"wheel does not contain WHEEL file in dist-info")

        seperator_rx = re.compile("\\s*:\\s*")
        lines = (l.strip() for l in path.read_text().splitlines())
        kvs = (seperator_rx.split(kv) for kv in lines if kv)
        return cls(path=path, data={kv[0]: kv[1] for kv in kvs})


@dataclass
class _FileMoveCommand:
    source: Path
    target: Path
    is_script: bool

    def run(self, env: Environment):
        if self.is_script:
            with self.source.open('rb') as script_fd, self.target.open('wb+') as target_fd:

                first_line = script_fd.readline()
                if first_line.startswith(b"#!python"):
                    w = 'w' if first_line.startswith(b"#!pythonw") else ''
                    target_fd.write(
                        f"#!{env.interpreter_path.absolute()}{w}{os.linesep}".encode(sys.getfilesystemencoding()))
                else:
                    target_fd.write(first_line)

                target_fd.write(script_fd.read())

            st = os.stat(self.source)
            os.chmod(self.target, st.st_mode | stat.S_IEXEC)

        else:
            shutil.move(self.source, self.target)

    @staticmethod
    def run_all(commands: List["_FileMoveCommand"], env: Environment):
        directories_to_create: Set[Path] = {c.target.parent for c in commands}
        for d in directories_to_create:
            d.mkdir(parents=True, exist_ok=True)

        for c in commands:
            c.run(env)

    @classmethod
    def relocate(cls, source_dir: Path, target_dir: Path, scripts: bool = False,
                 accept: Callable[[Path], bool] = lambda _: True) -> List["_FileMoveCommand"]:
        result = []
        for file in source_dir.iterdir():
            if not accept(file):
                continue
            if file.is_dir():
                result.extend(cls.relocate(file, target_dir / file.name))
            else:
                result.append(_FileMoveCommand(file, target_dir / file.name, scripts))

        return result


class WheelDistribution:

    def __init__(self, wheel: Path):
        self._wheel = wheel

    def install(self, env: Environment, user_request: Optional[Dependency] = None):
        """
        Implementation of wheel installer based on PEP427
        as described in: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        """
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with ZipFile(self._wheel) as zip:
                zip.extractall(tmp_path)

            dist_info = _find_dist_info(tmp_path)

            wheel_file = WheelFileConfiguration.load(dist_info / 'WHEEL')
            wheel_file.validate_supported_version()

            site_packages = env.sysconfig_path(
                'purelib' if wheel_file['Root-Is-Purelib'] == 'true' else 'platlib')

            records_file = dist_info / "RECORD"
            if not records_file.exists():
                raise InstallationException("Unsigned wheel (no RECORD file found in dist-info)")

            copy_commands: List[_FileMoveCommand] = []
            for d in tmp_path.iterdir():
                if d.is_dir():
                    if d.suffix == '.data':
                        for k in d.iterdir():
                            target_path = env.sysconfig_path(k.name)
                            if not target_path:
                                raise InstallationException(
                                    f'wheel contains data entry with unsupported key: {k.name}')
                            copy_commands.extend(_FileMoveCommand.relocate(k, target_path, k.name == 'scripts'))
                    else:
                        copy_commands.extend(
                            _FileMoveCommand.relocate(d, site_packages / d.name, accept=lambda it: it != records_file))
                else:
                    copy_commands.append(_FileMoveCommand(d, site_packages / d.name, False))

            # check that there are no file collisions
            for copy_command in copy_commands:
                if copy_command.target.exists():
                    raise InstallationException(
                        f"package files conflicts with other package files: {copy_command.target} already exist")

            # check that the records hash match
            files_left_to_check: Dict[str, _FileMoveCommand] = {
                str(c.source.relative_to(tmp_path)): c for c in copy_commands}
            target_hashes: Dict[Path, HashSignature] = {}

            with records_file.open('r', newline='') as records_fd:
                for record in csv.reader(records_fd):
                    file, hash_sig, _ = record
                    if cc := files_left_to_check.pop(file, None):
                        parsed_sig = HashSignature.parse_urlsafe_base64_nopad_encoded(hash_sig)
                        if not parsed_sig.validate_against(cc.source):
                            raise InstallationException(f"File signature not matched for: {file}")
                        target_hashes[cc.target] = parsed_sig

            # check that there are no records with missing signatures
            if files_left_to_check:
                raise InstallationException(
                    "Wheel contains files with no signature in RECORD, "
                    f"e.g., {first_or_none(files_left_to_check.keys())}")

            # everything is good - start copying...
            _FileMoveCommand.run_all(copy_commands, env)

            # build the new records file
            new_dist_info = site_packages / dist_info.name
            new_record_file = new_dist_info / "RECORD"
            new_record_file.parent.mkdir(parents=True, exist_ok=True)
            with new_record_file.open('w+', newline='') as new_record_fd:
                csv.writer(new_record_fd).writerows(
                    (f"{target.relative_to(site_packages)}", str(sig), target.stat().st_size) for target, sig in
                    target_hashes.items())

            # mark the installer and the requested flag
            (new_dist_info / "INSTALLER").write_text("pkm")
            if user_request:
                (new_dist_info / "REQUESTED").write_text(str(user_request))

            # and finally, compile py to pyc
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                for cc in copy_commands:
                    if cc.target.suffix == '.py':
                        compileall.compile_file(cc.target, force=True, quiet=True)


def _find_dist_info(unpacked_wheel: Path) -> Path:
    dist_info = list(unpacked_wheel.rglob("*.dist-info"))
    if not dist_info:
        raise InstallationException(f"wheel does not contain dist-info")
    if len(dist_info) != 1:
        raise InstallationException(f"wheel contains more than one possible dist-info")

    return dist_info[0]

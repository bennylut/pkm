import compileall
import re
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Callable, Dict, Set, Optional, TYPE_CHECKING
from zipfile import ZipFile

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo, Record
from pkm.api.distributions.distribution import Distribution
from pkm.api.distributions.executables import Executables
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.utils.files import path_to
from pkm.utils.hashes import HashSignature
from pkm.utils.iterators import first_or_none

_METADATA_FILE_RX = re.compile("[^/]*\\.dist-info/METADATA")

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class InstallationException(IOError):
    ...


@dataclass
class _FileMoveCommand:
    source: Path
    target: Path
    is_script: bool

    def run(self, env: "Environment"):
        if self.is_script:
            Executables.patch_shabang_for_env(self.source, self.target, env)
        else:
            shutil.move(self.source, self.target)

    @staticmethod
    def run_all(commands: List["_FileMoveCommand"], env: "Environment"):
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


class WheelDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, wheel: Path):
        self._wheel = wheel
        self._package = package

    def extract_metadata(self, env: "Environment") -> PackageMetadata:
        # monitor.on_extracting_metadata()

        with ZipFile(self._wheel) as zipf:
            for name in zipf.namelist():
                if _METADATA_FILE_RX.fullmatch(name):
                    with TemporaryDirectory() as tdir:
                        zipf.extract(name, tdir)
                        return PackageMetadata.load(Path(tdir) / name)
        raise FileNotFoundError("could not find metadata in wheel")

    @property
    def owner_package(self) -> PackageDescriptor:
        return self._package

    def install_to(self, env: "Environment", user_request: Optional[Dependency] = None, editable: bool = False):
        """
        Implementation of wheel installer based on PEP427
        as described in: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        """
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            with ZipFile(self._wheel) as zipf:
                zipf.extractall(tmp_path)

            dist_info = _find_dist_info(tmp_path, self._package)

            wheel_file = dist_info.load_wheel_cfg()  # WheelFileConfiguration.load(dist_info / 'WHEEL')
            wheel_file.validate_supported_version()

            entrypoints = dist_info.load_entrypoints_cfg().entrypoints

            site_packages = Path(env.paths['purelib' if wheel_file['Root-Is-Purelib'] == 'true' else 'platlib'])

            records_file = dist_info.load_record_cfg()
            if not records_file.exists():
                raise InstallationException(
                    f"Unsigned wheel for package {self._package} (no RECORD file found in dist-info)")

            copy_commands: List[_FileMoveCommand] = []
            for d in tmp_path.iterdir():
                if d.is_dir():
                    if d.suffix == '.data':
                        for k in d.iterdir():
                            target_path = env.paths.get(k.name)
                            if not target_path:
                                raise InstallationException(
                                    f'wheel contains data entry with unsupported key: {k.name}')
                            copy_commands.extend(_FileMoveCommand.relocate(k, Path(target_path), k.name == 'scripts'))
                    else:
                        copy_commands.extend(
                            _FileMoveCommand.relocate(d, site_packages / d.name,
                                                      accept=lambda it: it != records_file.path))
                else:
                    copy_commands.append(_FileMoveCommand(d, site_packages / d.name, False))

            # check that there are no file collisions
            for copy_command in copy_commands:
                if copy_command.target.exists():

                    print(f"package files conflicts with other package files: {copy_command.target} already exist")

                    if not copy_command.target.is_dir():
                        # shutil.rmtree(copy_command.target)
                        # else:
                        copy_command.target.unlink()

                    # raise InstallationException(
                    #     f"package files conflicts with other package files: {copy_command.target} already exist")

            # check that the records hash match
            files_left_to_check: Dict[str, _FileMoveCommand] = {
                str(c.source.relative_to(tmp_path)): c for c in copy_commands}
            target_hashes: Dict[Path, HashSignature] = {}

            for record in records_file.records:
                if cc := files_left_to_check.pop(record.file, None):
                    if not record.hash_signature.validate_against(cc.source):
                        if any(it.name.endswith('.dist-info') for it in cc.source.parents):
                            print(f"Weak Warning: mismatch hash signature for {cc.source}")
                        else:
                            raise InstallationException(f"File signature not matched for: {record.file}")
                    target_hashes[cc.target] = record.hash_signature
                else:
                    print(f"hash signature is provided for {record.file} but file not found..")

            # check that there are no records with missing signatures
            if files_left_to_check:
                raise InstallationException(
                    "Wheel contains files with no signature in RECORD, "
                    f"e.g., {first_or_none(files_left_to_check.keys())}")

            # everything is good - start copying...
            _FileMoveCommand.run_all(copy_commands, env)

            # build entry points
            generated_entrypoints = []
            scripts_path = Path(env.paths.get("scripts", env.path / "bin"))
            for entrypoint in entrypoints:
                if entrypoint.is_script():
                    generated_entrypoints.append(Executables.generate_for_entrypoint(entrypoint, env, scripts_path))

            # build the new records file
            new_dist_info = DistInfo.load(site_packages / dist_info.path.name)
            new_record_file = new_dist_info.load_record_cfg()

            new_record_file.records.extend(
                Record(str(path_to(site_packages, target)), sig, target.stat().st_size)
                for target, sig in target_hashes.items())

            new_record_file.records.extend(
                Record(
                    str(path_to(site_packages, generated_ep)),
                    HashSignature.create_urlsafe_base64_nopad_encoded('sha256', generated_ep),
                    generated_ep.stat().st_size)
                for generated_ep in generated_entrypoints
            )

            new_record_file.save()

            # mark the installer and the requested flag
            (new_dist_info.path / "INSTALLER").write_text("pkm")
            if user_request:
                (new_dist_info.path / "REQUESTED").write_text(str(user_request))

            # and finally, compile py to pyc
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore')
                for cc in copy_commands:
                    if cc.target.suffix == '.py':
                        compileall.compile_file(cc.target, force=True, quiet=True)


def _find_dist_info(unpacked_wheel: Path, package: PackageDescriptor) -> DistInfo:
    dist_info = list(unpacked_wheel.glob("*.dist-info"))
    if not dist_info:
        raise InstallationException(f"wheel for {package} does not contain dist-info")
    if len(dist_info) != 1:
        raise InstallationException(f"wheel for {package} contains more than one possible dist-info")

    return DistInfo.load(dist_info[0])

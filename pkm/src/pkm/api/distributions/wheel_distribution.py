import compileall
import re
import warnings
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, TYPE_CHECKING
from zipfile import ZipFile

from pkm.api.distributions.distinfo import DistInfo, RequestedPackageInfo
from pkm.api.distributions.distribution import Distribution
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version import StandardVersion
from pkm.distributions.executables import Executables
from pkm.utils.archives import extract_archive
from pkm.utils.files import path_to, CopyTransaction, temp_dir

_METADATA_FILE_RX = re.compile("[^/]*\\.dist-info/METADATA")

if TYPE_CHECKING:
    from pkm.api.packages.package import PackageInstallationTarget
    from pkm.api.projects.project import Project
    from pkm.api.environments.environment import Environment


class InstallationException(IOError):
    ...


class WheelDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, wheel: Path):
        self._wheel = wheel
        assert wheel, "no path for wheel provided"
        self._package = package

    def extract_metadata(self, env: Optional["Environment"] = None) -> PackageMetadata:
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

    def compute_compatibility_tags(self) -> str:
        """
        return the string that represents the compatibility tags in this wheel file name
        :return: the compatibility tag
        """
        return WheelDistribution.compute_compatibility_tags_of(self._wheel)

    @staticmethod
    def compute_compatibility_tags_of(wheel: Path) -> str:
        """
        return the string that represents the compatibility tags in the wheel file name
        :param wheel: the wheel file name
        :return: the compatibility tag
        """
        return '-'.join(wheel.stem.split('-')[-3:])

    @staticmethod
    def expected_wheel_file_name(project: "Project") -> str:
        from pkm.api.environments.environment import Environment
        project_config = project.config.project
        req = project_config.requires_python

        min_interpreter: StandardVersion = req.min \
            if req and not req.is_any() else StandardVersion((Environment.current().interpreter_version.release[0],))

        req_interpreter = 'py' + ''.join(str(it) for it in min_interpreter.release[:2])
        return f"{project.descriptor.expected_src_package_name}-{project.version}-{req_interpreter}-none-any.whl"

    def install_to(self, target: "PackageInstallationTarget", user_request: Optional[RequestedPackageInfo] = None):
        """
        Implementation of wheel installer based on PEP427
        as described in: https://packaging.python.org/en/latest/specifications/binary-distribution-format/
        """
        with temp_dir() as tmp_path:
            extract_archive(self._wheel, tmp_path)
            dist_info = _find_dist_info(tmp_path, self._package)

            wheel_file = dist_info.load_wheel_cfg()
            wheel_file.validate_supported_version()

            entrypoints = dist_info.load_entrypoints_cfg().entrypoints

            site_packages = Path(target.purelib if wheel_file['Root-Is-Purelib'] == 'true' else target.platlib)

            records_file = dist_info.load_record_cfg()
            if not records_file.exists():
                raise InstallationException(
                    f"Unsigned wheel for package {self._package} (no RECORD file found in dist-info)")

            # check that the records hash match
            record_by_path = {r.file: r for r in records_file.records}

            for file in tmp_path.rglob("*"):
                if file.is_dir():
                    continue

                path = str(path_to(tmp_path, file))
                if record := record_by_path.get(path):
                    if not record.hash_signature.validate_against(file):
                        if any(it.name.endswith('.dist-info') for it in file.parents):
                            warnings.warn(f"mismatch hash signature for {file}")
                        else:
                            raise InstallationException(f"File signature not matched for: {record.file}")

                elif file != dist_info.path / "RECORD":
                    raise InstallationException(
                        f"Wheel contains files with no signature in RECORD, "
                        f"e.g., {path}")

            with CopyTransaction() as ct:
                for d in tmp_path.iterdir():
                    if d.is_dir():
                        if d.suffix == '.data':
                            for k in d.iterdir():
                                if not (target_path := getattr(target, k.name, None)):
                                    raise InstallationException(
                                        f'wheel contains data entry with unsupported key: {k.name}')

                                if k.name == 'scripts':
                                    ct.copy_tree(
                                        k, Path(target_path),
                                        file_copy=lambda s, t: Executables.patch_shabang_for_interpreter(
                                            s, t, target.env.interpreter_path))
                                else:
                                    ct.copy_tree(k, Path(target_path))
                        else:
                            ct.copy_tree(d, site_packages / d.name, accept=lambda it: it != records_file.path)
                    else:
                        ct.copy(d, site_packages / d.name)

                # build entry points
                scripts_path = Path(target.scripts)
                for entrypoint in entrypoints:
                    if entrypoint.is_script():
                        ct.touch(Executables.generate_for_entrypoint(target.env, entrypoint, scripts_path))

                # build the new records file
                new_dist_info = DistInfo.load(site_packages / dist_info.path.name)
                new_record_file = new_dist_info.load_record_cfg()

                new_record_file.sign_files(ct.copied_files, site_packages, {
                    r.file: r.hash_signature for r in records_file.records
                })

                new_record_file.save()

                # mark the installer and the requested flag
                (new_dist_info.path / "INSTALLER").write_text(f"pkm\n{self._wheel.name}")
                if user_request:
                    new_dist_info.mark_as_user_requested(user_request)

                # and finally, compile py to pyc
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    for cc in ct.copied_files:
                        if cc.suffix == '.py':
                            compileall.compile_file(cc, force=True, quiet=2)


def _find_dist_info(unpacked_wheel: Path, package: PackageDescriptor) -> DistInfo:
    dist_info = list(unpacked_wheel.glob("*.dist-info"))
    if not dist_info:
        raise InstallationException(f"wheel for {package} does not contain dist-info")
    if len(dist_info) != 1:
        raise InstallationException(f"wheel for {package} contains more than one possible dist-info")

    return DistInfo.load(dist_info[0])

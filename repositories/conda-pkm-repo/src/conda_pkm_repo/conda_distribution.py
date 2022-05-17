import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Dict, Set

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import PackageInstallationInfo, DistInfo
from pkm.api.distributions.distribution import Distribution
from pkm.api.distributions.wheel_distribution import InstallationException
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.utils.archives import extract_archive
from pkm.utils.files import temp_dir, path_to, CopyTransaction
from pkm.utils.hashes import HashSignature, stream
from pkm.utils.iterators import first_or_none
from pkm.utils.processes import monitored_run
from pkm.utils.seqs import seq

_PURELIB_UNIX_RX = re.compile(r"python\d+\.\d+")


class CondaDistribution(Distribution):

    def __init__(self, package: PackageDescriptor, bz2dist: Path):
        self._package = package
        self._dist = bz2dist

    @property
    def owner_package(self) -> PackageDescriptor:
        return self._package

    def _generate_dist_info(self, dist_info_path: Path):
        dist_info = DistInfo.load(dist_info_path)

        wheel = dist_info.load_wheel_cfg()
        wheel["Wheel-Version"] = "1.0"
        wheel["Generator"] = "conda-pkm-repo"
        wheel["Root-Is-Purelib"] = "true"
        wheel.save()

        self._generate_default_metadata(dist_info.load_metadata_cfg()).save()

    def _generate_default_metadata(self, metadata: Optional[PackageMetadata] = None) -> PackageMetadata:
        metadata = metadata or PackageMetadata(path=None)
        metadata["Metadata-Version"] = "2.1"
        metadata["Name"] = self.owner_package.name
        metadata["Version"] = str(self.owner_package.version)
        return metadata

    def install_to(self, target: "PackageInstallationTarget", user_request: Optional[Dependency] = None,
                   installation_info: Optional[PackageInstallationInfo] = None):
        with temp_dir() as tdir:
            extract_archive(self._dist, tdir)

            info_dir = tdir / "info"

            if not info_dir.exists() or not info_dir.is_dir():
                raise InstallationException("missing info directory")

            relocated_files: Dict[Path, Path] = {}

            # first validate hashes
            signatures_by_path: Dict[Path, HashSignature] = {}
            if not (paths_file := info_dir / "paths.json").exists():
                raise InstallationException("unsigned package")

            paths_data = json.loads(paths_file.read_text())['paths']
            for path_data in paths_data:
                path = tdir / path_data['_path']

                if not path.exists():
                    raise InstallationException(f"path: {path} was signed but not found")

                hashcode = path_data['sha256']
                sha256 = hashlib.sha256()
                stream(sha256, path)

                if sha256.hexdigest() != hashcode:
                    raise InstallationException(f"path: {path} has incorrect signature")

                hashsig = HashSignature.create_urlsafe_base64_nopad_encoded('sha256', sha256)
                signatures_by_path[path.relative_to(tdir)] = hashsig

            index = json.loads((info_dir / "index.json").read_text())

            def exec_installation_script(script_name: str):
                env = {**os.environ, 'PREFIX': target.data, 'PKG_NAME': self._package.name,
                       'PKG_VERSION': str(self._package.version), 'PKG_BUILDNUM': index['build_number']}
                if target.env.operating_platform.has_windows_os():
                    if (script_path := info_dir / "Scripts" / f"{script_name}.bat").exists():
                        monitored_run(f"conda installation hook: {script_name}", [
                            env.get("COMSPEC", "cmd.exe"), '/c', str(script_path)
                        ], env=env).check_returncode()
                else:
                    if (script_path := info_dir / "bin" / f"{script_name}.sh").exists():
                        monitored_run(f"conda installation hook: {script_name}", [
                            "/bin/bash", str(script_path)
                        ], env=env).check_returncode()

            exec_installation_script('pre-link')
            data_path = Path(target.data)
            purelib_path = Path(target.purelib)
            python_lib_path = purelib_path.parent

            package_lib_path = tdir / "lib"

            if package_lib_path.exists():
                package_purelib_path = first_or_none(
                    p for p in (tdir / "lib").iterdir() if _PURELIB_UNIX_RX.match(p.name))

                if package_purelib_path and package_lib_path.name != python_lib_path.name:
                    new_purelib = package_purelib_path.parent / python_lib_path.name
                    for subpath in package_purelib_path.rglob("*"):
                        relocated_files[subpath.relative_to(tdir)] = \
                            (new_purelib / subpath.relative_to(package_purelib_path)).relative_to(tdir)
                    shutil.move(str(package_purelib_path), str(new_purelib))

            created_parents: Set[Path] = set()
            files_to_link = seq((info_dir / "files").read_text().splitlines(keepends=False)) \
                .filter(bool)  # drop empties

            with CopyTransaction() as ct:
                precomputed_record_hashes: Dict[str, HashSignature] = {}
                purelib_in_package_path = tdir / purelib_path.relative_to(data_path)
                for file in files_to_link:
                    path = Path(file)
                    precomputed_hash = signatures_by_path[path]
                    path = relocated_files.get(path, path)

                    abs_path = tdir / path
                    precomputed_record_hashes[str(path_to(purelib_in_package_path, abs_path))] = precomputed_hash

                    target_path = data_path / path
                    parent = target_path.parent
                    if parent not in created_parents:
                        parent.mkdir(exist_ok=True, parents=True)
                        created_parents.add(parent)

                    ct.copy(abs_path, target_path)

                dist_info_path = purelib_path / DistInfo.expected_dir_name(self.owner_package)
                if not dist_info_path.exists():
                    self._generate_dist_info(dist_info_path)
                dist_info = DistInfo.load(dist_info_path)

                # rewrite records
                dist_info.record_path().unlink(missing_ok=True)
                records = dist_info.load_record_cfg()
                precomputed_record_hashes.pop(str(path_to(purelib_in_package_path, records.path)), None)
                copied_files = [file for file in ct.copied_files if file.name != 'RECORD' or file.exists()]
                records.sign_files(copied_files, dist_info.path.parent, precomputed_record_hashes)
                records.save()

                exec_installation_script('post-link')

    def extract_metadata(self, env: Optional["Environment"] = None) -> PackageMetadata:
        with temp_dir() as tdir:
            extract_archive(self._dist, tdir)
            if dist_info_path := first_or_none(tdir.rglob(f"*{DistInfo.expected_dir_name(self.owner_package)}")):
                return DistInfo.load(dist_info_path).load_metadata_cfg()
            return self._generate_default_metadata()

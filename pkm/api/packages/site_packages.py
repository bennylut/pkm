import csv
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Iterable, Set, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.logging.console import console
from pkm.utils.files import is_empty_directory
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class SitePackages:
    def __init__(self, purelib: Path, platlib: Path, other_sites: Iterable[Path], is_read_only: bool):
        self._purelib = purelib
        self._platlib = platlib
        self._other_sites = other_sites
        self._is_read_only = is_read_only

    @property
    def purelib_path(self) -> Path:
        return self._purelib

    @property
    def platlib_path(self) -> Path:
        return self._platlib

    @cached_property
    def _name_to_packages(self) -> Dict[str, "InstalledPackage"]:
        result: Dict[str, InstalledPackage] = {}
        self._scan_packages(self._purelib, result, self._is_read_only)
        self._scan_packages(self._platlib, result, self._is_read_only)
        for other_site in self._other_sites:
            self._scan_packages(other_site, result, True)

        return result

    def _scan_packages(self, site: Path, result: Dict[str, "InstalledPackage"], readonly: bool):
        if not site.exists():
            return

        for file in site.iterdir():
            if file.suffix == ".dist-info":
                metadata_file = file / "METADATA"
                if metadata_file.exists():
                    metadata = PackageMetadata.load(metadata_file)
                    user_request = _read_user_request(file, metadata)
                    result[metadata.package_name] = InstalledPackage(file, metadata, user_request, self, readonly)

    def installed_packages(self) -> Iterable["InstalledPackage"]:
        return self._name_to_packages.values()

    def installed_package(self, package_name: str) -> Optional["InstalledPackage"]:
        return self._name_to_packages.get(package_name)

    def reload(self):
        clear_cached_properties(self)


def _read_user_request(dist_info: Path, metadata: PackageMetadata) -> Optional[Dependency]:
    requested_file = dist_info / "REQUESTED"
    if not requested_file.exists():
        return None

    requested_data = requested_file.read_text().strip()
    try:
        if requested_data:
            return Dependency.parse_pep508(requested_data)
    except ValueError:
        pass

    return Dependency(metadata.package_name, SpecificVersion(metadata.package_version))


class InstalledPackage(Package):

    def __init__(
            self, dist_info: Path, metadata: PackageMetadata, user_request: Optional[Dependency],
            site: SitePackages, readonly: bool):

        self._meta = metadata
        self._desc = PackageDescriptor(metadata.package_name, metadata.package_version)

        self._dist_info = dist_info
        self._user_request = user_request
        self.site = site
        self.readonly = readonly

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    @property
    def user_request(self) -> Optional[Dependency]:
        return self._user_request

    def unmark_user_requested(self) -> bool:
        if self.readonly:
            return False

        (self._dist_info / "REQUESTED").unlink()
        self._user_request = None
        return True

    def mark_user_requested(self, request: Dependency) -> bool:
        if self.readonly:
            return False

        (self._dist_info / "REQUESTED").write_text(str(request))
        self._user_request = request
        return True

    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        return self._meta.dependencies

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._meta.required_python_spec.allows_version(env.interpreter_version)

    def install_to(self, env: "Environment", build_packages_repo: Repository, user_request: Optional[Dependency] = None):
        raise NotImplemented()  # maybe re-mark user request?

    def uninstall(self) -> bool:
        console.log(f"uninstalling {self._desc}")
        if self.readonly:
            console.log("could not uninstall, package is readonly")
            return False

        root = self._dist_info.parent

        parents: Set[Path] = set()
        record_file = self._dist_info / "RECORD"

        if not record_file.exists():
            return False

        with record_file.open('r', newline='') as record_fd:
            for record in csv.reader(record_fd):
                record_path = root / record[0]
                record_path.unlink(missing_ok=True)
                parents.add(record_path.parent)

        record_file.unlink(missing_ok=True)
        for parent in sorted(parents, key=lambda it: len(str(it)), reverse=True):
            if not parent.exists():
                continue

            to_check = [parent, *parent.parents]

            while to_check:
                if root == to_check.pop():
                    break

            for path in to_check:
                if (precompiled := path / "__pycache__").exists():
                    shutil.rmtree(precompiled)
                if is_empty_directory(path):
                    path.rmdir()

        self.site.reload()

        return True

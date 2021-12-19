import csv
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Iterable, Set, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.utils.files import is_empty_directory
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class SitePackages:
    def __init__(self, sites: Iterable[Path]):
        self._sites = sites

    @cached_property
    def _name_to_packages(self) -> Dict[str, "InstalledPackage"]:
        result: Dict[str, InstalledPackage] = {}
        for site in self._sites:
            for file in site.iterdir():
                if file.suffix == ".dist-info":
                    metadata_file = file / "METADATA"
                    if metadata_file.exists():
                        metadata = PackageMetadata.load(metadata_file)
                        user_request = _read_user_request(file, metadata)
                        result[metadata.package_name] = InstalledPackage(file, metadata, user_request, self)

        return result

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
            site: SitePackages):

        self._meta = metadata
        self._desc = PackageDescriptor(metadata.package_name, metadata.package_version)

        self._dist_info = dist_info
        self._user_request = user_request
        self.site = site

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._desc

    @property
    def user_request(self) -> Optional[Dependency]:
        return self._user_request

    def unmark_user_requested(self):
        (self._dist_info / "REQUESTED").unlink()
        self._user_request = None

    def mark_user_requested(self, request: Dependency):
        (self._dist_info / "REQUESTED").write_text(str(request))
        self._user_request = request

    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        return self._meta.dependencies

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._meta.required_python_spec.allows_version(env.interpreter_version)

    def install_to(self, env: "Environment", user_request: Optional[Dependency] = None):
        raise NotImplemented()  # maybe re-mark user request?

    def uninstall(self):
        root = self._dist_info.parent

        parents: Set[Path] = set()
        record_file = self._dist_info / "RECORD"

        if not record_file.exists():
            return  # unremovable package - should i notify it?

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

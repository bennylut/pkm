import csv
import shutil
import warnings
from pathlib import Path
from typing import Optional, List, Dict, Iterable, Set, TYPE_CHECKING, Iterator

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version_specifiers import SpecificVersion
from pkm.utils.files import is_empty_directory, is_relative_to
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


class SitePackages:
    def __init__(
            self, env: "Environment", purelib: Path, platlib: Path, other_sites: Iterable[Path], is_read_only: bool):

        self._purelib = purelib
        self._platlib = platlib
        self._other_sites = other_sites
        self._is_read_only = is_read_only
        self.env = env

    def all_sites(self) -> Iterator[Path]:
        yield self._purelib
        if self._platlib != self._purelib:
            yield self._platlib

        yield from self._other_sites

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
                    result[file.name.split("-")[0].lower()] = \
                        InstalledPackage(DistInfo.load(file), self, readonly)

    def installed_packages(self) -> Iterable["InstalledPackage"]:
        return self._name_to_packages.values()

    def installed_package(self, package_name: str) -> Optional["InstalledPackage"]:
        return self._name_to_packages.get(PackageDescriptor.normalize_source_dir_name(package_name))

    def reload(self):
        clear_cached_properties(self)


def _read_user_request(dist_info: Path, metadata: PackageMetadata) -> Optional[Dependency]:
    requested_file = dist_info / "REQUESTED"
    if not requested_file.exists():
        return None

    requested_data = requested_file.read_text().strip()
    try:
        if requested_data:
            return Dependency.parse(requested_data)
    except ValueError:
        pass

    return Dependency(metadata.package_name, SpecificVersion(metadata.package_version))


class InstalledPackage(Package):

    def __init__(self, dist_info: DistInfo, site: Optional[SitePackages] = None, readonly: bool = False):

        self._dist_info = dist_info
        self.site = site
        self.readonly = readonly

    @cached_property
    def published_metadata(self) -> Optional["PackageMetadata"]:
        return self._dist_info.load_metadata_cfg()

    @property
    def dist_info(self) -> DistInfo:
        """
        :return: the installed package dist-info
        """
        return self._dist_info

    @cached_property
    def descriptor(self) -> PackageDescriptor:
        meta = self.published_metadata
        return PackageDescriptor(meta.package_name, meta.package_version)

    @cached_property
    def user_request(self) -> Optional[Dependency]:
        """
        :return: the dependency that was requested by the user
                 if this package was directly requested by the user or its project
                 otherwise None
        """
        return _read_user_request(self._dist_info.path, self.published_metadata)

    def unmark_user_requested(self) -> bool:
        """
        remove the "user request" mark from a package
        :return: True if the mark removed, False if the package is readonly
        """

        if self.readonly:
            return False

        (self._dist_info.path / "REQUESTED").unlink(missing_ok=True)
        del self.user_request  # noqa
        return True

    def mark_user_requested(self, request: Dependency) -> bool:
        if self.readonly:
            return False

        (self._dist_info.path / "REQUESTED").write_text(str(request))
        del self.user_request  # noqa
        return True

    def _all_dependencies(self, environment: "Environment") -> List["Dependency"]:
        return self.published_metadata.dependencies

    def is_compatible_with(self, env: "Environment") -> bool:
        return self.published_metadata.required_python_spec.allows_version(env.interpreter_version)

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None):
        raise NotImplemented()  # maybe re-mark user request?

    def is_in_purelib(self) -> bool:
        """
        :return: True if this package is installed to purelib, False if it is installed into platlib
        """

        return is_relative_to(self.dist_info.path, self.site.purelib_path)

    def uninstall(self) -> bool:
        if self.readonly:
            warnings.warn("could not uninstall, package is readonly")
            return False

        parents_to_check = set()
        for installed_file in self._dist_info.installed_files():
            installed_file.unlink(missing_ok=True)
            parents_to_check.add(installed_file.parent)

        installation_site = self.dist_info.path.parent
        while parents_to_check:
            parent = parents_to_check.pop()

            if parent == installation_site or not is_relative_to(parent, installation_site):
                continue

            if (precompiled := parent / "__pycache__").exists():
                shutil.rmtree(precompiled, ignore_errors=True)

            if is_empty_directory(parent):
                parent.rmdir()
                parents_to_check.add(parent.parent)

        if self._dist_info.path.exists():
            shutil.rmtree(self._dist_info.path)

        if self.site:
            self.site.reload()

        return True

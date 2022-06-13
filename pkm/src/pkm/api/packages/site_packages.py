from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Iterable, TYPE_CHECKING, Iterator

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_installation_info import StoreMode, PackageInstallationInfo
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version_specifiers import VersionMatch
from pkm.utils.files import is_empty_directory, is_relative_to
from pkm.utils.ipc import IPCPackable
from pkm.utils.properties import cached_property, clear_cached_properties
from pkm.utils.sequences import pop_or_none
from pkm.utils.sets import try_add

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.packages.package_installation import PackageInstallationTarget


class SitePackages(IPCPackable):

    def __init__(self, env: "Environment", purelib: Path, platlib: Path):

        self._purelib = purelib
        self._platlib = platlib
        self.env = env

    def __getstate__(self):
        return [self.env, self._purelib, self._platlib]

    def __setstate__(self, state):
        self.__init__(*state)

    def all_sites(self) -> Iterator[Path]:
        yield self._purelib
        if self._platlib != self._purelib:
            yield self._platlib

    def __eq__(self, other):
        return isinstance(other, SitePackages) \
               and other._purelib == self._purelib \
               and other._platlib == self._platlib \
               and other.env.path == self.env.path

    @property
    def purelib_path(self) -> Path:
        return self._purelib

    @property
    def platlib_path(self) -> Path:
        return self._platlib

    @cached_property
    def _name_to_packages(self) -> Dict[str, InstalledPackage]:
        result: Dict[str, InstalledPackage] = {}
        self._scan_packages(self._purelib, result)
        self._scan_packages(self._platlib, result)
        return result

    # @staticmethod
    # def normalize_package_name(package_name: str) -> str:
    #     return PackageDescriptor.normalize_src_package_name(package_name).lower()

    def _scan_packages(self, site: Path, result: Dict[str, InstalledPackage]):
        if not site.exists():
            return

        for di in DistInfo.scan(site):
            result[PackageDescriptor.package_name_key(di.package_name_by_dirname)] = InstalledPackage(di, self)

    def installed_packages(self) -> Iterable[InstalledPackage]:
        return self._name_to_packages.values()

    def installed_package(self, package_name: str) -> Optional[InstalledPackage]:
        return self._name_to_packages.get(PackageDescriptor.package_name_key(package_name))

    def find_requested_packages(self) -> List[InstalledPackage]:
        return [r for r in self.installed_packages() if r.user_request is not None]

    def find_orphan_packages(self) -> Iterable[InstalledPackage]:
        installed = self.installed_packages()
        requested = [p for p in installed if p.user_request is not None]
        orphans = {p.name_key: p for p in installed}
        done = set()

        while next_ := pop_or_none(requested):
            name = next_.name_key
            if not try_add(done, name):
                continue

            orphans.pop(name, None)

            requested.extend(
                i for d in next_.published_metadata.dependencies
                if (i := self.installed_package(d.package_name)) is not None)

        return orphans.values()

    def reload(self):
        clear_cached_properties(self)


def _read_user_request(dist_info: DistInfo, metadata: PackageMetadata) -> Optional[Dependency]:
    if stored_request := dist_info.load_user_requested_info():
        return stored_request
    elif dist_info.is_user_requested():
        return Dependency(metadata.package_name, VersionMatch(metadata.package_version))
    return None


class InstalledPackage(Package, IPCPackable):

    def __init__(self, dist_info: DistInfo, site: Optional[SitePackages] = None):

        self._dist_info = dist_info
        self.site = site

    def __getstate__(self):
        return [self._dist_info, self.site]

    def __setstate__(self, state):
        self.__init__(*state)

    @cached_property
    def published_metadata(self) -> Optional["PackageMetadata"]:
        return self._dist_info.load_metadata_cfg()

    @property
    def dist_info(self) -> DistInfo:
        """
        :return: the installed package dist-info
        """
        return self._dist_info

    def reload(self):
        clear_cached_properties(self)

    @cached_property
    def descriptor(self) -> PackageDescriptor:
        meta = self.published_metadata
        if not (meta.package_name and meta.package_version):
            return PackageDescriptor(self.dist_info.package_name_by_dirname, self._dist_info.package_version_by_dirname)

        return PackageDescriptor(meta.package_name, meta.package_version)

    @cached_property
    def user_request(self) -> Optional[Dependency]:
        """
        :return: the dependency that was requested by the user
                 if this package was directly requested by the user or its project
                 otherwise None
        """
        return _read_user_request(self._dist_info, self.published_metadata)

    @cached_property
    def installation_info(self) -> PackageInstallationInfo:
        return self._dist_info.load_installation_info() or PackageInstallationInfo()

    def dependencies(
            self, target: "PackageInstallationTarget", extras: Optional[List[str]] = None) -> List["Dependency"]:
        all_deps = self.published_metadata.dependencies
        return [d for d in all_deps if d.is_applicable_for(target.env, extras)]

    def is_compatible_with(self, env: "Environment") -> bool:
        return self.published_metadata.required_python_spec.allows_version(env.interpreter_version)

    def install_to(
            self, target: "PackageInstallationTarget", user_request: Optional["Dependency"] = None,
            store_mode: StoreMode = StoreMode.AUTO):
        if target.site_packages != self.site:
            raise NotImplemented()  # maybe re-mark user request?

    def is_in_purelib(self) -> bool:
        """
        :return: True if this package is installed to purelib, False if it is installed into platlib
        """
        return is_relative_to(self.dist_info.path, self.site.purelib_path)

    def update_at(self, target: "PackageInstallationTarget", user_request: Optional["Dependency"] = None,
                  store_mode: StoreMode = StoreMode.AUTO):

        if user_request:
            self.dist_info.mark_as_user_requested(user_request)
        else:
            self.dist_info.unmark_as_user_requested()

    def uninstall(self):
        """
        uninstall this package from its site packages
        """

        parents_to_check = set()
        for installed_file in self._dist_info.installed_files():
            installed_file.unlink(missing_ok=True)
            parents_to_check.add(installed_file.parent)

        installation_site = self.dist_info.path.parent
        while parents_to_check:
            parent = parents_to_check.pop()  # noqa : pycharm does not know's about set's pop method?

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

from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.package_containers import PackageContainer
from pkm.api.packages.package import Package
from pkm.api.packages.package_installation_info import StoreMode
from pkm.api.versions.version_specifiers import VersionSpecifier, AllowAllVersions
from pkm.utils.properties import cached_property


class SelfController:
    def __init__(self):
        self.global_environment = Environment.current()
        pkm_cli_container: PackageContainer

        self._installation_target = self.global_environment.installation_target
        if pkm_cli_container := self.global_environment.package_containers.container_of('pkm-cli'):
            self._installation_target = pkm_cli_container.installation_target

    @cached_property
    def pkm_cli_package(self) -> Package:
        return self._installation_target.site_packages.installed_package('pkm-cli')

    def install_plugins(
            self, dependencies: List[Dependency], store_mode: StoreMode = StoreMode.AUTO, update: bool = False):

        store_modes = {d.package_name: store_mode for d in dependencies}
        updates = [d.package_name for d in dependencies] if update else None
        self._installation_target.install(dependencies, store_mode=store_modes, updates=updates)

    def uninstall_plugin(self, packages: List[str], force: bool = False):
        if force:
            for package in packages:
                self._installation_target.force_remove(package)
        else:
            self._installation_target.uninstall(packages)

    def update(self, vspec: Optional[VersionSpecifier] = None):
        self._installation_target.install([Dependency('pkm-cli', vspec or AllowAllVersions)], updates=['pkm-cli'])

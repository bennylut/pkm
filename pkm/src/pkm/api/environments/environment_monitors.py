from __future__ import annotations

from pkm.api.packages.package import Package
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.repositories.repository import Repository
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor
from pkm.resolution.resolution_monitor import HasDependencyResolutionStepMonitor
from pkm.utils.monitors import Monitor, no_monitor


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class EnvironmentOperationsMonitor(Monitor):
    def on_install(self) -> EnvironmentPackageModificationMonitor:
        return no_monitor()

    def on_uninstall(self) -> EnvironmentPackageModificationMonitor:
        return no_monitor()


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class EnvironmentPackageModificationMonitor(HasDependencyResolutionStepMonitor):

    def on_access_repository(self, repository: Repository) -> RepositoryOperationsMonitor:
        return no_monitor()

    def on_access_package(self, package: Package) -> PackageOperationsMonitor:
        return no_monitor()

from __future__ import annotations

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment_monitors import EnvironmentOperationsMonitor, \
    EnvironmentPackageModificationMonitor
from pkm.api.packages.package import Package
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.repositories.repository import Repository
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor
from pkm.resolution.resolution_monitor import DependencyResolutionMonitor
from pkm_cli.display.display import Display
from pkm_cli.monitors.dependency_resolution_monitors import ConsoleDependencyResolutionMonitor
from pkm_cli.monitors.package_monitors import ConsolePackageOperationsMonitor
from pkm_cli.monitors.repository_monitors import ConsoleRepositoryOperationsMonitor


class ConsoleEnvironmentPackageModificationMonitor(EnvironmentPackageModificationMonitor):

    def on_dependency_resolution(self, request: Dependency, repository: Repository) -> DependencyResolutionMonitor:
        Display.print(f"executing dependency resolution for: {request}")
        return ConsoleDependencyResolutionMonitor()

    def on_access_repository(self, repository: Repository) -> RepositoryOperationsMonitor:
        Display.print(f"accessing repository: {repository.name}")
        return ConsoleRepositoryOperationsMonitor()

    def on_access_package(self, package: Package) -> PackageOperationsMonitor:
        Display.print(f"accessing package: {package.descriptor}")
        return ConsolePackageOperationsMonitor()


class ConsoleEnvironmentOperationsMonitor(EnvironmentOperationsMonitor):

    def on_install(self) -> EnvironmentPackageModificationMonitor:
        Display.print("install")
        return ConsoleEnvironmentPackageModificationMonitor()

    def on_uninstall(self) -> EnvironmentPackageModificationMonitor:
        Display.print("uninstall")
        return ConsoleEnvironmentPackageModificationMonitor()

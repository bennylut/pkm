from pkm.api.packages.package import Package
from pkm.api.packages.site_packages import InstalledPackage
from pkm.resolution.resolution_monitor import DependencyResolutionMonitor
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import Monitor, no_monitor


# noinspection PyMethodMayBeStatic
class PackageInstallMonitor(Monitor):
    def on_package_may_download(self) -> FetchResourceMonitor:
        return no_monitor()


class EnvironmentPackageUpdateMonitor(Monitor):
    def on_dependency_resolution(self, request: Package) -> DependencyResolutionMonitor:
        return no_monitor()

    def on_install(self, package: Package) -> PackageInstallMonitor:
        return no_monitor()

    def on_uninstall(self, package: InstalledPackage) -> Monitor:
        return no_monitor()

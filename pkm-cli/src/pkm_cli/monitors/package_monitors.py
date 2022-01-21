from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_monitors import PackageOperationsMonitor, PackageInstallMonitor, PackageBuildMonitor
from pkm.api.packages.site_packages import InstalledPackage
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm_cli.display.display import Display


class ConsolePackageOperationsMonitor(PackageOperationsMonitor):
    def on_fetch(self, package: PackageDescriptor) -> FetchResourceMonitor:
        Display.print(f"fetching package: {package}")
        return super().on_fetch(package)

    def on_install(self, package: Package, env: Environment) -> PackageInstallMonitor:
        Display.print(f"installing package: {package}")
        return super().on_install(package, env)

    def on_uninstall(self, package: InstalledPackage, env: Environment):
        Display.print(f"uninstalling package: {package}")
        super().on_uninstall(package, env)

    def on_build(self, package: PackageDescriptor, artifact: str) -> PackageBuildMonitor:
        Display.print(f"building package: {package} for artifact: {artifact}")
        return super().on_build(package, artifact)

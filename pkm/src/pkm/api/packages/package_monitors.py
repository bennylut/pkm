from __future__ import annotations

from typing import TYPE_CHECKING

from pkm.utils.monitors import no_monitor, Monitor
from pkm.utils.http.http_monitors import FetchResourceMonitor

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment
    from pkm.api.packages.package import PackageDescriptor, Package
    from pkm.api.packages.site_packages import InstalledPackage
    from pkm.api.distributions.distribution import Distribution


class PackageBuildMonitor(Monitor):
    ...


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class HasBuildStepMonitor(Monitor):
    def on_build(self, package: "PackageDescriptor", artifact: str) -> PackageBuildMonitor:
        """
        :param package:
        :param artifact: # ['metadata', 'wheel', 'editable', 'sdist', 'app']
        :return:
        """
        return no_monitor()


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class PackageInstallMonitor(HasBuildStepMonitor, Monitor):

    def on_distribution_chosen(self, dist: "Distribution"):
        ...

    def on_copying_files(self):
        ...

    def on_generating_entrypoints(self):
        ...


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class PackageOperationsMonitor(HasBuildStepMonitor, Monitor):
    def on_fetch(self, package: "PackageDescriptor") -> FetchResourceMonitor:
        return no_monitor()

    def on_install(self, package: "Package", env: "Environment") -> PackageInstallMonitor:
        return no_monitor()

    def on_uninstall(self, package: "InstalledPackage", env: "Environment"):
        ...

    def on_extracting_metadata(self):
        ...

from __future__ import annotations

from typing import Dict

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.utils.monitors import Monitor, no_monitor
from pkm.utils.types import IterableWithLen


class HasDependencyResolutionStepMonitor(Monitor):
    def on_dependency_resolution(self, request: Dependency, repository: Repository) -> DependencyResolutionMonitor:
        return no_monitor()


# noinspection PyMethodMayBeStatic
class DependencyResolutionMonitor(Monitor):
    def on_resolution_iteration(self, packages_completed: IterableWithLen[str],
                                packages_requested: IterableWithLen[str], current_package: str):
        ...

    def on_final_decision(self, decisions: Dict[str, Version]):
        ...

    def on_package_examination(self, package: str, version: Version) -> PackageOperationsMonitor:
        return no_monitor()

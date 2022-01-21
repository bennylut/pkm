from typing import Dict, Optional

from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.api.versions.version import Version
from pkm.resolution.resolution_monitor import DependencyResolutionMonitor
from pkm.utils.types import IterableWithLen
from pkm_cli.display.display import Display
from pkm_cli.display.progress import Progress
from pkm_cli.monitors.package_monitors import ConsolePackageOperationsMonitor


class ConsoleDependencyResolutionMonitor(DependencyResolutionMonitor):
    def __init__(self):
        self._progress: Optional[Progress] = None

    def on_resolution_iteration(
            self, packages_completed: IterableWithLen[str],
            packages_requested: IterableWithLen[str], current_package: str):
        self._progress.completed = len(packages_completed)
        self._progress.total = len(packages_requested)

    def on_final_decision(self, decisions: Dict[str, Version]):
        d = {**decisions}
        del d['installation-request']
        self.on_end()
        Display.print(f"Reached decision: {d}")

    def on_package_examination(self, package: str, version: Version) -> PackageOperationsMonitor:
        return ConsolePackageOperationsMonitor()

    def on_start(self):
        self._progress = Display.progressbar('Dependency Resolution')

    def on_end(self):
        self._progress.close()

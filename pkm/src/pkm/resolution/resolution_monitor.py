from typing import Dict

from pkm.api.versions.version import Version
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import Monitor, no_monitor
from pkm.utils.types import IterableWithLen


class DependencyResolutionMonitor(Monitor):
    def on_resolution_iteration(self, packages_completed: IterableWithLen[str],
                                packages_requested: IterableWithLen[str], current_package: str):
        ...

    def on_final_decision(self, decisions: Dict[str, Version]):
        ...

    def on_package_may_download(self, package: str, version: Version) -> FetchResourceMonitor:
        return no_monitor()

from typing import Dict, Iterable


from pkm.api.versions.version import Version
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import Monitor, no_monitor


class DependencyResolutionMonitor(Monitor):
    def on_state_update(self, packages_completed: Iterable[str], packages_requested: Iterable[str]):
        ...

    def on_final_decision(self, decisions: Dict[str, Version]):
        ...

    def on_package_may_download(self, package: str, version: Version) -> FetchResourceMonitor:
        return no_monitor()

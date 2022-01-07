from pkm.api.environments.environment_monitors import EnvironmentPackageUpdateMonitor
from pkm.utils.monitors import Monitor, no_monitor


class ProjectPackageUpdateMonitor(Monitor):
    def on_environment_installation(self) -> EnvironmentPackageUpdateMonitor:
        return no_monitor()

    def on_update_lock(self):
        ...

    def on_update_pyproject(self):
        ...

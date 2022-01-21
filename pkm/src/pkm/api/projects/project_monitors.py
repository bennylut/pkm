from typing import Iterable, TYPE_CHECKING

from pkm.api.environments.environment_monitors import EnvironmentOperationsMonitor
from pkm.api.packages.package_monitors import PackageOperationsMonitor
from pkm.utils.monitors import no_monitor

if TYPE_CHECKING:
    from pkm.api.dependencies.dependency import Dependency
    from pkm.api.projects.project import Project


# noinspection PyMethodMayBeStatic
class ProjectOperationsMonitor(PackageOperationsMonitor):
    def on_environment_modification(self, project: "Project") -> EnvironmentOperationsMonitor:
        return no_monitor()

    def on_dependencies_modified(self, project: "Project", old_deps: Iterable["Dependency"],
                                 new_deps: Iterable["Dependency"]):
        ...

    def on_lock_modified(self):
        ...

    def on_pyproject_modified(self):
        ...

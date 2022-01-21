from typing import Iterable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment_monitors import EnvironmentOperationsMonitor
from pkm.api.projects.project import Project
from pkm.api.projects.project_monitors import ProjectOperationsMonitor
from pkm_cli.display.display import Display
from pkm_cli.monitors.environment_monitors import ConsoleEnvironmentOperationsMonitor
from pkm_cli.monitors.package_monitors import ConsolePackageOperationsMonitor


class ConsoleProjectOperationsMonitor(ProjectOperationsMonitor, ConsolePackageOperationsMonitor):
    def on_environment_modification(self, project: Project) -> EnvironmentOperationsMonitor:
        Display.print("modifying project environment...")
        return ConsoleEnvironmentOperationsMonitor()

    def on_dependencies_modified(self, project: Project, old_deps: Iterable[Dependency],
                                 new_deps: Iterable[Dependency]):
        Display.print("modifying project dependencies...")

    def on_lock_modified(self):
        Display.print("modifying project lock...")

    def on_pyproject_modified(self):
        Display.print("modifying pyproject...")

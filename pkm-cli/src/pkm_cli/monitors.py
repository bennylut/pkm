from pathlib import Path
from rich.console import Console
from rich.progress import Progress, TaskID, BarColumn, TimeElapsedColumn
from typing import Optional, Dict

from pkm.api.environments.environment_monitors import EnvironmentPackageUpdateMonitor, PackageInstallMonitor
from pkm.api.packages.package import Package
from pkm.api.packages.site_packages import InstalledPackage
from pkm.api.projects.project_monitors import ProjectPackageUpdateMonitor
from pkm.api.versions.version import Version
from pkm.resolution.resolution_monitor import DependencyResolutionMonitor
from pkm.utils.http.http_monitors import FetchResourceMonitor
from pkm.utils.monitors import Monitor, no_monitor
from pkm.utils.types import IterableWithLen


class ConsoleFetchResourceMonitor(FetchResourceMonitor):

    def __init__(self, progress_manager: Progress, resource_name: str):
        self._progress_manager = progress_manager
        self._resource_name = resource_name
        self._task_id: Optional[TaskID] = None

    def _description_header(self) -> str:
        return f"Fetch {self._resource_name}"

    def on_start(self):
        self._task_id = self._progress_manager.add_task(self._description_header())

    def on_end(self):
        self._progress_manager.update(self._task_id, completed=True)

    def on_cache_hit(self):
        self._progress_manager.update(self._task_id, description=f"{self._description_header()} | Taken from cache.")

    def on_download_start(self, file_size: int, path: Path):
        self._progress_manager.update(self._task_id, description=f"{self._description_header()} | Downloading.")
        # should track...


class ConsoleDependencyResolutionMonitor(DependencyResolutionMonitor):

    def __init__(self, console: Console):
        self._console = console
        self._progress = progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.completed}/{task.total}",
            TimeElapsedColumn(),
        )
        self._task_id = self._progress.add_task('Dependency Resolution')
        self._progress_ended = False

    def on_resolution_iteration(
            self, packages_completed: IterableWithLen[str],
            packages_requested: IterableWithLen[str], current_package: str):
        # self._console.log(f"currently decided on: {list(packages_completed)}")
        self._progress.update(self._task_id, completed=len(packages_completed), total=len(packages_requested))

    def on_final_decision(self, decisions: Dict[str, Version]):
        d = {**decisions}
        del d['installation-request']
        self.on_end()
        self._console.print(f"Reached decision: {d}")

    def on_package_may_download(self, package: str, version: Version) -> FetchResourceMonitor:
        return super().on_package_may_download(package, version)

    def on_start(self):
        self._progress.__enter__()

    def on_end(self):
        if not self._progress_ended:
            self._progress_ended = True
            self._progress.__exit__(None, None, None)


class ConsoleEnvironmentPackageUpdateMonitor(EnvironmentPackageUpdateMonitor):

    def __init__(self, progress: Progress, console: Console):
        self._install_progress = progress
        self._console = console

    def on_dependency_resolution(self, request: Package) -> DependencyResolutionMonitor:
        self._console.print("starting dependency resolution")
        return ConsoleDependencyResolutionMonitor(self._console)

    def on_install(self, package: Package) -> PackageInstallMonitor:
        self._console.print(f"installing package {package}")
        return no_monitor()

    def on_uninstall(self, package: InstalledPackage) -> Monitor:
        self._console.print(f"uninstalling package {package}")
        return no_monitor()


class ConsoleProjectPackageUpdateMonitor(ProjectPackageUpdateMonitor):

    def __init__(self, console: Console):
        self._console = console

    def on_environment_installation(self) -> EnvironmentPackageUpdateMonitor:
        return ConsoleEnvironmentPackageUpdateMonitor(prog := Progress(console=self._console), prog.console)

    def on_update_lock(self):
        self._console.print("updating lock...")

    def on_update_pyproject(self):
        self._console.print("updating pyproject...")

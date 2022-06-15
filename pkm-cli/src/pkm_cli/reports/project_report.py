from typing import Dict, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.site_packages import InstalledPackage
from pkm.api.projects.project import Project
from pkm_cli.display.display import Display
from pkm_cli.reports.attached_repository_report import AttachedRepositoryReport
from pkm_cli.reports.report import Report


class ProjectReport(Report):

    def __init__(self, project: Project):
        super().__init__()
        self._project = project

    def display_options(self):
        self.option_help(
            'lock', 'Displays locked versions')

    def display(self, options: Dict[str, bool]):
        env = self._project.attached_environment
        site_ = env.site_packages

        with self.section("Project Basic Info"):
            self.writeln(f"Name: {self._project.name}")
            self.writeln(f"Version: {self._project.version}")
            self.writeln(f"Description: {self._project.config.project.description}")
            self.writeln(f"Requires Python: {self._project.config.project.requires_python}")

        if self._project.group:
            with self.section("Project Group"):
                self.writeln(f"Path: {self._project.group.path}")

        with self.section("Attached Environment"):
            self.writeln(f"Path: {env.path}")
            self.writeln(f"Interpreter Version: {env.interpreter_version}")

        dependencies = self._project.config.project.dependencies
        optional_dependencies = self._project.config.project.optional_dependencies
        if dependencies or optional_dependencies:
            with self.section("Dependencies"):
                with self.ulist() as dependencies_ulist:
                    for dependency in dependencies:
                        dependencies_ulist.item(_dependency_status_line(
                            dependency, site_.installed_package(dependency.package_name), None))

                    for group, dependencies_in_group in optional_dependencies.items():
                        for dependency in dependencies_in_group:
                            dependencies_ulist.item(_dependency_status_line(
                                dependency, site_.installed_package(dependency.package_name), group))

        if options.get('lock', False):
            with self.section("Lock (for attached env signature)"):
                with self.ulist(empty_text='No Lock Information') as lock_ulist:
                    for locked_package in self._project.lock.env_specific_locks(env):
                        lock_ulist.item(f"{locked_package.name} {locked_package.version}")

        AttachedRepositoryReport(self._project).display({})


def _dependency_status_line(
        d: Dependency, installed: Optional[InstalledPackage] = None, optional: Optional[str] = None) -> str:
    result = f"{d} | "
    if installed:
        result += f"Installed Version: {installed.version} | "
    else:
        result += f"Not Installed | "
    if optional:
        result += f"Optional by {optional}"
    else:
        result += "Required"

    return result

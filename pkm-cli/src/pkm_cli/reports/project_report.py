from pkm.api.projects.project import Project
from pkm_cli.display.display import Display
from pkm_cli.reports.report import Report


class ProjectReport(Report):

    def __init__(self, project: Project):
        self._project = project

    def display(self, dumb: bool = Display.is_dumb()):
        env = self._project.default_environment

        line = "-" * 80
        Display.print(line)

        Display.print("Project Basic Info")
        Display.print(line)
        Display.print(f"Name: {self._project.name}")
        Display.print(f"Version: {self._project.version}")
        Display.print(f"Description: {self._project.config.project.description}")
        Display.print(f"Requires Python: {self._project.config.project.requires_python}")
        Display.print(line)

        Display.print("Attached Virtual Environment")
        Display.print(line)
        Display.print(f"Path: {env.path}")
        Display.print(f"Interpreter Version: {env.interpreter_version}")
        Display.print(line)

        Display.print("Dependencies")
        Display.print(line)
        for dependency in self._project.config.project.dependencies:
            Display.print(
                f"- {dependency} | "
                f"Installed: {env.site_packages.installed_package(dependency.package_name).version}")
        Display.print(line)

        Display.print("Lock (for attached env signature)")
        Display.print(line)
        for locked_package in self._project.lock.env_specific_locks(env):
            Display.print(f"- {locked_package.name} {locked_package.version}")
        Display.print(line)


from dataclasses import dataclass, field
from typing import Dict, List, Set

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.package_containers import PackageContainer
from pkm.api.packages.site_packages import InstalledPackage
from pkm_cli.display.display import Display
from pkm_cli.reports.attached_repository_report import AttachedRepositoryReport
from pkm_cli.reports.report import Report


class EnvironmentReport(Report):

    def __init__(self, env: Environment):
        super().__init__()
        self._env = env

    def display_options(self):
        self.option_help(
            'all-installed', 'Displays all the packages installed in this environment, not only the user requested')
        self.option_help(
            'attached-repository', 'Displays information about the attached repository')
        self.option_help(
            'package-containers', 'Display information about the installed package containers')
        self.option_help(
            'scripts', 'Display information about the available scripts installed to this environment')

    def display(self, options: Dict[str, bool]):
        env = self._env
        with self.section("Basic Environment Info"):
            Display.print(f"Path: {env.path}")
            Display.print(f"Interpreter Version: {env.interpreter_version}")

        containers: Dict[str, PackageContainer] = {
            container.package.name_key: container
            for container in env.package_containers.containers()
        }

        installed_packages: Dict[str, _PackageInfo] = {
            package.name_key: _PackageInfo(package)
            for package in env.site_packages.installed_packages()
            if package.name_key not in containers
        }

        for p in installed_packages.values():
            dependencies = p.package.dependencies(env.installation_target)
            for d in dependencies:
                norm_package_name = d.package_name_key
                if q := installed_packages.get(norm_package_name):
                    q.required_by.append(p.package)
                else:
                    p.missing_dependencies.append(d)

        display_all = options.get('all-installed', False)
        pacakages_to_show = [p for p in installed_packages.values() if display_all or p.package.user_request]

        if pacakages_to_show:
            with self.section("Installed Packages"):
                for p in pacakages_to_show:
                    p.display()

        if containers and options.get('package-containers', True):
            with self.section("Package Containers"):
                for container in containers.values():
                    cp = container.containerized_package

                    self.writeln(f"Container: {cp.name} {cp.version}")
                    with self.ulist('+', 'No Containers Installed') as containers_ulist:
                        for plugin in container.list_installed_plugins():
                            containers_ulist.item(f"{plugin.name} {plugin.version}")

        if options.get("scripts", False):
            with self.section("Scripts"), self.ulist(empty_text="No Installed Scripts Found") as scripts_ulist:
                for installed_pacakge in env.site_packages.installed_packages():
                    for entrypoint in installed_pacakge.dist_info.load_entrypoints_cfg().entrypoints:
                        if entrypoint.is_script():
                            scripts_ulist.item(f"{entrypoint.name}, installed by {installed_pacakge.name}")

        if options.get('attached-repository', True):
            AttachedRepositoryReport(self._env).display({})


@dataclass
class _PackageInfo:
    package: InstalledPackage
    required_by: List[InstalledPackage] = field(default_factory=list)
    missing_dependencies: List[Dependency] = field(default_factory=list)

    def display(self):
        dsp = f" + {self.package.name} {self.package.version}, "
        if ur := self.package.user_request:
            dsp += f"required by the user ({ur})"
        else:
            if self.required_by:
                dsp += f"required by: " + ', '.join(str(r.name) for r in self.required_by)
            else:
                dsp += "(orphan)"

        Display.print(dsp)
        if self.missing_dependencies:
            Display.print("* WARNING: this package has missing dependencies: ")
            for md in self.missing_dependencies:
                Display.print(f"  - {md}")

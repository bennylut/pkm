from dataclasses import dataclass, field
from typing import Dict, List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.site_packages import InstalledPackage
from pkm_cli.display.display import Display
from pkm_cli.reports.report import Report


class EnvironmentReport(Report):

    def __init__(self, env: Environment, options: Dict[str, bool]):
        self._env = env
        self._options = options

    def display_options(self):
        Display.print(
            "[all-installed]: Displays all the packages installed in this environment, not only the user requested")

    def display(self):
        env = self._env
        Display.print("")

        with self._section("Basic Environment Info"):
            Display.print(f"Path: {env.path}")
            Display.print(f"Interpreter Version: {env.interpreter_version}")

        with self._section("Installed Packages"):
            package_info: Dict[str, _PackageInfo] = {
                package.name_key: _PackageInfo(package)
                for package in env.site_packages.installed_packages()
            }

            for p in package_info.values():
                dependencies = p.package.dependencies(env.installation_target)
                for d in dependencies:
                    norm_package_name = d.package_name_key
                    if q := package_info.get(norm_package_name):
                        q.required_by.append(p.package)
                    else:
                        p.missing_dependencies.append(d)

            display_all = 'all-installed' in self._options
            for p in package_info.values():
                if display_all or p.package.user_request:
                    p.display()


@dataclass
class _PackageInfo:
    package: InstalledPackage
    required_by: List[InstalledPackage] = field(default_factory=list)
    missing_dependencies: List[Dependency] = field(default_factory=list)

    def display(self):
        dsp = f"- {self.package.name} {self.package.version}, "
        if ur := self.package.user_request:
            dsp += f"required by the user ({ur})"
        else:
            dsp += f"required by: " + ', '.join(str(r.name) for r in self.required_by)

        Display.print(dsp)
        if self.missing_dependencies:
            Display.print("* WARNING: this package has missing dependencies: ")
            for md in self.missing_dependencies:
                Display.print(f"  - {md}")

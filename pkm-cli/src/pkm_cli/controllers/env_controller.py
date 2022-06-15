from typing import Optional, List

from pkm.api.environments.environment import Environment
from pkm.utils.seqs import seq
from pkm_cli.display.display import Display


class EnvController:
    def __init__(self, env: Environment):
        self._env = env

    def _find_target(self, container: Optional[str]):
        return self._env.package_containers.container_of(container).installation_target \
            if container else self._env.installation_target

    def uninstall_orphans(self, container: Optional[str] = None):
        target = self._find_target(container)

        orphans = target.site_packages.find_orphan_packages()
        if orphans:
            Display.print(f"Will remove packages: {[p.descriptor for p in orphans]}")
            target.uninstall([p.name for p in orphans])
        else:
            Display.print("There are no orphan packages found in environment")

    def uninstall(self, package_names: List[str], force: bool, container: Optional[str]):
        if container and not package_names:
            container = self._env.package_containers.container_of(container)
            uninstalled = [container.package.name]
            container.uninstall()
        else:
            target = self._find_target(container)
            if force:
                uninstalled = []
                for package in package_names:
                    if target.force_remove(package):
                        uninstalled.append(package)
            else:
                uninstalled = target.uninstall(package_names)

        Display.print(f"Package Removed: {seq(uninstalled).str_join(', ')}")

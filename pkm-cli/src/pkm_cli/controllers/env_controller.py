from typing import Optional

from pkm.api.environments.environment import Environment
from pkm_cli.display.display import Display


class EnvController:
    def __init__(self, env: Environment):
        self._env = env

    def uninstall_orphans(self, app: Optional[str] = None):
        target = self._env.app_containers.container_of(app).installation_target \
            if app else self._env.installation_target

        orphans = target.site_packages.find_orphan_packages()
        if orphans:
            Display.print(f"Will remove packages: {[p.descriptor for p in orphans]}")
            target.uninstall([p.name for p in orphans])
        else:
            Display.print("There are no orphan packages found in environment")

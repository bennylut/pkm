from typing import Set, Dict

from pkm.api.pkm import HasAttachedRepository
from pkm_cli.display.display import Display
from pkm_cli.reports.report import Report


class AttachedRepositoryReport(Report):

    def display_options(self):
        self.writeln("No Options")

    def __init__(self, context: HasAttachedRepository):
        super().__init__()
        self._context = context

    def display(self, options: Dict[str, bool]):
        with self.section("Attached Repository"):
            rm = self._context.repository_management

            Display.print(f"Configuration Chain: (Inheritance = {rm.configuration.inheritance})")
            with self.ulist() as configs_ulist:
                for rman in rm.package_lookup_chain():
                    config = rman.configuration
                    configs_ulist.item(f"{config.path}: ")
                    with self.olist("No (Unbounded) Repositories Defined") as repositories_olist:
                        for repo_name, repo_value in config.repos.items():
                            if not repo_value.bind_only:
                                repositories_olist.item(f"{repo_name}: {repo_value.type}")
                        if config.package_bindings:
                            self.writeln(f" + Bound Packages: {','.join(config.package_bindings.keys())}")

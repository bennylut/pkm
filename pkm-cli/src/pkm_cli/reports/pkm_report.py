from typing import Dict

from pkm.api.pkm import pkm
from pkm.utils.files import numbytes_to_human, dir_size
from pkm_cli.controllers.self_controller import SelfController
from pkm_cli.reports.report import Report


class PkmReport(Report):

    def __init__(self):
        super().__init__()

    def display_options(self):
        self.writeln("No options")

    def display(self, options: Dict[str, bool]):
        controller = SelfController()
        with self.section("Pkm Installation"):
            package = controller.pkm_cli_package
            self.writeln(f"pkm-cli: {package.version}")
            self.writeln(f"Global Environment: {controller.global_environment.path}")
            self.writeln(f"Home Path: {pkm.home}")

        with self.section("Caches"):
            self.writeln(f"Downloaded Files Cache: [blue]{numbytes_to_human(dir_size(pkm.httpclient.workspace))}[/]")
            self.writeln(
                f"Build Packages Cache: [blue]{numbytes_to_human(dir_size(pkm.source_build_cache.workspace))}[/]")

        with self.section("Configuration"):
            cfg = pkm.config
            self.writeln(f"Concurrency Mode = {cfg.concurrency_mode}")
            self.writeln(f"Custom Interpreters Search Path = {cfg.interpreters_search_paths}")

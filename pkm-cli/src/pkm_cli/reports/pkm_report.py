from typing import Dict, TYPE_CHECKING

from pkm.api.pkm import pkm
from pkm.utils.files import numbytes_to_human, dir_size
from pkm_cli.reports.report import Report
from pkm_cli.controllers.self_controller import SelfController


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

        with self.section("Global Flags"):
            for flag, value in pkm.global_flags.to_config().items():
                self.writeln(f"{flag}: {value}")

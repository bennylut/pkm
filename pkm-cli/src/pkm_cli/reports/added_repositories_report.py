from typing import Dict

from pkm.api.pkm import HasAttachedRepository
from pkm.utils.sequences import pop_or_none
from pkm.utils.sets import add_if_absent
from pkm_cli.display.display import Display
from pkm_cli.reports.report import Report
import re


class AddedRepositoriesReport(Report):

    def __init__(self, with_repo: HasAttachedRepository):
        super().__init__()
        self._with_repo = with_repo

    def display_options(self):
        self.writeln("No Options")

    def display(self, options: Dict[str, bool]):
        for har in self._with_repo.repository_management.package_lookup_chain():
            if defined_repositories := har.defined_repositories():
                with self.section(f"{_context_name(har.context)} Context"):
                    for name, added_repository in defined_repositories:
                        desc = f"{name}: {added_repository.type}"
                        if added_repository.bind_only:
                            desc += " (bind only)"
                        Display.print(desc)


def _context_name(context: HasAttachedRepository) -> str:
    return re.sub('([A-Z])', r' \1', type(context).__name__).strip()

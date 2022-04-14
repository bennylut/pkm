from pathlib import Path
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distribution import Distribution
from pkm.api.packages.package import Package
from pkm.api.projects.project import Project
from pkm.api.repositories.repository import AbstractRepository
from pkm.utils.strings import endswith_any, without_prefix


class FileRepository(AbstractRepository):
    def __init__(self):
        super().__init__("file")

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if not (vurl := dependency.version_spec.specific_url()):
            return []

        package = load_package_from_filesystem(Path(without_prefix(vurl.url, "file://")))
        return [package] if package else []


def load_package_from_filesystem(location: Path) -> Optional[Package]:
    if location.is_dir():
        return Project.load(location)
    elif endswith_any(location.name, ('.tar.gz', '.whl')):
        return Distribution.package_from(location)

    return None

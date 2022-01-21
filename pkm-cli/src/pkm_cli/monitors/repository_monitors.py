from pkm.api.dependencies.dependency import Dependency
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor


class ConsoleRepositoryOperationsMonitor(RepositoryOperationsMonitor):
    def on_dependency_match(self, dependency: Dependency):
        super().on_dependency_match(dependency)

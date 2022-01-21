from pkm.api.dependencies.dependency import Dependency
from pkm.utils.monitors import Monitor


class RepositoryOperationsMonitor(Monitor):
    def on_dependency_match(self, dependency: Dependency):
        ...

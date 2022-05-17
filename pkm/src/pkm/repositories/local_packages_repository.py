from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional, Any

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distribution import Distribution
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import AbstractRepository, RepositoryBuilder, Repository
from pkm.utils.strings import endswith_any

LOCAL_PACKAGES_REPOSITORY_TYPE = "local"


class PackagesDictRepository(AbstractRepository):

    def __init__(self, name: str, packages: Dict[str, List[Package]]):
        super().__init__(name)
        self._packages = packages

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        all_packages = self._packages.get(dependency.package_name) or []
        return [p for p in all_packages if dependency.version_spec.allows_version(p.version)]


class LocalPackagesRepositoryBuilder(RepositoryBuilder):

    def __init__(self):
        super().__init__(LOCAL_PACKAGES_REPOSITORY_TYPE)

    def build(self, name: Optional[str], packages_limit: Optional[List[str]], **kwargs: Any) -> Repository:
        projects: List[str] = kwargs.get('projects', [])
        distributions: List[str] = kwargs.get('distributions', [])

        packages_limit: Dict[str, List[Package]] = defaultdict(list)

        # load projects
        for project_path_str in projects:
            project_path = Path(project_path_str)
            if (project_path / 'pyproject-group.toml').exists():
                project_group = ProjectGroup.load(project_path)
                for project in project_group.project_children_recursive:
                    packages_limit[project.name].append(project)
            else:
                project = Project.load(project_path)
                packages_limit[project.name].append(project)

        # load distributions
        for distribution_path_str in distributions:
            distribution_path = Path(distribution_path_str)
            if distribution_path.is_dir():
                for dist in distribution_path.iterdir():
                    if endswith_any(dist.name, ('.tar.gz', '.whl')):
                        package = Distribution.package_from(dist)
                        packages_limit[package.name].append(package)
            else:
                package = Distribution.package_from(distribution_path)
                packages_limit[package.name].append(package)

        return PackagesDictRepository(name, packages_limit)

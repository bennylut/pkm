from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repositories_configuration import RepositoriesConfiguration, RepositoryInstanceConfig
from pkm.api.repositories.repository import Repository, AbstractRepository
from pkm.api.repositories.repository_loader import RepositoryLoader, REPOSITORIES_CONFIGURATION_PATH
from pkm.repositories.shared_pacakges_repo import SharedPackagesRepository
from pkm.resolution.packages_lock import LockPrioritizingRepository
from pkm.utils.properties import cached_property, clear_cached_properties


class RepositoryManagement(ABC):
    def __init__(self, cfg: RepositoriesConfiguration, loader: Optional[RepositoryLoader] = None):
        if not loader:
            from pkm.api.pkm import pkm
            loader = pkm.repository_loader

        self._loader = loader
        self.configuration = cfg

    @abstractmethod
    def _load_attached(self) -> Repository:
        ...

    @cached_property
    def attached_repo(self) -> Repository:
        return self._load_attached()

    def _update_config(self):
        self.configuration.save()
        clear_cached_properties(self)

    def add_repository(self, name: str, builder: str, args: Dict[str, str], packages_limit: Optional[List[str]] = None):
        config = RepositoryInstanceConfig(builder, packages_limit, name, args)

        # the following line act a s a safeguard before the add operation,
        # if it fails the actual addition will not take place
        self._loader.build(config)

        self.configuration.repositories = [
            *self.configuration.repositories, config]

        self._update_config()

    def list_defined_repositories(self) -> List[RepositoryInstanceConfig]:
        return self.configuration.repositories

    def remove_repository(self, name: str):
        self.configuration.repositories = [repo for repo in self.configuration.repositories if repo.name != name]
        self._update_config()


def _config_at(path: Path) -> RepositoriesConfiguration:
    return RepositoriesConfiguration.load(path / REPOSITORIES_CONFIGURATION_PATH)


class EnvRepositoryManagement(RepositoryManagement):

    def __init__(self, env: Environment, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(env.path), loader)
        self.env = env

    def _load_attached(self) -> Repository:
        repo = self._loader.main
        if zoo := self.env.zoo:
            repo = zoo.attached_repository

        if self.configuration.path.exists():
            repo = self._loader.load("env-configured-repository", self.configuration, repo)

        return repo


class ZooRepositoryManagement(RepositoryManagement):
    def __init__(self, zoo: EnvironmentsZoo, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(zoo.path), loader)
        self.zoo = zoo

    def _load_attached(self) -> Repository:
        repo = self._loader.main
        if self.configuration.path.exists():
            repo = self._loader.load("zoo-configured-repository", self.configuration, repo)

        if self.zoo.config.package_sharing.enabled:
            repo = SharedPackagesRepository(self.zoo.path / ".zoo/shared", repo)

        return repo


def _load_for_project_group(
        loader: RepositoryLoader,
        group: ProjectGroup,
        config: RepositoriesConfiguration,
        base_repo: Optional[Repository] = None) -> Repository:
    repo = base_repo or loader.main

    if config.path.exists():
        repo = loader.load("group-configured-repository", config, repo)

    repo = _ProjectsRepository.create("group-projects-repository", group.project_children_recursive, repo)
    return repo


class ProjectRepositoryManagement(RepositoryManagement):

    def __init__(self, project: Project, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(project.path), loader)
        self.project = project

    def _load_attached(self) -> Repository:
        repo = self.project.attached_environment.attached_repository

        if group := self.project.group:
            repo = _load_for_project_group(self._loader, group, _config_at(group.path), repo)
        else:
            repo = _ProjectsRepository.create('project-repository', [self.project], repo)

        if self.configuration.exists():
            repo = self._loader.load("project-configured-repository", self.configuration, repo)

        repo = LockPrioritizingRepository(
            "lock-prioritizing-repository", repo, self.project.lock,
            self.project.attached_environment)

        return repo


class ProjectGroupRepositoryManagement(RepositoryManagement):
    def __init__(self, group: ProjectGroup, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(group.path), loader)
        self.group = group

    def _load_attached(self) -> Repository:
        return _load_for_project_group(self._loader, self.group, self.configuration, None)


class _ProjectsRepository(AbstractRepository):
    def __init__(self, name: str, projects: Dict[str, Tuple[PackageDescriptor, Path]], base_repo: Repository):
        super().__init__(name)
        self._packages = projects
        self._base_repo = base_repo

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        if (package_and_path := self._packages.get(dependency.package_name)) and \
                dependency.version_spec.allows_version(package_and_path[0].version):
            return [Project.load(package_and_path[1])]
        return self._base_repo.match(dependency, env)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        return packages

    @classmethod
    def create(cls, name: str, projects: Iterable[Project], base: Repository) -> _ProjectsRepository:
        return _ProjectsRepository(name, {p.name: (p.descriptor, p.path) for p in projects}, base)

    def accept_non_url_packages(self) -> bool:
        return self._base_repo.accept_non_url_packages()

    def accepted_url_protocols(self) -> Iterable[str]:
        return self._base_repo.accepted_url_protocols()

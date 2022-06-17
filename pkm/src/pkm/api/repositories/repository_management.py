from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterable, Union, Set

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.environments_zoo import EnvironmentsZoo
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.pkm import HasAttachedRepository, Pkm, pkm
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repositories_configuration import RepositoriesConfiguration, RepositoryInstanceConfig, \
    RepositoriesConfigInheritanceMode
from pkm.api.repositories.repository import Repository, AbstractRepository, RepositoryPublisher
from pkm.api.repositories.repository_loader import RepositoryLoader, REPOSITORIES_CONFIGURATION_PATH
from pkm.repositories.shared_pacakges_repo import SharedPackagesRepository
from pkm.resolution.packages_lock import LockPrioritizingRepository
from pkm.utils.commons import NoSuchElementException
from pkm.utils.iterators import groupby
from pkm.utils.properties import cached_property, clear_cached_properties
from pkm.utils.seqs import seq
from pkm.utils.sequences import pop_or_none
from pkm.utils.sets import try_add
from pkm.utils.types import Supplier


class RepositoryManagement(ABC):
    def __init__(self, cfg: RepositoriesConfiguration, loader: Optional[RepositoryLoader] = None):
        if not loader:
            loader = pkm.repository_loader

        self._loader = loader
        self.configuration = cfg

    @abstractmethod
    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        ...

    @cached_property
    def _publishers(self) -> Dict[str, Optional[RepositoryPublisher]]:
        return {}  # it is cached only so that _update_config will clear it

    @property
    @abstractmethod
    def context(self) -> HasAttachedRepository:
        ...

    @abstractmethod
    def parent_contexts(self) -> List[Tuple[HasAttachedRepository, bool]]:
        """
        :return: list of parent contextes, an item in this list is a tuple, its second value represents if the
        given parent chain is inherited from (false indicate that we only looking at the direct configuration of
        the parent)
        """

    def package_lookup_chain(self) -> List[RepositoryManagement]:
        if self.configuration.inheritance_mode == RepositoriesConfigInheritanceMode.INHERIT_GLOBAL:
            return [pkm.repository_management]
        elif self.configuration.inheritance_mode != RepositoriesConfigInheritanceMode.INHERIT_CONTEXT:
            return [self]

        pending: List[Tuple[RepositoryManagement, bool]] = [(self, True)]
        closed: Set[Path] = set()
        chain: List[RepositoryManagement] = []

        while next_ := pop_or_none(pending):
            rman, inherit = next_
            if not try_add(closed, rman.configuration.path):
                continue
            chain.append(rman)
            if inherit:
                pending.extend(
                    (context.repository_management, inherit) for (context, inherit) in rman.parent_contexts())

        return chain

    def publisher_for(self, name: str) -> Optional[RepositoryPublisher]:
        if name in self._publishers:
            return self._publishers[name]

        for rman in self.package_lookup_chain():
            for repo_name, repo_config in rman.configuration.repos.items():
                if repo_name == name:
                    result = self._publishers[name] = self._loader.build(name, repo_config).publisher
                    return result

        raise NoSuchElementException(f"repository: {name} could not be found")

    def register_bindings(self, packages: List[str], repo: Optional[Union[str, RepositoryInstanceConfig]]):
        if repo:
            if isinstance(repo, RepositoryInstanceConfig):
                repo = repo.to_config()

            self.configuration.package_bindings = {
                **self.configuration.package_bindings,
                **{p: repo for p in packages}
            }
        else:
            self.configuration.package_bindings = {
                p: r for p, r in self.configuration.package_bindings.items()
                if p not in packages
            }

        self._update_config()

    @cached_property
    def attached_repo(self) -> Repository:
        repo = None
        for rman in reversed(self.package_lookup_chain()):
            if not isinstance(rman, PkmRepositoryManagement) and rman.configuration.path.exists():
                repo = self._loader.load(str(rman.configuration.path), rman.configuration, repo)
            repo = rman._wrap_attached_repository(repo)

        return repo

    def _update_config(self):
        self.configuration.save()
        clear_cached_properties(self)

    def add_repository(self, name: str, builder: str, args: Dict[str, str], bind_only: bool = False):
        config = RepositoryInstanceConfig(builder, bind_only, args)

        # the following line act a s a safeguard before the add operation,
        # if it fails the actual addition will not take place
        self._loader.build(name, config)

        self.configuration.repos[name] = config

        self._update_config()

    def defined_repositories(self) -> Iterable[RepositoryInstanceConfig]:
        return self.configuration.repos.values()

    def remove_repository(self, name: str):
        self.configuration.repos.pop(name, None)
        self.configuration.package_bindings = {
            p: r for p, r in self.configuration.package_bindings.items() if r != name}
        self._update_config()


def _config_at(path: Path) -> RepositoriesConfiguration:
    return RepositoriesConfiguration.load(path / REPOSITORIES_CONFIGURATION_PATH)


class PkmRepositoryManagement(RepositoryManagement):

    def __init__(self, pkm_: Pkm):
        super().__init__(pkm_.repository_loader.global_repo_config, pkm_.repository_loader)
        self.pkm = pkm_

    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        return self._loader.global_repo

    def parent_contexts(self) -> List[HasAttachedRepository]:
        return []

    @property
    def context(self) -> HasAttachedRepository:
        return self.pkm


class EnvRepositoryManagement(RepositoryManagement):

    def __init__(self, env: Environment, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(env.path), loader)
        self.env = env

    @property
    def context(self) -> HasAttachedRepository:
        return self.env

    def parent_contexts(self) -> List[Tuple[HasAttachedRepository, bool]]:
        return [(self.env.zoo or pkm, True)]

    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        return inherited


class ZooRepositoryManagement(RepositoryManagement):

    def __init__(self, zoo: EnvironmentsZoo, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(zoo.path), loader)
        self.zoo = zoo

    @property
    def context(self) -> HasAttachedRepository:
        return self.zoo

    def parent_contexts(self) -> List[Tuple[HasAttachedRepository, bool]]:
        return [(pkm, True)]

    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        if self.zoo.config.package_sharing.enabled:
            inherited = SharedPackagesRepository(self.zoo.path / ".zoo/shared", inherited)

        return inherited


class ProjectRepositoryManagement(RepositoryManagement):

    def __init__(self, project: Project, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(project.path), loader)
        self.project = project

    @property
    def context(self) -> HasAttachedRepository:
        return self.project

    def parent_contexts(self) -> List[Tuple[HasAttachedRepository, bool]]:
        result = [(self.project.attached_environment, True)]
        if self.project.group:
            result.append((self.project.group, False))

        return result

    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        # must wrap (even if it has project group) so that the repository will always return the exact same project
        # with any modifications made to it and won't reload it from disk
        inherited = _ProjectsRepository.create('project-repository', [self.project], inherited)

        inherited = LockPrioritizingRepository(
            "lock-prioritizing-repository", inherited, self.project.lock,
            self.project.attached_environment)

        return inherited


class ProjectGroupRepositoryManagement(RepositoryManagement):

    def __init__(self, group: ProjectGroup, loader: Optional[RepositoryLoader] = None):
        super().__init__(_config_at(group.path), loader)
        self.group = group

    @property
    def context(self) -> HasAttachedRepository:
        return self.group

    def parent_contexts(self) -> List[Tuple[HasAttachedRepository, bool]]:
        return [(pkm, True)]

    def _wrap_attached_repository(self, inherited: Optional[Repository]) -> Repository:
        group = self.group
        return _ProjectsRepository.create("group-projects-repository", group.project_children_recursive, inherited)


class _ProjectsRepository(AbstractRepository):
    def __init__(self, name: str, projects: Dict[str, List[Project]], base_repo: Repository):
        super().__init__(name)
        self._packages = projects
        self._base_repo = base_repo

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        if not dependency.required_url():
            if matched_projects := self._packages.get(dependency.package_name_key):
                return sorted([project for project in matched_projects], key=lambda it: it.version, reverse=True)
        return self._base_repo.match(dependency, env)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        return packages

    @classmethod
    def create(cls, name: str, projects: Iterable[Project], base: Repository) -> _ProjectsRepository:
        grouped_projects = groupby(projects, lambda it: it.name_key)
        return _ProjectsRepository(name, grouped_projects, base)

    def accept_non_url_packages(self) -> bool:
        return self._base_repo.accept_non_url_packages()

    def accepted_url_protocols(self) -> Iterable[str]:
        return self._base_repo.accepted_url_protocols()

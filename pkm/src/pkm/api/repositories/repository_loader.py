from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import Repository, RepositoryBuilder, AbstractRepository
from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.config.etc_chain import EtcChain
from pkm.utils.commons import NoSuchElementException
from pkm.utils.dicts import remove_none_values, put_if_absent
from pkm.utils.http.http_client import HttpClient

REPOSITORIES_ENTRYPOINT_GROUP = "pkm.repositories"
REPOSITORIES_CFG = "repositories.toml"


class RepositoryLoader:
    def __init__(self, etc: EtcChain, http: HttpClient, workspace: Path):

        from pkm.api.projects.project_group import ProjectGroupRepositoryBuilder

        from pkm.api.environments.environment import Environment
        from pkm.api.repositories.simple_repository import SimpleRepositoryBuilder
        from pkm.api.repositories.git_repository import GitRepository
        from pkm.api.repositories.pypi_repository import PyPiRepository
        from pkm.api.repositories.local_packages_repository import LocalPackagesRepositoryBuilder

        # base repositories
        self.pypi = PyPiRepository(http)
        self._cached_instances: Dict[RepositoryInstanceConfig, Repository] = {}

        self._url_repos = {
            r.name: r for r in (
                GitRepository(workspace / 'git'),
            )
        }

        # common builders
        self._builders = {
            b.name: b for b in (
                SimpleRepositoryBuilder(http),
                LocalPackagesRepositoryBuilder(),
                ProjectGroupRepositoryBuilder(),
            )
        }

        # builders from entrypoints
        for epoint in Environment.current().entrypoints[REPOSITORIES_ENTRYPOINT_GROUP]:
            try:
                builder: RepositoryBuilder = epoint.ref.import_object()()
                if not isinstance(builder, RepositoryBuilder):
                    raise ValueError("repositories entrypoint did not point to a repository builder class")
            except Exception:  # noqa
                import traceback
                print(f"malformed repository entrypoint: {epoint}")
                traceback.print_exc()

        self._etc_chain = etc
        self._main = self.load_for_context('main', None, None)

    @property
    def main(self) -> Repository:
        return self._main

    def _load_configuration_chain(self, context_path: Optional[Path]) -> Tuple[List[Repository], Dict[str, Repository]]:
        package_search_list = [self.pypi]
        package_associated_repo = {}
        opened_repository_names = set()

        etc_chain = self._etc_chain.config_chain(context_path, REPOSITORIES_CFG) \
            if context_path else [self._etc_chain.main_config(REPOSITORIES_CFG)]

        for link in etc_chain:
            config = RepositoriesConfiguration.load(link)
            for definition in config.repositories:
                if definition.name in opened_repository_names:
                    continue
                opened_repository_names.add(definition.name)
                instance = self.build(definition)

                if definition.type == 'pypi' and package_search_list[0].name == 'pypi':
                    package_search_list.pop(0)

                if definition.packages:
                    for package in definition.packages:
                        put_if_absent(package_associated_repo, package, instance)
                else:
                    package_search_list.append(instance)

        return package_search_list, package_associated_repo

    def load_for_context(self, name: str, context_path: Optional[Path],
                         context: Union[Project, ProjectGroup, None]) -> Repository:
        package_search_list, package_associated_repo = self._load_configuration_chain(context_path)

        projects_in_path = []
        if isinstance(context, Project):
            projects_in_path = context.group.project_children_recursive if context.group else [context]
        elif isinstance(context, ProjectGroup):
            projects_in_path = context.project_children_recursive

        if projects_in_path:
            repo = _ProjectsInContextRepository("projects under context", projects_in_path)
            for project in projects_in_path:
                package_associated_repo[project.name] = repo

        return _ContextualRepository(name, self._url_repos, package_search_list, package_associated_repo, context)

    def build(self, config: RepositoryInstanceConfig) -> Repository:
        if not (cached := self._cached_instances.get(config)):
            if not (builder := self._builders.get(config.type)):
                raise KeyError(f"unknown repository type: {config.type}")
            cached = builder.build(config.name, config.packages, **config.args)
            self._cached_instances[config] = cached

        return cached


class RepositoriesConfiguration(TomlFileConfiguration):
    repositories: List[RepositoryInstanceConfig]

    @computed_based_on("")
    def repositories(self) -> List[RepositoryInstanceConfig]:
        return [RepositoryInstanceConfig.from_config(name, repo) for name, repo in self.items()]


@dataclass(frozen=True, eq=True)
class RepositoryInstanceConfig:
    type: str
    packages: Optional[List[str]]
    name: Optional[str]
    args: Dict[str, Any]

    def to_config(self) -> Dict[str, Any]:
        return remove_none_values({
            **self.args,
            'type': self.type,
            'packages': self.packages,
        })

    @classmethod
    def from_config(cls, name: str, config: Dict[str, Any]) -> "RepositoryInstanceConfig":
        config = copy(config)
        type_ = config.pop('type')
        packages: Optional[List[str]] = config.pop('packages', None)
        args = config
        return RepositoryInstanceConfig(type_, packages, name, args)


class _ContextualRepository(AbstractRepository):
    def __init__(
            self, name: str, url_handlers: Dict[str, Repository], package_search_list: List[Repository],
            package_associated_repos: Dict[str, Repository], context: Optional[Any]):
        super().__init__(name)

        self._url_handlers = url_handlers
        self._package_search_list = package_search_list
        self._package_associated_repos = package_associated_repos
        self._context = context

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if url := dependency.version_spec.specific_url():

            if protocol := url.protocol:
                if repo := self._url_handlers.get(url.protocol):
                    return repo.match(dependency, False)
                raise NoSuchElementException(f"could not find repository to handle url with protocol: {protocol}")
            return self._url_handlers['url'].match(dependency, False)

        if repo := self._package_associated_repos.get(dependency.package_name):
            return repo.match(dependency, False)

        for repo in self._package_search_list:
            if result := repo.match(dependency, False):
                return result

        return []

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        if isinstance(self._context, Project):
            return self._context.lock.sort_packages_by_lock_preference(self._context.attached_environment, packages)
        return super()._sort_by_priority(dependency, packages)


class _ProjectsInContextRepository(AbstractRepository):
    def __init__(self, name: str, projects: List[Project]):
        super().__init__(name)
        self._packages = {
            p.name: p for p in projects
        }

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if (project := self._packages.get(dependency.package_name)) and \
                dependency.version_spec.allows_version(project.version):
            return [project]
        return []

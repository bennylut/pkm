from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple, Iterable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package
from pkm.api.projects.project import Project
from pkm.api.projects.project_group import ProjectGroup
from pkm.api.repositories.repository import Repository, RepositoryBuilder
from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.config.etc_chain import EtcChain
from pkm.utils.dicts import remove_none_values, put_if_absent
from pkm.utils.http.http_client import HttpClient
from pkm.utils.iterators import partition

REPOSITORIES_ENTRYPOINT_GROUP = "pkm.repositories"
REPOSITORIES_CFG = "repositories.toml"


class RepositoryLoader:
    def __init__(self, etc: EtcChain, http: HttpClient, workspace: Path):

        from pkm.api.projects.project_group import ProjectGroupRepositoryBuilder
        from pkm.api.repositories.local_packages_repository import LocalPackagesRepositoryBuilder
        from pkm.api.environments.environment import Environment
        from pkm.api.repositories.simple_repository import SimpleRepositoryBuilder
        from pkm.api.repositories.git_repository import GitRepository
        from pkm.api.repositories.pypi_repository import PyPiRepository

        # base repositories
        self.pypi = PyPiRepository(http)

        url_repos = [
            GitRepository(workspace / 'git')
        ]

        # common builders
        self._builders = {
            b.name: b for b in (
                SimpleRepositoryBuilder(http),
                LocalPackagesRepositoryBuilder(),
                ProjectGroupRepositoryBuilder()
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
        self._main = _MainRepository(
            self, url_repos, RepositoriesConfiguration.load(etc.main_config(REPOSITORIES_CFG)).repositories)

    @property
    def main(self) -> Repository:
        return self._main

    def load(self, name: str, context_path: Path, context: Union[Project, ProjectGroup, None]) -> Repository:
        config_files = self._etc_chain.config_chain(context_path, REPOSITORIES_CFG, include_main=False)
        instances: Dict[str, RepositoryInstanceConfig] = {}
        for file in config_files:
            for instance in RepositoriesConfiguration.load(file).repositories:
                put_if_absent(instances, instance.name, instance)

        projects_in_path = []
        if isinstance(context, Project):
            projects_in_path = context.group.project_children_recursive if context.group else [context]
        elif isinstance(context, ProjectGroup):
            projects_in_path = context.project_children_recursive

        return _ContextualRepository(name, projects_in_path, self._main, self, instances.values(), context)

    def build(self, config: RepositoryInstanceConfig) -> Repository:
        if not (builder := self._builders.get(config.type)):
            raise KeyError(f"unknown repository type: {config.type}")
        return builder.build(config.name, config.packages, **config.args)


def _build_instances(
        loader: RepositoryLoader, default: Repository, instances: Iterable[RepositoryInstanceConfig]
) -> Tuple[Repository, List[Tuple[RepositoryInstanceConfig, Repository]]]:
    non_default: List[Tuple[RepositoryInstanceConfig, Repository]] = []
    for i in instances:
        non_default.append((i, loader.build(i)))

    defaultabls, non_default = partition(non_default, lambda x: '*' in x[0].packages)
    if defaultabls:
        default = defaultabls[-1]

    return default, non_default


class RepositoriesConfiguration(TomlFileConfiguration):
    repositories: List[RepositoryInstanceConfig]

    @computed_based_on("")
    def repositories(self) -> List[RepositoryInstanceConfig]:
        return [RepositoryInstanceConfig.from_config(name, repo) for name, repo in self.items()]


@dataclass(frozen=True, eq=True)
class RepositoryInstanceConfig:
    type: str
    packages: Dict[str, Any]
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
        packages: List[Union[str, Dict]] = config.pop('packages')

        packages_dict = {}

        if packages == "*":
            packages_dict['*'] = {}
        else:
            for package in packages:
                if isinstance(package, str):
                    packages_dict[package] = {}
                else:
                    packages_dict[package['name']] = package

        args = config
        return RepositoryInstanceConfig(type_, packages_dict, name, args)


class _MainRepository(Repository):
    def __init__(self, loader: RepositoryLoader, url_repos: List[Repository],
                 defined_instances: List[RepositoryInstanceConfig]):

        super().__init__("main")

        default, non_default = _build_instances(loader, loader.pypi, defined_instances)

        self._default_repo = default
        self._url_repos = {r.name: r for r in url_repos}
        self.package_to_repo: Dict[str, Repository] = {
            package_name: repository
            for repository_config, repository in non_default
            for package_name in repository_config.packages.keys()
        }

    def _repository_for(self, d: Dependency) -> Repository:
        if url := d.version_spec.specific_url():
            if url.protocol and (repo := self._url_repos.get(url.protocol)):
                return repo
            return self._url_repos['url']

        return self.package_to_repo.get(d.package_name, self._default_repo)

    def _do_match(self, dependency: Dependency) -> List[Package]:
        return self._repository_for(dependency).match(dependency, False)


class _ContextualRepository(Repository):

    def __init__(self, name: str, projects_in_path: List[Project], main: _MainRepository,
                 loader: RepositoryLoader, defined_instances: Iterable[RepositoryInstanceConfig], ctx: Any):

        super().__init__(name)

        projects_in_path_packages = {
            p.name: {'path': str(p.path.absolute()), 'name': p.name, 'version': str(p.version)}
            for p in projects_in_path
        }

        self._path_repo: Repository = loader.build(
            RepositoryInstanceConfig('local', projects_in_path_packages, 'project-group', {}))

        default, non_default = _build_instances(loader, main, defined_instances)
        self._default_repo = default
        self.package_to_repo: Dict[str, Repository] = {
            package_name: repository
            for repository_config, repository in non_default
            for package_name in repository_config.packages.keys()
        }
        self._context = ctx

    def _repository_for(self, d: Dependency) -> Repository:
        return self.package_to_repo.get(d.package_name, self._default_repo)

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if dependency.version_spec.specific_url():
            return self._default_repo.match(dependency, False)

        if (gr := self._path_repo) and (gpacs := gr.match(dependency, False)):
            return gpacs

        return self._repository_for(dependency).match(dependency, False)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        if isinstance(self._context, Project):
            return self._context.lock.sort_packages_by_lock_preference(self._context.attached_environment, packages)
        return super()._sort_by_priority(dependency, packages)

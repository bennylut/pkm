from __future__ import annotations

from copy import copy
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package
from pkm.api.repositories.repository import Repository, RepositoryBuilder
from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.utils.dicts import remove_none_values
from pkm.utils.http.http_client import HttpClient
from pkm.utils.iterators import first_or_none

REPOSITORIES_ENTRYPOINT_GROUP = "pkm.repositories"


class RepositoryLoader:
    def __init__(self, config: RepositoriesConfiguration,
                 http: HttpClient, workspace: Path):

        from pkm.api.projects.project_group import ProjectGroupRepositoryBuilder
        from pkm.api.repositories.local_packages_repository import LocalPackagesRepositoryBuilder
        from pkm.api.environments.environment import Environment
        from pkm.api.repositories.simple_repository import SimpleRepositoryBuilder
        from pkm.api.repositories.git_repository import GitRepository
        from pkm.api.repositories.pypi_repository import PyPiRepository

        # base repositories
        self.pypi = default = PyPiRepository(http)

        url_repos = [
            GitRepository(workspace / 'git')
        ]

        # builders | TODO: load more using entry-points
        self._builders = {
            b.name: b for b in (
                SimpleRepositoryBuilder(http),
                LocalPackagesRepositoryBuilder(),
                ProjectGroupRepositoryBuilder()
            )
        }

        # load builders from entrypoints
        for epoint in Environment.current().entrypoints[REPOSITORIES_ENTRYPOINT_GROUP]:
            try:
                builder: RepositoryBuilder = epoint.ref.import_object()()
                if not isinstance(builder, RepositoryBuilder):
                    raise ValueError("repositories entrypoint did not point to a repository builder class")
            except Exception: # noqa
                import traceback
                print(f"malformed entrypoint: {epoint}")
                traceback.print_exc()

        # instances
        instances: List[Tuple[RepositoryInstanceConfig, Repository]] = [
            (cfg, self.load(cfg)) for cfg in config.repositories
        ]

        if default_instance := first_or_none(i for i in instances if '*' in i[0].packages):
            instances.remove(default_instance)
            default = default_instance[1]

        self._main = _MainRepository(default, url_repos, instances)

    @property
    def main(self) -> Repository:
        return self._main

    def load(self, config: RepositoryInstanceConfig) -> Repository:
        if not (builder := self._builders.get(config.type)):
            raise KeyError(f"unknown repository type: {config.type}")
        return builder.build(config.name, config.packages, **config.args)


class RepositoriesConfiguration(TomlFileConfiguration):
    repositories: List[RepositoryInstanceConfig]

    @computed_based_on("repos")
    def repositories(self) -> List[RepositoryInstanceConfig]:
        return [RepositoryInstanceConfig.from_config(it) for it in (self["repos"] or [])]


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
            'name': self.name
        })

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "RepositoryInstanceConfig":
        config = copy(config)
        type_ = config.pop('type')
        name = config.pop('name', None)
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
    def __init__(self, default_repo: Repository, url_repos: List[Repository],
                 package_specific_repos: List[Tuple[RepositoryInstanceConfig, Repository]]):
        super().__init__("main")

        self._default_repo = default_repo
        self._url_repos = {r.name: r for r in url_repos}
        self.package_to_repo: Dict[str, Repository] = {
            package_name: repository
            for repository_config, repository in package_specific_repos
            for package_name in repository_config.packages.keys()
        }

    def _repository_for(self, d: Dependency) -> Repository:
        if d.is_url_dependency:
            url = d.url
            if url.repository_protocol and (repo := self._url_repos.get(url.repository_protocol)):
                return repo
            return self._url_repos['url']

        return self.package_to_repo.get(d.package_name, self._default_repo)

    def _do_match(self, dependency: Dependency) -> List[Package]:
        return self._repository_for(dependency).match(dependency, False)

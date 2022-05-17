from __future__ import annotations

import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Iterable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package
from pkm.api.repositories.repositories_configuration import RepositoryInstanceConfig, RepositoriesConfiguration, \
    RepositoriesConfigInheritanceMode
from pkm.api.repositories.repository import Repository, RepositoryBuilder, AbstractRepository
from pkm.repositories.file_repository import FileRepository
from pkm.utils.dicts import put_if_absent
from pkm.utils.http.http_client import HttpClient

REPOSITORIES_EXTENSIONS_ENTRYPOINT_GROUP = "pkm-repositories"
REPOSITORIES_CONFIGURATION_PATH = "etc/pkm/repositories.toml"


class RepositoryLoader:
    def __init__(self, main_cfg: Path, http: HttpClient, workspace: Path):

        from pkm.api.environments.environment import Environment
        from pkm.repositories.simple_repository import SimpleRepositoryBuilder
        from pkm.repositories.git_repository import GitRepository
        from pkm.repositories.pypi_repository import PyPiRepository
        from pkm.repositories.local_packages_repository import LocalPackagesRepositoryBuilder
        from pkm.repositories.url_repository import UrlRepository

        # common builders
        self._builders = {
            b.name: b for b in (
                SimpleRepositoryBuilder(http),
                LocalPackagesRepositoryBuilder(),
            )
        }

        self.pypi = PyPiRepository(http)
        base_repositories = [
            self.pypi, GitRepository(workspace / 'git'), UrlRepository(), FileRepository()]

        # builders from entrypoints
        for epoint in Environment.current().entrypoints[REPOSITORIES_EXTENSIONS_ENTRYPOINT_GROUP]:
            try:
                ext: RepositoriesExtension = epoint.ref.import_object()()
                if not isinstance(ext, RepositoriesExtension):
                    raise ValueError("repositories entrypoint did not provide to a RepositoriesExtension class")

                for builder in ext.builders:
                    self._builders[builder.name] = builder

                base_repositories.extend(ext.instances)

            except Exception:  # noqa
                import traceback
                warnings.warn(f"malformed repository entrypoint: {epoint}")
                traceback.print_exc()

        base = _CompositeRepository('base', base_repositories, {})

        self._cached_instances: Dict[RepositoryInstanceConfig, Repository] = {}  # noqa

        self._main = self.load('main', RepositoriesConfiguration.load(main_cfg), base)
        self.workspace = workspace

    @property
    def main(self) -> Repository:
        return self._main

    def load(self, name: str, config: RepositoriesConfiguration, next_in_context: Repository) -> Repository:
        package_search_list = []
        package_associated_repo = {}

        if not (new_repos := config.repositories):
            if config.inheritance_mode == RepositoriesConfigInheritanceMode.INHERIT_MAIN:
                return self.main
            return next_in_context

        for definition in new_repos:
            print(f"DBG: building instance by definition {definition}")
            instance = self.build(definition)

            if definition.packages:
                for package in definition.packages:
                    if package == '*':
                        package_search_list.append(instance)
                    else:
                        put_if_absent(package_associated_repo, package, instance)
            else:
                package_search_list.append(instance)

        if config.inheritance_mode == RepositoriesConfigInheritanceMode.INHERIT_CONTEXT:
            package_search_list.append(next_in_context)
        elif config.inheritance_mode == RepositoriesConfigInheritanceMode.INHERIT_MAIN:
            package_search_list.append(self.main)

        return _CompositeRepository(name, package_search_list, package_associated_repo)

    def build(self, config: RepositoryInstanceConfig) -> Repository:
        if not (cached := self._cached_instances.get(config)):
            if not (builder := self._builders.get(config.type)):
                raise KeyError(f"unknown repository type: {config.type}")
            cached = builder.build(config.name, config.packages, **config.args)
            self._cached_instances[config] = cached

        return cached


class _CompositeRepository(AbstractRepository):
    def __init__(
            self, name: str, package_search_list: List[Repository],
            package_associated_repos: Dict[str, Repository]):
        super().__init__(name)

        self._url_handlers: Dict[str, List[Repository]] = defaultdict(list)
        self._package_search_list = []

        for repo in package_search_list:
            if repo.accept_non_url_packages():
                self._package_search_list.append(repo)
            for protocol in repo.accepted_url_protocols():
                self._url_handlers[protocol].append(repo)

        self._package_associated_repos = package_associated_repos

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:

        if url := dependency.required_url():
            for repo in self._url_handlers[url.protocol]:
                if match := repo.match(dependency, env):
                    return match
            raise []

        if repo := self._package_associated_repos.get(dependency.package_name):
            return repo.match(dependency, env)

        for repo in self._package_search_list:
            if result := repo.match(dependency, env):
                return result

        return []

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        return packages

    def accepted_url_protocols(self) -> Iterable[str]:
        return self._url_handlers.keys()


@dataclass
class RepositoriesExtension:
    builders: List[RepositoryBuilder] = field(default_factory=list)
    instances: List[Repository] = field(default_factory=list)

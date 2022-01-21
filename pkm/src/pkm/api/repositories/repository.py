from abc import abstractmethod, ABC
from base64 import b64encode
from dataclasses import dataclass
from io import UnsupportedOperation
from pathlib import Path
from typing import List, Union, Optional, Tuple, Dict, Any

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import Package
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor
from pkm.api.versions.version_specifiers import AnyVersion
from pkm.utils.iterators import partition
from pkm.utils.monitors import no_monitor


class Repository(ABC):

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def accepts(self, dependency: Dependency) -> bool:
        """
        :param dependency: the dependency to check 
        :return: true if this repository knows how to handle the given `dependency`.
                 e.g., pypi does not know how to handle local file dependency
        """
        return not dependency.is_url_dependency

    @abstractmethod
    def _do_match(self, dependency: Dependency, *, monitor: RepositoryOperationsMonitor) -> List[Package]:
        """
        IMPLEMENTATION NOTICE:
            do not try to filter pre-releases,
            it is handled for you in the `match` method that call this one.

        :param dependency: the dependency to match
        :param monitor: monitor for this operation
        :return: list of all the packages in this repository that match the given `dependency`,
        """

    def match(self, dependency: Union[Dependency, str], check_prereleases: bool = True, *,
              monitor: RepositoryOperationsMonitor = no_monitor()) -> List[Package]:
        """
        :param dependency: the dependency to match (or a pep508 string representing it)
        :param check_prereleases: whether or not to check pre-releases according to pep440 rules.
              if True, will only output pre-releases if the dependency version specifier is a
              pre-release or all the versions matching the dependency are pre-releases.
              Otherwise, will output all pre-releases matching the dependency
        :param monitor: monitor for this operation

        :return: list of all the packages in this repository that match the given `dependency`
        """

        if isinstance(dependency, str):
            dependency = Dependency.parse_pep508(dependency)

        matched = self._do_match(dependency, monitor=monitor)
        filtered = self._filter_prereleases(matched, dependency) if check_prereleases else matched
        return self._sort_by_priority(dependency, filtered)

    def _filter_prereleases(self, packages: List[Package], dependency: Dependency) -> List[Package]:
        if dependency.version_spec.allows_pre_or_dev_releases():
            return packages
        pre_release, rest = partition(packages, lambda it: it.version.is_pre_or_dev_release())
        return rest or packages

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        """
        sorts `matches` by the required priority
        :param dependency: the dependency that resulted in the given `packages`
        :param packages: the packages that were the result `_do_match(dependency)`
        :return: sorted packages by priority (first is more important than last)
        """
        packages.sort(key=lambda it: it.version, reverse=True)
        return packages

    def list(self, package_name: str) -> List[Package]:
        """
        :param package_name: the package to match 
        :return: list of all the packages that match the given `package_name`
        """
        dependency = Dependency(package_name, AnyVersion)
        if self.accepts(dependency):
            return self.match(dependency)
        raise UnsupportedOperation(f"Repository ({self.name}) does not support listing")

    @property
    def publisher(self) -> Optional["RepositoryPublisher"]:
        """
        :return: if this repository is 'publishable' returns its publisher
        """
        return None


class DelegatingRepository(Repository):

    def __init__(self, repo: Repository):
        super().__init__(repo.name)
        self._repo = repo

    def accepts(self, dependency: Dependency) -> bool:
        return self._repo.accepts(dependency)

    def _do_match(self, dependency: Dependency, *, monitor: RepositoryOperationsMonitor) -> List[Package]:
        return self._repo._do_match(dependency, monitor=monitor)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        return self._repo._sort_by_priority(dependency, packages)

    def _filter_prereleases(self, packages: List[Package], dependency: Dependency) -> List[Package]:
        return self._repo._filter_prereleases(packages, dependency)

    @property
    def publisher(self) -> Optional["RepositoryPublisher"]:
        return self._repo.publisher


class RepositoryPublisher:
    def __init__(self, repository_name: str):
        self.repository_name = repository_name

    # noinspection PyMethodMayBeStatic
    def required_authentication_fields(self) -> List[str]:
        return ['username', 'password']

    @abstractmethod
    def register(self, auth: "Authentication", package_meta: PackageMetadata):
        """
        registers the given package into the repository
         :param auth: authentication object filled with the fields that were
                     returned by the method `required_authentication_fields`
        :param package_meta: metadata for the package that we want to register
        """

    @abstractmethod
    def publish(self, auth: "Authentication", package_meta: PackageMetadata, distribution: Path):
        """
        publish a `distribution` belonging to the given `package_meta` into the repository,
        raise `RegistrationRequiredException` if the package needs to be registered first
        :param auth: authentication object filled with the fields that were
                     returned by the method `required_authentication_fields`
        :param package_meta: metadata for the package that this distribution belongs to
        :param distribution: the distribution archive (e.g., wheel, sdist)
        """


class RegistrationRequiredException(Exception):
    ...


@dataclass(frozen=True, eq=True)
class Authentication:
    username: str
    password: str

    def as_basic_auth_header(self) -> Tuple[str, str]:
        return 'Authorization', f'Basic {b64encode(f"{self.username}:{self.password}".encode()).decode("ascii")}'


class RepositoryBuilder(ABC):

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def build(self, name: Optional[str], package_settings: Dict[str, Any],
              **kwargs: Any) -> Repository:
        """
        build a new repository instance using the given `kwargs`
        :param name: name for the created repository
        :param package_settings: for each required package, its settings object as provided by the user
        :param kwargs: arguments for the instance creation, may be defined by derived classes
        :return: the created instance
        """

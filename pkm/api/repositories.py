from abc import abstractmethod, ABC
from io import UnsupportedOperation
from typing import List, Union

from pkm.api.packages import Dependency, Package
from pkm.api.versions.version_specifiers import AnyVersion
from pkm.utils.iterators import partition


class Repository(ABC):

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def accepts(self, dependency: Dependency) -> bool:
        """
        :param dependency: the dependency to check 
        :return: true if this repository knows how to handle the given [dependency]. 
                 e.g., pypi does not know how to handle local file dependency
        """
        ...

    @abstractmethod
    def _do_match(self, dependency: Dependency) -> List[Package]:
        """
        IMPLEMENTATION NOTICE:
            do not try to filter pre-releases,
            it is handled for you in the [match] method that call this one.

        :param dependency: the dependency to match
        :return: list of all the packages in this repository that match the given [dependency],
        """

    def match(self, dependency: Union[Dependency, str], check_prereleases: bool = True) -> List[Package]:
        """
        :param dependency: the dependency to match (or a pep508 string representing it)
        :param check_prereleases: whether or not to check pre-releases according to pep440 rules.
              if True, will only output pre-releases if the dependency version specifier is a 
              pre-release or all the versions matching the dependency are pre-releases.
              Otherwise, will output all pre-releases matching the dependency
                                     
        :return: list of all the packages in this repository that match the given [dependency]
        """

        if isinstance(dependency, str):
            dependency = Dependency.parse_pep508(dependency)

        matched = self._do_match(dependency)
        return self._filter_prereleases(matched, dependency) if check_prereleases else matched

    def _filter_prereleases(self, packages: List[Package], dependency: Dependency) -> List[Package]:
        if dependency.version_spec.allows_pre_or_dev_releases():
            return packages
        pre_release, rest = partition(packages, lambda it: it.version.is_pre_or_dev_release())
        return rest or packages

    def list(self, package_name: str) -> List[Package]:
        """
        :param package_name: the package to match 
        :return: list of all the packages that match the given [package_name]
        """
        dependency = Dependency(package_name, AnyVersion)
        if self.accepts(dependency):
            return self.match(dependency)
        raise UnsupportedOperation(f"Repository ({self.name}) does not support listing")

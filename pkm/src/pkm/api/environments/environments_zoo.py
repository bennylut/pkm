from abc import ABC, abstractmethod
from typing import Optional, Literal, Iterator, Union

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version


class EnvironmentsZoo(ABC):

    @abstractmethod
    def create_environment(self, name: str, python: Union[Dependency, str]) -> "ManagedEnvironment":
        """
        creates a new managed environment in this zoo
        :param name: name for the environment
        :param python: the interpreter version the new environment depends on (if str is given - parsed by pep508)
        :return: the created environment
        """

    @abstractmethod
    def create_application_environment(
            self, application: Union[str, Dependency], repository: Repository, name: Optional[str] = None,
            python: Optional[Union[str, Dependency]] = None) -> "ManagedEnvironment":
        """

        :param application: the application that the environment is created for (if str is given - parsed by pep508)
        :param repository: the repository to use to install the given application
        :param name: if supplied, the name of the environment if not supplied, the name: '<app>'
        :param python:  the interpreter version the new environment depends on (if none, will try to find the most
                        suitable version for this application in the system) (if str is given - parsed by pep508)
        :return: the created environment
        """

    @abstractmethod
    def list(self, match: Literal['application', 'general', 'all'] = 'all') -> Iterator["ManagedEnvironment"]:
        """
        :param match: filters the list, if =='application' return only application environments, if =='general'
                      return only non-application environments and finally if =='all' return both
        :return: iterator iterating over the requested environments that exists in this zoo
        """

    @abstractmethod
    def load_environment(self, name: str, application: bool) -> "ManagedEnvironment":
        """
        :param name: a name of an environment that exists in this zoo
        :param application: if ==true search for application environment with this name
                            otherwise search for regular environment
        :return: the loaded environment
        """


class ManagedEnvironment(ABC):

    @property
    @abstractmethod
    def environment(self) -> Environment:
        """
        :return: the environment managed by this instance
        """

    @property
    @abstractmethod
    def application(self) -> Optional[Dependency]:
        """
        :return: the application this environment created for (or none if it is a general environment)
        """
        ...

    @property
    def installed_application_version(self) -> Optional[Version]:
        """
        :return: the application version that is actually installed in this environment
                 (or none if it is a general environment / the application is not yet installed)
        """

        if app := self.application:
            return self.environment.site_packages.installed_package(app.package_name).version
        return None

    def is_application(self) -> bool:
        """
        :return: true if this is an application managed environment and false otherwise
        """
        return self.application is not None

    @abstractmethod
    def delete(self):
        """
        deletes the environment managed by this instance
        :return:
        """

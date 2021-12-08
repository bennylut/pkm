from abc import ABC, abstractmethod
from typing import Optional, List

from pkm.api.dependencies.env_markers import PEP508EnvMarkerParser, EnvironmentMarker
from pkm.api.environments import Environment
from pkm.api.versions.version_parser import VersionParser
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion
from pkm.utils.commons import unone
from pkm.utils.parsing import SimpleParser


class Dependency:

    def __init__(self, package_name: str, extras: Optional[List[str]] = None,
                 env_marker: Optional[EnvironmentMarker] = None):
        self.package_name = package_name
        self.extras = unone(extras, list)
        self.env_marker = env_marker

    def is_applicable_for(self, env: Environment, extras: List[str]) -> bool:
        return self.env_marker is None or self.env_marker.evaluate_on(env, extras)

    @classmethod
    def parse_pep508(cls, text: str) -> "Dependency":
        return PEP508DependencyParser(text).read_dependency()


class RepositoryDependency(Dependency):

    def __init__(self, package_name: str, version_spec: VersionSpecifier, repository: str = 'pypi',
                 extras: Optional[List[str]] = None,
                 env_marker: Optional[EnvironmentMarker] = None):
        super().__init__(package_name, extras, env_marker)
        self.version_spec = version_spec
        self.repository = repository

    def __repr__(self):
        estr = str(self.extras) if self.extras else ''
        mstr = f"; {self.env_marker}" if self.env_marker else ''
        rstr = f"[{self.repository}] " if self.repository != 'pypi' else ''
        return f"{rstr}{self.package_name}{estr} {self.version_spec}{mstr}"


class UrlDependency(Dependency):

    def __init__(self, package_name: str, url: str,
                 extras: Optional[List[str]] = None,
                 env_marker: Optional[EnvironmentMarker] = None):
        super().__init__(package_name, extras, env_marker)
        self.url = url


class PEP508DependencyParser(SimpleParser):

    def _read_extras(self) -> List[str]:
        self.match_or_err('[', 'expecting extras start ([)')
        extras: List[str] = []

        while self.is_not_empty():
            self.read_ws()
            extras.append(self._read_identifier())
            self.read_ws()
            if not self.match(','):
                break

        self.match_or_err(']', 'expecting extras end (])')

        return extras

    def _read_version_spec(self) -> VersionSpecifier:
        return self.subparser(VersionParser).read_specifier()

    def _read_identifier(self) -> str:
        if self.peek().isalpha():
            return self.until(lambda i, t: not t[i].isalnum() and t[i] not in '_-.')
        self.raise_err('expecting identifier')

    def read_emarker(self) -> EnvironmentMarker:
        return self.subparser(PEP508EnvMarkerParser).read_marker()

    def read_dependency(self) -> Dependency:
        self.read_ws()
        package_name = self._read_identifier()
        self.read_ws()

        extras: Optional[List[str]] = None
        if self.peek() == '[':
            extras = self._read_extras()
            self.read_ws()

        url: Optional[str] = None
        if self.match('@'):
            self.read_ws()
            url = self.read_url()
            self.read_ws()

        version_spec: Optional[VersionSpecifier] = None if url else AnyVersion
        if not url and self.peek() != ';':
            version_spec = self._read_version_spec()
            self.read_ws()

        env_marker: Optional[EnvironmentMarker] = None
        if self.match(";", '') and self.is_not_empty():
            env_marker = self.read_emarker()

        if version_spec:
            return RepositoryDependency(
                package_name, version_spec, extras=extras, env_marker=env_marker)

        return UrlDependency(package_name, url, extras=extras, env_marker=env_marker)

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any

from pkm.api.dependencies.env_markers import PEP508EnvMarkerParser, EnvironmentMarker
from pkm.api.environments import Environment
from pkm.api.versions.version_parser import VersionParser
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion
from pkm.utils.commons import unone
from pkm.utils.parsing import SimpleParser


class Dependency:

    def __init__(self, package_name: str,
                 version_spec: VersionSpecifier = AnyVersion,
                 extras: Optional[List[str]] = None,
                 env_marker: Optional[EnvironmentMarker] = None):
        self.package_name = package_name
        self.extras = extras
        self.env_marker = env_marker
        self.version_spec = version_spec

    def is_applicable_for(self, env: Environment, extras: List[str]) -> bool:
        return self.env_marker is None or self.env_marker.evaluate_on(env, extras or [])

    def write(self) -> Dict[str, Any]:
        return _without_none_values({
            'type': 'basic',
            'package': self.package_name,
            'version_spec': str(self.version_spec),

            'extras': self.extras,
            'env_marker': str(self.env_marker) if self.env_marker else None,
        })

    @classmethod
    def read_pep508(cls, text: str) -> "Dependency":
        return PEP508DependencyParser(text).read_dependency()

    @classmethod
    def _read_ex(cls, data: Dict[str, Any],
                 package: str,
                 version_spec: VersionSpecifier,
                 extras: Optional[List[str]],
                 env_marker: Optional[EnvironmentMarker]) -> "Dependency":

        return Dependency(package, version_spec, extras=extras, env_marker=env_marker)

    @classmethod
    def read(cls, data: Dict[str, Any]):
        type = data['type']
        package = data['package']
        vspec = VersionSpecifier.parse(data['version_spec'])
        extras = data['extras']
        env_marker = EnvironmentMarker.parse_pep508(data['env_marker']) if 'env_marker' in data else None

        if type == 'basic':
            dependency_cls = Dependency
        elif type == 'url':
            dependency_cls = UrlDependency
        else:
            raise KeyError(f"unknown dependency type: {type}")

        return dependency_cls._read_ex(data, package, vspec, extras, env_marker)


class UrlDependency(Dependency):

    def __init__(self, package_name: str, url: str,
                 extras: Optional[List[str]] = None,
                 env_marker: Optional[EnvironmentMarker] = None):
        super().__init__(package_name, AnyVersion, extras, env_marker)
        self.url = url

    def write(self) -> Dict[str, Any]:
        return {
            **super().write(),
            'type': 'url',
            'url': self.url
        }

    @classmethod
    def _read_ex(cls, data: Dict[str, Any],
                 package: str,
                 version_spec: VersionSpecifier,
                 extras: Optional[List[str]],
                 env_marker: Optional[EnvironmentMarker]) -> "Dependency":
        return UrlDependency(package, data['url'], extras, env_marker)


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
            return Dependency(package_name, version_spec, extras=extras, env_marker=env_marker)

        return UrlDependency(package_name, url, extras=extras, env_marker=env_marker)


def _without_none_values(d: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in dict(d):
        if v is None:
            del d[k]

    return d

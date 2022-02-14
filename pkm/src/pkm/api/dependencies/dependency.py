from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, TYPE_CHECKING

from pkm.api.dependencies.env_markers import PEP508EnvMarkerParser, EnvironmentMarker
from pkm.api.packages.package import PackageDescriptor
from pkm.api.versions.version import NamedVersion, Version
from pkm.api.versions.version_parser import VersionParser
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion, SpecificVersion, VersionUrl
from pkm.utils.parsers import SimpleParser
from pkm.utils.properties import cached_property
import re

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment


@dataclass(frozen=True, eq=True)
class Dependency:
    package_name: str
    version_spec: VersionSpecifier = AnyVersion
    extras: Optional[List[str]] = None
    env_marker: Optional[EnvironmentMarker] = None
    is_url_dependency: str = False

    def is_applicable_for(self, env: "Environment", extras: List[str]) -> bool:
        return self.env_marker is None or self.env_marker.evaluate_on(env, extras or [])

    @cached_property
    def url(self) -> Optional[VersionUrl]:

        if self.is_url_dependency:
            if isinstance(self.version_spec, SpecificVersion) \
                    and isinstance(self.version_spec.version, NamedVersion):
                return VersionUrl.parse(self.version_spec.version.name)
            raise ValueError("malformed url dependency")

        return None

    def __str__(self):
        extras_str = f"[{','.join(self.extras)}]" if self.extras else ''

        if url := self.url:
            version_str = f"@{url}"
        else:
            version_str = str(self.version_spec)

        marker_str = f";{self.env_marker}" if self.env_marker else ''

        return f"{self.package_name}{extras_str} {version_str}{marker_str}"

    def __repr__(self):
        return f"Dependency({self})"

    @classmethod
    def parse_pep508(cls, text: str) -> "Dependency":
        return PEP508DependencyParser(text).read_dependency()


class PEP508DependencyParser(SimpleParser):

    def _read_extras(self) -> List[str]:
        self.match_or_err('[', 'expecting extras start ([)')
        extras: List[str] = []

        while self.is_not_empty():
            self.match_ws()
            extras.append(self._read_identifier())
            self.match_ws()
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
        self.match_ws()
        package_name = PackageDescriptor.normalize_name(self._read_identifier())
        self.match_ws()

        extras: Optional[List[str]] = None
        if self.peek() == '[':
            extras = self._read_extras()
            self.match_ws()

        url: Optional[str] = None
        if self.match('@'):
            self.match_ws()
            url = self.until(lambda i, s: s[i].isspace())
            self.match_ws()

        version_spec: Optional[VersionSpecifier] = None if url else AnyVersion
        if not url and self.peek() != ';':
            version_spec = self._read_version_spec()
            self.match_ws()

        env_marker: Optional[EnvironmentMarker] = None
        if self.match(";", '') and self.is_not_empty():
            env_marker = self.read_emarker()

        return Dependency(package_name, version_spec or SpecificVersion(NamedVersion(url)), extras=extras,
                          env_marker=env_marker, is_url_dependency=url is not None)

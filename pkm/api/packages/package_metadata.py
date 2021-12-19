from email.message import EmailMessage
from email.parser import Parser
from pathlib import Path
from typing import List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.versions.version import StandardVersion, Version
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion
from pkm.config.configuration import FileConfiguration, computed_based_on
from pkm.utils.dicts import get_or_put

_MULTI_FIELDS = {
    'Provides-Extra', 'Platform', 'Supported-Platform', 'Classifier', 'Requires-Dist', 'Provides-Dist',
    'Obsoletes-Dist', 'Requires-External', 'Project-URL'
}


class PackageMetadata(FileConfiguration):
    """implementation of the package metadata 2.1 specification as described in pep 566"""

    @computed_based_on("Metadata-Version")
    def metadata_version(self) -> StandardVersion:
        return StandardVersion.parse(self['Metadata-Version'])

    @property
    def package_name(self) -> str:
        return self['Name']

    @computed_based_on("Version")
    def package_version(self) -> Version:
        return Version.parse(self['Version'])

    @computed_based_on("Requires-Dist")
    def dependencies(self) -> List[Dependency]:
        requires_dist = self["Requires-Dist"] or []
        return [Dependency.parse_pep508(d) for d in requires_dist]

    @computed_based_on("Requires-Python")
    def required_python_spec(self) -> VersionSpecifier:
        if version_str := self["Requires-Python"]:
            return VersionSpecifier.parse(version_str)
        return AnyVersion

    def generate_content(self) -> str:
        msg = EmailMessage()
        for key, value in self._data:
            if key in _MULTI_FIELDS and not isinstance(value, List):
                raise ValueError(f'{key} expected to be a list, found: {value}')

            if key == 'Description':
                continue  # will add it in payload

            if isinstance(value, List):
                for item in value:
                    msg[key] = item
            else:
                msg[key] = value

        if payload := self._data.get("Description"):
            msg.set_payload(payload)

        return msg.as_string()

    @classmethod
    def load(cls, path: Path) -> "PackageMetadata":
        if not path.exists():
            return PackageMetadata(path=path, data={})

        parser = Parser()
        with path.open('r') as path_fd:
            content = parser.parse(path_fd)

            data = {}
            for key, value in content.items():
                if key in _MULTI_FIELDS:
                    get_or_put(data, key, list).append(value)
                elif old_value := data.get(key):
                    if isinstance(old_value, List):
                        old_value.append(value)
                    else:
                        data[key] = [old_value, value]
                else:
                    data[key] = value

        return PackageMetadata(path=path, data=data)

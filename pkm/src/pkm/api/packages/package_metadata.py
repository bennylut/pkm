from __future__ import annotations

import warnings
from dataclasses import dataclass
from email.message import EmailMessage
from email.parser import Parser
from pathlib import Path
from typing import List, TYPE_CHECKING, Dict, Any

from pkm.api.dependencies.dependency import Dependency
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier, AllowAllVersions
from pkm.config.configclass import ConfigIO, config, config_field, ConfigFile
from pkm.utils.dicts import get_or_put, remove_none_values

if TYPE_CHECKING:
    from pkm.api.projects.pyproject_configuration import ProjectConfig

_METADATA_VERSION = '2.1'

_MULTI_FIELDS = {
    'Provides-Extra', 'Platform', 'Supported-Platform', 'Classifier', 'Requires-Dist', 'Provides-Dist',
    'Obsoletes-Dist', 'Requires-External', 'Project-URL', 'Dynamic'
}


class PackageMetadataIO(ConfigIO):

    def write(self, path: Path, data: Dict[str, Any]):
        msg = EmailMessage()
        for key, value in data.items():
            if value is None:
                continue

            if key in _MULTI_FIELDS and not isinstance(value, List):
                raise ValueError(f'{key} expected to be a list, found: {value}')

            if key == 'Description':
                continue  # will add it in payload

            if isinstance(value, List):
                for item in value:
                    msg[key] = item
            else:
                try:
                    msg[key] = value
                except Exception as e:
                    warnings.warn(f"malformed metadata key,value ({key}={value}) | {e}, ignoring it")

        if payload := data.get("Description"):
            msg.set_payload(payload)

        path.write_text(msg.as_string())

    def read(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}

        parser = Parser()
        with path.open('r', errors="ignore") as path_fd:
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

        return data


@dataclass
@config(io=PackageMetadataIO())
class PackageMetadata(ConfigFile):
    """
    implementation of the package metadata 2.1 specification as described in pep 566
    see also: https://packaging.python.org/en/latest/specifications/core-metadata/
    """

    metadata_version: Version = config_field(key="Metadata-Version")
    package_name: str = config_field(key="Name")
    package_version: Version = config_field(key="Version")
    summary: str = config_field(key="Summary")
    description: str = config_field(key="Description")
    dependencies: List[Dependency] = config_field(key="Requires-Dist", default_factory=list)
    required_python_spec: VersionSpecifier = config_field(key="Requires-Python", default=AllowAllVersions)
    leftovers = config_field(leftover=True)

    @classmethod
    def from_project_config(cls, prjc: "ProjectConfig") -> PackageMetadata:
        # filling authors and maintainers according to pep-621:
        # 1. If only name is provided, the value goes in Author/Maintainer as appropriate.
        # 2. If only email is provided, the value goes in Author-email/Maintainer-email as appropriate.
        # 3. If both email and name are provided, the value goes in Author-email/Maintainer-email as appropriate,
        #    with the format {name} <{email}> (with appropriate quoting, e.g. using email.headerregistry.Address).
        # 4. Multiple values should be separated by commas.

        author_names = [a.name for a in (prjc.authors or []) if a.name]
        author_emails = [a.email for a in (prjc.authors or []) if a.email]

        maintainer_names = [a.name for a in (prjc.authors or []) if a.name]
        maintainer_emails = [a.email for a in (prjc.authors or []) if a.email]

        extras = list((prjc.optional_dependencies or {}).keys())
        all_deps = prjc.all_dependencies

        data = {
            'Metadata-Version': _METADATA_VERSION,
            'Name': prjc.name, 'Version': str(prjc.version),
            'Summary': prjc.description, 'Description': prjc.readme_content(),
            'Description-Content-Type': prjc.readme_content_type(), 'Keywords': prjc.keywords or [],
            'Author': ', '.join(author_names), 'Author-email': ', '.join(author_emails),
            'Maintainer': ', '.join(maintainer_names), 'Maintainer-email': ', '.join(maintainer_emails),
            'License': prjc.license_content(), 'Classifier': prjc.classifiers,
            'Requires-Dist': [str(d) for d in all_deps], 'Requires-Python': str(prjc.requires_python),
            'Provides-Extra': extras,
            # 'Dynamic': prjc.dynamic or [], add back when pypi supports metadata version 2.2
        }

        return cls.from_config(remove_none_values(data))

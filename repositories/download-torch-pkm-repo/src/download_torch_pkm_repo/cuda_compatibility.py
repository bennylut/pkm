from __future__ import annotations

import platform
import subprocess
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

from pkm.api.pkm import pkm
from pkm.api.versions.version import Version, StandardVersion
from pkm.api.versions.version_specifiers import VersionSpecifier
from pkm.config.configuration import TomlFileConfiguration
from pkm.utils.properties import cached_property
from pkm.utils.resources import ResourcePath
from download_torch_pkm_repo.utils.html import BasicDomParser


@dataclass
class _CudaVersionSpec:
    cuda_version: StandardVersion
    linux_spec: VersionSpecifier
    windows_spec: VersionSpecifier

    def to_config(self) -> Dict[str, Any]:
        return {
            'cuda-version': str(self.cuda_version),
            'linux-spec': str(self.linux_spec),
            'windows-spec': str(self.windows_spec)
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> _CudaVersionSpec:
        return _CudaVersionSpec(
            StandardVersion.parse(config['cuda-version']),
            VersionSpecifier.parse(config['linux-spec']),
            VersionSpecifier.parse(config['windows-spec']),
        )


class CudaCompatibilityTable:

    def __init__(self, cuda_compatibility_spec: List[_CudaVersionSpec]):
        self._specs = cuda_compatibility_spec

    @cached_property
    def installed_nvidia_driver_version(self) -> Optional[Version]:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv"],
            capture_output=True
        )

        proc.check_returncode()
        return Version.parse(proc.stdout.splitlines(False)[-1].decode())

    def compatible_cuda_versions(
            self, nvidia_driver: Optional[Version] = None,
            is_windows: bool = platform.system() == 'Windows'
    ) -> List[StandardVersion]:

        nvidia_driver = nvidia_driver or self.installed_nvidia_driver_version
        result: List[StandardVersion] = []

        for spec in self._specs:
            if (is_windows and spec.windows_spec.allows_version(nvidia_driver)) or \
                    (not is_windows and spec.linux_spec.allows_version(nvidia_driver)):
                result.append(spec.cuda_version)

        return result

    @classmethod
    def load(cls, config_file: Optional[Path] = None) -> CudaCompatibilityTable:

        if not config_file:
            with ResourcePath("pkm_torch_repository.resources", "cuda-compatibilities.toml").use() as resources:
                return cls.load(resources)

        config_backup = TomlFileConfiguration.load(config_file)
        specs = []

        try:
            cuda_url = "https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html"
            data = pkm.httpclient.fetch_resource(cuda_url).data
            extractor = BasicDomParser()
            extractor.feed(data.read_text())

            compatibility_table_rows = extractor.dom.select(
                lambda it: it.attrs.get('id') == 'cuda-major-component-versions__table-cuda-toolkit-driver-versions',
                lambda it: it.tag == 'tbody',
                lambda it: it.tag == 'tr'
            )

            for row in compatibility_table_rows:
                columns = [td.data() for td in row.children if td.tag == 'td']
                specs.append(_CudaVersionSpec(
                    StandardVersion.parse(columns[0].split(" ")[1]),
                    VersionSpecifier.parse(columns[1]),
                    VersionSpecifier.parse(columns[2]),
                ))

            config_backup["version-spec"] = [spec.to_config() for spec in specs]
            config_backup.save()

        except Exception: # noqa
            warnings.warn("could not update cuda compatibility table, will use old known compatibility specs versions")
            specs = [_CudaVersionSpec.from_config(spec) for spec in config_backup["version-spec"]]

        return CudaCompatibilityTable(specs)

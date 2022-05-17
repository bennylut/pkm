from __future__ import annotations

import bz2
import json
from typing import List, Dict, Iterable

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package
from pkm.api.pkm import pkm
from pkm.api.repositories.repository import AbstractRepository
from src.conda_pkm_repo.conda_channel_subdir import CondaChannelSubdir, subdir_of

_DEFAULT_CHANNEL = "https://repo.anaconda.com/pkgs/main"
_REPODATA_PATH = "repodata.json.bz2"


class CondaRepository(AbstractRepository):

    def __init__(self, name: str, channel: str = _DEFAULT_CHANNEL):
        super().__init__(name)
        self.channel = _normalize_channel(channel)
        self.subdirs: Dict[str, CondaChannelSubdir] = {}

    def _do_match(self, dependency: Dependency, env: Environment) -> List[Package]:
        if urlv := dependency.required_url():
            assert urlv.protocol == "conda"
            url = urlv.url.lower()
            if url.startswith(self.channel + "/"):
                subdir_name, artifact = urlv.url[len(self.channel + "/"):].split("/")
                subdir = self.subdir_by_name(subdir_name)
                package = subdir.single_artifact_package(artifact)
                return [package] if package else []
            return []

        subdir_name = subdir_of(env.operating_platform)
        subdir = self.subdir_by_name(subdir_name)

        return [p for p in subdir.general_package(dependency.package_name) if
                dependency.version_spec.allows_version(p.version)]

    def subdir_by_name(self, subdir_name: str) -> CondaChannelSubdir:
        if not (subdir := self.subdirs.get(subdir_name)):
            path = pkm.httpclient.fetch_resource(f"{self.channel}/{subdir_name}/{_REPODATA_PATH}").data
            with bz2.open(path) as data:
                subdir = self.subdirs[subdir_name] = CondaChannelSubdir(self.channel, subdir_name, json.load(data))
        return subdir

    def accepted_url_protocols(self) -> Iterable[str]:
        return 'conda',


def _normalize_channel(channel: str) -> str:
    return channel.rstrip('/').lower()

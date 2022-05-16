from __future__ import annotations
import re
from collections import defaultdict

from dataclasses import replace, dataclass
from typing import Dict, Any, Optional, List, cast, Tuple

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import PackageInstallationInfo
from pkm.api.environments.environment import Environment, OperatingPlatform
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.pkm import pkm
from pkm.api.versions.version import Version, StandardVersion, UrlVersion
from pkm.api.versions.version_specifiers import VersionSpecifier, AllowAllVersions, VersionMatch, VersionsUnion, \
    StandardVersionRange, RestrictAllVersions
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.hashes import HashBuilder
from pkm.utils.iterators import first_or_none, groupby
from pkm.utils.properties import cached_property
from pkm.utils.sequences import strs
from src.conda_pkm_repo.conda_distribution import CondaDistribution

_RELATIVE_OPS_PREFIXES = "><=!~"

_SUBDIR_BY_PLATFORM = {
    "linux-64-x86": "linux-64",
    "linux-32-x86": "linux-32",
    "linux-64-arm": "linux-aarch64",
    "darwin-64-arm": "osx-arm64",
    "darwin-64-x86": "osx-64",
    "windows-64-x86": "win-64",
    "windows-32-x86": "win-32",
    "any": "noarch"
}

_SUBDIR_TO_OS_CTAG = {
    "linux-64": "linux_x86_64",
    "linux-32": "linux_i386",
    "linux-aarch64": "manylinux2014_aarch64",
    "osx-arm64": "macosx_11_0_arm64",
    "osx-64": "macosx_10_14_x86_64",
    "win-64": "win_amd64",
    "win-32": "win32",
    "any": "any"
}

_PLEASE_FILL_ISSUE = "if it works with regular conda, please fill an issue so that we can add it too"


def subdir_of(op: OperatingPlatform) -> str:
    os = op.os
    bits = op.python_interpreter_bits
    if op.has_x86_cpu():
        cpu = "x86"
    elif op.has_arm_cpu():
        cpu = "arm"
    else:
        raise UnsupportedOperationException(
            f"this cpu type is not supported yet for conda-pkm-repo, {_PLEASE_FILL_ISSUE}")

    subdir_key = f"{os}-{bits}-{cpu}"
    if subdir := _SUBDIR_BY_PLATFORM.get(subdir_key):
        return subdir

    raise UnsupportedOperationException(
        f"this platform is not supported yet for conda-pkm-repo, {_PLEASE_FILL_ISSUE}")


class CondaChannelSubdir:

    def __init__(self, channel: str, subdir: str, repodata: Dict[str, Any]):
        self.packages = {}
        self.channel = channel
        self.subdir = subdir

        package_to_artifacts: Dict[Tuple[str, str], List[CondaSubdirPackageArtifact]] = defaultdict(list)
        for artifact_name, artifact_info in repodata["packages"].items():
            package_artifacts = package_to_artifacts[(artifact_info["name"], artifact_info["version"])]
            package_artifacts.append(CondaSubdirPackageArtifact(self, artifact_name, artifact_info))

        packages = [CondaSubdirPackage(name, version, artifacts)
                    for (name, version), artifacts in package_to_artifacts.items()]

        self.packages = groupby(packages, lambda it: it.pname)
        self.repodata = repodata

    def __repr__(self):
        return f"CondaChannelSubdir({self.channel=}, {self.subdir=})"

    def __hash__(self):
        return HashBuilder().regulars(self.channel, self.subdir).build()

    def match_artifacts_by_build(self, package: str, version: str, build: str) -> List[CondaSubdirPackageArtifact]:
        assert build, "build must be provided"

        build_matcher = re.compile(re.escape(build).replace("\\*", ".*"))
        package_versions = self.packages.get(package) or []
        version_spec = AllowAllVersions if version == '*' else VersionSpecifier.parse(f"=={version}")
        allowed_packages = [p for p in package_versions if version_spec.allows_version(p.version)]
        return [artifact for p in allowed_packages for artifact in p.artifacts
                if build_matcher.match(artifact.info['build'])]

    def general_package(self, package: str) -> List[Package]:
        return self.packages.get(package) or []

    def single_artifact_package(self, artifact: str) -> Optional[Package]:
        if package_info := self.repodata["packages"].get(artifact):
            return CondaSubdirPackage(
                package_info['name'], package_info['version'],
                [CondaSubdirPackageArtifact(self, artifact, package_info)])
        return None


def _parse_specifier(spec: str) -> VersionSpecifier:
    if spec[0] in _RELATIVE_OPS_PREFIXES:
        return VersionSpecifier.parse(spec)
    if spec == "*":
        return AllowAllVersions
    if spec.endswith(".*"):
        return VersionSpecifier.parse(f"~={spec[:-2]}.0")
    return VersionMatch(Version.parse(spec))


@dataclass
class CondaSubdirPackageArtifact:
    container: CondaChannelSubdir
    artifact: str
    info: Dict[str, Any]

    def __hash__(self):
        return HashBuilder().regulars(self.container, self.artifact).build()

    @cached_property
    def _all_dependencies(self) -> List[Dependency]:
        dependencies: List[str] = self.info["depends"]
        return [self._parse_dependency(d) for d in dependencies]

    def _parse_dependency(self, dstr: str) -> Dependency:
        parts = dstr.split(" ")
        if len(parts) == 1:
            return Dependency(parts[0])
        elif len(parts) == 2:
            options = [_parse_specifier(it) for it in parts[1].split("|")]
            if len(options) == 1:
                return Dependency(parts[0], options[0])
            return Dependency(parts[0], VersionsUnion(options))
        else:

            artifacts = self.container.match_artifacts_by_build(parts[0], parts[1], parts[2])
            matches = [
                VersionMatch(UrlVersion.parse(f"conda+{self.container.channel}/{self.container.subdir}/{a.artifact}"))
                for a in artifacts]

            if not matches:
                spec = RestrictAllVersions
                print("DBG")
                self.container.match_artifacts_by_build(parts[0], parts[1], parts[2])
            elif len(matches) == 1:
                spec = matches[0]
            else:
                spec = VersionsUnion(matches)

            return Dependency(parts[0], spec)

    def dependencies(self, environment: "Environment", extras: Optional[List[str]] = None) -> List["Dependency"]:
        return [
            d for d in self._all_dependencies
            if d.package_name != 'python' and d.is_applicable_for(environment, extras)]

    @cached_property
    def required_python(self) -> VersionSpecifier:
        if python := first_or_none(d for d in self._all_dependencies if d.package_name == 'python'):
            return python.version_spec
        else:
            return AllowAllVersions

    @cached_property
    def compatibility_tag(self) -> str:
        subdir = self.container.subdir
        rp = self.required_python
        if rp is AllowAllVersions:
            py_ctag = "py2.py3"
        elif isinstance(rp, StandardVersionRange):
            min_python: StandardVersion = cast(StandardVersion, rp.min)
            if not rp.includes_min:
                min_python = replace(min_python, release=(*min_python.release[:-1], min_python.release[-1] + 1))
            py_ctag = 'py' + ''.join(strs(min_python.release[:2]))
        else:
            raise UnsupportedOperationException(f"could not parse required python: {rp}")

        return f"{py_ctag}-none-{_SUBDIR_TO_OS_CTAG[subdir]}"

    def build_number(self) -> int:
        return self.info["build_number"]


class CondaSubdirPackage(Package):

    def __init__(self, name: str, version: str, artifacts: List[CondaSubdirPackageArtifact]):
        self.artifacts = artifacts
        self.pname = name
        self._ver = version

    def _best_artifact_for(self, env: Environment) -> Optional[CondaSubdirPackageArtifact]:
        scored_artifacts = {
            a: (tag_score, a.build_number())
            for a in self.artifacts
            if (tag_score := env.compatibility_tag_score(a.compatibility_tag)) is not None
               and all(d.version_spec is not RestrictAllVersions for d in a.dependencies(env, [])) # noqa
        }

        if not scored_artifacts:
            return None

        return max(scored_artifacts.items(), key=lambda it: it[1])[0]

    @cached_property
    def descriptor(self) -> PackageDescriptor:
        return PackageDescriptor(self.pname, Version.parse(self._ver))

    def dependencies(self, environment: "Environment", extras: Optional[List[str]] = None) -> List["Dependency"]:
        artifact = self._best_artifact_for(environment)
        if not artifact:
            raise UnsupportedOperationException("asking for dependencies for unsupported environment")
        return artifact.dependencies(environment, extras)

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._best_artifact_for(env) is not None

    def install_to(self, target: "PackageInstallationTarget", user_request: Optional["Dependency"] = None,
                   editable: bool = True):
        artifact: CondaSubdirPackageArtifact = self._best_artifact_for(target.env)
        if not artifact:
            raise UnsupportedOperationException("asking to install inside unsupported environment")

        url = f"{artifact.container.channel}/{artifact.container.subdir}/{artifact.artifact}"
        artifact_path = pkm.httpclient.fetch_resource(url).data
        dist = CondaDistribution(self.descriptor, artifact_path)
        dist.install_to(target, user_request, PackageInstallationInfo(compatibility_tag=artifact.compatibility_tag))

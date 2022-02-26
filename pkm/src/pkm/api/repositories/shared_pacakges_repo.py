import hashlib
import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo, RecordsFileConfiguration
from pkm.api.distributions.pth_link import PthLink
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.repositories.repository import AbstractRepository, Repository
from pkm.distributions.executables import Executables
from pkm.utils.iterators import first_or_none


class SharedPackagesRepository(AbstractRepository):

    def __init__(self, workspace: Path, base_repository: Repository):
        super().__init__("shared")
        self._workspace = workspace
        self._base_repo = base_repository

    def _do_match(self, dependency: Dependency) -> List[Package]:
        packages_dir = self._workspace / dependency.package_name
        packages = self._base_repo.match(dependency, False)
        return [
            _SharedPackage(p, packages_dir / str(p.version))
            for p in packages
        ]

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        def key(p: Package):
            return 0 if isinstance(p, _SharedPackage) else 1

        packages.sort(key=key)
        return packages


@dataclass
class _SharedPackageArtifact:
    path: Path
    metadata: PackageMetadata


class _SharedPackage(Package):

    def __init__(self, package: Package, shared_path: Path):
        self._package = package
        self._shared_path = shared_path

        if shared_path.exists():
            self._artifacts = [
                _SharedPackageArtifact(artifact, PackageMetadata.load(artifact / "dist-info/METADATA"))
                for artifact in shared_path.iterdir()
            ]
        else:
            self._artifacts = []

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._package.descriptor

    def _shared_artifact_for(self, env: Environment) -> Optional[_SharedPackageArtifact]:
        return first_or_none(
            artifact for artifact in self._artifacts
            if artifact.metadata.required_python_spec.allows_version(env.interpreter_version))

    def _all_dependencies(self, environment: "Environment") -> List["Dependency"]:
        if artifact := self._shared_artifact_for(environment):
            return artifact.metadata.dependencies

        return self._package.dependencies(environment)

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._package.is_compatible_with(env)

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None):
        if shared := self._shared_artifact_for(env):
            _link_shared(self.descriptor, shared, env)
        else:
            self._package.install_to(env)
            env.reload()  # TODO: does that needed?
            shared = _copy_to_shared(self._package.descriptor, env, self._shared_path)
            env.force_remove(self._package.name)
            _link_shared(self.descriptor, shared, env)


def _copy_records(root: Path, shared: Path, records: List[Path]) -> List[Path]:
    shared.mkdir(parents=True)
    records_left = []
    for record in records:
        if record.is_relative_to(root):  # the path may lead out of the required source
            shared_path = shared / record.relative_to(root)
            if record.is_dir():
                shared_path.mkdir(exist_ok=True, parents=True)
            else:
                shared_path.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy(record, shared_path)
        else:
            records_left.append(record)
    return records_left


def _copy_to_shared(package: PackageDescriptor, env: Environment, shared_path: Path) -> _SharedPackageArtifact:
    installed_package = env.site_packages.installed_package(package.name)

    site_name = "purelib" if installed_package.is_in_purelib() else "platlib"

    dist_info = installed_package.dist_info
    shared_target = shared_path / hashlib.md5(
        str(installed_package.published_metadata.required_python_spec).encode()).hexdigest()

    records = list(dist_info.installed_files())

    # filter dist info records:
    records = [
        r for r in records
        if not r.is_relative_to(dist_info.path)]

    # copy site
    shared_purelib = shared_target / site_name
    records = _copy_records(dist_info.path.parent, shared_purelib, records)

    # copy scripts
    script_entrypoints = {e.name for e in dist_info.load_entrypoints_cfg().entrypoints if e.is_script()}
    bin_path = Path(env.paths["scripts"])
    shared_bin = shared_target / "bin"

    # filter script entrypoints - they should be re-generated
    records = [r for r in records if not r.is_relative_to(bin_path) or r.stem not in script_entrypoints]
    records = _copy_records(bin_path, shared_bin, records)

    # copy dist-info
    shutil.copytree(dist_info.path, shared_target / 'dist-info')

    if records:
        warnings.warn(f"{len(records)} unsharable records found in package: {package.name} {package.version}: "
                      f"{', '.join(str(r) for r in records)}")

    return _SharedPackageArtifact(shared_target, dist_info.load_metadata_cfg())


def _link_shared(package: PackageDescriptor, shared: _SharedPackageArtifact, env: Environment):
    files_created: List[Path] = []

    package_prefix = f"{package.expected_source_package_name}-{package.version}"

    site_name = "purelib" if (shared.path / "purelib").exists() else "platlib"
    site_path = Path(env.paths[site_name])

    # first link the site data
    purelib_link = PthLink(site_path / f"{package_prefix}.pth", [shared.path / site_name])
    purelib_link.save()
    files_created.append(purelib_link.path)

    # now create all script entrypoints
    shared_distinfo = DistInfo.load(shared.path / "dist-info")
    bin_dir = Path(env.paths['scripts'])
    for entrypoint in shared_distinfo.load_entrypoints_cfg().entrypoints:
        if entrypoint.is_script():
            files_created.append(Executables.generate_for_entrypoint(entrypoint, env, bin_dir))

    # then, patch non entrypoint scripts
    for script in (shared.path / 'bin').iterdir():
        target_script = bin_dir / script.name
        Executables.patch_shabang_for_env(script, target_script, env)
        files_created.append(target_script)

    # we are almost done, copy dist-info
    distinfo_path = site_path / f"{package_prefix}.dist-info"
    shutil.copytree(shared_distinfo.path, distinfo_path)
    files_created.extend(file for file in distinfo_path.rglob("*") if file.name != "RECORD")

    # and finally, sign the installation
    record_path = distinfo_path / "RECORD"
    record_path.unlink(missing_ok=True)
    RecordsFileConfiguration.load(record_path).sign_files(files_created, site_path).save()

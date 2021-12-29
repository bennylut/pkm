import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Optional, Set, Dict, List, Literal, Any
from urllib.parse import unquote_plus, quote_plus
from zipfile import ZipFile

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.lightweight_environment_builder import LightweightEnvironmentBuilder
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.packages.standard_package import AbstractPackage, StandardPackageArtifact
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, BuildSystemConfig
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.resolution.pubgrub import MalformedPackageException
from pkm.utils.sequences import single_or_fail

_BUILD_KEY_T = str
_METADATA_FILE_RX = re.compile("[^/]*\.dist-info/METADATA")


class BuildError(IOError):
    ...


class SourceBuildsRepository(Repository):
    def __init__(self, workspace: Path):
        super().__init__("source-builds")
        self._workspace = workspace
        self._ongoing_builds: Dict[_BUILD_KEY_T, Set[PackageDescriptor]] = defaultdict(set)

    def _build(self, build_key: _BUILD_KEY_T, package: PackageDescriptor,
               source_tree: Path, target_env: Environment, build_packages_repo: Repository):

        package_dir = self._workspace / package.name / quote_plus(str(package.version))
        artifacts_dir = package_dir / 'artifacts'
        metadata_file = package_dir / "METADATA"

        if package in (ongoingbuilds := self._ongoing_builds[build_key]):
            raise BuildError(f"cycle detected involving: {ongoingbuilds}")

        ongoingbuilds.add(package)
        pyproject = _read_effective_pyproject_toml(source_tree)
        if not pyproject:
            raise MalformedPackageException(f"cannot resolve {package}'s build system")
        buildsys: BuildSystemConfig = pyproject.build_system

        with TemporaryDirectory() as tdir:
            tdir_path = Path(tdir)
            build_env = LightweightEnvironmentBuilder.create(tdir_path / 'venv', target_env.interpreter_path)
            if buildsys.requirements:
                build_env.install(buildsys.requirements, build_packages_repo)

            # start build cycle:
            wheels_path = (tdir_path / "wheels").absolute()
            wheel_metadata_path = tdir_path / "meta"

            if buildsys.build_backend == _LEGACY_BUILDSYS['build_backend']:
                build_env.run_proc(
                    [build_env.interpreter_path, 'setup.py', 'bdist_wheel', '-d', str(wheels_path)],
                    cwd=str(source_tree.absolute())).check_returncode()

                wheel_path = next(wheels_path.glob("*.whl"), None)
            else:
                # 1. check for wheel extra requirements
                extra_requirements = _exec_build_cycle_script(
                    source_tree, build_env, buildsys, 'get_requires_for_build_wheel', [None])

                if extra_requirements.status == 'success':
                    build_env.install([Dependency.parse_pep508(d) for d in extra_requirements.result],
                                         build_packages_repo)

                # 2. build the wheel
                wheel_output = _exec_build_cycle_script(
                    source_tree, build_env, buildsys, 'build_wheel', [str(wheels_path), None, None])

                wheel_path = wheels_path / wheel_output.result

            if not wheel_path or not wheel_path.exists():
                raise BuildError("build backend did not produced expected wheel")

            if not metadata_file.exists():
                with ZipFile(wheel_path) as zip:
                    for name in zip.namelist():
                        if _METADATA_FILE_RX.fullmatch(name):
                            zip.extract(name, wheel_metadata_path)
                            wheel_metadata_path = wheel_metadata_path / name
                            break

                if not wheel_metadata_path.exists():
                    raise BuildError("build backend did not produced metadata in wheel")

            # done setting up, storing in package dir
            artifacts_dir.mkdir(exist_ok=True, parents=True)
            shutil.copy(wheel_path, artifacts_dir / wheel_path.name)
            if not metadata_file.exists():
                shutil.copy(wheel_metadata_path, metadata_file)

    def build(self, package: PackageDescriptor, source_tree: Path, target_env: Environment,
              build_packages_repo: Repository) -> Package:

        # TODO: the key should be the building thread... this is not correct now..
        self._build(f"{package.name} {package.version}", package, source_tree, target_env, build_packages_repo)
        return single_or_fail(self.match(package.to_dependency()))

    def accepts(self, dependency: Dependency) -> bool:
        return True

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if not (versions_dir := self._workspace / dependency.package_name).exists():
            return []

        result = []
        for version_dir in versions_dir.iterdir():
            version = Version.parse(unquote_plus(version_dir.name))
            if dependency.version_spec.allows_version(version):
                result.append(
                    _PrebuiltPackage(dependency.package_name, version, version_dir))

        return result


@dataclass
class _BuildCycleResult:
    status: Literal['success', 'undefined_hook']
    result: Any


def _exec_build_cycle_script(
        source_tree: Path, env: Environment, buildsys: BuildSystemConfig, hook: str,
        arguments: List[Any]) -> _BuildCycleResult:
    with TemporaryDirectory() as tdir:
        tdir_path = Path(tdir)
        build_backend_parts = buildsys.build_backend.split(":")
        build_backend_import = build_backend_parts[0]
        build_backend = 'build_backend' + (f".{build_backend_parts[1]}" if len(build_backend_parts) > 1 else "")

        script = f"""
            import {build_backend_import} as build_backend
            import json
            
            def ret(status, result):
                out = open('{str((tdir_path / 'output').absolute())}', 'w+')
                out.write(json.dumps({{'status': status, 'result': result}}))
                out.close()
                exit(0)
            
            if not hasattr({build_backend}, '{hook}'):
                ret('undefined_hook', None)
            else:
                result = {build_backend}.{hook}({', '.join(repr(arg) for arg in arguments)})
                ret('success', result)
        """

        print("EXECUTING PROCESS")
        process_results = env.run_proc([env.interpreter_path, '-c', dedent(script)], cwd=source_tree)
        print("DONE EXECUTING PROCESS")
        process_results.check_returncode()
        return _BuildCycleResult(**json.loads((tdir_path / 'output').read_text()))


class _PrebuiltPackage(AbstractPackage):

    def __init__(self, name: str, version: Version, path: Path):
        super().__init__(
            PackageDescriptor(name, version),
            [StandardPackageArtifact.from_wheel(wheel) for wheel in (path / 'artifacts').iterdir()])

        self._path = path
        self._metadata = PackageMetadata.load(path / "METADATA")

    def _retrieve_artifact(self, artifact: StandardPackageArtifact) -> Path:
        return self._path / 'artifacts' / artifact.file_name

    def _all_dependencies(self, environment: "Environment") -> List[Dependency]:
        return self._metadata.dependencies


_LEGACY_BUILDSYS = {
    'requires': ['setuptools', 'wheel', 'pip'],
    'build_backend': '__legacy__'
}


def _read_effective_pyproject_toml(source_tree: Path) -> Optional[PyProjectConfiguration]:
    pyproject_file = source_tree / 'pyproject.toml'
    pyproject = PyProjectConfiguration.load(pyproject_file)
    if pyproject['build-system'] is None:
        if not (source_tree / 'setup.py').exists():
            return None

        pyproject['build-system'] = _LEGACY_BUILDSYS
    return pyproject

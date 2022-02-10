import json
import shutil
import threading
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Set, Dict, List, Literal, Any, Optional, TYPE_CHECKING
from urllib.parse import unquote_plus, quote_plus

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.packages.standard_package import AbstractPackage, StandardPackageArtifact
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, BuildSystemConfig
from pkm.api.repositories.build_monitors import BuildPackageMonitoredOp, BuildPackageHookExecutionEvent
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.utils.sequences import single_or_fail

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment

_BUILD_KEY_T = int


class BuildError(IOError):
    ...


class SourceBuildsRepository(Repository):
    def __init__(self, workspace: Path, build_packages_repo: Repository):
        super().__init__("source-builds")
        self._workspace = workspace
        self._ongoing_builds: Dict[_BUILD_KEY_T, Set[PackageDescriptor]] = defaultdict(set)
        self._build_packages_repo = build_packages_repo

    def _version_dir(self, package: PackageDescriptor) -> Path:
        return self._workspace / package.name / quote_plus(str(package.version))

    def _build(self, build_key: _BUILD_KEY_T, package: PackageDescriptor,
               required_artifact: str,  # ['metadata', 'wheel', 'editable']
               source_tree: Path, target_env: "Environment", build_packages_repo: Optional[Repository]):

        from pkm.api.environments.lightweight_environment_builder import LightweightEnvironments
        # with monitor.on_build(package, required_artifact) as build_monitor:

        with BuildPackageMonitoredOp(package) as mop:
            package_dir = self._version_dir(package)
            artifacts_dir = package_dir / 'artifacts'
            metadata_file = package_dir / "METADATA"

            if package in (ongoingbuilds := self._ongoing_builds[build_key]):
                raise BuildError(f"cycle detected involving: {ongoingbuilds}")

            ongoingbuilds.add(package)
            pyproject = PyProjectConfiguration.load_effective(source_tree / 'pyproject.toml', package)
            buildsys: BuildSystemConfig = pyproject.build_system
            build_packages_repo = build_packages_repo or self._build_packages_repo

            with TemporaryDirectory() as tdir:
                tdir_path = Path(tdir)
                build_env = LightweightEnvironments.create(tdir_path / 'venv', target_env.interpreter_path)
                if buildsys.requirements:
                    build_env.install(buildsys.requirements, build_packages_repo)
                if buildsys.backend_path:
                    build_env.install_link('build_backend', [source_tree / pth for pth in buildsys.backend_path])

                # start build life-cycle:
                wheels_path = (tdir_path / "wheels").absolute()
                wheels_path.mkdir(parents=True, exist_ok=True)

                requires_wheel = True

                # 1. check for wheel extra requirements
                command = 'get_requires_for_build_editable' \
                    if required_artifact == 'editable' else 'get_requires_for_build_wheel'
                mop.notify(BuildPackageHookExecutionEvent(package, command))

                extra_requirements = _exec_build_cycle_script(source_tree, build_env, buildsys, command, [None])

                if extra_requirements.status == 'success':
                    build_env.install(
                        [Dependency.parse_pep508(d) for d in extra_requirements.result],
                        build_packages_repo)

                if required_artifact == 'metadata':
                    # 2. try to build metadata only
                    command = 'prepare_metadata_for_build_wheel'
                    mop.notify(BuildPackageHookExecutionEvent(package, command))
                    dist_info_output = _exec_build_cycle_script(
                        source_tree, build_env, buildsys, command,
                        [str(wheels_path), None])
                    if dist_info_output.status == 'success':
                        wheel_metadata_path = wheels_path / dist_info_output.result / 'METADATA'
                        if wheel_metadata_path.exists():
                            requires_wheel = False
                            metadata_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy(wheel_metadata_path, metadata_file)

                if requires_wheel:
                    # 2. build the wheel
                    command = 'build_editable' if required_artifact == 'editable' else 'build_wheel'
                    mop.notify(BuildPackageHookExecutionEvent(package, command))
                    wheel_output = _exec_build_cycle_script(
                        source_tree, build_env, buildsys, command, [str(wheels_path), None, None])

                    wheel_path = wheels_path / wheel_output.result

                    if not wheel_path or not wheel_path.exists():
                        raise BuildError("build backend did not produced expected wheel")

                    if not metadata_file.exists():
                        metadata = WheelDistribution(package, wheel_path).extract_metadata(target_env)

                    # done setting up, storing in package dir
                    artifacts_dir.mkdir(exist_ok=True, parents=True)
                    shutil.copy(wheel_path, artifacts_dir / wheel_path.name)
                    if not metadata_file.exists():
                        metadata.save_to(metadata_file)

    def build(self, package: PackageDescriptor, source_tree: Path, target_env: "Environment", editable: bool,
              build_packages_repo: Optional[Repository]) -> Package:

        package_type = 'wheel' if not editable else 'editable'
        self._build(threading.current_thread().ident, package, package_type, source_tree, target_env,
                    build_packages_repo)
        return single_or_fail(self.match(package.to_dependency()))

    def build_or_get_metadata(self, package: PackageDescriptor, source_tree: Path,
                              target_env: "Environment", build_packages_repo: Optional[Repository]) -> PackageMetadata:
        metadata_file = self._version_dir(package) / "METADATA"
        if not metadata_file.exists():
            self._build(
                threading.current_thread().ident, package, 'metadata', source_tree, target_env,
                build_packages_repo)

        return PackageMetadata.load(metadata_file)

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
        source_tree: Path, env: "Environment", buildsys: BuildSystemConfig, hook: str,
        arguments: List[Any]) -> _BuildCycleResult:
    with TemporaryDirectory() as tdir:
        tdir_path = Path(tdir)
        build_backend_parts = buildsys.build_backend.split(":")
        build_backend_import = build_backend_parts[0]
        build_backend = 'build_backend' + (f".{build_backend_parts[1]}" if len(build_backend_parts) > 1 else "")
        output_path = tdir_path / 'output'
        output_path_str = str(output_path.absolute()).replace('\\', '\\\\')

        script = f"""
            import {build_backend_import} as build_backend
            import json

            def ret(status, result):
                out = open('{output_path_str}', 'w+')
                out.write(json.dumps({{'status': status, 'result': result}}))
                out.close()
                exit(0)

            if not hasattr({build_backend}, '{hook}'):
                ret('undefined_hook', None)
            else:
                result = {build_backend}.{hook}({', '.join(repr(arg) for arg in arguments)})
                ret('success', result)
        """

        script_path = tdir_path / 'execution.py'
        script_path.write_text(dedent(script))
        process_results = env.run_proc([str(env.interpreter_path), str(script_path)], cwd=source_tree)
        if process_results.returncode != 0:
            raise BuildError(
                f"PEP517 build cycle execution failed (execution of hook: {hook}, resulted in exit code:"
                f" {process_results.returncode})")
        return _BuildCycleResult(**json.loads((tdir_path / 'output').read_text()))


class _PrebuiltPackage(AbstractPackage):

    def __init__(self, name: str, version: Version, path: Path):
        artifacts_path = (path / 'artifacts')
        if artifacts_path.exists():
            artifacts = [StandardPackageArtifact(wheel.name) for wheel in artifacts_path.iterdir()]
        else:
            artifacts = []

        super().__init__(
            PackageDescriptor(name, version),
            artifacts,
            published_metadata=PackageMetadata.load(path / "METADATA")
        )

        self._path = path

    def _retrieve_artifact(self, artifact: StandardPackageArtifact) -> Path:
        return self._path / 'artifacts' / artifact.file_name

    def _all_dependencies(self, environment: "Environment") -> List["Dependency"]:
        return self.published_metadata.dependencies

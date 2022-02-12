import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import List, Literal, Any, TYPE_CHECKING
from urllib.parse import unquote_plus, quote_plus

import pkm.project_builders.external_builders as ext_build
from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.packages.standard_package import AbstractPackage, StandardPackageArtifact
from pkm.api.projects.pyproject_configuration import BuildSystemConfig
from pkm.api.repositories.repository import Repository
from pkm.api.versions.version import Version
from pkm.project_builders.external_builders import BuildError
from pkm.utils.files import temp_dir
from pkm.utils.sequences import single_or_fail

if TYPE_CHECKING:
    from pkm.api.environments.environment import Environment



class SourceBuildsRepository(Repository):
    def __init__(self, workspace: Path):
        super().__init__("source-builds")
        self._workspace = workspace

    def _version_dir(self, package: PackageDescriptor) -> Path:
        return self._workspace / package.name / quote_plus(str(package.version))

    def _build(self, package: PackageDescriptor,
               required_artifact: str,  # ['metadata', 'wheel', 'editable']
               source_tree: Path, target_env: "Environment"):

        from pkm.api.projects.project import Project
        editable = required_artifact == 'editable'
        metadata = required_artifact == 'metadata'

        package_dir = self._version_dir(package)

        project = Project.load(source_tree)

        with temp_dir() as tdir:
            try:
                output = ext_build.build_wheel(
                    project, tdir, only_meta=metadata, editable=editable, target_env=target_env)
            except BuildError:
                if metadata:
                    output = ext_build.build_wheel(
                        project, tdir, only_meta=False, editable=editable, target_env=target_env)
                else:
                    raise

        metadata_file = package_dir / "METADATA"
        artifacts_dir = package_dir / 'artifacts'

        if output.is_dir():  # metadata
            wheel_metadata_path = output / 'METADATA'
            if not wheel_metadata_path.exists():
                raise BuildError("build backend did not create a wheel METADATA file")

            shutil.copy(wheel_metadata_path, metadata_file)
        else:
            if not metadata_file.exists():
                metadata = WheelDistribution(package, output).extract_metadata(target_env)
                metadata.save_to(metadata_file)

            artifacts_dir.mkdir(exist_ok=True, parents=True)
            shutil.move(output, artifacts_dir / output.name)

    def build(self, package: PackageDescriptor, source_tree: Path, target_env: "Environment",
              editable: bool) -> Package:

        package_type = 'wheel' if not editable else 'editable'
        self._build(package, package_type, source_tree, target_env)
        return single_or_fail(self.match(package.to_dependency()))

    def build_or_get_metadata(self, package: PackageDescriptor, source_tree: Path,
                              target_env: "Environment") -> PackageMetadata:
        metadata_file = self._version_dir(package) / "METADATA"
        if not metadata_file.exists():
            self._build(package, 'metadata', source_tree, target_env)

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

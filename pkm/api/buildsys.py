import shutil
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from shutil import ignore_patterns
from tempfile import TemporaryDirectory
from typing import ContextManager
from zipfile import ZipFile

from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, ProjectConfig
from pkm.api.versions.version import StandardVersion
from pkm.distributions.wheel_distribution import WheelFileConfiguration
from pkm.utils.commons import UnsupportedOperationException


@dataclass
class _BuildContext:
    pyproject: PyProjectConfiguration
    build_dir: Path
    project_name_underscore: str

    def wheel_file_name(self) -> str:
        project_cfg = self.pyproject.project
        min_interpreter: StandardVersion = project_cfg.requires_python.min \
            if project_cfg.requires_python else StandardVersion((3,))

        req_interpreter = 'py' + ''.join(str(it) for it in min_interpreter.release[:2])
        return f"{req_interpreter}-none-any.whl"

    def sdist_file_name(self) -> str:
        return f"{self.project_name_underscore}-{self.pyproject.project.version}.tar.gz"

    def dist_info_dir_name(self) -> str:
        return f'{self.project_name_underscore}-{self.pyproject.project.version}.dist-info'

    def build_dist_info(self, dst: Path):
        metadata_file = dst / "METADATA"
        license_file = dst / "LICENSE"
        wheel_file = dst / "WHEEL"

        dst.mkdir(exist_ok=True, parents=True)
        project_config: ProjectConfig = self.pyproject.project

        PackageMetadata.from_project_config(project_config).save_to(metadata_file)
        license_file.write_text(
            project_config.license_content())

        # TODO: probably later we will want to add the version of pkm in the generator..
        WheelFileConfiguration.create(generator="pkm", purelib=True).save_to(wheel_file)

    def copy_sources(self, dst: Path):
        src_dir = self.pyproject.path.parent / 'src'
        if not src_dir.exists():
            raise UnsupportedOperationException("currently only the src layout is supported for source trees")

        shutil.copytree(src_dir, dst, ignore=ignore_patterns('__pycache__'))


@contextmanager
def _build_context() -> ContextManager[_BuildContext]:
    pyproject = PyProjectConfiguration.load_effective(Path("pyproject.toml"), None)
    project_cfg: ProjectConfig = pyproject.project

    project_name_underscores = project_cfg.name.replace('-', '_')

    with TemporaryDirectory() as tdir:
        build_dir = Path(tdir)

        yield _BuildContext(pyproject, build_dir, project_name_underscores)


def build_wheel(wheel_directory: str, config_settings=None, metadata_directory=None):
    with _build_context() as bc:
        dist_info_path = bc.build_dir / bc.dist_info_dir_name()
        bc.build_dist_info(dist_info_path)
        bc.copy_sources(bc.build_dir)

        wheel_name = bc.wheel_file_name()
        with ZipFile(Path(wheel_directory) / wheel_name, 'w') as wheel:
            for file in bc.build_dir.glob('*'):
                wheel.write(file, file.relative_to(bc.build_dir))

    return wheel_name


def build_sdist(sdist_directory: str, config_settings=None):
    with _build_context() as bc:
        sdist_file_name = bc.sdist_file_name()
        data_dir = bc.build_dir / sdist_file_name[:-len('.tar.gz')]
        data_dir.mkdir()

        dist_info_path = bc.build_dir / 'dist-info'
        bc.build_dist_info(dist_info_path)
        shutil.copy(dist_info_path / "METADATA", data_dir / "PKG_INFO")
        shutil.copy(bc.pyproject.path, data_dir / 'pyproject.toml')
        bc.copy_sources(data_dir / 'src')

        with tarfile.open(Path(sdist_directory) / sdist_file_name, 'w:gz', format=tarfile.PAX_FORMAT) as sdist:
            for file in data_dir.glob('*'):
                sdist.write(file, file.relative_to(bc.build_dir))

    return sdist_file_name


def get_requires_for_build_wheel(config_settings=None):
    return []


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings=None):
    with _build_context() as bc:
        dist_info_name = bc.dist_info_dir_name()
        bc.build_dist_info(Path(metadata_directory) / dist_info_name)
        return dist_info_name


def get_requires_for_build_sdist(config_settings=None):
    return []

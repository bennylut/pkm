import shutil
import tarfile
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from shutil import ignore_patterns
from tempfile import TemporaryDirectory
from typing import List, Optional, ContextManager, Union, Iterable
from zipfile import ZipFile

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.pkm import pkm
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, ProjectConfig
from pkm.api.repositories.repository import Repository, RepositoryPublisher, Authentication
from pkm.api.versions.version import StandardVersion
from pkm.distributions.wheel_distribution import WheelDistribution, WheelFileConfiguration
from pkm.utils.commons import UnsupportedOperationException, NoSuchElementException
from pkm.utils.properties import cached_property, clear_cached_properties


class Project(Package):

    def __init__(self, pyproject: PyProjectConfiguration):
        self._path = pyproject.path.absolute().parent
        self._pyproject = pyproject
        self._descriptor = pyproject.project.package_descriptor()

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._descriptor

    def _all_dependencies(self, environment: "Environment", build_packages_repo: "Repository") -> List["Dependency"]:
        return self._pyproject.project.all_dependencies

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._pyproject.project.requires_python.allows_version(env.interpreter_version)

    def install_to(self, env: "Environment", build_packages_repo: Optional[Repository] = None,
                   user_request: Optional["Dependency"] = None):
        with TemporaryDirectory() as tdir:
            tdir = Path(tdir)
            wheel = self.build_wheel(tdir)
            WheelDistribution(self.descriptor, wheel) \
                .install_to(env, build_packages_repo or pkm.repositories.pypi, user_request)

    @cached_property
    def directories(self) -> "ProjectDirectories":
        """
        :return: common project directories
        """
        return ProjectDirectories.create(self._pyproject)

    def remove_dependencies(self, packages: List[str]):
        """
        remove and uninstall all dependencies that are related to the given list of packages
        :param packages: the list of package names to remove
        """

        package_names_set = set(packages)
        self._default_env.remove(packages)

        self._pyproject.project = replace(
            self._pyproject.project,
            dependencies=[d for d in self._pyproject.project.dependencies if d.package_name not in package_names_set])

    def install_dependencies(self, new_dependencies: Optional[List[Dependency]] = None):
        """
        install the dependencies of this project to its assigned environments
        :param new_dependencies: if given, resolve and add these dependencies to this project and then install
        """
        deps = {d.package_name: d for d in (self._pyproject.project.dependencies or [])}
        new_deps = {d.package_name: d for d in new_dependencies} if new_dependencies else {}

        all_deps = {**deps, **new_deps}

        self._default_env.install(list(all_deps.values()), self._repository)

        self._pyproject.project = replace(
            self._pyproject.project,
            dependencies=[d for d in deps.values() if d.package_name not in new_deps] + list(new_deps.values()))

    def _reload(self):
        clear_cached_properties(self)

    @cached_property
    def _repository(self) -> "_ProjectRepository":
        return _ProjectRepository(self)

    @cached_property
    def _default_env(self) -> Environment:
        default_env = Environment(self._path / '.venv')
        if not default_env.path.exists():
            requirement = self._pyproject.project.requires_python
            python_versions = pkm.repositories.installed_pythons.match(Dependency('python', requirement))
            if not python_versions:
                raise NoSuchElementException("could not find installed python interpreter "
                                             f"that match the project requirements: {requirement}")
            python_versions[0].install_to(default_env)
        return default_env

    def build_sdist(self, target_dir: Optional[Path]) -> Path:
        """
        build a source distribution from this project
        :param target_dir: the directory to put the created archive in
        :return: the path to the created archive
        """

        target_dir = target_dir or (self.directories.dist / str(self.version))

        with _build_context() as bc:
            sdist_path = target_dir / bc.sdist_file_name()
            data_dir = bc.build_dir / sdist_path[:-len('.tar.gz')]
            data_dir.mkdir()

            dist_info_path = bc.build_dir / 'dist-info'
            bc.build_dist_info(dist_info_path)
            shutil.copy(dist_info_path / "METADATA", data_dir / "PKG_INFO")
            shutil.copy(bc.pyproject.path, data_dir / 'pyproject.toml')
            bc.copy_sources(data_dir / 'src')

            with tarfile.open(sdist_path, 'w:gz', format=tarfile.PAX_FORMAT) as sdist:
                for file in data_dir.glob('*'):
                    sdist.write(file, file.relative_to(bc.build_dir))

        return sdist_path

    def build_wheel(self, target_dir: Optional[Path], only_meta: bool = False) -> Path:
        """
        build a wheel distribution from this project
        :param target_dir: directory to put the resulted wheel in
        :param only_meta: if True, only builds the dist-info directory otherwise the whole wheel
        :return: path to the built artifact (directory if only_meta, wheel archive otherwise)
        """

        target_dir = target_dir or (self.directories.dist / str(self.version))

        with _build_context() as bc:
            if only_meta:
                dist_info_path = target_dir / bc.dist_info_dir_name()
                bc.build_dist_info(dist_info_path)
                return dist_info_path

            dist_info_path = bc.build_dir / bc.dist_info_dir_name()
            bc.build_dist_info(dist_info_path)
            bc.copy_sources(bc.build_dir)

            wheel_path = target_dir / bc.wheel_file_name()
            target_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(wheel_path, 'w') as wheel:
                for file in bc.build_dir.rglob('*'):
                    wheel.write(file, file.relative_to(bc.build_dir))

        return wheel_path

    def publish(self, repository: Union[Repository, RepositoryPublisher], auth: Authentication,
                distributions_dir: Optional[Path] = None):

        """
        publish this project distributions, as found in the given `distributions_dir` to the given `repository`.
        using `auth` for authentication

        :param repository: the repository to publish to
        :param auth: authentication for this repository
        :param distributions_dir: directory containing the distributions (archives like wheels and sdists) to publish
        """

        distributions_dir = distributions_dir or (self.directories.dist / str(self.version))

        if not distributions_dir.exists():
            raise FileNotFoundError(f"{distributions_dir} does not exists")

        publisher = repository if isinstance(repository, RepositoryPublisher) else repository.publisher
        if not publisher:
            raise UnsupportedOperationException(f"the given repository ({repository.name}) is not publishable")

        metadata = PackageMetadata.from_project_config(self._pyproject.project)
        for distribution in distributions_dir.iterdir():
            if distribution.is_file():
                publisher.publish(auth, metadata, distribution)

    @classmethod
    def load(cls, path: Path) -> "Project":
        pyproject = PyProjectConfiguration.load(path / 'pyproject.toml')
        return Project(pyproject)


class _ProjectRepository(Repository):

    def __init__(self, project: Project):
        super().__init__(f"{project.name}'s repository")
        self.project = project

    def _do_match(self, dependency: Dependency) -> List[Package]:
        if dependency.package_name == self.project.name:
            return [self.project]

        # TODO: the usage of pypi is only temporary until we will handle the use-case of custom repositories
        return pkm.repositories.pypi.match(dependency, False)

    def accepts(self, dependency: Dependency) -> bool:
        return pkm.repositories.pypi.accepts(dependency)


@dataclass
class _BuildContext:
    pyproject: PyProjectConfiguration
    build_dir: Path
    project_name_underscore: str

    def wheel_file_name(self) -> str:
        project_cfg = self.pyproject.project
        min_interpreter: StandardVersion = project_cfg.requires_python.min.version \
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
        dirs = ProjectDirectories.create(self.pyproject)

        for package_dir in dirs.src_packages:
            destination = dst / package_dir.name
            if package_dir.exists():
                shutil.copytree(package_dir, destination, ignore=ignore_patterns('__pycache__'))
            else:
                raise FileNotFoundError(f"the package {package_dir}, which is specified in pyproject.toml"
                                        " has no corresponding directory in project")


@contextmanager
def _build_context() -> ContextManager[_BuildContext]:
    pyproject = PyProjectConfiguration.load_effective(Path("pyproject.toml"), None)
    project_cfg: ProjectConfig = pyproject.project

    project_name_underscores = project_cfg.name.replace('-', '_')

    with TemporaryDirectory() as tdir:
        build_dir = Path(tdir)

        yield _BuildContext(pyproject, build_dir, project_name_underscores)


@dataclass()
class ProjectDirectories:
    src_packages: List[Path]
    dist: Path

    @classmethod
    def create(cls, pyproject: PyProjectConfiguration) -> "ProjectDirectories":
        project_path = pyproject.path.parent
        packages_relative = pyproject.pkm_project.packages
        if packages_relative:
            packages = [project_path / p for p in packages_relative]
        else:
            if not (src_dir := project_path / 'src').exists():
                raise FileNotFoundError("source directory is not found and "
                                        "`tool.pkm.project.packages` is not declared in pyproject.toml")
            packages = [p for p in src_dir.iterdir() if p.is_dir()]

        return ProjectDirectories(packages, project_path / 'dist')

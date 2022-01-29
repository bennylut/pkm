from dataclasses import dataclass, replace
from pathlib import Path
from typing import List, Optional, Union, Tuple, Dict, TYPE_CHECKING

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import Package, PackageDescriptor
from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.packages.package_monitors import PackageOperationsMonitor, HasBuildStepMonitor
from pkm.api.pkm import pkm
from pkm.api.projects.project_monitors import ProjectOperationsMonitor
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, PkmRepositoryInstanceConfig
from pkm.api.repositories.repository import Repository, RepositoryPublisher, Authentication
from pkm.api.repositories.repository_monitors import RepositoryOperationsMonitor
from pkm.api.versions.version import StandardVersion, Version
from pkm.api.versions.version_specifiers import VersionRange, SpecificVersion
from pkm.resolution.packages_lock import PackagesLock
from pkm.utils.commons import UnsupportedOperationException, NoSuchElementException
from pkm.utils.files import temp_dir
from pkm.utils.iterators import first_or_none
from pkm.utils.monitors import no_monitor
from pkm.utils.properties import cached_property, clear_cached_properties

if TYPE_CHECKING:
    from pkm.api.projects.project_group import ProjectGroup


class Project(Package):

    def __init__(self, pyproject: PyProjectConfiguration):
        self._path = pyproject.path.absolute().parent
        self._pyproject = pyproject
        self._descriptor = pyproject.project.package_descriptor()

    @property
    def config(self) -> PyProjectConfiguration:
        return self._pyproject

    @cached_property
    def group(self) -> Optional["ProjectGroup"]:
        from pkm.api.projects.project_group import ProjectGroup
        return ProjectGroup.of(self)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def descriptor(self) -> PackageDescriptor:
        return self._descriptor

    def _all_dependencies(self, environment: "Environment", monitor: PackageOperationsMonitor) -> List["Dependency"]:
        return self._pyproject.project.all_dependencies

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._pyproject.project.requires_python.allows_version(env.interpreter_version)

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None,
                   *, monitor: PackageOperationsMonitor = no_monitor(),
                   build_packages_repo: Optional["Repository"] = None):
        with monitor.on_install(self, env) as install_monitor:
            with temp_dir() as tdir:
                wheel = self.build_wheel(tdir, editable=True)
                distribution = WheelDistribution(self.descriptor, wheel)
                install_monitor.on_distribution_chosen(distribution)
                distribution.install_to(env, user_request)

    @cached_property
    def lock(self) -> PackagesLock:
        return PackagesLock.load(self.directories.etc_pkm / 'packages-lock.toml')

    @cached_property
    def directories(self) -> "ProjectDirectories":
        """
        :return: common project directories
        """
        return ProjectDirectories.create(self._pyproject)

    def bump_version(self, particle: str) -> Version:
        """
        bump up the version of this project
        :param particle: the particle of the version to bump, can be any of: major, minor, patch, a, b, rc
        :return: the new version after the bump
        """

        version: Version = self.config.project.version
        if not isinstance(version, StandardVersion) or not len(version.release) == 3:
            raise UnsupportedOperationException("cannot bump version that does not follow the semver semantics")

        new_version = version.bump(particle)
        self.config.project = replace(self.config.project, version=new_version)
        self.config.save()
        return new_version

    def remove_dependencies(self, packages: List[str]):
        """
        remove and uninstall all dependencies that are related to the given list of packages
        :param packages: the list of package names to remove
        """

        package_names_set = set(packages)
        self._pyproject.project = replace(
            self._pyproject.project,
            dependencies=[d for d in self._pyproject.project.dependencies if d.package_name not in package_names_set])
        self._pyproject.save()

        # fix installation metadata of the project by reinstalling it (without dependencies)
        self.default_environment.force_remove(self.name)
        self.install_to(self.default_environment, self.descriptor.to_dependency())

        self.default_environment.uninstall(packages)

        self.lock.update_lock(self.default_environment)
        self.lock.save()

    def install_with_dependencies(self, new_dependencies: Optional[List[Dependency]] = None, *,
                                  monitor: ProjectOperationsMonitor = no_monitor()):
        """
        install the dependencies of this project to its assigned environments
        :param monitor: monitor the operations made by this method
        :param new_dependencies: if given, resolve and add these dependencies to this project and then install
        """

        deps = {d.package_name: d for d in (self._pyproject.project.dependencies or [])}
        new_deps = {d.package_name: d for d in new_dependencies} if new_dependencies else {}
        uninvolved_deps = [d for d in deps.values() if d.package_name not in new_deps]

        self._pyproject.project = replace(
            self._pyproject.project,
            dependencies=uninvolved_deps + list(new_deps.values()))

        monitor.on_dependencies_modified(self, deps.values(), new_deps.values())

        with monitor.on_environment_modification(self) as env_ops_monitor:
            repository = _ProjectRepository(self)
            self.default_environment.force_remove(self.name)
            self.default_environment.install(
                self.descriptor.to_dependency(), repository, monitor=env_ops_monitor)

            new_deps_with_version = []
            for dep in new_deps.values():
                installed = self.default_environment.site_packages.installed_package(dep.package_name).version
                if isinstance(installed, StandardVersion):
                    spec = VersionRange(
                        SpecificVersion(installed),
                        SpecificVersion(replace(installed, release=(installed.release[0] + 1,))),
                        True, False)
                else:
                    spec = SpecificVersion(installed)

                new_deps_with_version.append(replace(dep, version_spec=spec))

            self._pyproject.project = replace(
                self._pyproject.project,
                dependencies=uninvolved_deps + new_deps_with_version
            )

            self._pyproject.save()
            monitor.on_pyproject_modified()

            self.lock.update_lock(self.default_environment)
            self.lock.save()
            monitor.on_lock_modified()

    def _reload(self):
        clear_cached_properties(self)

    @cached_property
    def default_environment(self) -> Environment:
        default_env = Environment(self._path / '.venv')
        if not default_env.path.exists():
            requirement = self._pyproject.project.requires_python
            python_versions = pkm.repositories.installed_pythons.match(Dependency('python', requirement))
            if not python_versions:
                raise NoSuchElementException("could not find installed python interpreter "
                                             f"that match the project requirements: {requirement}")
            python_versions[0].install_to(default_env)
        return default_env

    def build_application_installer(self, target_dir: Optional[Path] = None, *,
                                    monitor: ProjectOperationsMonitor = no_monitor()) -> Path:
        """
        builds a package that contains application installer for this project
        note that the installer is itself a project with the same name as this project appended with '-app'
        and therefore on publishing will require different project registration

        :param target_dir: the directory to put the installer in
        :param monitor: monitor the operations made by this method
        :return: the path to the created installer package
        """
        from pkm.project_builders.application_builders import build_app_installer
        return build_app_installer(self, target_dir, monitor=monitor)

    def build_sdist(self, target_dir: Optional[Path] = None, *,
                    monitor: ProjectOperationsMonitor = no_monitor()) -> Path:
        """
        build a source distribution from this project
        :param target_dir: the directory to put the created archive in
        :param monitor: monitor the operations made by this method
        :return: the path to the created archive
        """

        from pkm.project_builders.standard_builders import build_sdist
        return build_sdist(self, target_dir, monitor=monitor)

    def build_wheel(self, target_dir: Optional[Path] = None, only_meta: bool = False, editable: bool = False, *,
                    monitor: HasBuildStepMonitor = no_monitor()) -> Path:
        """
        build a wheel distribution from this project
        :param target_dir: directory to put the resulted wheel in
        :param only_meta: if True, only builds the dist-info directory otherwise the whole wheel
        :param editable: if True, a wheel for editable install will be created
        :param monitor: monitor the operations made by this method
        :return: path to the built artifact (directory if only_meta, wheel archive otherwise)
        """

        from pkm.project_builders.application_builders import is_application_installer_project, build_app_installation
        from pkm.project_builders.standard_builders import build_wheel

        if not only_meta and is_application_installer_project(self):
            return build_app_installation(self, target_dir, monitor=monitor)

        return build_wheel(self, target_dir, only_meta, editable, monitor=monitor)

    def build(self, target_dir: Optional[Path] = None, *,
              monitor: ProjectOperationsMonitor = no_monitor()) -> List[Path]:
        """
        builds the project into all distributions that are required as part of its configuration
        :param target_dir: directory to put the resulted distributions in
        :param monitor: monitor the operations made by this method
        :return list of paths to all the distributions created
        """
        result: List[Path] = [self.build_sdist(target_dir, monitor=monitor),
                              self.build_wheel(target_dir, monitor=monitor)]
        if self.config.pkm_project.application:
            result.append(self.build_application_installer(target_dir, monitor=monitor))

        return result

    def publish(self, repository: Union[Repository, RepositoryPublisher], auth: Authentication,
                distributions_dir: Optional[Path] = None, *, monitor: ProjectOperationsMonitor = no_monitor()):
        """
        publish/register this project distributions, as found in the given `distributions_dir` to the given `repository`.
        using `auth` for authentication

        :param repository: the repository to publish to
        :param auth: authentication for this repository
        :param distributions_dir: directory containing the distributions (archives like wheels and sdists) to publish
        :param monitor: monitor the operations made by this method
        """

        with monitor.on_publish(repository):
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

            print("publishing application project")
            if self.config.pkm_project.application:
                from pkm.project_builders.application_builders import application_installer_project_name, \
                    application_installer_dir
                metadata['Name'] = application_installer_project_name(self)
                if (app_installer_dist_dir := application_installer_dir(
                        distributions_dir)).exists() and app_installer_dist_dir.is_dir():
                    for distribution in app_installer_dist_dir.iterdir():
                        if distribution.is_file():
                            publisher.publish(auth, metadata, distribution)

    @classmethod
    def load(cls, path: Union[Path, str]) -> "Project":
        path = Path(path)
        pyproject = PyProjectConfiguration.load(path / 'pyproject.toml')
        return Project(pyproject)


class _ProjectRepository(Repository):

    def __init__(self, project: Project, env: Optional[Environment] = None):
        super().__init__(f"{project.name}'s repository")
        self.project = project
        self._env = env or project.default_environment

        group_settings = {
            p.name: {'path': str(p.path.absolute()), 'name': p.name, 'version': str(p.version)}
            for p in (project.group.project_children_recursive if project.group else [])
        }
        group_settings[project.name] = {'path': str(project.path.absolute()), 'name': project.name,
                                        'version': str(project.version)}
        self._group_repo = pkm.repository_builders['local'].build('project-group', group_settings)
        # self._group_repo = ProjectGroupRepository(project.group) if project.group else None

        built_repositories: List[Tuple[PkmRepositoryInstanceConfig, Repository]] = []
        for rcfg in project.config.pkm_repositories:
            if not (builder := pkm.repository_builders.get(rcfg.type)):
                raise KeyError(f"unknown repository type: {rcfg.type}")
            built_repositories.append((rcfg, builder.build(rcfg.name, rcfg.packages, **rcfg.args)))

        self._default_repo = pkm.repositories.pypi
        if default_repo := first_or_none(
                repository for repository_config, repository in built_repositories
                if '*' in repository_config.packages):
            self._default_repo = default_repo

        self.package_to_repo: Dict[str, Repository] = {
            package_name: repository
            for repository_config, repository in built_repositories
            for package_name in repository_config.packages.keys()
        }

    def _repository_for(self, d: Dependency) -> Repository:
        return self.package_to_repo.get(d.package_name, self._default_repo)

    def _do_match(self, dependency: Dependency, *, monitor: RepositoryOperationsMonitor) -> List[Package]:
        monitor.on_dependency_match(dependency)
        if dependency.package_name == self.project.name:
            return [self.project]

        if (gr := self._group_repo) and gr.accepts(dependency) and (gpacs := gr.match(dependency, False)):
            return gpacs

        return self._repository_for(dependency).match(dependency, False)

    def _sort_by_priority(self, dependency: Dependency, packages: List[Package]) -> List[Package]:
        return self.project.lock.sort_packages_by_lock_preference(self._env, packages)

    def accepts(self, dependency: Dependency) -> bool:
        return self._repository_for(dependency).accepts(dependency)


@dataclass()
class ProjectDirectories:
    src_packages: List[Path]
    dist: Path
    etc_pkm: Path

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

        etc_pkm = project_path / 'etc' / 'pkm'
        etc_pkm.mkdir(parents=True, exist_ok=True)
        return ProjectDirectories(packages, project_path / 'dist', etc_pkm)

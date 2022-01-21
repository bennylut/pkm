import shutil
from collections import defaultdict
from dataclasses import replace
from pathlib import Path
from textwrap import dedent
from typing import Optional, List

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import ObjectReference
from pkm.api.distributions.source_distribution import SourceDistribution
from pkm.api.environments.environment import Environment
from pkm.api.packages.package import PackageDescriptor, Package
from pkm.api.packages.package_monitors import PackageOperationsMonitor, HasBuildStepMonitor, PackageBuildMonitor
from pkm.api.projects.project import Project
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration
from pkm.api.repositories.repository import Repository
from pkm.utils.files import temp_dir
from pkm.utils.monitors import no_monitor
from pkm.utils.properties import cached_property


def build_app_installer(application_project: Project, target_dir: Optional[Path], *,
                        monitor: HasBuildStepMonitor = no_monitor()) -> Path:
    """
    builds a package that contains application installer for the given project
    :param application_project: the project to create the installer to
    :param target_dir: the directory to put the installer in
    :param monitor: monitor the operations made by this method
    :return: the path to the created installer package (sdist)
    """

    with monitor.on_build(application_project.descriptor, 'app') as build_monitor:
        target_dir = target_dir or (application_project.directories.dist / str(application_project.version))
        target_dir.mkdir(parents=True, exist_ok=True)

        with temp_dir() as tdir:
            installer_project_name = application_project.name + '-app'

            # create source for the different entrypoints
            installer_source_dir = tdir / 'src' / PackageDescriptor.normalize_name(installer_project_name) \
                .replace('-', '_')
            installer_source_dir.mkdir(parents=True)

            new_entrypoints = defaultdict(list)
            for entrypoint in application_project.config.project.script_entrypoints():
                entrypoint_module = f"{installer_source_dir.name}.{entrypoint.name}"
                new_entrypoints[entrypoint.group].append(
                    replace(entrypoint, ref=ObjectReference(entrypoint_module, "main")))

                (installer_source_dir / f"{entrypoint.name}.py").write_text(dedent(f"""
                    import sys
                    import os 
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '__package_layer__'))
    
                    def main():
                        {entrypoint.ref.execution_script_snippet()}
                    """))

            installer_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installer_pyproject.project = replace(
                application_project.config.project,
                name=application_project.name + '-app',
                dependencies=[],
                entry_points=new_entrypoints
            )

            installer_pyproject['tool.pkm.internal.package'] = {
                'type': 'application-installer',
            }

            installer_pyproject.build_system = replace(
                application_project.config.build_system,
                requirements=application_project.config.build_system.requirements + [
                    application_project.descriptor.to_dependency()])

            installer_pyproject.save()
            installer_project = Project.load(tdir)
            return installer_project.build_sdist(target_dir)


def is_application_installer_project(project: Project) -> bool:
    """
    :param project: the project to check
    :return: true if the given project is application installer project, false otherwise
    """

    return project.config['tool.pkm.internal.package.type'] == 'application-installer'


def build_app_installation(installer_project: Project, output_dir: Path, *,
                           monitor: HasBuildStepMonitor = no_monitor()) -> Path:
    """
    build installation package (wheel) from the given `installer_project` and put it inside the given `output_dir`
    this process will resolve and download all the required artifacts, create the "embedded environment"
    for the application and the patch the entrypoints to use it (TODO)
    :param installer_project: installer project, created using the `ApplicationInstaller.build_app_installer` method
    :param output_dir: installation package (wheel) which contain the application in an embedded environment
           in addition to the entrypoints which will be patched to use the embedded environment
    :param monitor: monitor the operations made by this method
    :return: path to the created installation package
    """

    with monitor.on_build(installer_project.descriptor, 'wheel') as build_monitor:

        with temp_dir() as tdir:

            # create installation project
            installation_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installation_pyproject['project'] = installer_project.config['project']

            # copy installer source to installation project
            package_name = PackageDescriptor.normalize_name(installer_project.name).replace('-', '_')
            installation_src = tdir / 'src' / package_name
            shutil.copytree(installer_project.path / 'src' / package_name, installation_src)

            # moving the dependencies to the installer source under __package_layer__
            # currently assumes that this process lives in a build dedicated environment
            current_env = Environment.current()
            current_env_sites = list(current_env.site_packages.all_sites())
            package_layer = installation_src / "__package_layer__"
            package_layer.mkdir(exist_ok=True, parents=True)

            for d in current_env_sites:
                if d.exists() and current_env.path in d.parents:
                    shutil.copytree(d, package_layer, symlinks=True, dirs_exist_ok=True)

            # build the wheel for the installation project
            installation_pyproject.save()
            installation_project = Project.load(tdir)

            class _MonitorProvider(HasBuildStepMonitor):
                def on_build(self, package: PackageDescriptor, artifact: str) -> PackageBuildMonitor:
                    return build_monitor

            return installation_project.build_wheel(output_dir, monitor=_MonitorProvider())


class ApplicationInstallerProjectWrapper(Package):
    def __init__(self, project: Project):
        self._project = project

    @property
    def wrapped_project(self) -> Project:
        return self._project

    @cached_property
    def descriptor(self) -> PackageDescriptor:
        return PackageDescriptor(self._project.name + "-app", self._project.version)

    def _all_dependencies(self, environment: "Environment", monitor: PackageOperationsMonitor) -> List["Dependency"]:
        return []

    def is_compatible_with(self, env: "Environment") -> bool:
        return self._project.is_compatible_with(env)

    def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None, *,
                   monitor: PackageOperationsMonitor = no_monitor(),
                   build_packages_repo: Optional["Repository"] = None):
        with temp_dir() as tdir:
            installer = self._project.build_application_installer(tdir)
            distribution = SourceDistribution(self.descriptor, installer, build_packages_repo)
            distribution.install_to(env, user_request)

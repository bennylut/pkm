import os
import shutil
from dataclasses import replace
from importlib.resources import path
from pathlib import Path
from typing import List, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.lightweight_environment_builder import LightweightEnvironments
from pkm.api.packages.package import PackageDescriptor
from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration
from pkm.api.repositories.repository import Repository
from pkm.applications.application_loader import PACKAGE_LAYER
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.entrypoints import EntryPoint
from pkm.utils.files import temp_dir


class Application:
    def __init__(self, project: Project):
        self._project = project

    def build_installation_package(self, target_dir: Path, repository: Optional[Repository] = None) -> Path:
        """
        build installation package (wheel) from the given `installer_project` and put it inside the given `target_dir`
        this process will resolve and download all the required artifacts, create the "embedded environment"
        for the application and the patch the entrypoints to use it
        :param target_dir: installation package (wheel) which contain the application in an embedded environment
               in addition to the entrypoints which will be patched to use the embedded environment
        :param repository: the repository to download the actual application from
        :return: path to the created installation package
        """

        print("building installation package!")

        repository = repository or pkm.repositories.main

        with temp_dir() as tdir:
            # create installation project
            print("creating installation source")
            installation_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installation_pyproject['project'] = self._project.config['project']
            installation_pyproject.build_system = self._project.config.build_system

            # copy installer source to installation project
            print("copying installation entrypoints")
            if not (app_dep := self._project.config['tool.pkm.application-installer.app']):
                raise ValueError("malformed installer package")

            app_dep = Dependency.parse_pep508(app_dep)
            package_name = PackageDescriptor.normalize_source_dir_name(app_dep.package_name)
            installation_src = tdir / 'src' / package_name
            shutil.copytree(self._project.path / 'src' / package_name, installation_src)

            print("downloading dependencies")
            env = LightweightEnvironments.create(tdir / 'env')
            env.install(app_dep, repository)

            print("moving dependencies from temporary env into package layer")
            package_layer = installation_src / PACKAGE_LAYER
            package_layer.parent.mkdir(exist_ok=True, parents=True)
            shutil.move(env.site_packages.purelib_path, package_layer)

            # build the wheel for the installation project
            print("building wheel")
            installation_pyproject.save()
            installation_project = Project.load(
                tdir, PackageDescriptor(app_dep.package_name, app_dep.version_spec.min))

            return installation_project.build_wheel(target_dir)

    def build_installer_package(self, target_dir: Path) -> Path:
        """
        builds a package that contains application installer for the internal project
        :param target_dir: the directory to put the installer in
        :return: the path to the created installer package (sdist)
        """

        target_dir = (target_dir or (self._project.directories.dist / str(self._project.version))) / 'app'
        target_dir.mkdir(parents=True, exist_ok=True)

        application_config = self._project.config.pkm_application
        if not (installer_project_name := application_config.installer_package):
            raise UnsupportedOperationException(
                f"cannot create installer to application {self._project.name}, no installer package defined")

        with temp_dir() as tdir:
            # create source for the different entrypoints
            installer_source_dir = tdir / 'src'
            installer_source_dir.mkdir(parents=True)

            epoints_writer = _ApplicationEntrypointsWriter(
                installer_source_dir, self._project.descriptor.expected_source_package_name)

            epoints_writer.add_entrypoints(self._project.config.project.all_entrypoints())

            installer_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installer_pyproject.project = replace(
                self._project.config.project,
                name=installer_project_name,
                dependencies=[],
            )

            installer_pyproject['tool.pkm.application-installer'] = {
                'app': str(self._project.descriptor.to_dependency())
            }

            installer_pyproject.build_system = self._project.config.build_system

            installer_pyproject.save()
            installer_project = Project.load(tdir)
            return installer_project.build_sdist(target_dir)

    @staticmethod
    def is_application(project: Project) -> bool:
        return project.config.pkm_application.installer_package is not None

    @staticmethod
    def is_application_installer(project: Project) -> bool:
        return project.config['tool.pkm.application-installer.app'] is not None


class _ApplicationEntrypointsWriter:

    def __init__(self, source_path: Path, app_pacakge: str):
        self._source = source_path
        self._app_package = app_pacakge

        source_pacakge = source_path / app_pacakge.replace('.', '/')
        source_pacakge.mkdir(exist_ok=True, parents=True)
        with path('pkm.applications', 'application_loader.py') as p, (
                source_pacakge / '__app__.py').open('w+') as pw:
            pw.write(p.read_text())
            pw.write(os.linesep)
            pw.write(f"app = ApplicationLoader('{app_pacakge}')")
            pw.write(os.linesep)

    def add_entrypoints(self, epoints: List[EntryPoint]):
        modules_to_export = {e.ref.module_path for e in epoints}

        module: str
        for module in modules_to_export:
            module_file = self._source / module.replace(".", "/") / "__init__.py"
            module_file.parent.mkdir(exist_ok=True, parents=True)
            module_file.write_text(
                f"from {self._app_package}.__app__ import app; globals().update(vars(app.load('{module}')))")

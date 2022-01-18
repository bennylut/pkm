import sys
from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.environments.lightweight_environment_builder import LightweightEnvironments
from pkm.api.projects.project import Project
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration
from pkm.api.repositories.repository import Repository
from pkm.utils.files import temp_dir


class ApplicationInstaller:

    @staticmethod
    def build_app_installer(application_project: Project, output_dir: Path) -> Path:
        """
        builds a package that contains application installer for the given project
        :param application_project: the project to create the installer to
        :param output_dir: the directory to put the installer in
        :return: the path to the created installer package (sdist)
        """
        with temp_dir() as tdir:
            installer_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installer_pyproject['project'] = application_project.pyproject['project']
            installer_pyproject['project.name'] = application_project.name + '-app'
            installer_pyproject['project.dependencies'] = []
            installer_pyproject['tool.pkm.internal.package'] = {
                'type': 'application',
                'app': str(application_project.descriptor.to_dependency()),
            }

            installer_pyproject.save()
            installer_project = Project.load(tdir)

            (tdir / 'src').mkdir()

            return installer_project.build_sdist(output_dir)

    @staticmethod
    def build_installation(installer_project: Project, repository: Repository, output_dir: Path) -> Path:
        """
        build installation package (wheel) from the given `installer_project` and put it inside the given `output_dir`
        this process will resolve and download all the required artifacts, create the "embedded environment" for the application
        and the patch the entrypoints to use it (TODO)
        :param installer_project: installer project, created using the `ApplicationInstaller.build_app_installer` method
        :param repository: the repository to fetch artifacts from
        :param output_dir: installation package (wheel) which contain the application in an embedded environment
               in addition to the entrypoints which will be patched to use the embedded environment
        :return: path to the created installation package
        """

        with temp_dir() as tdir:
            # need to create a project and add the entrypoint source code into it
            # need to also supply it with the actual entry points and then finally create a whl from it

            installation_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
            installation_src = tdir / 'src'
            installation_pyproject['project'] = installer_project.pyproject['project']

            emb_env_dir = installation_src / "__embedded_env__"
            emb_env = LightweightEnvironments.create(emb_env_dir, Path(sys.executable))
            pre_existing_binaries = list(Path(emb_env.paths['scripts']).iterdir())

            app_dependency = Dependency.parse_pep508(installer_project.pyproject['tool.pkm.internal.package.app'])
            emb_env.install(app_dependency, repository)

            for binary in pre_existing_binaries:
                binary.unlink(missing_ok=True)

            (emb_env_dir / 'lib64').unlink(True)

            installation_pyproject.save()
            installation_project = Project.load(tdir)
            return installation_project.build_wheel(output_dir)


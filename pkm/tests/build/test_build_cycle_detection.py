from unittest import TestCase

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment_builder import EnvironmentBuilder
from pkm.api.packages.package import PackageDescriptor
from pkm.api.projects.project import Project
from pkm.api.repositories.repository_management import ProjectsRepository
from pkm.api.versions.version import Version
from pkm.utils.files import temp_dir, mkdir


class TestBuildCycleDetector(TestCase):
    def test_project_requires_itself(self):
        with temp_dir() as tdir:
            project = Project.load(mkdir(tdir / "project"), PackageDescriptor('test-project', Version.parse('1.0.0')))
            project.config.build_system.requirements = [Dependency.parse("test-project >= 1.0.0")]
            repository = ProjectsRepository.create('test', [project])

            # noinspection PyPropertyAccess
            project.repository_management.attached_repo = repository

            temp_env = EnvironmentBuilder.create(tdir / 'env')
            temp_env.install([project.descriptor.to_dependency()], repository=repository)

    def test_cycle(self):
        with temp_dir() as tdir:
            project1 = Project.load(mkdir(tdir / "project1"),
                                    PackageDescriptor('test-project1', Version.parse('1.0.0')))
            project1.config.build_system.requirements = [Dependency.parse("test-project2 >= 1.0.0")]

            project2 = Project.load(mkdir(tdir / "project2"),
                                    PackageDescriptor('test-project2', Version.parse('1.0.0')))
            project2.config.build_system.requirements = [Dependency.parse("test-project1 >= 1.0.0")]

            repository = ProjectsRepository.create('test', [project1, project2])

            # noinspection PyPropertyAccess
            project1.repository_management.attached_repo = repository
            # noinspection PyPropertyAccess
            project2.repository_management.attached_repo = repository

            temp_env = EnvironmentBuilder.create(tdir / 'env')
            temp_env.install([project1.descriptor.to_dependency()], repository=repository)

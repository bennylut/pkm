# # # from pathlib import Path
# # #
# # # from pkm.api.distributions.source_distribution import SourceDistribution
# # # from pkm.api.environments.environment import Environment
# # # from pkm.api.packages.package import PackageDescriptor
# # # from pkm.api.projects.project import Project
# # # from pkm.api.versions.version import Version
# # # from pkm.applications.application import Application
# # # from pkm_cli.cli_monitors import listen
# # #
# # # listen(True)
# # #
# # # p = Path("/home/bennyl/projects/pkm-new/repositories/pkm-conda-repository")
# # # e = Path("/home/bennyl/projects/pkm-new/repositories/pkm-conda-repository/dist/app/env")
# # #
# # # # env = LightweightEnvironments.create(e)
# # # env = Environment(e)
# # # prj = Project.load(p)
# # # app = Application(prj)
# # #
# # # # ip = app.build_installer_package(prj.directories.dist)
# # # ip = Path("/home/bennyl/projects/pkm-new/repositories/pkm-conda-repository/dist/app/"
# # #           "pkm_conda_repository_app-0.1.0.tar.gz")
# # # SourceDistribution(PackageDescriptor("pkm-conda-repository-app", Version.parse("0.1.0")), ip).install_to(env)
from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.projects.project import Project
from pkm_cli.cli_monitors import listen

listen(True)
p = Path("/home/bennyl/projects/pkm-new/repositories/pkm-ltt-repository")
Project.load(p).install_with_dependencies([Dependency.parse("pkm")])
# from pkm.api.dependencies.dependency import Dependency
#
# print(Dependency.parse("pip (<20.3.*,>=20.1.*)"))

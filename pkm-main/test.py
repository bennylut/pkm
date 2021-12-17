from pathlib import Path

from pkm.config.configuration import IniFileConfiguration

from pkm_main.environments.standard_environments_zoo import StandardEnvironmentsZoo
from pkm_main.installation.wheel_installer import WheelInstaller

workspace = Path("/home/bennyl/projects/pkm-new/workspace")
zoo = StandardEnvironmentsZoo(workspace / 'env-zoo')

menv = zoo.create_environment('bamba', 'python >= 3.6')
# menv = zoo.load_environment('bamba', False)

installer = WheelInstaller()
installer.install(menv.environment, Path('/home/bennyl/projects/pkm-new/workspace/whl-test/xxx.whl'))

# from pathlib import Path
#
# from pkm_main.environments.standard_environments_zoo import StandardEnvironmentsZoo
#
# workspace = Path("/home/bennyl/projects/pkm-new/workspace")
# zoo = StandardEnvironmentsZoo(workspace / 'env-zoo')
# x = zoo.create_environment('bamba', 'python > 3.6, <3.8')
# print(x.environment.interpreter_version)
#
# # # from pathlib import Path
# # #
# # # from pkm_main.environments.virtual_environment import UninitializedVirtualEnvironment
# # # from pkm_main.repositories.local_pythons_repository import LocalPythonsRepository
# # #
# # # venv = UninitializedVirtualEnvironment(Path("/home/bennyl/projects/pkm-new/workspace/venvs/test1"))
# # # lpr = LocalPythonsRepository()
# # # packages = lpr.match("python ~=3.6.0")
# # # print(packages)
# # #
# # # packages[0].install_to(venv)
# # #
# # #
# # #
# # from pathlib import Path
# #
# # from pkm.api.dependencies.dependency import Dependency
# #
# # from pkm_main.environments.virtual_environment import VirtualEnvironment
# # from pkm_main.installation.package_installation_plan import PackageInstallationPlan
# # from pkm_main.installation.packages_lock import PackagesLock
# # from pkm_main.repositories.pypi_repository import PyPiRepository
# # from pkm_main.utils.http.http_client import HttpClient
# #
# # workspace = Path("/home/bennyl/projects/pkm-new/workspace")
# # http = HttpClient(workspace / "cache/http")
# # pypi = PyPiRepository(http)
# #
# # env = VirtualEnvironment(Path("/home/bennyl/projects/pkm-new/workspace/venvs/test1"))
# #
# # iplan = PackageInstallationPlan.create(Dependency.parse_pep508('allennlp *'), env, pypi, PackagesLock())
# # print({p.name: p.version for p in iplan.packages_to_install})
# # print(iplan)
# # # #
# # # #
# # # # # packages = pypi.list('pandas')
# # # # # for package in packages:
# # # # #     if package.is_compatible_with(env):
# # # # #         print(f"package {package} is compatible, fetching deps")
# # # # #         deps = package.dependencies(env)
# # # # #         print(deps)
# # # # #     else:
# # # # #         print(f"package {package} is NOT compatible")
# # # # # print(packages)

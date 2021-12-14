from pathlib import Path

from pkm.api.dependencies.dependency import Dependency

from pkm_main.environments.virtual_environment import VirtualEnvironment
from pkm_main.installation.package_installation_plan import PackageInstallationPlan
from pkm_main.installation.packages_lock import PackagesLock
from pkm_main.repositories.pypi_repository import PyPiRepository
from pkm_main.utils.http.http_client import HttpClient

workspace = Path("/home/bennyl/projects/pkm-new/workspace")
http = HttpClient(workspace / "cache/http")
pypi = PyPiRepository(http)

env = VirtualEnvironment(Path("/home/bennyl/projects/pkm-new/.venv"))

# ppp = pypi.match(Dependency.parse_pep508('fairscale ==0.4.0'))
# ppp[0].is_compatible_with(env)

ppp = pypi.match("cached-path ==0.3.1")
print(ppp)



packages = pypi.match(Dependency.parse_pep508('allennlp ==2.8.0'))
package = packages[0]

iplan = PackageInstallationPlan.create(package, env, pypi, PackagesLock())
print({p.name: p.version for p in iplan.packages_to_install})
print(iplan)


# packages = pypi.list('pandas')
# for package in packages:
#     if package.is_compatible_with(env):
#         print(f"package {package} is compatible, fetching deps")
#         deps = package.dependencies(env)
#         print(deps)
#     else:
#         print(f"package {package} is NOT compatible")
# print(packages)

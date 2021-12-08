from pathlib import Path

from pkm.api.dependencies.dependency import RepositoryDependency
from pkm.api.versions.version_specifiers import VersionSpecifier

from pkm_main.environments.virtual_environment import VirtualEnvironment
from pkm_main.repositories.pypi_repository import PyPiRepository
from pkm_main.utils.http.http_client import HttpClient

workspace = Path("/home/bennyl/projects/pkm-new/workspace")
http = HttpClient(workspace / "cache/http")
pypi = PyPiRepository(http)

env = VirtualEnvironment(Path("/home/bennyl/projects/pkm-new/.venv"))

packages = pypi.list('pandas')
for package in packages:
    if package.is_compatible_with(env):
        print(f"package {package} is compatible, fetching deps")
        deps = package.dependencies(env)
        print(deps)
    else:
        print(f"package {package} is NOT compatible")
print(packages)

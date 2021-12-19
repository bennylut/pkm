from pathlib import Path

from pkm_main.environments.standard_environments_zoo import StandardEnvironmentsZoo
from pkm_main.repositories.pypi_repository import PyPiRepository
from pkm_main.utils.http.http_client import HttpClient

workspace = Path("/home/bennyl/projects/pkm-new/workspace")
zoo = StandardEnvironmentsZoo(workspace / 'env-zoo')
http = HttpClient(workspace / "cache/http")
pypi = PyPiRepository(http)

menv = zoo.create_environment('bamba', 'python >= 3.6')
menv.environment.install('pandas *', pypi)

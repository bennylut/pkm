from pathlib import Path

from pkm.api.environments.environment import Environment
from pkm.api.environments.lightweight_environment_builder import LightweightEnvironmentBuilder

from pkm_main.repositories.pypi_repository import PyPiRepository
from pkm_main.utils.http.http_client import HttpClient


python3_8 = Path("/usr/bin/python3.8")
env_path = Path("/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/yyy")
env = LightweightEnvironmentBuilder.create(env_path, python3_8)

#
workspace = Path("/home/bennyl/projects/pkm-new/workspace")
http = HttpClient(workspace / "cache/http")

pypi = PyPiRepository(http)
#
# env_path = Path("/home/bennyl/projects/pkm-new/workspace/env-zoo/envs/xxx")
# env = Environment(env_path)
#
env.install('pandas *', pypi)

from pkm.api.environments.environment import Environment
from src.conda_pkm_repo.conda_repo import CondaRepository

env = Environment.load("/home/bennyl/projects/pkm-new/workspace/test-env")
conda_repo = CondaRepository()
env.install("pandas", repository=conda_repo)

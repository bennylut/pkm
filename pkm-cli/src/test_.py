# from pkm_cli.main import main
# main(['-c', "/home/bennyl/projects/pkm-group/workspace/xxx", "install", "allennlp"])
from pathlib import Path

from pkm.api.projects.pyproject_configuration import PyProjectConfiguration

pp = PyProjectConfiguration.load_effective(Path("/home/bennyl/projects/pkm-group/workspace/termcolor-1.1.0/pyproject.toml"))
print(pp.build_system)
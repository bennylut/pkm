from dataclasses import replace
from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration

# from pkm.config import toml
#
# data, dumps = toml.load("/home/bennyl/projects/pkm-new/pkm-cli/pyproject.toml")
# data['project']['dependencies'] = [*data['project']['dependencies'], 'xxx']
# print(dumps(data))

pypr = PyProjectConfiguration.load(Path("/home/bennyl/projects/pkm-new/pkm-cli/pyproject.toml"))
pypr.project = replace(pypr.project, dependencies=pypr.project.dependencies + [Dependency.parse("xxx")])
print(pypr.generate_content())

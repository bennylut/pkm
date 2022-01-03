from pathlib import Path

from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.repositories.repository import Authentication

project = Project.load(Path('/home/bennyl/projects/pkm-new'))
# project.build_wheel()
project.build_sdist()

project.publish(pkm.repositories.pypi, Authentication('bennyl', 'a5v583wd'))
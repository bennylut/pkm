from pathlib import Path

from pkm.api.pkm import pkm
from pkm.api.projects.project import Project
from pkm.api.repositories.repository import Authentication

project = Project.load(Path("/home/bennyl/projects/pkm-new/pkm-cli"))
# project.install_with_dependencies()
project.build()


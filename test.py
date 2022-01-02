from pathlib import Path

from pkm.api.projects.project import Project

project = Project.load(Path("/home/bennyl/projects/pkm-new"))
# project.install_dependencies()
project.build_wheel(Path("/home/bennyl/projects/pkm-new/dist"))

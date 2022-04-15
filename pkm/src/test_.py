from pathlib import Path

from pkm.api.projects.project import Project

Project.load(Path("/home/bennyl/projects/pkm-new/pkm-cli")).build()  # .install_with_dependencies()

from pathlib import Path

from pkm.api.projects.project import Project

p = Project.load(Path("/home/bennyl/projects/pkm-new/workspace/projects/p1"))

p.install_dependencies()

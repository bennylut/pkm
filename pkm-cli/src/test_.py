from pathlib import Path

from pkm.api.projects.project import Project
from pkm_cli import cli_monitors

cli_monitors.listen(True)
Project.load(Path("/home/bennyl/projects/pkm-new/workspace/projects/p1")).install_with_dependencies()

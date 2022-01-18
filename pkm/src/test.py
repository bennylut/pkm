# from pathlib import Path
#
# from pkm.api.applications.application_installer import ApplicationInstaller
# from pkm.api.projects.project import Project, _ProjectRepository
#
# test_apps_path = Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-apps")
# pkm_cli_path = Path("/home/bennyl/projects/pkm-new/pkm-cli")
# pkm_cli_project = Project.load(pkm_cli_path)
#
# installation = ApplicationInstaller.build_installation(
#     Project.load(Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-apps/pkm_cli_app-0.1.0")),
#     _ProjectRepository(pkm_cli_project), test_apps_path)
from pathlib import Path

from pkm.api.projects.project import Project

p2 = "/home/bennyl/projects/pkm-new/workspace/projects/p2"
Project.load(Path(p2)).install_dependencies()

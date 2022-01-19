# from pathlib import Path
#
# from pkm.project_builders.application_installers import ApplicationInstallers
# from pkm.api.projects.project import Project, _ProjectRepository
#
# test_apps_path = Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-apps")
# pkm_cli_path = Path("/home/bennyl/projects/pkm-new/pkm-cli")
# pkm_cli_project = Project.load(pkm_cli_path)
#
# # ApplicationInstallers.build_app_installer(pkm_cli_project, Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-apps"))
#
# installation = ApplicationInstallers.build_installation(
#     Project.load(Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-apps/pkm_cli_app-0.1.0")),
#     _ProjectRepository(pkm_cli_project), test_apps_path)
#
# # from pathlib import Path
# #
# # from pkm.api.projects.project import Project
# #
# # p2 = "/home/bennyl/projects/pkm-new/workspace/projects/p2"
# # Project.load(Path(p2)).install_dependencies()
from pathlib import Path

from pkm.api.projects.project import Project

Project.load(Path("/home/bennyl/projects/pkm-new/workspace/projects/p1")).install_with_dependencies()
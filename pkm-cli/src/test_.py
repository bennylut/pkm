from pathlib import Path

from pkm.api.projects.project import Project
from pkm_cli.cli_monitors import listen

listen(True)
Project.load(Path("/home/bennyl/projects/pkm-new/pkm-cli")).install_with_dependencies()


# env = EnvironmentBuilder.create(Path("/home/bennyl/projects/pkm-new/workspace/tmp/venv"))
# env = Environment(Path("/home/bennyl/projects/pkm-new/workspace/tmp/venv"))
# env.default_installation_target.app_containers.install(Dependency.parse("jupyterlab"))

# fake_pyproject = PyProjectConfiguration(path=None)
# fake_pyproject.project = ProjectConfig.from_config({"name": "testit", "version": "1.2.3"})
# fake_pyproject.pkm_application = PkmApplicationConfig(
#     True, inner_deps=[Dependency.parse("jupyterlab")],
#     inner_deps_overwrites={},
#     exposed_inner_apps=["jupyterlab"]
# )
#
# fake_project = Project(fake_pyproject)
# build_wheel(fake_project, Path("/home/bennyl/projects/pkm-new/workspace/tmp"))

from pathlib import Path

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.projects.project import Project
from pkm_cli.cli_monitors import listen

listen(True)
# Project.load(Path("/home/bennyl/projects/pkm-new/pkm-cli")).install_with_dependencies()
env = Environment(Path("/home/bennyl/projects/pkm-new/workspace/envs/test"))
env.app_containers.get_or_install(Dependency.parse("allennlp"))#.install_plugins([Dependency.parse("poetry")])
# env.default_installation_target.app_containers.container_of("allennlp").uninstall_plugins(["poetry"])

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

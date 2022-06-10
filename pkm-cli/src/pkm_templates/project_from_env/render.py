from pathlib import Path

from pkm.api.environments.environment import Environment
from pkm.api.projects.project import Project

global ask
global target_dir
global render_template


def setup(project_name: str = None, env_path: Path = None) -> dict:
    env_path = env_path or Path(ask("Path to Environment", path=True))
    if not Environment.is_venv_path(env_path):
        raise ValueError(f"path: {env_path} does not lead to a valid environment")

    env = Environment.load(env_path)
    project_name = project_name or ask("Project Name")
    render_template(
        'project', project_name=project_name, required_python=str(env.interpreter_version.without_patch()))

    project = Project.load(target_dir / project_name)
    pyprj = project.config
    pyprj.project.dependencies = [p.descriptor.to_dependency(True) for p in env.site_packages.find_requested_packages()]
    pyprj.save()

    environments_toml = project.environments_config.path.relative_to(project.path.parent)
    env_path = env_path.resolve()

    return locals()

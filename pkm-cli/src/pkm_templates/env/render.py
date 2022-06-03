from pkm.api.environments.environment_builder import EnvironmentBuilder
from pkm.api.dependencies.dependency import Dependency
from pkm.api.pkm import pkm
from pathlib import Path

global ask


def setup(name: str = None) -> dict:
    env_name = name or ask("Environment Name")

    python_available_versions = [str(p.version.without_patch()) for p in pkm.repositories.installed_pythons.list()]
    required_python = ask("Required Python Version", options=python_available_versions)

    env_path = Path.cwd() / env_name
    EnvironmentBuilder.create_matching(env_path, Dependency.parse(f"python~={required_python}.0"))

    return locals()

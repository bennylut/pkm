from pathlib import Path

from pkm.api.environments.environment_builder import EnvironmentBuilder
from pkm.api.pkm import pkm
from pkm.api.versions.version_specifiers import VersionSpecifier

global ask


def setup(name: str = None) -> dict:
    """
    creates a new virtual environment

    :param name: the environment name (creates the environment in a directory with the same name)
    """
    env_name = name or ask("Environment Name")

    python_available_versions = [str(p.version.without_patch()) for p in pkm.installed_pythons.all_installed]
    required_python = ask("Required Python Version", options=python_available_versions)

    env_path = Path.cwd() / env_name
    EnvironmentBuilder.create_matching(env_path, VersionSpecifier.parse(f"~={required_python}.0"))

    return locals()

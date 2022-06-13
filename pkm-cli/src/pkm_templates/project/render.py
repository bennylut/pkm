import os

from pkm.api.licenses import KNOWN_LICENSES
from pkm.api.packages.package import PackageDescriptor
from pkm.api.pkm import pkm
from pkm.api.projects.project_group import ProjectGroup

try:
    import pwd

    default_author = pwd.getpwuid(os.getuid()).pw_name
except: # noqa
    default_author = os.environ.get('USERNAME') or 'Johon Doe'

global ask
global confirm
global target_dir


def setup(project_name: str = None, required_python: str = None) -> dict:
    project_name = project_name or ask("Project Name")
    package_name = PackageDescriptor.normalize_src_package_name(project_name)
    version = ask("Version", default="0.1.0")
    description = ask("Short description", default="")
    readme_type = ask("Readme type", options=['Markdown', "reStructuredText"], default="Markdown")
    readme_file_ext = "md" if readme_type == 'Markdown' else 'rst'

    python_available_versions = [str(p.version.without_patch()) for p in pkm.installed_pythons.all_installed]
    required_python = required_python or ask("Required Python Version", options=python_available_versions)

    author = ask("Author", default=default_author)

    license_text = ask("License", options=KNOWN_LICENSES, autocomplete=True, default="MIT License")
    return locals()


def post_render(context):
    if ProjectGroup.is_valid(target_dir):
        if confirm("Register into the project group in the current directory"):
            ProjectGroup.load(target_dir).add(target_dir / context['project_name'])

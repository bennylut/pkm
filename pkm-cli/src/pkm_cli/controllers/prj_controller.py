from typing import Optional, List, Iterable, Dict

from pkm.api.dependencies.dependency import Dependency
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_installation_info import StoreMode
from pkm.api.projects.project import Project
from pkm.api.repositories.repository import AuthParamType
from pkm.api.versions.version_specifiers import AllowAllVersions
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.dicts import get_or_put
from pkm.utils.seqs import seq
from pkm_cli.display.display import Display
import questionary as q


class PrjController:
    def __init__(self, prj: Project):
        self.prj = prj

    def install_project(self, optional_group: Optional[str] = None):
        self.prj.install_project(optional_group)

    def uninstall_dependencies(self, packages: List[str], force: bool = False):
        prj = self.prj
        package_names_set = set(PackageDescriptor.package_name_key(it) for it in packages)
        project_dependencies = prj.config.project.dependencies or []
        project_optional_deps = prj.config.project.optional_dependencies or {}

        def filter_dep(deps: List[Dependency]):
            return [d for d in deps if d.package_name_key not in package_names_set]

        prj.config.project.dependencies = filter_dep(project_dependencies)
        prj.config.project.optional_dependencies = {g: filter_dep(d) for g, d in project_optional_deps.items()}

        prj.update_at(prj.attached_environment.installation_target)
        removed = prj.attached_environment.uninstall(packages, force)
        Display.print(f"Packages Removed: {', '.join(removed)}")

        Display.print("Updating pyproject & lock")
        prj.config.save()
        prj.lock.update_lock(prj.attached_environment).save()

        Display.print("Operation Completed Successfully")

    def install_dependencies(
            self, dependencies: List[Dependency], optional_group: Optional[str] = None, update: bool = False,
            store_mode: StoreMode = StoreMode.AUTO):

        def combined_deps(old_deps: List[Dependency]) -> Iterable[Dependency]:
            new_dependency_package_names = {d.package_name_key for d in dependencies}
            yield from (d for d in old_deps if d.package_name_key not in new_dependency_package_names)
            yield from dependencies

        project_cfg = self.prj.config.project

        configured_dependencies = project_cfg.dependencies
        if optional_group:
            configured_dependencies = get_or_put(project_cfg.optional_dependencies, optional_group, list)

        prev_deps = [*configured_dependencies]
        configured_dependencies.clear()
        configured_dependencies.extend(combined_deps(prev_deps))

        try:
            updates = [d.package_name for d in dependencies] if update else []
            store_modes = {d.package_name: store_mode for d in dependencies}

            self.prj.install_project(optional_group, updates, store_modes)

            Display.print("Updating pyproject & lock")
            site_packages = self.prj.attached_environment.site_packages
            for dependency in dependencies:
                if dependency.version_spec is AllowAllVersions:
                    installed = site_packages.installed_package(dependency.package_name)
                    assert installed, f"could not find {dependency.package_name}"
                    dependency_index = seq(configured_dependencies) \
                        .index_of_matching(lambda it: it.package_name_key == dependency.package_name_key)
                    configured_dependencies[dependency_index] = installed.descriptor.to_dependency(generalize=True)

            self.prj.config.save()
            self.prj.lock.update_lock(self.prj.attached_environment).save()
            Display.print("Operation Completed Successfully")
        except Exception as e:
            configured_dependencies.clear()
            configured_dependencies.extend(prev_deps)
            raise e

    def publish(self, repo_name: str, auth_args: Dict[str, str]) -> Dict[str, str]:
        project = self.prj
        if not project.is_built_in_default_location():
            project.build()

        if not (publisher := project.repository_management.publisher_for(repo_name)):
            raise UnsupportedOperationException(f"repository: {repo_name} does not support publishing")

        requested_auth_params = {}
        for param in publisher.authentication_params():
            if not (user_provided_value := auth_args.get(param.name)):
                if param.type == AuthParamType.PASSWORD:
                    user_provided_value = q.password(param.name).unsafe_ask()
                elif param.type == AuthParamType.FILE:
                    user_provided_value = q.path(param.name).unsafe_ask()
                else:
                    user_provided_value = q.text(param.name).unsafe_ask()
            requested_auth_params[param.name] = user_provided_value

        project.publish(publisher, requested_auth_params)
        return requested_auth_params

import os
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from textwrap import dedent
from typing import List, Union, Optional, ContextManager, Dict

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.packages.site_packages import InstalledPackage
from pkm.api.projects.project import Project
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, PkmApplicationConfig, ProjectConfig, \
    BuildSystemConfig
from pkm.api.repositories.repositories_configuration import RepositoriesConfiguration, RepositoryInstanceConfig
from pkm.api.repositories.repository import Repository
from pkm.api.repositories.repository_loader import REPOSITORIES_CONFIGURATION_PATH
from pkm.distributions.executables import Executables
from pkm.pep517_builders.pkm_builders import build_wheel
from pkm.repositories.local_packages_repository import LOCAL_PACKAGES_REPOSITORY_TYPE
from pkm.utils.entrypoints import EntryPoint, ObjectReference
from pkm.utils.files import temp_dir, mkdir, CopyTransaction, path_to
from pkm.utils.hashes import HashSignature

_CONTAINERIZED_WRAPPER_SUFFIX = "_containerized"
_CONTAINERIZED_WRAPPER_VERSION = "0.0.1"
_CONTAINERIZED_TARGET_USED_PATHS = ["purelib", "data", "scripts"]

CONTAINERIZED_APP_DATA_PATH = "__container__"
CONTAINERIZED_APP_SITE_PATH = "__container__/site"
CONTAINERIZED_APP_BIN_PATH = "__container__/bin"


class ContainerizedApplication:
    def __init__(self, package: InstalledPackage, target: PackageInstallationTarget):
        self.package = package
        self._target = target

    @property
    def app_package(self) -> InstalledPackage:
        return self.package

    @property
    def installation_target(self) -> PackageInstallationTarget:
        return self._target

    def uninstall(self):
        self.package.uninstall()

    def install_plugins(
            self, plugins: List[Dependency], repo: Optional[Repository] = None):
        self._target.install(plugins, repository=repo, user_requested=True)

    def uninstall_plugins(self, plugin_packages: List[str]):
        self._target.uninstall(plugin_packages)

    def list_installed_plugins(self) -> List[InstalledPackage]:
        return [it
                for it in self._target.site_packages.installed_packages()
                if it.dist_info.is_user_requested() and it.name != self.package.name]


class ContainerizedApplications:
    def __init__(self, target: PackageInstallationTarget):
        self._target = target

    def containers(self) -> List[ContainerizedApplication]:
        return [
            ContainerizedApplication(it, self._target_of(it.name))
            for it in self._target.site_packages.installed_packages()
            if it.dist_info.is_app_container()]

    def _target_of(self, package: str) -> PackageInstallationTarget:
        app_base = Path(self._target.purelib) / PackageDescriptor.normalize_src_package_name(package)
        app_site = str(app_base / CONTAINERIZED_APP_SITE_PATH)
        app_bin = str(app_base / CONTAINERIZED_APP_BIN_PATH)
        app_data = str(app_base / CONTAINERIZED_APP_DATA_PATH)

        return replace(self._target, platlib=app_site, purelib=app_site, scripts=app_bin, data=app_data)

    def container_of(self, package: str) -> Optional[ContainerizedApplication]:
        spacks = self._target.site_packages
        package_cnt = package + _CONTAINERIZED_WRAPPER_SUFFIX
        if (cnt := spacks.installed_package(package)) or (cnt := spacks.installed_package(package_cnt)):
            if cnt.dist_info.is_app_container():
                return ContainerizedApplication(cnt, self._target_of(cnt.name))
            raise ValueError(f"installed package: {cnt.descriptor} is not containerized")
        return None

    @contextmanager
    def _wrapper_project(self, app: Union[Dependency, Project]) -> ContextManager[Project]:
        with temp_dir() as tdir:
            pyprj = PyProjectConfiguration.load(tdir / 'pyproject.toml')

            if isinstance(app, Project):
                repocfg = RepositoriesConfiguration.load(tdir / REPOSITORIES_CONFIGURATION_PATH)
                repocfg.repositories = [RepositoryInstanceConfig.from_config('wrapped-project', {
                    'type': LOCAL_PACKAGES_REPOSITORY_TYPE,
                    'projects': [app.path]
                })]

                repocfg.save()
                app = app.descriptor.to_dependency()

            pyprj.project = ProjectConfig.from_config({
                'name': app.package_name + _CONTAINERIZED_WRAPPER_SUFFIX,
                'version': _CONTAINERIZED_WRAPPER_VERSION,
            })

            pyprj.build_system = BuildSystemConfig([], "pkm_containerized", ["."])

            pyprj.pkm_application = PkmApplicationConfig(True, [app], {}, [app.package_name])
            pyprj.save()
            yield Project.load(tdir)

    def _install(self, app: Project, editable: bool = True) -> ContainerizedApplication:
        contained_target = self._target_of(app.name)
        app_dir = Path(contained_target.purelib).parent.parent

        with temp_dir() as tdir, CopyTransaction() as ct:

            if Path(contained_target.purelib).exists():
                contained_target.force_remove(app.name)
            else:
                for path in _CONTAINERIZED_TARGET_USED_PATHS:
                    mkdir(Path(getattr(contained_target, path)))

            contained_site = contained_target.site_packages
            app_config = app.config.pkm_application

            contained_target.install(
                app_config.inner_deps, dependencies_override=app_config.inner_deps_overwrites,
                repository=app.attached_repository)

            WheelDistribution(app.descriptor, build_wheel(app, tdir / "whl", editable=editable)) \
                .install_to(contained_target, app.descriptor.to_dependency())

            contained_site.reload()

            for path in _CONTAINERIZED_TARGET_USED_PATHS:
                ct.touch_tree(Path(getattr(contained_target, path)))

            contained_app = contained_site.installed_package(app.name)
            contained_distinfo = contained_app.dist_info

            # now create the dist-info
            dist_info_path = app_dir.parent / contained_distinfo.path.name
            if dist_info_path.exists():
                ct.rm(dist_info_path)
            dist_info = DistInfo.load(mkdir(dist_info_path))

            ct.copy_tree(contained_distinfo.path, dist_info.path)
            (app_dir / "__init__.py").touch()

            # collect script entrypoints
            script_entrypoints: List[EntryPoint] = []
            apps_to_expose = app_config.exposed_inner_apps + [app.name]
            for exposed_app in apps_to_expose:
                if installed := contained_site.installed_package(exposed_app):
                    script_entrypoints.extend(
                        it for it in installed.dist_info.load_entrypoints_cfg().entrypoints if it.is_script())

            # submit script entrypoints
            app_entrypoints = dist_info.load_entrypoints_cfg()
            entrypoints = []
            if script_entrypoints:
                (app_dir / "entrypoints.py").write_text(_entrypoints_script(script_entrypoints))
                scripts_path = Path(self._target.scripts)
                for script_ep in script_entrypoints:
                    epn = PackageDescriptor.normalize_src_package_name(script_ep.name)
                    entrypoints.append(
                        script_ep := replace(script_ep, ref=ObjectReference.parse(f"{app_dir.name}.entrypoints:{epn}")))
                    ct.touch(Executables.generate_for_entrypoint(self._target.env, script_ep, scripts_path))

            app_entrypoints.entrypoints = entrypoints
            app_entrypoints.save()

            ct.touch(dist_info.app_container_path(), True)  # mark as containerized
            ct.touch(dist_info.user_requested_path(), True)  # mark as user requested

            records = dist_info.load_record_cfg()
            records.records.clear()

            # reuse precomputed hashes in order to sign our records
            precomputed_hashes: Dict[str, HashSignature] = {}
            installation_site = dist_info.path.parent
            for pk in contained_site.installed_packages():
                for record in pk.dist_info.load_record_cfg().records:
                    path_relative_to_site = str(path_to(installation_site, record.absolute_path(pk.dist_info)))
                    precomputed_hashes[path_relative_to_site] = record.hash_signature

            records.sign_files(ct.copied_files, installation_site, precomputed_hashes)
            records.save()

        self._target.site_packages.reload()
        return self.container_of(app.name)

    def install(self, app: Union[Dependency, Project], editable: bool = True) -> ContainerizedApplication:
        if isinstance(app, Project) and app.is_pkm_application():
            return self._install(app, editable)

        with self._wrapper_project(app) as prj:
            return self.install(prj, editable)


def _entrypoints_script(epoints: List[EntryPoint]):
    def define_epfunc(ep: EntryPoint):
        epn = PackageDescriptor.normalize_src_package_name(ep.name)
        return f"def {epn}():{ep.ref.execution_script_snippet()}"

    return dedent(f"""

    # setting up the application container
    import site 
    import sys
    import os
    from pathlib import Path

    container_path = Path(__file__).parent

    sys.path, remainder = sys.path[:1], sys.path[1:]
    site.addsitedir(container_path / '{CONTAINERIZED_APP_SITE_PATH}')
    sys.path.extend(remainder)

    old_path = os.environ['PATH']
    new_path = str(container_path / '{CONTAINERIZED_APP_BIN_PATH}')
    if old_path:
        new_path = old_path + os.pathsep + new_path
    os.environ['PATH'] = new_path
    
    sys.prefix = str(container_path/'{CONTAINERIZED_APP_DATA_PATH}')

    # defining entry points 
    """) + os.linesep.join([define_epfunc(ep) for ep in epoints])
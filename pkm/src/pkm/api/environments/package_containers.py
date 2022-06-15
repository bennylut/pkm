import os
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from textwrap import dedent
from typing import List, Union, Optional, ContextManager, Dict

from pkm.api.dependencies.dependency import Dependency
from pkm.api.distributions.distinfo import DistInfo
from pkm.api.packages.package_installation_info import StoreMode, PackageInstallationInfo
from pkm.api.distributions.wheel_distribution import WheelDistribution
from pkm.api.packages.package import PackageDescriptor
from pkm.api.packages.package_installation import PackageInstallationTarget
from pkm.api.packages.site_packages import InstalledPackage
from pkm.api.projects.project import Project
from pkm.api.projects.pyproject_configuration import PyProjectConfiguration, PkmApplicationConfig, ProjectConfig, \
    BuildSystemConfig
from pkm.api.repositories.repositories_configuration import RepositoriesConfiguration, RepositoryInstanceConfig
from pkm.api.repositories.repository_loader import REPOSITORIES_CONFIGURATION_PATH
from pkm.api.versions.version import Version
from pkm.distributions.executables import Executables
from pkm.pep517_builders.pkm_builders import build_wheel
from pkm.repositories.file_system_repository import FILE_SYSTEM_REPOSITORY_TYPE
from pkm.utils.entrypoints import EntryPoint, ObjectReference
from pkm.utils.files import temp_dir, mkdir, CopyTransaction, path_to
from pkm.utils.hashes import HashSignature
from pkm.utils.properties import cached_property

_CONTAINERIZED_WRAPPER_SUFFIX = "_containerized"
_CONTAINERIZED_WRAPPER_VERSION = "0.0.1"
_CONTAINERIZED_TARGET_USED_PATHS = ["purelib", "data", "scripts"]

CONTAINERIZED_APP_DATA_PATH = "__container__"
CONTAINERIZED_APP_SITE_PATH = "__container__/site"
CONTAINERIZED_APP_BIN_PATH = "__container__/bin"


class PackageContainer:
    def __init__(self, package: InstalledPackage, target: PackageInstallationTarget):
        self.package = package
        self._target = target

    @cached_property
    def containerized_package(self) -> InstalledPackage:
        """
        :return: the (main) package that contained in this container
        """
        site = self._target.site_packages
        result = None
        if self.package.name_key.endswith(_CONTAINERIZED_WRAPPER_SUFFIX):
            result = site.installed_package(self.package.name[:-len(_CONTAINERIZED_WRAPPER_SUFFIX)])

        return result or site.installed_package(self.package.name)

    @property
    def installation_target(self) -> PackageInstallationTarget:
        """
        :return: this container installation target
        """
        return self._target

    def uninstall(self):
        """
        uninstall this container - removing it from the hosting environment
        """
        self.package.uninstall()

    def list_installed_plugins(self) -> List[InstalledPackage]:
        """
        :return: list of all user installed packages that are not the main containerized
        """
        return [it
                for it in self._target.site_packages.installed_packages()
                if it.dist_info.is_user_requested()
                and it.name != self.containerized_package.name
                and it.name != self.package.name]


class PackageContainers:
    """
    controller class for package containers that resides in a given installation target
    """

    def __init__(self, target: PackageInstallationTarget):
        self._target = target

    def containers(self) -> List[PackageContainer]:
        """
        :return: list of all package containers that are installed in the according installation target
        """

        return [
            PackageContainer(it, self._target_of(it.name))
            for it in self._target.site_packages.installed_packages()
            if it.dist_info.is_app_container()]

    def _target_of(self, package: str) -> PackageInstallationTarget:
        app_base = Path(self._target.purelib) / PackageDescriptor.normalize_src_package_name(package)
        app_site = str(app_base / CONTAINERIZED_APP_SITE_PATH)
        app_bin = str(app_base / CONTAINERIZED_APP_BIN_PATH)
        app_data = str(app_base / CONTAINERIZED_APP_DATA_PATH)

        return replace(self._target, platlib=app_site, purelib=app_site, scripts=app_bin, data=app_data)

    def container_of(self, package: str) -> Optional[PackageContainer]:
        """
        :param package: the package to look for container of
        :return: the package container if this package was installed into a container, None otherwise
        """

        spacks = self._target.site_packages
        package_cnt = package + _CONTAINERIZED_WRAPPER_SUFFIX
        if (cnt := spacks.installed_package(package)) or (cnt := spacks.installed_package(package_cnt)):
            if cnt.dist_info.is_app_container():
                return PackageContainer(cnt, self._target_of(cnt.name))
        return None

    @contextmanager
    def _wrapper_project(self, app: Union[Dependency, "Project"]) -> ContextManager["Project"]:
        from pkm.api.projects.project import Project
        with temp_dir() as tdir:
            pyprj = PyProjectConfiguration.load(tdir / 'pyproject.toml')

            if isinstance(app, Project):
                repocfg = RepositoriesConfiguration.load(tdir / REPOSITORIES_CONFIGURATION_PATH)
                repocfg.repositories = [RepositoryInstanceConfig.from_config('wrapped-project', {
                    'type': FILE_SYSTEM_REPOSITORY_TYPE,
                    'path': app.path
                })]

                repocfg.save()
                app = app.descriptor.to_dependency()

            pyprj.project = ProjectConfig(
                name=app.package_name + _CONTAINERIZED_WRAPPER_SUFFIX,
                version=Version.parse(_CONTAINERIZED_WRAPPER_VERSION)
            )

            pyprj.build_system = BuildSystemConfig([], "pkm_containerized", ["."])
            pyprj.pkm_application = PkmApplicationConfig(True, [app], {}, [app.package_name])

            pyprj.save()
            yield Project.load(tdir)

    def _install(
            self, app: "Project", store_mode: StoreMode = StoreMode.AUTO) -> PackageContainer:

        editable = store_mode != StoreMode.COPY
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
                app_config.dependencies, dependencies_override=app_config.dependency_overwrites,
                repository=app.attached_repository,
                store_mode={d.package_name: store_mode for d in app_config.dependencies},
                updates=[d.package_name for d in app_config.dependencies])

            WheelDistribution(app.descriptor, build_wheel(app, tdir / "whl", editable=editable)) \
                .install_to(contained_target, app.descriptor.to_dependency(),
                            PackageInstallationInfo(store_mode=StoreMode.EDITABLE if editable else StoreMode.COPY))

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
            ct.touch(app_dir / "__init__.py", True)

            contained_metadata = contained_distinfo.load_metadata_cfg()
            contained_metadata.dependencies = app_config.dependencies
            contained_metadata.save()

            # collect script entrypoints
            script_entrypoints: List[EntryPoint] = []
            apps_to_expose = app_config.exposed_packages + [app.name]
            for exposed_app in apps_to_expose:
                if installed := contained_site.installed_package(exposed_app):
                    script_entrypoints.extend(
                        it for it in installed.dist_info.load_entrypoints_cfg().entrypoints if it.is_script())

            # submit script entrypoints
            app_entrypoints = dist_info.load_entrypoints_cfg()
            entrypoints = []
            if script_entrypoints:
                app_entrypoints_script = (app_dir / "entrypoints.py")
                app_entrypoints_script.write_text(_entrypoints_script(script_entrypoints))
                ct.touch(app_entrypoints_script)
                scripts_path = Path(self._target.scripts)
                for script_ep in script_entrypoints:
                    epn = PackageDescriptor.normalize_src_package_name(script_ep.name)
                    entrypoints.append(
                        script_ep := replace(script_ep, ref=ObjectReference.parse(f"{app_dir.name}.entrypoints:{epn}")))
                    ct.touch(Executables.generate_for_entrypoint(self._target.env, script_ep, scripts_path))

            app_entrypoints.entrypoints = entrypoints
            app_entrypoints.save()

            # submit container registration hooks
            container_registration_script = app_dir / "register_container.py"
            container_registration_script.write_text(_register_container_script(app.name))
            ct.touch(container_registration_script)

            container_registration_pth = Path(
                self._target.purelib) / f"register_{app.descriptor.expected_src_package_name}_container.pth"
            container_registration_pth.write_text(_register_container_import_hook(app_dir.name))
            ct.touch(container_registration_pth)

            dist_info.save_installation_info(PackageInstallationInfo(containerized=True, store_mode=StoreMode.COPY))
            ct.touch(dist_info.installation_info_path())
            ct.touch(dist_info.user_requested_path(), True)  # mark as user requested

            records = dist_info.load_record_cfg()
            records.records.clear()

            # reuse precomputed hashes in order to sign our records
            # TODO: notify a monitor that we are spending time on signing the package
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

    def _get_or_install(self, app: Union[Dependency, Project],
                        store_mode: StoreMode = StoreMode.AUTO) -> PackageContainer:
        dep = app
        if isinstance(dep, Project):
            dep = app.descriptor.to_dependency()

        if (container := self.container_of(dep.package_name)) \
                and dep.version_spec.allows_version(container.containerized_package.version):
            return container

        return self.install(app, store_mode, True)

    def install(
            self, app: Union[Dependency, Project], store_mode: StoreMode = StoreMode.AUTO, update: bool = False
    ) -> PackageContainer:
        """
        installs the given app in its own containerized environment
        :param app: the app to install, if not referring to a containerized project will create containerized wrapper
        :param store_mode: affect the store mode of the `app` inside the container
        :param update: if true, will force re-installation,
            even if the same version is already installed in the relevant site
        :return: containerized application controller class for the performed installation
        """

        if not update:
            return self._get_or_install(app, store_mode)

        if isinstance(app, Project) and app.is_containerized_application():
            return self._install(app, store_mode)

        with self._wrapper_project(app) as prj:
            return self.install(prj, store_mode, True)


def _entrypoints_script(epoints: List[EntryPoint]):
    def define_epfunc(ep: EntryPoint):
        epn = PackageDescriptor.normalize_src_package_name(ep.name)
        ref = ep.ref
        return f"def {epn}():del sys.modules[__package__];" \
               f"import {ref.module_path};" \
               f"{ref.module_path}.{ref.object_path}()"

    prolog = dedent("""
    import sys
    from .register_container import register
    
    register()
    
    """)
    return prolog + os.linesep.join([define_epfunc(ep) for ep in epoints])


def _register_container_script(name: str) -> str:
    return dedent(f"""
    registered = False
    
    def register():
        global registered
        if registered:
            return
        registered = True
        
        os.environ["PKM_PACKAGE_CONTAINER"] = "{name}"
    
        import site
        import sys
        from pathlib import Path
    
        container_path = Path(__file__).parent
        container_site = str(container_path / '{CONTAINERIZED_APP_SITE_PATH}')
        site.addsitedir(container_site)
        sys.path.insert(1, sys.path.pop())
    
        old_path = os.environ.get('PATH')
        path = str(container_path / '{CONTAINERIZED_APP_BIN_PATH}')
        if old_path:
            path = (path + os.pathsep + old_path) if path not in old_path else old_path
        os.environ['PATH'] = path
    
        sys.prefix = str(container_path / '{CONTAINERIZED_APP_DATA_PATH}')
    
    import os
    ppc = os.environ.get("PKM_PACKAGE_CONTAINER")
    if ppc == "{name}":
        register()
    """)


def _register_container_import_hook(app_package: str) -> str:
    return f"import {app_package}.register_container"

# import shutil
# import sys
# from collections import defaultdict
# from dataclasses import replace
# from pathlib import Path
# from textwrap import dedent
# from typing import Optional, List, Dict
#
# from pkm.api.dependencies.dependency import Dependency
# from pkm.api.distributions.distinfo import ObjectReference, DistInfo
# from pkm.api.environments.environment import Environment
# from pkm.api.packages.package import PackageDescriptor, Package
# from pkm.api.packages.package_monitors import PackageInstallMonitoredOp
# from pkm.api.projects.project import Project
# from pkm.api.projects.pyproject_configuration import PyProjectConfiguration
# from pkm.utils.dicts import put_if_absent
# from pkm.utils.files import temp_dir, resolve_relativity
# from pkm.utils.properties import cached_property
#
#
# def build_app_installer(application_project: Project, target_dir: Optional[Path]) -> Path:
#     """
#     builds a package that contains application installer for the given project
#     :param application_project: the project to create the installer to
#     :param target_dir: the directory to put the installer in
#     :return: the path to the created installer package (sdist)
#     """
#
#     # with monitor.on_build(application_project.descriptor, 'app') as build_monitor:
#     target_dir = (target_dir or (application_project.directories.dist / str(application_project.version))) / 'app'
#     target_dir.mkdir(parents=True, exist_ok=True)
#
#     with temp_dir() as tdir:
#         installer_project_name = application_installer_project_name(application_project)
#
#         # create source for the different entrypoints
#         installer_source_dir = tdir / 'src' / PackageDescriptor.normalize_source_dir_name(installer_project_name)
#         installer_source_dir.mkdir(parents=True)
#
#         new_entrypoints = defaultdict(list)
#         for entrypoint in application_project.config.project.script_entrypoints():
#             entrypoint_module = f"{installer_source_dir.name}.{entrypoint.name}"
#             new_entrypoints[entrypoint.group].append(
#                 replace(entrypoint, ref=ObjectReference(entrypoint_module, "main")))
#
#             (installer_source_dir / f"{entrypoint.name}.py").write_text(dedent(f"""
#                 import sys
#                 import os
#
#                 package_layer_path = os.path.join(os.path.dirname(__file__), '__package_layer__')
#                 sys.path.insert(0, package_layer_path)
#
#                 if 'PYTHONPATH' in os.environ:
#                     os.environ['PYTHONPATH'] = package_layer_path + os.pathsep + os.environ['PYTHONPATH']
#                 else:
#                     os.environ['PYTHONPATH'] = package_layer_path
#
#                 def main():
#                     {entrypoint.ref.execution_script_snippet()}
#                 """))
#
#         installer_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
#         installer_pyproject.project = replace(
#             application_project.config.project,
#             name=application_project.name + '-app',
#             dependencies=[],
#             entry_points=new_entrypoints
#         )
#
#         installer_pyproject['tool.pkm.internal.package'] = {
#             'type': 'application-installer',
#             'app': application_project.name
#         }
#
#         installer_pyproject.build_system = replace(
#             application_project.config.build_system,
#             requirements=application_project.config.build_system.requirements + [
#                 application_project.descriptor.to_dependency()])
#
#         installer_pyproject.save()
#         installer_project = Project.load(tdir)
#         return installer_project.build_sdist(target_dir)
#
#
# def is_application_installer_project(project: Project) -> bool:
#     """
#     :param project: the project to check
#     :return: true if the given project is application installer project, false otherwise
#     """
#
#     return project.config['tool.pkm.internal.package.type'] == 'application-installer'
#
#
# def application_installer_dir(distributions_dir: Path) -> Path:
#     return distributions_dir / 'app'
#
#
# def application_installer_project_name(project: Project) -> str:
#     return project.name + '-app'
#
#
# def build_app_installation(installer_project: Project, output_dir: Path) -> Path:
#     """
#     build installation package (wheel) from the given `installer_project` and put it inside the given `output_dir`
#     this process will resolve and download all the required artifacts, create the "embedded environment"
#     for the application and the patch the entrypoints to use it (TODO)
#     :param installer_project: installer project, created using the `ApplicationInstaller.build_app_installer` method
#     :param output_dir: installation package (wheel) which contain the application in an embedded environment
#            in addition to the entrypoints which will be patched to use the embedded environment
#     :return: path to the created installation package
#     """
#
#     # with monitor.on_build(installer_project.descriptor, 'wheel') as build_monitor:
#
#     with temp_dir() as tdir:
#
#         # create installation project
#         installation_pyproject = PyProjectConfiguration.load(tdir / 'pyproject.toml')
#         installation_pyproject['project'] = installer_project.config['project']
#
#         # copy installer source to installation project
#         package_name = PackageDescriptor.normalize_source_dir_name(installer_project.name)
#         if not (app_name := installer_project.config['tool.pkm.internal.package.app']):
#             raise ValueError("malformed installer package")
#
#         installation_src = tdir / 'src' / package_name
#         shutil.copytree(installer_project.path / 'src' / package_name, installation_src)
#
#         # moving the dependencies to the installer source under __package_layer__
#         # currently assumes that this process lives in a build dedicated environment
#
#         packages = _scan_local_packages()
#         app_package: str = PackageDescriptor.normalize_source_dir_name(app_name)
#         package_layer = installation_src / "__package_layer__"
#         package_layer.mkdir(exist_ok=True, parents=True)
#
#         open_list = [app_package]
#         close_set = set()
#         while open_list:
#             nex = open_list.pop()
#             if nex in close_set:
#                 continue
#             close_set.add(nex)
#
#             # TODO:
#             # this code does not filter extras and env-markers, instead it assumes that if the packages
#             # exists in the system they are somehow needed, while this is an acceptable start we should change
#             # it to achieve a more predictable outcome
#             nex_dist: DistInfo = packages.get(nex)
#             if not nex_dist:
#                 continue
#             try:
#                 print(f"loading metadata for {nex_dist.path}")
#                 nex_package_deps = nex_dist.load_metadata_cfg().dependencies
#                 open_list.extend([PackageDescriptor.normalize_source_dir_name(r.package_name)
#                                   for r in nex_package_deps])
#             except:  # noqa
#                 print(f"could not parse metadata:\n{nex_dist.metadata_path().read_text()}")
#                 raise
#
#             dist_parent = nex_dist.path.parent
#             for record in nex_dist.load_record_cfg().records:
#                 record_file = Path(record.file)
#                 source = resolve_relativity(record_file, dist_parent)
#                 target = package_layer / source.relative_to(dist_parent)
#
#                 target.parent.mkdir(exist_ok=True, parents=True)
#                 shutil.copy(source, target)
#
#             # copy the actual record file, which does not need to be in the records, it should be empty as the
#             # actual app package is the one that put is responsible for all the files in the package layer:
#             source = resolve_relativity(nex_dist.record_path(), dist_parent)
#             target = package_layer / source.relative_to(dist_parent)
#             target.write_text("")
#
#         # build the wheel for the installation project
#         installation_pyproject.save()
#         installation_project = Project.load(tdir)
#
#         return installation_project.build_wheel(output_dir)
#
#
# def _scan_local_packages() -> Dict[str, DistInfo]:
#     result: Dict[str, DistInfo] = {}
#     for path_str in sys.path:
#         path = Path(path_str)
#         if path.is_dir():
#             for dist in path.glob("*.dist-info"):
#                 if dist.is_dir():
#                     dist_info = DistInfo.load(dist)
#                     package = dist.name.split('-')[0].lower()
#                     put_if_absent(result, package, dist_info)
#
#     return result
#
#
# class ApplicationInstallerProjectWrapper(Package):
#     def __init__(self, project: Project):
#         self._project = project
#
#     @property
#     def wrapped_project(self) -> Project:
#         return self._project
#
#     @cached_property
#     def descriptor(self) -> PackageDescriptor:
#         return PackageDescriptor(self._project.name + "-app", self._project.version)
#
#     def _all_dependencies(self, environment: "Environment") -> List["Dependency"]:
#         return []
#
#     def is_compatible_with(self, env: "Environment") -> bool:
#         return self._project.is_compatible_with(env)
#
#     def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None):
#         with temp_dir() as tdir, PackageInstallMonitoredOp(self.descriptor):
#             installer = self._project.build_application_installer(tdir)
#             Project.load(installer).install_to(env, user_request)

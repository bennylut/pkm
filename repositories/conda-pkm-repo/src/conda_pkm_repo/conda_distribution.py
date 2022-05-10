# import bz2
# import json
# import os
# import shutil
# from dataclasses import replace
# from pathlib import Path
# from typing import Optional
#
# from pkm.api.dependencies.dependency import Dependency
# from pkm.api.distributions.distinfo import PackageInstallationInfo, DistInfo
# from pkm.api.distributions.distribution import Distribution
# from pkm.api.distributions.wheel_distribution import WheelDistribution
# from pkm.api.environments.environment import Environment
# from pkm.api.packages.package import PackageDescriptor
# from pkm.api.packages.package_installation import PackageInstallationTarget
# from pkm.api.packages.package_metadata import PackageMetadata
# from pkm.utils.archives import extract_archive
# from pkm.utils.files import temp_dir
# from pkm.utils.iterators import first_or_none, first_or_raise
# from pkm.utils.processes import monitored_run
#
#
# class CondaDistribution(Distribution):
#
#     def __init__(self, package: PackageDescriptor, bz2dist: Path):
#         self._package = package
#         self._dist = bz2dist
#
#     @property
#     def owner_package(self) -> PackageDescriptor:
#         return self._package
#
#     def install_to(self, target: "PackageInstallationTarget", user_request: Optional[Dependency] = None,
#                    installation_info: Optional[PackageInstallationInfo] = None):
#         with temp_dir() as tdir:
#             extract_archive(self._dist, tdir)
#             dist_info_path = first_or_raise(tdir.rglob("*.dist-info"))
#
#             info_path = tdir / "info"
#             index = json.loads((info_path / "index.json").read_text())
#
#             def exec_installation_script(script_name: str):
#                 env = {**os.environ, 'PREFIX': target.data, 'PKG_NAME': self._package.name,
#                        'PKG_VERSION': str(self._package.version), 'PKG_BUILDNUM': index['build_number']}
#                 if target.env.operating_platform.has_windows_os():
#                     if (script_path := info_path / "Scripts" / f"{script_name}.bat").exists():
#                         monitored_run(f"conda installation hook: {script_name}", [
#                             env.get("COMSPEC", "cmd.exe"), '/c', str(script_path)
#                         ], env=env).check_returncode()
#                 else:
#                     if (script_path := info_path / "bin" / f"{script_name}.sh").exists():
#                         monitored_run(f"conda installation hook: {script_name}", [
#                             "/bin/bash", str(script_path)
#                         ], env=env).check_returncode()
#
#             exec_installation_script('pre-link')
#             wheel_root = dist_info_path.parent
#
#             if (scripts_data := (tdir / Path(target.scripts).name)).exists():
#                 shutil.copytree(scripts_data, wheel_root / f"{dist_info_path.stem}.data/scripts")
#             WheelDistribution.install_extracted_wheel(
#                 self._package, wheel_root, target, user_request, installation_info)
#
#             exec_installation_script('post-link')
#
#     def extract_metadata(self, env: Optional["Environment"] = None) -> PackageMetadata:
#         with temp_dir() as tdir:
#             extract_archive(self._dist, tdir)
#             dist_info_path = first_or_raise(tdir.rglob("*.dist-info"))
#             return DistInfo.load(dist_info_path).load_metadata_cfg()

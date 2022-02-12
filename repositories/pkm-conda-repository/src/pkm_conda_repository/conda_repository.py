# from typing import List, Optional
#
# from pkm.api.dependencies.dependency import Dependency
# from pkm.api.packages.package import Package, PackageDescriptor
# from pkm.api.repositories.repository import Repository
#
#
# class CondaRepository(Repository):
#     def _do_match(self, dependency: Dependency) -> List[Package]:
#         pass
#
#
# class _CondaPackage(Package):
#
#     def __init__(self, desc: PackageDescriptor):
#         self._desc = desc
#
#     @property
#     def descriptor(self) -> PackageDescriptor:
#         return self._desc
#
#     def _all_dependencies(self, environment: "Environment") -> List["Dependency"]:
#         pass
#
#     def is_compatible_with(self, env: "Environment") -> bool:
#         pass
#
#     def install_to(self, env: "Environment", user_request: Optional["Dependency"] = None, *,
#                    build_packages_repo: Optional["Repository"] = None):
#         pass

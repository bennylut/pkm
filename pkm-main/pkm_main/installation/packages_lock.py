import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments import Environment
from pkm.api.versions.version import Version
from pkm.config.configuration import TomlFileConfiguration
from pkm.utils.sequences import groupby

from pkm_main.installation.package_installation_plan import PackageInstallationPlan


@dataclass
class _LockedPackage:
    markers_hash: str
    dependency: Dependency
    version: Version

    def write(self) -> Dict[str, Any]:
        return {
            'env_markers_hash': self.markers_hash,
            'dependency': self.dependency.write(),
            'version': str(self.version)
        }

    @classmethod
    def read(cls, data: Dict[str, Any]) -> "_LockedPackage":
        env_markers_hash = data['env_markers_hash']
        dependency = Dependency.read(data['dependency'])
        version = Version.parse(data['version'])

        return _LockedPackage(env_markers_hash, dependency, version)


class PackagesLock:

    def __init__(self, locked_packages: List[_LockedPackage], lock_file: Optional[Path] = None):
        self._locked_packages: Dict[str, List[_LockedPackage]] = \
            groupby(locked_packages, lambda it: it.dependency.package_name)
        self._lock_file = lock_file

    def locked_versions(self, env: Environment, dependency: Dependency) -> List[Version]:
        """
        :param env: environment that the given dependency should be compatible with
        :param dependency: the dependency to find lock information for
        :return: list of versions to try and install on the environment, sorted by importance (try the first one first)
        """

        relevant_locks = self._locked_packages[dependency.package_name]
        if not relevant_locks:
            return []

        env_markers_hash = env.markers_hash

        result = [lock.version for lock in relevant_locks if lock.markers_hash != env_markers_hash]
        if len(result) != len(relevant_locks):
            result.insert(0, next(lock.version for lock in relevant_locks if lock.markers_hash == env_markers_hash))

        return result

    def update_lock(self, installation_plan: PackageInstallationPlan):
        """
        lock the packages in the given installation plan for the relevant environment
        :param installation_plan: a plan of selected versions to install on the given environment
        """

        env_hash = installation_plan.environment.markers_hash
        new_locks = [
            lock for locks_by_name in self._locked_packages.values()
            for lock in locks_by_name
            if lock.markers_hash != env_hash]

        for pd in installation_plan.expectation_after_install():
            for pr in installation_plan.requesters_of(pd.name):
                new_locks.append(_LockedPackage(env_hash, pr.dependency, pd.version))

        self._locked_packages = groupby(new_locks, lambda it: it.dependency.package_name)

    def save(self, lock_file: Optional[Path] = None):
        """
        saves the state of this packages lock to the given file
        :param lock_file:
        """

        lock_file = lock_file or self._lock_file
        if not lock_file:
            raise FileNotFoundError('lock file is not given')

        configuration = TomlFileConfiguration.load(lock_file)
        locks = [l.write() for locks_by_name in self._locked_packages.values() for l in locks_by_name]
        configuration['lock'] = locks
        configuration.save()

    @classmethod
    def load(cls, lock_file: Path) -> "PackagesLock":
        """
        load packages lock from the given lock file
        :param lock_file: the file to load from
        :return: the loaded lock
        """

        configuration = TomlFileConfiguration.load(lock_file)
        locked_packages = [_LockedPackage.read(l) for l in configuration['lock']]
        return PackagesLock(locked_packages, lock_file)

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from pkm.api.environments.environment import Environment
from pkm.api.packages import PackageDescriptor
from pkm.config.configuration import TomlFileConfiguration
from pkm.utils.commons import unone
from pkm.utils.iterators import groupby


@dataclass
class _LockedVersion:
    env_markers_hash: str
    package: PackageDescriptor

    def write(self) -> Dict[str, Any]:
        return {
            'env_markers_hash': self.env_markers_hash,
            'package': self.package.write(),
        }

    @classmethod
    def read(cls, data: Dict[str, Any]) -> "_LockedVersion":
        return _LockedVersion(data['env_markers_hash'], PackageDescriptor.read(data['package']))


class PackagesLock:

    def __init__(self, locked_packages: Optional[List[_LockedVersion]] = None, lock_file: Optional[Path] = None):
        locked_packages = unone(locked_packages, list)
        self._locked_packages: Dict[str, List[_LockedVersion]] = \
            groupby(locked_packages, lambda it: it.package)
        self._lock_file = lock_file

    def locked_versions(self, env: Environment, package: str) -> List[PackageDescriptor]:
        """
        :param env: environment that the given dependency should be compatible with
        :param package: the package to find lock information for
        :return: list of package descriptors to try and install on the environment, sorted by importance
                 (try the first one first)
        """

        relevant_locks = [l for l in (self._locked_packages.get(package) or ())]
        if not relevant_locks:
            return []

        env_markers_hash = env.markers_hash

        result = [lock.package for lock in relevant_locks if lock.env_markers_hash != env_markers_hash]
        if len(result) != len(relevant_locks):
            result.insert(0, next(lock.package for lock in relevant_locks if lock.env_markers_hash == env_markers_hash))

        return result

    def update_lock(self, env: Environment):
        """
        lock the packages in the given environment
        :param env: the environment to use to extract lock information
        """

        env_hash = env.markers_hash
        new_locks = [
            lock for locks_by_name in self._locked_packages.values()
            for lock in locks_by_name
            if lock.env_markers_hash != env_hash]

        for pd in env.installed_packages:
            new_locks.append(_LockedVersion(env_hash, pd))

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
        locked_packages = [_LockedVersion.read(l) for l in configuration['lock']]
        return PackagesLock(locked_packages, lock_file)

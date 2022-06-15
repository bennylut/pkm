from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union, Optional, List, TYPE_CHECKING

from pkm.api.pkm import HasAttachedRepository
from pkm.api.projects.environments_config import EnvironmentsConfiguration, ENVIRONMENT_CONFIGURATION_PATH
from pkm.api.projects.project import Project
from pkm.config.configclass import config, ConfigFile, config_field
from pkm.config.configfiles import TomlConfigIO
from pkm.utils.files import ensure_exists, resolve_relativity
from pkm.utils.ipc import IPCPackable
from pkm.utils.iterators import single_or_raise
from pkm.utils.properties import cached_property

if TYPE_CHECKING:
    from pkm.api.repositories.repository_management import RepositoryManagement


class ProjectGroup(HasAttachedRepository, IPCPackable):
    """
    project group, like the name implies, is a group of projects
    the projects are related to themselves in a parent/children manner,
    a parent is always a group and children may be projects or another project groups

    the project group is configured by the pyproject-group.toml configuration file
    """

    def __init__(self, config_: "PyProjectGroupConfiguration", parent: Optional[ProjectGroup] = None):
        self._config = config_
        self.path = self._config.path.parent
        if parent:
            self.parent = parent  # noqa

    def __getstate__(self):
        return [self._config, self.parent]

    def __setstate__(self, state):
        return self.__init__(*state)

    @property
    def config(self) -> "PyProjectGroupConfiguration":
        return self._config

    @cached_property
    def environments_config(self) -> EnvironmentsConfiguration:
        return EnvironmentsConfiguration.load(self.path / ENVIRONMENT_CONFIGURATION_PATH)

    @cached_property
    def repository_management(self) -> "RepositoryManagement":
        from pkm.api.repositories.repository_management import ProjectGroupRepositoryManagement
        return ProjectGroupRepositoryManagement(self)

    @cached_property
    def parent(self) -> Optional["ProjectGroup"]:
        """
        :return: the parent of this project group (if such exists)
        """
        if not (parent := self._config.parent):
            return ProjectGroup._find_group(self.path.resolve())
        else:
            return ProjectGroup(PyProjectGroupConfiguration.load(
                ensure_exists(parent, lambda: f"{self.path}'s parent path {parent} doesn't exists")
            ))

    @cached_property
    def root(self) -> Optional["ProjectGroup"]:
        """
        :return: the top most parent of this project group
        """
        return parent.root if (parent := self.parent) else None

    @cached_property
    def children(self) -> Iterable[Union[Project, "ProjectGroup"]]:
        """
        :return: the child projects (or project groups) defined in this group
        """
        result = []
        for child in self._config.resolved_children:
            if (child / 'pyproject.toml').exists():
                result.append(Project.load(child, group=self))
            elif (child / 'pyproject-group.toml').exists:
                result.append(
                    ProjectGroup(PyProjectGroupConfiguration.load(child / 'pyproject-group.toml'), parent=self))

        return result

    @cached_property
    def project_children_recursive(self) -> List[Project]:
        """
        :return: the child projects defined in this group and
        recursively the child projects of the project groups defined in this group
        """
        result = []
        for child in self.children:
            if isinstance(child, Project):
                result.append(child)
            else:
                result.extend(child.project_children_recursive)

        return result

    def add(self, project: Union[Project, Path]):
        """
        add project to this group, saving the modification in the configuration file
        :param project: the project to add
        """

        project_path = project if isinstance(project, Path) else project.path
        self._config.children.append(project_path)
        self._config.save()

    def remove(self, project: Union[str, Path]):
        """
        remove project from this group, saving the modification in the configuration file
        :param project: the project name or path to remove
        """
        if isinstance(project, str):
            project = single_or_raise(p for p in self.children if p.name == project).path

        project = project.resolve()

        self._config.children = [
            p for p, rp in zip(self._config.children, self._config.resolved_children) if rp != project]
        self._config.save()

    def build_all(self):
        """
        recursively run the build operation on all projects and subprojects in this group
        """
        # with monitor.on_build_all(self):
        for project in self.children:
            if isinstance(project, Project):
                project.build()
            else:
                project.build_all()

    @classmethod
    def _find_group(cls, path: Path) -> Optional["ProjectGroup"]:
        for path_parent in path.parents:
            if (group_config_file := (path_parent / 'pyproject-group.toml')).exists():
                group_config = PyProjectGroupConfiguration.load(group_config_file)
                if any(child == path for child in group_config.resolved_children):
                    return ProjectGroup(group_config)
        return None

    @classmethod
    def of(cls, project: Project) -> Optional["ProjectGroup"]:
        """
        :param project: the project to get the project group for
        :return: the project group if such defined
        """
        if (pkm_project := project.config.pkm_project) and (group := pkm_project.group):
            return ProjectGroup(PyProjectGroupConfiguration.load(resolve_relativity(Path(group), project.path)))
        return cls._find_group(project.path)

    @classmethod
    def load(cls, path: Path) -> "ProjectGroup":
        """
        load the project group from a specific path
        :param path: the path to the project group directory
        :return: the loaded project group
        """
        return ProjectGroup(PyProjectGroupConfiguration.load(path / 'pyproject-group.toml'))

    @staticmethod
    def is_valid(path: Path) -> bool:
        """
        :param path: the path to check
        :return: True if the path contain project group, False otherwise
        """
        return (path / 'pyproject-group.toml').exists()


@config(io=TomlConfigIO())
class PyProjectGroupConfiguration(ConfigFile):
    _name: str = config_field(key="name")
    children: List[Path] = config_field(default_factory=list)
    parent: Path = None

    @property
    def resolved_children(self) -> Iterable[Path]:
        return (self.path.parent.joinpath(it).resolve() for it in self.children)

    @property
    def name(self) -> str:
        return self._name or self.path.parent.name

from pathlib import Path
from typing import Iterable, Union, Optional, Tuple

from pkm.api.projects.project import Project
from pkm.config.configuration import TomlFileConfiguration, computed_based_on
from pkm.utils.files import path_to, ensure_exists, resolve_relativity
from pkm.utils.iterators import single_or_fail
from pkm.utils.properties import cached_property


class ProjectGroup:
    def __init__(self, config: "PyProjectGroupConfiguration"):
        self._config = config
        self.path = self._config.path.parent

    @cached_property
    def parent(self) -> Optional["ProjectGroup"]:
        if not (parent := self._config.parent):
            return ProjectGroup.find_parent(self.path.resolve())
        else:
            return ProjectGroup(PyProjectGroupConfiguration.load(
                ensure_exists(parent, lambda: f"{self.path}'s parent path {parent} doesn't exists")
            ))

    @cached_property
    def root(self) -> Optional["ProjectGroup"]:
        return parent.root if (parent := self.parent) else None

    @cached_property
    def children(self) -> Iterable[Union[Project, "ProjectGroup"]]:
        result = []
        for child in self._config.children:
            if (child / 'pyproject.toml').exists():
                result.append(Project.load(child))
            elif (child / 'pyproject-group.toml').exists:
                result.append(ProjectGroup(PyProjectGroupConfiguration.load(child / 'pyproject-group.toml')))

        return result

    @cached_property
    def project_children_recursive(self) -> Iterable[Project]:
        result = []
        for child in self.children:
            if isinstance(child, Project):
                result.append(child)
            else:
                result.extend(child.project_children_recursive)

        return result

    def add(self, project: Union[Project, Path]):
        project_path = project if isinstance(project, Path) else project.path
        self._config.children = (*self._config.children, project_path)
        self._config.save()

    def remove(self, project: Union[str, Path]):
        if isinstance(project, str):
            project = single_or_fail(p for p in self.children if p.name == project).path

        project = project.resolve()

        self._config.children = tuple(p for p in self._config.children if p != project)
        self._config.save()

    @classmethod
    def find_parent(cls, path: Path) -> Optional["ProjectGroup"]:
        for path_parent in path.parents:
            if (parent_config_file := (path_parent / 'pyproject-group.toml')).exists():
                parent_config = PyProjectGroupConfiguration.load(parent_config_file)
                if any(child == path for child in parent_config.children):
                    return ProjectGroup(parent_config)
        return None

    @classmethod
    def of(cls, project: Project) -> Optional["ProjectGroup"]:
        if group := project.pyproject.pkm_project.group:
            return ProjectGroup(PyProjectGroupConfiguration.load(resolve_relativity(Path(group), project.path)))
        return cls.find_parent(project.path)


class PyProjectGroupConfiguration(TomlFileConfiguration):

    @computed_based_on("name")
    def name(self) -> str:
        return self['name'] or self._path.parent.name

    @property
    def path(self) -> Path:
        return self._path

    @computed_based_on("project-group.children")
    def children(self) -> Tuple[Path, ...]:
        if not (children := self["project-group.children"]):
            return tuple()

        root = self.path.parent
        result = []
        for path in children:
            path = Path(path)
            if path.is_absolute():
                result.append(path.resolve())
            else:
                result.append((root / path).resolve())

        return tuple(result)

    @children.modifier
    def set_children(self, new: Iterable[Path]):
        root = self.path.parent
        result = []
        for path in new:
            if path.is_absolute():
                result.append(path_to(root, path))
            else:
                result.append(path)

        self["project-group.children"] = result

    @computed_based_on("project-group.parent")
    def parent(self) -> Optional[Path]:
        if parent := self["project-group.parent"]:
            path = Path(parent)
            if path.is_absolute():
                return path.resolve()
            return (self.path.parent / path).resolve()
        return None


# class ProjectGroupRepository(Repository):
#
#     def __init__(self, group: ProjectGroup, name: Optional[str] = None):
#         super().__init__(name or group.path.name)
#         self._projects: Dict[str, Project] = {p.name: p for p in group.project_children_recursive}
#
#     def _do_match(self, dependency: Dependency) -> List[Package]:
#         if project := self._projects.get(dependency.package_name):
#             if dependency.version_spec.allows_version(project.version):
#                 return [project]
#
#         return []

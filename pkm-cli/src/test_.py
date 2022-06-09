from pkm.api.dependencies.dependency import Dependency
from pkm.api.projects.project import Project

p = Project.load("/home/bennyl/projects/pkm-new/workspace/xxx_prj")
p.dev_install([Dependency.parse("poetry")])

from pkm.api.projects.project import Project

p = Project.load("/home/bennyl/projects/pkm-new/workspace/xxx_prj")
p.dev_install()
# e = Environment.load("/home/bennyl/projects/pkm-new/workspace/xxx_prj/.venv")
# e.install([Dependency.parse("numpy")])

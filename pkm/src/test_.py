from pkm.api.projects.project import Project

project = Project.load("/home/bennyl/projects/pkm-new/workspace/test-prj")
project.attached_environment.install("numpy", updates=["numpy"], repository=project.attached_repository)

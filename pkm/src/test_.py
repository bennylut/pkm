from src.pkm.api.projects.project import Project

p = Project.load("/home/bennyl/projects/pkm-group/pkm-cli")
p.dev_install()

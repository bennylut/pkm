from pkm.api.projects.project import Project

p = Project.load("/home/bennyl/projects/pkm-new/repositories/conda-pkm-repo")
print(p.attached_repository)
# p.dev_install()
# e = Environment.load("/home/bennyl/projects/pkm-new/workspace/test-env")
# from pkm_cli.main import main
# main(['-c', "/home/bennyl/projects/pkm-new/repositories/conda-pkm-repo", 'status'])

# e.install([Dependency.parse("numpy")])

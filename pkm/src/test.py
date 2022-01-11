from pathlib import Path

from pkm.api.projects.project import Project

# pp = PyProjectConfiguration.load(Path("/home/bennyl/projects/pkm-new/workspace/projects/p1/x.toml"))
# pp["x"].append("xxxx")
# pp.save()

p1 = Project.load(Path("/home/bennyl/projects/pkm-new/pkm-cli"))
p1.install_dependencies()
# p1.default_environment.symlink_pth_links()

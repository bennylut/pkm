from pkm.api.environments.environment import Environment

e = Environment.load("/home/bennyl/projects/pkm-new/pkm-cli/.venv")
print(e.site_packages.find_orphan_packages())
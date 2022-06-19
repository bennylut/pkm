# # from pkm.api.dependencies.dependency import Dependency
# from pkm.api.environments.environment import Environment
#
# e = Environment.load("/home/bennyl/projects/pkm-group/workspace/xxx/.venv")
# # e.install([Dependency.parse("pandas")])
# from pkm.repositories.simple_repository import SimpleRepository
#
# sr = SimpleRepository('pypi-simple', "https://pypi.org/simple")
# result = sr.list("poetry", e)
# result[0].install_to(e.installation_target)
# print(result)
from http.server import SimpleHTTPRequestHandler

SimpleHTTPRequestHandler
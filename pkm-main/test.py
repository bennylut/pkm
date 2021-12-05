from pkm_main.environments.remote_introspect import EnvironmentIntrospection

x = EnvironmentIntrospection.local()
print(x)

# from pathlib import Path
#
# interpreter_path = Path('/home/bennyl/projects/pkm-new/pkm-main').rglob('**/bin/python')
# print(list(interpreter_path))


###### EXECUTE PYTHON ######
# import subprocess
# import sys
# import os
# import site
# from pathlib import Path
#
# from pkm_main.environments.remote_introspect import EnvironmentIntrospection
#
# EnvironmentIntrospection().write(Path('/home/bennyl/projects/pkm-new/workspace/introspection.json'))
#
# subprocess.run(
#     ['/home/bennyl/projects/protopy/.venv/bin/python3',
#      '/home/bennyl/projects/pkm-new/pkm-main/pkm_main/environments/remote_introspect.py',
#      '/home/bennyl/projects/pkm-new/workspace/sys-introspection.json'],
#
#     env={"PYTHONPATH": os.pathsep.join(site.getsitepackages())}
# )
#
# print(__file__)

######  list installed packages #######
# import pkg_resources
# installed_packages = {d.project_name: d.version for d in pkg_resources.working_set}
# print(installed_packages)


# from pathlib import Path
# from time import sleep
#
# import pkm.logging.console
# from pkm_main.logging.rich_console import RichConsole
# from pkm_main.utils.http.cache_directive import CacheDirective
# from pkm_main.utils.http.http_client import HttpClient
#
# pkm.logging.console.console = RichConsole()
#
# if __name__ == '__main__':
#     import http.client
#     import logging
#
#     http.client.HTTPConnection.debuglevel = 1
#     logging.basicConfig()
#     logging.getLogger().setLevel(logging.DEBUG)
#     requests_log = logging.getLogger("requests.packages.urllib3")
#     requests_log.setLevel(logging.DEBUG)
#     requests_log.propagate = True
#
#     client = HttpClient(Path('/home/bennyl/projects/pkm-new/workspace/cache'))
#     client.get('https://pypi.org/pypi/relaxed-poetry/json', cache=CacheDirective.ask_for_update()).result()
#     client.get('https://pypi.org/pypi/relaxed-poetry/json', cache=CacheDirective.ask_for_update()).result()


# import sys
# import os
#
# print(sys.path)
# print(os.environ["PYTHONPATH"])

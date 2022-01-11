# from pathlib import Path
#
# from pkm.api.dependencies.dependency import Dependency
# from pkm.api.projects.project import Project
# from pkm_cli.console import console
# from pkm_cli.monitors import ConsoleProjectPackageUpdateMonitor
#
# p = Project.load(Path("/home/bennyl/projects/pkm-new/workspace/projects/p1"))
# p.install_dependencies(
#     new_dependencies=[Dependency.parse_pep508('allennlp')],
#     monitor=ConsoleProjectPackageUpdateMonitor(console))
# from pathlib import Path
#
# from pkm_cli.scaffold.engine import ScaffoldingEngine
#
# engine = ScaffoldingEngine()
# engine.render(
#     Path("/home/bennyl/projects/pkm-new/pkm-cli/src/pkm_cli/scaffold/new_project"),
#     Path("/home/bennyl/projects/pkm-new/workspace/tmp/test-templates"),
#
# )


from prompt_toolkit.shortcuts import ProgressBar
import time
from prompt_toolkit import print_formatted_text as print

print('Hello world')


with ProgressBar() as pb:
    for i in pb(range(800)):
        if i % 100 == 0:
            print("and i going on...")
        time.sleep(.01)
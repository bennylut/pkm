from pkm.api.dependencies.dependency import Dependency
from pkm.api.environments.environment import Environment
from pkm.api.projects.project import Project

# p = Project.load("/home/bennyl/projects/pkm-new/workspace/xxx_prj")
# p.dev_install([Dependency.parse("allennlp")])
e = Environment.load("/home/bennyl/projects/pkm-new/workspace/test-env2")
e.install([Dependency.parse("allennlp")])

# # import test2_
# # test2_.run()
# #
# from time import sleep
#
# from pkm.utils.multiproc import ProcessPoolExecutor
# from test2_ import hello
#
# procs = ProcessPoolExecutor(max_inactivity_seconds=1, max_workers=2)
# r1 = procs.execute(hello, 1, 1)
# r2 = procs.execute(hello, 2, 2)
# r3 = procs.execute(hello, 3, 0)
#
# print(f"r1 = {r1.result()}")
# print(f"r2 = {r1.result()}")
# print(f"r3 = {r1.result()}")
#
# print("sleeping")
# sleep(5)
#
# r4 = procs.execute(hello, 4, 0)
# sleep(1)
# r5 = procs.execute(hello, 5, 0)
#
#
# print(f"r4 = {r4.result()}")
# print(f"r5 = {r5.result()}")
#
#
#
#

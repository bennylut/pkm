from os import chdir

from pkm_cli.main import main
chdir("/home/bennyl/projects/pkm-group/workspace/hello/tasks")
main("pkm -v run @xxx".split())
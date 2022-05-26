from pathlib import Path

import os
from os import system

# builtin extensions: 
global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


# your task execution code:
def run():
    os.chdir(Path(project_info['group_path']) / "docs")
    exit(system("bundle exec jekyll serve"))

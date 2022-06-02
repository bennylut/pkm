import multiprocessing
import shutil
from pathlib import Path

# builtin extensions:
from sphinx.application import Sphinx

global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


# your task execution code:
def run():
    project_path = Path(project_info['path'])

    source_path = project_path / "src"
    output_path = project_path.parent / "docs"

    if output_path.exists():
        print("Deleting previous builds..")
        shutil.rmtree(output_path)

    print("Composing Documentation ...")
    Sphinx(str(source_path), str(source_path), str(output_path), str(output_path / ".doctrees"), "html",
           parallel=multiprocessing.cpu_count()).build()

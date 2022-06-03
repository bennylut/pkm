import shutil
from pathlib import Path

from utils.sphinx_server import SphinxAutoreloadServer

global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


def run(clean=False):
    project_path = Path(project_info['path'])

    source_path = project_path / "src"
    output_path = project_path.parent / "docs"

    if clean and output_path.exists():
        print("Deleting previous builds..")
        shutil.rmtree(output_path)

    with SphinxAutoreloadServer(source_path, output_path, 8000) as server:
        server.serve_forever()

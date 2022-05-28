from pathlib import Path
from typing import Callable

# builtin extensions:
import sass

global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


# your task execution code:
def run():
    project_path = Path(project_info['path'])
    input_path = project_path / "src/_static/scss"
    output_path = project_path / "build/_static"

    assert input_path.exists(), f"input directory could not be found: {input_path}"
    assert output_path.exists(), f"output directory could not be found: {output_path}"

    sass.compile(dirname=(str(input_path), str(output_path)), output_style="compressed")

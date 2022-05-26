import shutil
import subprocess
from pathlib import Path
from re import Pattern
from typing import Callable, List, Tuple
import re

# builtin extensions: 
global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


def relocate_underscores(path: Path, underscore_dirs: List[str]):
    for underscore_dir in underscore_dirs:
        shutil.move(path / underscore_dir, path / underscore_dir[1:])

    rxs: List[Tuple[str, Pattern]] = []
    rxs.extend((uscore, re.compile(f'<[^>]*=\\"(([^"]*\\/{uscore})|{uscore})')) for uscore in underscore_dirs)
    rxs.extend((uscore, re.compile(f"<[^>]*='(([^']*\\/{uscore})|{uscore})")) for uscore in underscore_dirs)
    for html in path.rglob("*.html"):
        text = html.read_text()
        replaced = False
        for uscore, rx in rxs:
            new_text = []
            i = 0
            for match in rx.finditer(text):
                new_text.append(text[i:match.start()])
                new_text.append(match.group()[:-len(uscore)])
                new_text.append(uscore[1:])
                i = match.end()

            if i != 0:
                new_text.append(text[i:])
                text = ''.join(new_text)
                replaced = True

        if replaced:
            html.write_text(text)


# your task execution code:
def run():
    project_path = Path(project_info['path'])

    docs_generation_path = Path(project_info['group_path']).joinpath("docs", "code", "pkm-cli")

    if docs_generation_path.exists():
        print("Deleting previous artifacts..")
        shutil.rmtree(docs_generation_path)

    source_path = project_path / "src"
    sphinx_etc_path = project_path.joinpath('etc', 'sphinx')
    sphinx_templates_path = project_path.joinpath('etc', 'sphinx', "_templates", "apidoc")

    print("Generating API Documentation ...")
    subprocess.run([
        "sphinx-apidoc", "-feMTd5", "--implicit-namespaces",
        "-t", str(sphinx_templates_path),
        "-o", str(sphinx_etc_path / "api"),
        source_path / project_info["name"].replace("-", "_")]).check_returncode()

    print("Composing Documentation ...")
    subprocess.run([
        "sphinx-build", "-b", "html", sphinx_etc_path, str(docs_generation_path), ]).check_returncode()

    print("Relocating underscore directories")
    relocate_underscores(docs_generation_path, ['_modules', '_static', '_sources'])

    print("Done.")

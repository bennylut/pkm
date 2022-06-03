from pathlib import Path

global ask
global target_dir


def setup(name: str = None) -> dict:
    if (target_dir / "pyproject.toml").exists():
        task_parts = name or ask(prompt="Task Name").replace('-', '_').split(".")
        task_name = task_parts[-1]
        task_path = str(Path("tasks").joinpath(*task_parts[:-1]))
    else:
        print("[red]task generation should be initiated in the root of your project[/]")

    return locals()

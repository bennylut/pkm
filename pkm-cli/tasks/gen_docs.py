import warnings
from pathlib import Path

import pdoc

import pkm_cli

# builtin extensions:
global run_task  # run_task(task_name, *args, **kwargs)
global project_info  # dictionary containing information about the executing project context


def run():
    print("Generating Documentation...", end='', flush=True)
    warnings.filterwarnings("ignore", message="Couldn't read PEP-224")
    context = pdoc.Context()
    pdoc.link_inheritance(context)

    doc_generation_path = Path(project_info['group_path']) / "docs" / "code" / "pkm-cli"
    doc_generation_path.mkdir(parents=True, exist_ok=True)

    modules = [pdoc.Module(pkm_cli, context=context)]
    while modules:
        m = modules.pop()
        m_name_parts = m.name.split(".")
        if m.is_package:
            m_path = doc_generation_path.joinpath(*m_name_parts, "index.html")
        else:
            m_path = doc_generation_path.joinpath(*m_name_parts[:-1], f"{m_name_parts[-1]}.html")

        m_path.parent.mkdir(exist_ok=True, parents=True)
        m_path.write_text(m.html())
        modules.extend(m.submodules())

    warnings.resetwarnings()
    print("Done.")

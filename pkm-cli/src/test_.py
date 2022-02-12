from pathlib import Path

from pkm.utils.resources import ResourcePath
from pkm_cli.scaffold.engine import ScaffoldingEngine

ScaffoldingEngine().render(
    ResourcePath('pkm_cli.scaffold', Path(f"new_project.tar.gz")), Path.cwd())

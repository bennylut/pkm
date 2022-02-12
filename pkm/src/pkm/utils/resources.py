from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from importlib.resources import path
from typing import ContextManager


@dataclass
class ResourcePath:
    base_module: str
    path: Path

    @contextmanager
    def use(self) -> ContextManager[Path]:
        with path(self.base_module, self.path) as use_path:
            yield use_path



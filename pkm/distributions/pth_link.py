import os
from pathlib import Path
from typing import List


class PthLink:
    def __init__(self, path: Path, imports: List[str], links: List[Path]):
        self.path = path
        self._imports = imports
        self._links = links

    def save(self):
        with self.path.open('w+') as out:
            for imp in self._imports:
                out.write('import ')
                out.write(imp)
                out.write(os.linesep)

            for link in self._links:
                out.write(str(link.absolute()))
                out.write('\n')

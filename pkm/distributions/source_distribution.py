from pathlib import Path


class SourceDistribution:

    def __init__(self, archive: Path):
        self._archive = archive
        
    def make_wheel(self, store_dir: Path) -> Path:
        """
        creates a wheel from this source distribution and store it inside `store_dir`, then return its path
        :param store_dir: the directory to store the wheel in
        :return: the path to the stored wheel
        """


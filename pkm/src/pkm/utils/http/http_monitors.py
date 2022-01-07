from pathlib import Path

from pkm.utils.monitors import Monitor


class FetchResourceMonitor(Monitor):
    def on_cache_hit(self):
        ...

    def on_download_start(self, file_size: int, path: Path):
        ...

    def on_download_completed(self):
        ...

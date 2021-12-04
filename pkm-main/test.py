from pathlib import Path
from time import sleep

import pkm.logging.console
from pkm_main.logging.rich_console import RichConsole
from pkm_main.utils.http.cache_directive import CacheDirective
from pkm_main.utils.http.http_client import HttpClient

pkm.logging.console.console = RichConsole()

if __name__ == '__main__':
    import http.client
    import logging

    http.client.HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

    client = HttpClient(Path('/home/bennyl/projects/pkm-new/workspace/cache'))
    client.get('https://pypi.org/pypi/relaxed-poetry/json', cache=CacheDirective.ask_for_update()).result()
    client.get('https://pypi.org/pypi/relaxed-poetry/json', cache=CacheDirective.ask_for_update()).result()

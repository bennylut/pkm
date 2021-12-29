import hashlib
import json
import locale
import shutil
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from urllib.parse import SplitResult as ParsedUrl

import urllib3
from pkm.config.configuration import TomlFileConfiguration
from pkm.logging.console import console
from pkm.utils.promises import Promise, Deferred
from pkm.utils.properties import cached_property, clear_cached_properties
from urllib3 import HTTPResponse, Retry

from pkm_main.utils.http.cache_directive import TF_HTTP, CacheDirective

locale.setlocale(locale.LC_ALL, 'en_US.utf8')


class HttpException(IOError):

    def __init__(self, msg: str, response: Optional[HTTPResponse]) -> None:
        super().__init__(msg)
        self.response = response


class TSPoolManager(urllib3.PoolManager):
    # TODO: consider the password manager when creating the pool
    #  (also maybe change the name to auth_manager if it also handles certificates)
    def _new_pool(self, scheme, host, port, request_context=None):
        result = super()._new_pool(scheme, host, port, request_context)

        class PoolProxy:
            def __getattr__(self, item):
                return getattr(result, item)

            def close(self):
                ...

            def __del__(self):
                print("closing connection pool")
                result.close()

        return PoolProxy()


_CONNECTIONS = TSPoolManager(
    25, retries=Retry(connect=5, read=2, redirect=5))  # probably should come from configuration


# _THREADS = ThreadPoolExecutor(os.cpu_count() * 2)


@dataclass
class FetchedResource:
    fetch_info: Path
    data: Path
    _root: Path

    def delete(self):
        self.fetch_info.unlink(missing_ok=True)
        self.data.unlink(missing_ok=True)

        p = self.fetch_info.parent
        while p != self._root:
            if any(p.iterdir()):
                break

            p.unlink()
            p = p.parent

        clear_cached_properties(self)

    def exists(self) -> bool:
        return self.data.exists() and self.fetch_info.exists()

    def read_data_as_json(self) -> Any:
        with self.data.open('r') as inp:
            return json.load(inp)

    @cached_property
    def fetch_info_data(self) -> TomlFileConfiguration:
        return TomlFileConfiguration.load(self.fetch_info)

    def is_hash_valid(self, hash_function: str, hash_hex_value: str):

        fetch_info = self.fetch_info_data
        fetch_hash = fetch_info[f'hash.{hash_function}']

        if not fetch_hash:
            hash = hashlib.new(hash_function)
            with open(self.data, 'rb') as f:
                while True:
                    next = f.read(8192)
                    if not next:
                        break
                    hash.update(next)

            fetch_hash = hash.hexdigest()
            fetch_info[f'hash.{hash_function}'] = fetch_hash
            fetch_info.save()

        return fetch_hash == hash_hex_value

    def save(self, response: HTTPResponse):
        self.data.parent.mkdir(exist_ok=True, parents=True)
        if self.fetch_info.exists():
            self.fetch_info.unlink()

        try:
            with open(self.data, 'wb') as df:
                shutil.copyfileobj(response, df)

            rheaders = response.headers
            last_modified = rheaders.get('last-modified', rheaders.get('date'))

            # noinspection PyPropertyAccess
            fetch_info = self.fetch_info_data = TomlFileConfiguration(path=self.fetch_info)
            fetch_info['fetch-time'] = last_modified or datetime.utcnow().strftime(TF_HTTP)
            fetch_info['etag'] = rheaders.get("etag") or ''

            fetch_info.save()
        except:  # noqa
            self.delete()
            raise


class HttpClient:

    def __init__(self, cache_dir: Path):
        self._cache_dir = cache_dir
        if cache_dir:
            cache_dir.mkdir(exist_ok=True, parents=True)

        self._fetch_inprogress: Dict[str, Promise[FetchedResource]] = {}
        self._fetch_lock = Lock()

    def _add_standard_headers(self, headers: Dict[str, str]):
        headers['user-agent'] = f'pkm'
        headers['accept-encoding'] = 'gzip,deflate'
        headers['connection'] = 'keep-alive'

    def _cache_files_of(self, url: str, parsed_url: ParsedUrl) -> FetchedResource:
        url_hash = hashlib.md5(url.encode('ascii')).hexdigest()
        url_path = Path(parsed_url.path.lstrip('/'))

        if url_path.parent:
            cache_dir = self._cache_dir / parsed_url.netloc / url_path.parent / url_hash
        else:
            cache_dir = self._cache_dir / parsed_url.netloc / url_hash

        data_file = cache_dir / url_path.name
        fetch_file = data_file.with_suffix(".fetch.toml")

        return FetchedResource(fetch_file, data_file, self._cache_dir)

    # def post(self, url: str, body: Union[str, bytes, IOBase], *,
    #          headers: Optional[Dict[str, str]] = None) -> Future:
    #
    #     def _post():
    #
    #         response: Optional[HTTPResponse] = None
    #
    #         try:
    #             nonlocal headers
    #             headers = headers or {}
    #             self._add_standard_headers(headers)
    #             response = _CONNECTIONS.request(
    #                 "POST", url, headers=headers, body=body)
    #
    #             if response.status == 200:
    #                 return response.data
    #             else:
    #                 raise HttpException(f"server responded with {response.status} ({response.msg}) status", response)
    #         except Exception as e:
    #             if isinstance(e, HttpException):
    #                 raise
    #             else:
    #                 raise HttpException(str(e), response) from e
    #
    #     return _THREADS.submit(_post)

    def get(self, url: str, cache: Optional[CacheDirective] = None) -> Optional[FetchedResource]:

        if not cache:
            cache = CacheDirective.allways()

        with self._fetch_lock:

            # If I am already requesting this url - no need to actually do it twice, note that
            # this may pose a problem if one of the recipients will delete the files, i it revealed to be a problem
            # we can fix it by adding a ref-counting delete operation for the FetchedResource for example
            promise = self._fetch_inprogress.get(url)
            if promise:
                return promise.result()

            def _fetch() -> Optional[FetchedResource]:
                headers = {}
                parsed_url: ParsedUrl = urllib.parse.urlsplit(url)
                cache_files = self._cache_files_of(url, parsed_url)
                fetch_info = TomlFileConfiguration.load(cache_files.fetch_info)  # TODO: maybe add the response headers
                self._add_standard_headers(headers)

                use_cached_data = cache_files.exists() and cache.is_cache_valid(fetch_info)
                if not use_cached_data:
                    console.log(f"[Start]: GET {url}...")
                    response: Optional[HTTPResponse] = None

                    try:
                        cache.add_headers(fetch_info, headers)
                        response = _CONNECTIONS.request(
                            "GET", url, headers=headers, preload_content=False)

                        console.log(f"[MID] GET {url} resulted with status code: {response.status}...")

                        if response.status == 200:
                            cache_files.save(response)
                        elif response.status != 304:
                            raise HttpException(
                                f"request to {url} ended with unexpected status code:"
                                f" {response.status} ({response.msg})", response)
                    except Exception as e:
                        if isinstance(e, HttpException):
                            raise
                        else:
                            raise HttpException(str(e), response) from e
                    finally:
                        console.log(f"[End]: GET {url}..., releasing conn")
                        if response:
                            response.release_conn()
                            response.close()
                        with self._fetch_lock:
                            del self._fetch_inprogress[url]

                return cache_files

            deffered: Deferred[Optional[FetchedResource]] = Deferred()
            promise = self._fetch_inprogress[url] = deffered.promise()

        try:
            deffered.complete(_fetch())
        except Exception as e:
            deffered.fail(e)

        return promise.result()

    def clear_cache(self):
        shutil.rmtree(self._cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

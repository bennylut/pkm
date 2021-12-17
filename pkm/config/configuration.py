import configparser
from abc import ABC, abstractmethod
from copy import copy
from pathlib import Path
from typing import Optional, Dict, Any, List, Sequence, Mapping, Iterator, Callable

from pkm.config import toml


class Configuration(ABC):
    DEFAULT_SUBDIR = "etc/pkm"

    def __init__(
            self, *,
            parent: Optional["Configuration"] = None,
            data: Optional[Dict[str, Any]] = None):
        self._parent = parent
        self._data = data if data is not None else {}

    def __getitem__(self, item: Sequence[str]) -> Any:
        if isinstance(item, str):
            item = toml.key2path(item)

        r = self._get(item)
        if r is None and self._parent:
            r = self._parent[item]
        return r

    def __setitem__(self, key: Sequence[str], value: Any):
        if isinstance(key, str):
            key = toml.key2path(key)

        self._set(key, value)

    def __delitem__(self, key: Sequence[str]):
        if isinstance(key, str):
            key = toml.key2path(key)

        self._del(key)

    def __contains__(self, item: Sequence[str]):
        return self[item] is not None

    def get_or_put(self, key: Sequence[str], value_computer: Callable[[], Any]) -> Any:
        if isinstance(key, str):
            key = toml.key2path(key)

        result = self[key]
        if result is None:
            self[key] = result = value_computer()

        return result

    def _get(self, path: Sequence[str]) -> Any:
        r = self._data
        for p in path:
            if r is None:
                return None
            if not isinstance(r, Mapping):
                raise ValueError(f"path: {path} passing through a terminal value {r} at '{p}'")

            r = r.get(p)

        return r

    def _del(self, path: Sequence[str]):
        r = self._data
        for p in path[:-1]:
            if r is None:
                return

            if not isinstance(r, Mapping):
                raise ValueError(f"path: {path} passing through a terminal value {r} at '{p}'")

            r = r.get(p)

        if r is not None:
            del r[path[-1]]

    def _subs_chain(self) -> Iterator["Configuration"]:
        result = []
        r = self
        while r is not None:
            result.append(r)
            r = r._parent

        return reversed(result)

    def collect(self, path: Sequence[str]) -> Any:
        if isinstance(path, str):
            path = toml.key2path(path)

        result = self[path]
        if isinstance(result, List):
            return [it for conf in self._subs_chain() for it in (conf._get(path) or [])]
        elif isinstance(result, Mapping):
            return {k: v for conf in self._subs_chain() for k, v in (conf._get(path).items() or {})}

        return result

    def _set(self, path: Sequence[str], value: Any):
        r = self._data
        for p in path[:-1]:
            if not isinstance(r, Mapping):
                raise ValueError(f"path: {path} passing through a terminal value {r} at '{p}'")

            rp = r.get(p)
            if rp is None:
                r = r[p] = {}
            else:
                r = rp

        r[path[-1]] = value

    def save(self) -> bool:
        self._do_save()
        self._on_modification()
        return True

    def with_parent(self, new_parent: Optional["Configuration"]) -> "Configuration":
        cp = copy(self)
        cp._parent = new_parent
        return cp

    @abstractmethod
    def _do_save(self):
        ...

    def _on_modification(self):
        ...


class FileConfiguration(Configuration, ABC):
    def __init__(self, *, path: Path, parent: Optional["Configuration"] = None, data: Optional[Dict[str, Any]] = None):
        super().__init__(parent=parent, data=data)
        self._path = path

    @abstractmethod
    def generate_content(self) -> str:
        ...

    def _do_save(self):
        self._path.parent.mkdir(exist_ok=True, parents=True)
        self._path.write_text(self.generate_content())

    def exists(self) -> bool:
        return self._path.exists()

    @property
    def path(self) -> Path:
        return self._path


class TomlFileConfiguration(FileConfiguration):
    def generate_content(self) -> str:
        dumps = toml.dumps
        if self._path.exists():
            _, dumps = toml.load(self._path)
        return dumps(self._data)

    @classmethod
    def load(cls, file: Path, parent: Optional[Configuration] = None) -> "TomlFileConfiguration":
        data, _ = toml.load(file) if file.exists() else ({}, None)
        return cls(path=file, parent=parent, data=data)


class InMemConfiguration(Configuration):
    def _do_save(self):
        pass

    @classmethod
    def load(cls, data: Dict[str, Any], parent: Optional[Configuration]) -> "InMemConfiguration":
        return cls(parent=parent, data=data)


class _CaseSensitiveConfigParser(configparser.ConfigParser):
    optionxform = staticmethod(str)


_CASE_SENSITIVE_INI_PARSER = configparser.ConfigParser()


class IniFileConfiguration(FileConfiguration):
    def generate_content(self) -> str:
        class StringWriter:
            def __init__(self):
                self.v: List[str] = []

            def write(self, s: str):
                self.v.append(s)

        sw = StringWriter()
        _CASE_SENSITIVE_INI_PARSER.write(sw)
        return ''.join(sw.v)

    @classmethod
    def load(cls, file: Path) -> "IniFileConfiguration":
        data = _CASE_SENSITIVE_INI_PARSER.read(str(file)) if file.exists() else {}
        return cls(path=file, data=data)

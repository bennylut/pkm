from __future__ import annotations

import builtins
import importlib
import importlib.util as iu
import sys
from dataclasses import dataclass
from threading import RLock
from types import ModuleType, TracebackType
from typing import Any, Optional, Sequence, Dict

PACKAGE_LAYER = "__package_layer__"
_MISSING = object()
_DEBUG = False


def filter_stack(t: Optional[TracebackType] = None) -> TracebackType:
    if t is None:
        t = sys.exc_info()[2]
    base = None
    if (next := t.tb_next) is not None:
        base = filter_stack(next)
    if (fn := t.tb_frame.f_code.co_filename).endswith("__app__.py") or fn.startswith("<frozen importlib."):
        return base
    return TracebackType(base, t.tb_frame, t.tb_lasti, t.tb_lineno)


if _DEBUG:
    def filter_stack(_=None):
        return sys.exc_info()[2]


class _AppModules(dict):
    def _get(self, item):
        if (result := super().get(item, _MISSING)) is _MISSING:
            result = sys.modules.get(item, _MISSING)
        return result

    def __getitem__(self, item):
        if (result := self._get(item)) is _MISSING:
            raise KeyError(item)
        return result

    def get(self, key, default=None):
        if (result := self._get(key)) is _MISSING:
            return default
        return result

    def items(self):
        yield from super().items()
        yield from sys.modules.items()


@dataclass
class _PathImport:
    first_module: ModuleType
    last_module: ModuleType
    in_app: bool


class _AppImporter:

    def __init__(self, app_package: str):
        self.app_builtins = ModuleType(builtins.__name__, builtins.__doc__)
        self.app_builtins.__dict__.update(builtins.__dict__)
        self.app_builtins.__import__ = self.__import__

        self.app_importlib = ModuleType(importlib.__name__, importlib.__doc__)
        self.app_importlib.__dict__.update(importlib.__dict__)
        self.app_importlib.__import__ = self.__import__
        self.app_importlib.import_module = self.import_module

        self.app_sys = ModuleType(sys.__name__, sys.__doc__)
        self.app_sys.__dict__.update(sys.__dict__)

        self._import_lock = RLock()
        self._import_cache: Dict[str, _AppImport] = {
            'sys': _AppImport(self, 'sys', self.app_sys),
            'importlib': _AppImport(self, 'importlib', self.app_importlib),
            'builtins': _AppImport(self, 'builtins', self.app_builtins)
        }

        self.app_sys.modules = _AppModules()
        self.app_sys.modules.update({k: i.module for k, i in self._import_cache.items()})

        self.app_package = app_package
        self.app_prefix = f"{app_package}.{PACKAGE_LAYER}"

    def _single_import(self, fqn: str, check_app_packages: bool = True) -> _AppImport:
        with self._import_lock:
            cur_import = self._import_cache.get(fqn)
            if not cur_import:
                cur_import = self._import_cache[fqn] = _AppImport(self, fqn)

        cur_import.do_import(self.app_prefix if check_app_packages else '')
        assert cur_import.module is not None
        return cur_import

    def _path_import(self, app_fqn: str) -> _PathImport:
        required_modules = app_fqn.split(".")

        package_import = self._single_import(required_modules[0])
        in_app_packages = package_import.is_in_app_packages()
        last_module = first_module = package_import.module

        for i in range(1, len(required_modules)):
            if not (next_module := getattr(last_module, required_modules[i], None)) \
                    or not isinstance(next_module, ModuleType):
                setattr(
                    last_module, required_modules[i], next_module := self._single_import(
                        '.'.join(required_modules[:i + 1]), in_app_packages).module)
            last_module = next_module

        return _PathImport(first_module, last_module, in_app_packages)

    def import_module(self, name: str, package: Optional[str] = None):
        app_fqn = name
        if package is not None:
            app_fqn = iu.resolve_name(name, package)
            if app_fqn.startswith(self.app_prefix + "."):
                app_fqn = app_fqn[len(self.app_prefix) + 1:]

        try:
            return self._path_import(app_fqn).last_module
        except Exception as e:
            raise e.with_traceback(filter_stack())

    def __import__(self, name: str, globals: Optional[Dict[str, Any]] = None,  # noqa
                   locals: Optional[Dict[str, Any]] = None,  # noqa
                   fromlist: Sequence[str] = (), level: int = 0):

        if level > 0:
            app_fqn = iu.resolve_name('.' * level + name, globals['__package__'])
            if not app_fqn.startswith(self.app_prefix):
                raise ImportError("attempt for stepping out of application packages")
            app_fqn = app_fqn[len(self.app_prefix) + 1:]
        else:
            app_fqn = name

        try:
            path_import = self._path_import(app_fqn)

            if fromlist:
                if (lm := path_import.last_module).__spec__.submodule_search_locations:
                    for item in fromlist:
                        if not hasattr(lm, item):
                            setattr(lm, item, self._single_import(f"{app_fqn}.{item}", path_import.in_app).module)
                return lm

            return path_import.first_module
        except Exception as e:
            raise e.with_traceback(filter_stack())

    def unregister_module(self, imp: _AppImport):
        with self._import_lock:
            if imp.is_in_app_packages():
                del self.app_sys.modules[imp.app_fqn]  # noqa
            del sys.modules[imp.sys_fqn]

    def register_module(self, imp: _AppImport):
        with self._import_lock:
            if imp.is_in_app_packages():
                self.app_sys.modules[imp.app_fqn] = imp.module  # noqa
            sys.modules[imp.sys_fqn] = imp.module


class _AppImport:
    def __init__(self, importer: _AppImporter, app_fqn: str, module: Optional[ModuleType] = None):
        self.app_fqn = app_fqn
        self.sys_fqn = app_fqn
        self.module: Optional[ModuleType] = module
        self._import_lock = RLock()
        self._importer = importer

    def is_in_app_packages(self) -> bool:
        return self.app_fqn != self.sys_fqn

    def do_import(self, app_prefix: str):
        if self.module is not None:
            return

        with self._import_lock:
            # while I waited for the lock, other thread might have imported the module
            if self.module is not None:
                return

            if not app_prefix or not (spec := iu.find_spec(sys_fqn := f"{app_prefix}.{self.app_fqn}")):
                if not (spec := iu.find_spec(sys_fqn := self.app_fqn)):
                    self._importer.register_module(self)
                    raise ModuleNotFoundError(f"no module named '{self.app_fqn}'")

            self.sys_fqn = sys_fqn

            if preloaded := sys.modules.get(spec.name):
                self.module = preloaded
                return

            self.module = iu.module_from_spec(spec)
            self._importer.register_module(self)

        if self.is_in_app_packages():
            self.module.__builtins__ = self._importer.app_builtins.__dict__

        try:
            spec._initializing = True
            spec.loader.exec_module(self.module)
        except Exception:
            self._importer.unregister_module(self)
            self.module = None
            raise
        finally:
            spec._initializing = False


class ApplicationLoader:
    def __init__(self, app_package: str):
        self.importer = _AppImporter(app_package)

    def load(self, module: str) -> Any:
        return self.importer.import_module(module)
    #
    # def exec(self, module: str, object_ref: Optional[str]) -> NoReturn:
    #     from importlib.resources import path
    #     with path(self._app_package, PACKAGE_LAYER) as player_path:
    #         sys.path.insert(0, str(player_path))
    #         if object_ref:
    #             exec(f"import {module} as m; exit(m.{object_ref}())")
    #         else:
    #             exec(f"import {module}; exit(0)")

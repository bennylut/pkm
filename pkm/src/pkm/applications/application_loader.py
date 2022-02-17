import importlib
import sys
import threading
from types import ModuleType
from typing import Set, NoReturn, Any, Optional

# PACKAGE_LAYER = "__package_layer__"
PACKAGE_LAYER = "__package_layer__"


# noinspection PyShadowingBuiltins,PyUnresolvedReferences
class ApplicationLoader:
    def __init__(self, app_package: str):
        self._app_package = app_package

        app_builtins = ModuleType(__builtins__.__name__, __builtins__.__doc__)

        for k in dir(__builtins__):
            setattr(app_builtins, k, getattr(__builtins__, k))

        normal_import = __builtins__.__import__
        import importlib.util as iu
        app_packages = f"{app_package}.{PACKAGE_LAYER}"
        tlocal = threading.local()

        def tlocal_loading() -> Set[str]:
            if not (result := getattr(tlocal, 'loading', None)):
                result = tlocal.loading = set()
            return result

        def __import__(name, globals=None, locals=None, fromlist=(), level=0):
            loading = tlocal_loading()

            if level > 0:
                iname = '.'.join([*globals['__package__'].split(".")[:-level + 1], name])
            else:
                iname = f"{app_packages}.{name}"

            if module := sys.modules.get(iname):
                return module

            if spec := importlib.util.find_spec(iname):
                if iname in loading:
                    raise ImportError("Import cycle detected")

                loading.add(iname)
                try:
                    module = importlib.util.module_from_spec(spec)

                    module.__builtins__ = app_builtins
                    spec.loader.exec_module(module)
                    sys.modules[iname] = module
                    return module
                finally:
                    loading.remove(iname)

            return normal_import(name, globals, locals, fromlist, level)

        app_builtins.__import__ = __import__
        self._app_builtins = app_builtins

    def load(self, module: str) -> Any:
        return self._app_builtins.__import__(module)

    def exec(self, module: str, object_ref: Optional[str]) -> NoReturn:
        from importlib.resources import path
        with path(self._app_package, PACKAGE_LAYER) as player_path:
            sys.path.insert(0, str(player_path))
            if object_ref:
                exec(f"import {module} as m; exit(m.{object_ref}())")
            else:
                exec(f"import {module}; exit(0)")

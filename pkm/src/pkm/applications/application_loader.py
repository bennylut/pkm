import sys
import threading
from threading import RLock
from types import ModuleType
from typing import NoReturn, Any, Optional, Set

PACKAGE_LAYER = "__package_layer__"


# noinspection PyShadowingBuiltins,PyUnresolvedReferences
class ApplicationLoader:
    def __init__(self, app_package: str):
        self._app_package = app_package

        builtin_dict = __builtins__
        if not isinstance(builtin_dict, dict):
            builtin_dict = builtin_dict.__dict__

        app_builtins = ModuleType(builtin_dict['__name__'], builtin_dict['__doc__'])
        app_builtins.__dict__.update(builtin_dict)
        normal_import = builtin_dict['__import__']
        import importlib.util as iu
        app_packages = f"{app_package}.{PACKAGE_LAYER}"

        blacklist: Set[str] = set()
        blacklist_lock = RLock()

        def is_in_blacklist(module_fqn: str) -> bool:
            with blacklist_lock:
                return module_fqn in blacklist

        def add_to_blacklist(module_fqn: str):
            with blacklist_lock:
                blacklist.add(module_fqn)

        tlocal = threading.local()

        def tlocal_loading() -> Set[str]:
            if not (result := getattr(tlocal, 'loading', None)):
                result = tlocal.loading = set()
            return result

        def package_layer_import(module_fqn: str) -> Optional[ModuleType]:
            if module := sys.modules.get(module_fqn):
                return module

            try:
                if not package_layer_import(module_fqn[:module_fqn.rindex('.')]):
                    return None
            except IndexError:
                pass

            loading = tlocal_loading()

            if spec := iu.find_spec(module_fqn):
                if module_fqn in loading:
                    raise ImportError("Import cycle detected")

                loading.add(module_fqn)

                try:
                    module = iu.module_from_spec(spec)
                    module.__builtins__ = app_builtins.__dict__
                    sys.modules[module_fqn] = module
                    spec.loader.exec_module(module)

                    return module
                finally:
                    loading.remove(module_fqn)

            return None

        def __import__(name, globals=None, locals=None, fromlist=(), level=0):

            og_fromlist = fromlist

            # handle relative imports
            if level > 0:
                module_fqn = iu.resolve_name('.' * level + name, globals['__package__'])
            else:
                module_fqn = f"{app_packages}.{name}"

            # handle full module imports
            if not fromlist and '.' in name:
                lindex = module_fqn.rindex('.')
                fromlist = (module_fqn[lindex + 1:],)
                module_fqn = module_fqn[:lindex]

            if is_in_blacklist(module_fqn):
                return normal_import(name, globals, locals, og_fromlist, level)

            main_module = package_layer_import(module_fqn)

            if main_module is None:
                add_to_blacklist(module_fqn)
                return normal_import(name, globals, locals, og_fromlist, level)

            if not fromlist or not main_module.__spec__.submodule_search_locations:
                return main_module

            for submodule_name in fromlist:
                if not hasattr(main_module, submodule_name):
                    submodule_fqn = f"{module_fqn}.{submodule_name}"
                    if is_in_blacklist(submodule_fqn):
                        return normal_import(name, globals, locals, og_fromlist, level)

                    if (submodule := package_layer_import(submodule_fqn)) is None:
                        add_to_blacklist(submodule_fqn)
                        return normal_import(name, globals, locals, og_fromlist, level)

                    setattr(main_module, submodule_name, submodule)

            return main_module

        app_builtins.__import__ = __import__
        self._app_builtins = app_builtins

    def load(self, module: str) -> Any:
        result = self._app_builtins.__import__(module)
        try:
            return getattr(result, module[module.rindex('.') + 1:])
        except AttributeError:
            return result

    def exec(self, module: str, object_ref: Optional[str]) -> NoReturn:
        from importlib.resources import path
        with path(self._app_package, PACKAGE_LAYER) as player_path:
            sys.path.insert(0, str(player_path))
            if object_ref:
                exec(f"import {module} as m; exit(m.{object_ref}())")
            else:
                exec(f"import {module}; exit(0)")

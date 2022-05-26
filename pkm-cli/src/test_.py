# import argparse
# import ast
# import inspect
# import typing
# from types import FunctionType
# from typing import Optional, Dict, TYPE_CHECKING, Callable
#
# args = ["name", "15", "some=thing"]
# # if TYPE_CHECKING:
# from pkm.api.pkm import Pkm
# import pkm_cli.display.display as d
#
#
# def run(name: str, value, bla: Optional[str], some: Pkm):
#     print(locals())
#
#
# def coerse(arg_types: Dict[str, type]):
#     ...
#
#
# def arg2py(arg: str) -> str:
#     name, sep, value = arg.partition('=')
#     if sep:
#         return f"{name}={repr(value)}"
#     return repr(arg)
#
#
# def get_type_hints(fun: FunctionType) -> Dict[str, type]:
#     try:
#         return typing.get_type_hints(fun)
#     except NameError as e:
#
#         print(f"got ERROR: {e}")
#
#         module = inspect.getmodule(fun)
#         source = inspect.getsource(module)
#         t = ast.parse(source)
#         for element in ast.walk(t):
#             if isinstance(element, (ast.Import, ast.ImportFrom)):
#                 print([it.asname for it in element.names])
#                 print(ast.dump(element))
#                 print(ast.unparse(element))
#
#
# print(typing.get_type_hints(run))
# print(inspect.getfullargspec(run))
# exec("run(" + ', '.join(arg2py(it) for it in args) + ")")

# print(get_type_hints(run))
#
#
# def run(arg1: str, arg2: int, optional_arg1: int = 7, optional_arg2: Optional[str] = None):
#     print(locals())
#
#
# run("arg1-value", 42, optional_arg2='value for arg2')

import typing
import importlib
import json
import sys
import inspect
from pathlib import Path


def run(name: str, age: int, v1: str = 'hello', v2: int = 17):
    print(locals())


# insn = json.loads(Path(sys.argv[0]).read_text())
# sys.path.insert(1, insn['path'])
# task = importlib.import_module(insn['task'])
# run_function = task.run
run_function = run
arg_types = typing.get_type_hints(run_function)
# args = insn['args']
args = ["hello", "47"]
kwargs = {"v2": "145"}
arg_names = inspect.getfullargspec(run).args
named_args = zip(args, arg_names)


def identity(x):
    return x


def typeof(name: str):
    result = arg_types.get(name, identity)
    if isinstance(result, str):
        result = identity
    return result


parsed_args = [typeof(name)(arg) for arg, name in named_args]
parsed_kwargs = {k: typeof(k)(v) for k, v in kwargs.items()}

print(parsed_args)
print(parsed_kwargs)

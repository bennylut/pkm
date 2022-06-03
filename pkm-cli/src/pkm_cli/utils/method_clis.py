# IMPORTANT: THIS FILE IS INTENDED TO BE COPIED STANDALONE TO OTHER ENVIRONMENTS BY THE TASK RUNNER
# IT SHOULD ONLY USE THE PYTHON STANDARD LIBRARY

from __future__ import annotations

import inspect
import typing
from io import UnsupportedOperation
from typing import List, Dict, Callable, Any, Optional, Union


class MethodCliArgs:
    def __init__(self, args: List[str], kwargs: Dict[str, str]):
        self._args = args
        self._kwargs = kwargs

    def execute(self, method: Callable) -> Any:
        arg_types = typing.get_type_hints(method)
        arg_names = inspect.getfullargspec(method).args
        named_args = zip(self._args, arg_names)

        def identity(x):
            return x

        def parser_for(name: str):
            result_ = arg_types.get(name, identity)
            if result_ == str:
                result_ = identity
            elif str(result_).startswith("typing.Union["): # horible hack to handle Optional...
                type_args = typing.get_args(result_)
                if len(type_args) == 2 and type_args[1].__name__ == 'NoneType':
                    result_ = type_args[0]

            return result_

        parsed_args = [parser_for(name)(arg) for arg, name in named_args]
        parsed_kwargs = {k: parser_for(k)(v) for k, v in self._kwargs.items()}
        return method(*parsed_args, **parsed_kwargs)

    @classmethod
    def parse(cls, args: List[str]) -> MethodCliArgs:
        a, k = [], {}
        for arg in args:

            if arg.startswith('--'):
                if '=' in arg:
                    arg = arg[2:]
                else:
                    arg = arg[2:] + "=True"

            name, sep, value = arg.partition('=')
            if sep:
                k[name] = value
            elif k:
                raise UnsupportedOperation(
                    f"positional arguments are not supported after named arguments: {arg}")
            else:
                a.append(arg)

        return cls(a, k)

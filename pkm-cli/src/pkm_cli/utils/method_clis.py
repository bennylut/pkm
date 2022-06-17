# IMPORTANT: THIS FILE IS INTENDED TO BE COPIED STANDALONE TO OTHER ENVIRONMENTS BY THE TASK RUNNER
# IT SHOULD ONLY USE THE PYTHON STANDARD LIBRARY

from __future__ import annotations

import inspect
import typing
from abc import ABC, abstractmethod
from io import UnsupportedOperation
from typing import List, Dict, Callable, Any


class MethodArgs(ABC):

    @abstractmethod
    def invoke(self, mtd: Callable) -> Any:
        ...


class SimpleMethodArgs(MethodArgs):

    def __init__(self, *args, **kwargs):
        self._args = args
        self._kwargs = kwargs

    def invoke(self, mtd: Callable) -> Any:
        return mtd(*self._args, **self._kwargs)


class CliMethodArgs(MethodArgs):
    def __init__(self, args: List[str], kwargs: Dict[str, str]):
        self._args = args
        self._kwargs = kwargs

    def invoke(self, method: Callable) -> Any:
        arg_types = typing.get_type_hints(method)
        arg_names = inspect.getfullargspec(method).args
        named_args = zip(self._args, arg_names)

        def identity(x):
            return x

        def parser_for(name: str) -> Callable:
            type_ = arg_types.get(name, identity)
            if type_ == str:
                type_ = identity
            elif type_ == typing.Union or typing.get_origin(type_) == typing.Union:
                type_args = [t for t in typing.get_args(type_) if t.__name__ != 'NoneType']
                if type_args:
                    type_ = type_args[0]

            return type_

        parsed_args = [parser_for(name)(arg) for arg, name in named_args]
        parsed_kwargs = {k: parser_for(k)(v) for k, v in self._kwargs.items()}
        return method(*parsed_args, **parsed_kwargs)

    @classmethod
    def parse(cls, args: List[str]) -> CliMethodArgs:
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

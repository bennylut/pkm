from argparse import Action, FileType, Namespace, ArgumentParser
from copy import copy
from dataclasses import dataclass
from typing import List, Type, Union, Optional, Any, TypeVar, Generic, Callable, Tuple, Iterable, Dict

from pkm.utils.dicts import remove_none_values
from pkm.utils.pipes import pipe, p_map_not_none, p_for_each

_T = TypeVar("_T")
_CommandHandler = Callable[[Namespace], None]


@dataclass
class Arg(Generic[_T]):
    name_or_flags: Union[str, List[str]]
    action: Union[str, Type[Action], None] = None
    nargs: Union[int, str, None] = None
    const: Optional[Any] = None
    default: Optional[_T] = None
    type: Union[Callable[[str], _T], FileType, None] = None
    choices: Optional[Iterable[_T]] = None
    required: Optional[bool] = None
    help: Optional[str] = None
    metavar: Union[str, Tuple[str, ...], None] = None
    dest: Optional[str] = None
    version: Optional[str] = None


@dataclass
class Command:
    path: str
    args: Iterable[Arg]
    handler: _CommandHandler
    help: str


def command(path: str, *args: Arg):
    def _command(func: _CommandHandler) -> _CommandHandler:
        func.__command = Command(path, args, func, func.__doc__)
        return func

    return _command


class SubParsers:
    def __init__(self, parser: ArgumentParser):
        self._parser = parser
        self._subparsers_holder = parser.add_subparsers()
        self._subparsers: Dict[str, SubParsers] = {}

    def add_command(self, cmd: Command) -> ArgumentParser:
        path = cmd.path.split()

        if not path:
            raise ValueError("path cannot be empty")

        sp = self
        for p in path[1:-1]:
            if not (nsp := sp._subparsers.get(p)):
                new_parser = sp._subparsers_holder.add_parser(p)
                nsp = sp._subparsers[p] = SubParsers(new_parser)
            sp = nsp

        parser = sp._subparsers_holder.add_parser(path[-1])
        if cmd.help:
            parser.epilog = cmd.help

        for arg in cmd.args:
            d = remove_none_values(copy(arg.__dict__))
            name_or_flags = d.pop('name_or_flags')
            if isinstance(name_or_flags, str):
                name_or_flags = [name_or_flags]

            parser.add_argument(*name_or_flags, **d)

        parser.set_defaults(func=cmd.handler)
        return parser


def create_args_parser(
        desc: str, commands: Iterable[Any], command_customizer: Callable[[ArgumentParser], None] = lambda _: None
) -> ArgumentParser:
    main = ArgumentParser(description=desc)
    parser = SubParsers(main)

    pipe(commands) \
        | p_map_not_none(lambda it: getattr(it, "__command", None)) \
        | p_for_each(lambda it: command_customizer(parser.add_command(it)))

    return main


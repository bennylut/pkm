from __future__ import annotations

import re
from abc import abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from types import FunctionType, GeneratorType
from typing import List, Protocol, Optional, Dict, Callable, TypeVar, Iterable, Any, Tuple, Union, Mapping, cast

from pkm.utils.commons import IllegalStateException, UnsupportedOperationException, NoSuchElementException
from pkm.utils.dicts import get_or_put
from pkm.utils.iterators import first_or_raise, first_or_none
from pkm.utils.properties import cached_property
from pkm.utils.seqs import seq
from pkm.utils.symbol import Symbol
from pkm.utils.types import Mapper
from pkm_cli.display.display import Display

_COMMAND_SYM = Symbol("commandline_parser.command")
_MISSING = object()


@dataclass
class Command:
    ast: CommandAST
    parent: Optional[Command] = None
    path: Tuple[str, ...] = field(default_factory=tuple)
    arguments: Dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, item):
        return self.arguments.get(item)

    def parents(self) -> Iterable[Command]:
        if self.parent:
            yield from self.parent.parents()
            yield self.parent

    def parent_by_path(self, *path: str) -> Command:
        parents = list(self.parents())
        if len(parents) < len(path):
            raise NoSuchElementException(f"{' '.join(path)} is not part of the path to parent")

        for part, parent in zip(path, parents[1:]):
            if part != parent.path[-1]:
                raise NoSuchElementException(f"{part} is no a part of the path to parent")

        return parents[len(path)]

    def execute(self) -> Any:
        if cmd_def := self.ast.command_def:
            return cmd_def.execution(self)
        return None


class ArgDefsProvider(Protocol):
    @abstractmethod
    def __call__(self, left_parse: Command) -> List[ArgumentDef]:
        ...


class ArgumentDef(Protocol):
    help: str
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgDefsProvider] = None

    @cached_property
    def defined_names(self) -> Iterable[str]:
        if name := getattr(self, "name", None):
            return name,

        elif names := getattr(self, "names"):
            return names

        else:
            raise IllegalStateException("no name / names field")

    @cached_property
    def field_name(self) -> str:
        names = self.defined_names
        field_base = first_or_none(
            it for it in names if it.startswith("--") or not it.startswith("-")) or first_or_raise(names)
        return _identifierify(field_base.lstrip('-+'))

    def has_subfields(self) -> bool:
        return self.fields_provider is not None or self.fields is not None

    def compute_subfield_defs(self, left_command: Command) -> Optional[List[ArgumentDef]]:
        if not self.has_subfields():
            return None

        result = []
        if self.fields_provider:
            result.extend(self.fields_provider(left_command))
        if self.fields:
            result.extend(self.fields)

        for subfield in result:
            if (subfield.fields_provider or subfield.fields) is not None:
                raise UnsupportedOperationException(
                    f"fields of an argument cannot have sub-fields: {self.display_name}::{subfield.display_name} has.")

        return result

    @cached_property
    def display_name(self) -> str:
        return ', '.join(self.defined_names)

    def short_name(self) -> str:
        return seq(self.defined_names).min_by(len)

    def is_required(self) -> bool:
        return True

    def is_multival(self):
        return False

    @property
    def default_value(self) -> Any:
        return None

    def map_value(self, v: str) -> Any:
        if choices := getattr(self, 'choices', None):
            if v not in choices:
                raise ValueError(f"illegal value for argument {self.display_name}: {v}, "
                                 f"choices are: {', '.join(choices)}")
        if mapper := getattr(self, 'mapper', None):
            v = mapper(v)

        return v


@dataclass
class PositionalArgumentDef(ArgumentDef):
    name: str
    help: str = ""
    choices: Optional[List[str]] = None
    n_values: Union[int, str] = 1
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgDefsProvider] = None
    mapper: Optional[Mapper[str, Any]] = None

    def __post_init__(self):
        assert not self.name.startswith("+"), "attached positional arguments are not supported"

    def is_multival(self):
        return self.n_values != 1


@dataclass
class OptionDef(ArgumentDef):
    names: List[str]
    help: str = ""
    default_value: Any = _MISSING
    choices: Optional[List[str]] = None
    repeatable: bool = False
    mutex_group: Optional[str] = None
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgDefsProvider] = None
    mapper: Optional[Mapper[str, Any]] = None

    def __post_init__(self):
        if not self.names:
            raise UnsupportedOperationException("at least one name is required for option definition")

    def is_multival(self):
        return self.repeatable

    def is_required(self) -> bool:
        return self.default_value is _MISSING


@dataclass
class FlagDef(ArgumentDef):
    names: List[str]
    help: str = ""
    mutex_group: Optional[str] = None
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgDefsProvider] = None

    def __post_init__(self):
        if not self.names:
            raise UnsupportedOperationException("at least one name is required for flag definition")

    @property
    def default_value(self) -> Any:
        return False

    def is_required(self) -> bool:
        return False

    def map_value(self, assignment: str) -> Any:
        return True


@dataclass
class DynamicArgumentsDef(ArgumentDef):
    provider: ArgDefsProvider

    @property
    def name(self) -> str:
        return "__dynamic__"


@dataclass
class CommandDef:
    path: List[str]
    execution: Callable[[Command], Any]
    arguments_def: Iterable[ArgumentDef] = field(default_factory=tuple)
    help: str = ""
    short_desc: str = ""

    def __post_init__(self):
        assert not self.is_dynamic() or not self.arguments_def, "dynamic command providers cannot have arguments"

    def is_dynamic(self) -> bool:
        return self.path and self.path[-1] == '*'


positional = PositionalArgumentDef
dynamic = DynamicArgumentsDef
_F = TypeVar("_F", FunctionType, Callable)
_COMMA_RX = re.compile(r"\s*,\s*")


# noinspection PyShadowingBuiltins
def flag(
        names: str, *, help: str = "", mutex_group: Optional[str] = None,
        fields: Optional[List[ArgumentDef]] = None, fields_provider: Optional[ArgDefsProvider] = None) -> FlagDef:
    return FlagDef(
        _COMMA_RX.split(names), help=help, mutex_group=mutex_group, fields=fields,
        fields_provider=fields_provider)


# noinspection PyShadowingBuiltins
def option(
        names: str, *, help: str = "", default_value: Any = _MISSING, choices: Optional[List[str]] = None,
        repeatable: bool = False, mutex_group: Optional[str] = None, fields: Optional[List[ArgumentDef]] = None,
        fields_provider: Optional[ArgDefsProvider] = None, mapper: Optional[Mapper[str, Any]] = None) -> OptionDef:
    return OptionDef(
        _COMMA_RX.split(names), help, default_value, choices, repeatable, mutex_group, fields=fields,
        fields_provider=fields_provider, mapper=mapper)


# noinspection PyShadowingBuiltins
def command(path: str, *argument_definitions: ArgumentDef, short_desc: str = "") -> Callable[[_F], _F]:
    def decorate(f: _F) -> _F:
        _COMMAND_SYM.setattr(
            f, CommandDef(path.split(), f, argument_definitions, (f.__doc__ or short_desc).strip(), short_desc))
        return f

    return decorate


@dataclass
class CommandAST:
    path: Tuple[str, ...]
    command_def: Optional[CommandDef] = None
    children: Optional[Dict[str, CommandAST]] = None
    dynamic: bool = False

    @cached_property
    def options(self) -> Dict[str, ArgumentDef]:
        if not self.command_def:
            return {}

        return {
            o_name: o for o in self.command_def.arguments_def
            if isinstance(o, (OptionDef, FlagDef))
            for o_name in o.names}

    @cached_property
    def positional_args(self) -> Tuple[PositionalArgumentDef, ...]:
        if not self.command_def:
            return ()

        return tuple(
            a for a in self.command_def.arguments_def
            if isinstance(a, (PositionalArgumentDef, DynamicArgumentsDef)))

    @classmethod
    def create(cls, commands: List[CommandDef], base_path: Tuple[str] = ()) -> CommandAST:
        result = CommandAST(base_path)
        for command_ in commands:
            node = result
            for p in command_.path:
                if p == "*":
                    if node.children:
                        colliding: CommandAST = first_or_raise(node.children.values())
                        raise UnsupportedOperationException(
                            f"Dynamic Command {' '.join(command_.path)} collides with {' '.join(colliding.path)}")
                    node.dynamic = True
                    break

                if not node.children:
                    node.children = {}

                if not (next_node := node.children.get(p)):
                    next_node = node.children[p] = CommandAST((*node.path, p))
                node = next_node

            node.command_def = command_

        return result


def commands_from(env: Union[Iterable[Any], Dict[str, Any]]) -> List[CommandDef]:
    if isinstance(env, Mapping):
        env = env.values()

    return [command_ for v in env if (command_ := _COMMAND_SYM.getattr(v))]


class DynamicCommandLine:
    def __init__(
            self, args: List[str], commands: List[CommandDef], offset: int = 0,
            base_command: Optional[Command] = None):
        self._args = args
        self._index = offset
        self._commands = commands
        self._command = base_command or Command(CommandAST.create(commands))
        self._positional_index = 0

    def _skip(self):
        self._index += 1

    def _next_or_none(self) -> Optional[str]:
        if self._index < len(self._args):
            result = self._args[self._index]
            self._index += 1
            return result
        return None

    def _peek_or_none(self) -> Optional[str]:
        if self._index < len(self._args):
            return self._args[self._index]
        return None

    def _next_or_raise(self, err: str) -> str:
        if (result := self._next_or_none()) is not None:
            return result
        raise ValueError(err)

    def _remaining(self) -> int:
        return len(self._args) - self._index

    def _has_remaining(self) -> bool:
        return len(self._args) > self._index

    @staticmethod
    def _generate_defaults_for(argument_def: ArgumentDef) -> Any:
        if argument_def.is_required():
            raise ValueError(f"missing required argument: {argument_def.display_name}")

        return argument_def.default_value

    def _expand_dynamic(
            self, dynamic_arg_def: Union[DynamicArgumentsDef]):

        command_def = self._command.ast.command_def
        old_args = command_def.arguments_def

        dynamic_args: List[ArgumentDef] = dynamic_arg_def.provider(self._command)

        abs_dynamic_position = seq(old_args).index_of_matching(lambda it: it is dynamic_arg_def)

        expanded_args = [*old_args[:abs_dynamic_position], *dynamic_args, *old_args[abs_dynamic_position + 1:]]
        dynamic_command_def = replace(command_def, arguments_def=expanded_args)

        self._command = replace(self._command, ast=replace(self._command.ast, command_def=dynamic_command_def))

    def _read_subfields(self, arg_def: ArgumentDef, value: Any) -> Any:
        if (subfields := arg_def.compute_subfield_defs(self._command)) is not None:
            value = {'value': value}

            subfields_map: Dict[str, ArgumentDef] = {name: it for it in subfields for name in it.defined_names}

            while (next_ := self._peek_or_none()) and next_.startswith("+"):
                self._next_or_none()
                okey, _, ovalue = next_.partition("=")

                if not (option_def := subfields_map.get(okey)):
                    raise ValueError(f"unrecognized attached option: {okey} for target: {arg_def.display_name}")

                value[option_def.field_name] = option_def.map_value(ovalue)

            for subfield in subfields:
                if subfield.field_name not in value:
                    value[subfield.field_name] = self._generate_defaults_for(subfield)

        return value

    def _read_positional(self):
        argument: PositionalArgumentDef = self._command.ast.positional_args[self._positional_index]
        nvalues = argument.n_values
        values = []

        while self._has_remaining() and (nvalues == "*" or len(values) < nvalues):
            next_ = self._next_or_none()
            if next_.startswith("-") or next_.startswith("+"):
                raise ValueError(f"missing value for positional argument {argument.display_name}")
            values.append(self._read_subfields(argument, argument.map_value(next_)))

        if nvalues == "*":
            ...
        elif nvalues != len(values):
            raise ValueError(
                f"insufficient values for positional argument {argument.display_name}, expecting {nvalues}")
        elif nvalues == 1:
            values = values[0]

        self._command.arguments[argument.field_name] = values

        self._positional_index += 1
        self._expand_positional_dynamics()

    def _expand_positional_dynamics(self):
        while (pi := self._positional_index) < len(pargs := self._command.ast.positional_args) and \
                isinstance(dp := pargs[pi], DynamicArgumentsDef):
            self._expand_dynamic(dp)

    def _read_option_value(self, option_def: OptionDef, assignment: str) -> Any:
        if not (option_value := assignment or self._next_or_none()):
            raise ValueError(f"missing value for option {option_def.display_name}")

        if option_value.startswith("-") and not assignment:
            raise ValueError(f"missing value for option {option_def.display_name}")

        value = self._read_subfields(option_def, option_def.map_value(option_value))

        if option_def.repeatable:
            get_or_put(self._command.arguments, option_def.field_name, list).append(value)
        else:
            self._command.arguments[option_def.field_name] = value

    def _read_option_or_flag(self):
        node, command_ = self._command.ast, self._command
        next_ = self._next_or_raise("option or flag expected")
        akey, _, avalue = next_.partition("=")

        if akey.startswith("--"):  # long option
            if not (option_def := node.options.get(akey)):
                raise ValueError(f"unknown option: {akey}")

            if isinstance(option_def, FlagDef):
                command_.arguments[option_def.field_name] = True
                return

            self._read_option_value(cast(OptionDef, option_def), avalue)

        elif next_.startswith("-"):
            need_value: Optional[OptionDef] = None
            for option_ in next_[1:]:
                if need_value:
                    raise ValueError(f"missing value for option {need_value.display_name}")
                if not (option_def := node.options.get(f'-{option_}')):
                    raise ValueError(f"unknown option: {next_}")

                if isinstance(option_def, FlagDef):
                    command_.arguments[option_def.field_name] = self._read_subfields(option_def, True)
                else:
                    need_value = option_def

            if need_value:
                self._read_option_value(need_value, "")

    def parse(self, partial: bool) -> Command:
        self._expand_positional_dynamics()

        try:
            while next_ := self._peek_or_none():
                node = self._command.ast

                if next_.startswith("-"):  # long option
                    self._read_option_or_flag()
                elif next_.startswith("+"):
                    raise UnsupportedOperationException(
                        f"attached option ({next_}) must come after a supporting argument")
                elif node.children and (subcommand := node.children.get(next_)):
                    self._skip()
                    self._command = Command(subcommand, path=(*self._command.path, next_), parent=self._command)
                    self._positional_index = 0
                    node = subcommand
                elif node.positional_args and self._positional_index < len(node.positional_args):
                    self._read_positional()
                else:
                    raise ValueError(
                        f"does not know how to handle {next_} at: \n"
                        f"{' '.join(it for it in self._args[:self._index - 1])} [{next_}]")

                if node.dynamic:
                    dynamic_commands = node.command_def.execution(self._command)
                    dynamic_commands_ast = CommandAST.create(dynamic_commands, node.path)
                    dynamic_commands_ast.command_def = node.command_def
                    parsed_command = Command(dynamic_commands_ast, self._command,
                                             self._command.path, self._command.arguments)
                    return DynamicCommandLine(self._args, dynamic_commands, self._index, parsed_command) \
                        .parse(partial)

            node = self._command.ast
            if not node.command_def:
                raise ValueError(f"no such command {' '.join(node.path)}")

            # validate mutex groups and fill in defaults for unset options and flags
            mutex = {}
            for argument_def in node.command_def.arguments_def:
                if not isinstance(argument_def, (FlagDef, OptionDef)):
                    continue

                if argument_def.field_name not in self._command.arguments:
                    self._command.arguments[argument_def.field_name] = self._generate_defaults_for(argument_def)
                elif argument_def.mutex_group:
                    if preassigned := mutex.get(argument_def.mutex_group):
                        raise ValueError(
                            f"these options are mutual exclusive: {argument_def.display_name}, {preassigned}")
                    mutex[argument_def.mutex_group] = argument_def.display_name

            # validate that all positional arguments are assigned
            if self._positional_index != len(self._command.ast.positional_args):
                raise ValueError(
                    f"missing value for positional argument: "
                    f"{self._command.ast.positional_args[self._positional_index].display_name}")

            return self._command
        except Exception:
            if partial:
                return self._command
            raise

    def execute(self) -> Any:
        cmd = self.parse(False)

        def kick(coroutine: Any):
            if isinstance(coroutine, GeneratorType):
                try:
                    next(coroutine)
                    return coroutine
                except StopIteration:
                    return None

        # noinspection PyProtectedMember
        @contextmanager
        def execute_contextual(cmd_: Command):
            if cmd_.parent:
                with execute_contextual(cmd_.parent) as ctx:
                    kick(ctx)
                    try:
                        yield cmd_.execute()
                    finally:
                        kick(ctx)
            else:
                yield cmd_.execute()

        with execute_contextual(cmd) as result:
            return result

    def print_help(self):
        from pkm_cli.dynamic_cli.help_generator import generate_usage, generate_arguments_overview
        parsed_command = self.parse(True)
        Display.print(generate_usage(parsed_command))
        Display.print()
        if parsed_command.ast.command_def:
            Display.print(f"{parsed_command.ast.command_def.help}\n")
        Display.print(generate_arguments_overview(parsed_command))


def _identifierify(txt: str) -> str:
    return re.sub(r'\W+|^(?=\d+)', '_', txt)

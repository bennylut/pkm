from __future__ import annotations

import inspect
import re
from abc import abstractmethod
from dataclasses import dataclass, field, replace
from types import FunctionType, GeneratorType
from typing import List, Protocol, Optional, Dict, Callable, TypeVar, Iterable, Any, Tuple, Union, Mapping, Literal, \
    NoReturn, Type, Sequence, cast

import sys

from pkm.utils.commons import IllegalStateException, UnsupportedOperationException, NoSuchElementException, as_instance, \
    MISSING
from pkm.utils.dicts import get_or_put
from pkm.utils.formatting import camel_case_to_upper_snake_case
from pkm.utils.iterators import first_or_raise, first_or_none
from pkm.utils.properties import cached_property
from pkm.utils.seqs import seq
from pkm.utils.symbol import Symbol
from pkm.utils.types import Mapper

_COMMAND_SYM = Symbol("commandline_parser.command")


class CommandParsingError(IOError):
    ...


@dataclass
class Command:
    ast: CommandAST
    parent: Optional[Command] = None
    path: Tuple[str, ...] = field(default_factory=tuple)
    arguments: Dict[str, Any] = field(default_factory=dict)
    parse_error: Optional[Exception] = None

    def __getattr__(self, item):
        if (result := self.arguments.get(item, MISSING)) is MISSING:
            if self.parent:
                result = getattr(self.parent, item, MISSING)

        if result is MISSING:
            raise AttributeError(f"no such argument: {item}")

        return result

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
        if self.parse_error:
            raise self.parse_error

        parent_context = None
        if self.parent and (parent_context := as_instance(self.parent.execute(), GeneratorType)):
            next(parent_context, None)
        try:
            if (cmd_def := self.ast.command_def) and not cmd_def.dynamic:
                return cmd_def.execution(self)
            return None
        finally:
            if parent_context:
                next(parent_context, None)

    def print_help(self):
        from pkm_cli.api.dynamic_cli.help_generator import generate_usage, generate_arguments_overview
        print(generate_usage(self))
        print()
        if (cdef := self.ast.command_def) and cdef.help:
            print(f"{cdef.help}\n")
        print(generate_arguments_overview(self))


class ArgumentReader(Protocol):
    @abstractmethod
    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        ...

    def value_hint(self) -> str:
        return "VAL"


class ArgumentFieldsProvider(Protocol):
    @abstractmethod
    def provide(self, cmd: Command, arg: ArgumentDef, value: Any) -> Iterable[OptionDef]:
        ...


class CommandsProvider(Protocol):
    @abstractmethod
    def __call__(self, prev_cmd: Command, next_args: ArgumentsBuffer) -> Iterable[CommandDef]:
        ...


class FlagReader(ArgumentReader):

    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        return True

    def value_hint(self) -> str:
        return ""


_FLAG_READER = FlagReader()


class ChoicesReader(ArgumentReader):

    def __init__(self, choices: List[str]):
        super().__init__()
        self.choices = choices

    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        v = buf.next_or_raise(f"value is expected for {argument.display_name}")
        if v not in self.choices:
            raise CommandParsingError(
                f"illegal value for argument {argument.display_name}: {v}, choices are: {', '.join(self.choices)}")
        return v

    def value_hint(self) -> str:
        return '{' + ', '.join(self.choices) + "}"


class DefaultArgumentReader(ArgumentReader):

    def __init__(self, type_: Type = str):
        self.type = type_

    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        v = buf.next_or_raise(f"value is expected for {argument.display_name}")
        return self.type(v)

    def value_hint(self) -> str:
        return camel_case_to_upper_snake_case(self.type.__name__)


_STR_ARG_READER = DefaultArgumentReader(str)


class ConstantReader(ArgumentReader):

    def __init__(self, constant: str):
        self.constant = constant

    def read(self, cmd: Command, argument: ArgumentDef, buf: ArgumentsBuffer) -> Any:
        if buf.next_or_none() != self.constant:
            raise CommandParsingError(f"expecting constant: {self.constant}")
        return self.constant

    def value_hint(self) -> str:
        return self.constant


class ArgumentDef(Protocol):
    help: str
    reader: ArgumentReader
    fields: Optional[List[ArgumentDef]]
    fields_provider: Optional[ArgumentFieldsProvider]
    default_value: Any

    @cached_property
    def defined_names(self) -> Iterable[str]:
        if name := getattr(self, "name", None):
            return name,

        elif names := getattr(self, "names"):
            return sorted(cast(List[str], names), key=len)

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

    @cached_property
    def display_name(self) -> str:
        return ', '.join(self.defined_names)

    def short_name(self) -> Optional[str]:
        return first_or_none(it for it in self.defined_names if not it.startswith("--"))

    def long_name(self) -> Optional[str]:
        return first_or_none(it for it in self.defined_names if it.startswith("--"))

    def is_required(self) -> bool:
        return self.default_value is MISSING

    def is_multival(self):
        return False

    def read_value(self, cmd: Command, buf: ArgumentsBuffer) -> Any:
        return self.reader.read(cmd, self, buf)


@dataclass
class PositionalArgumentDef(ArgumentDef):
    name: str
    help: str = ""
    n_values: Union[int, Literal["*"]] = 1
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgumentFieldsProvider] = None
    reader: ArgumentReader = _STR_ARG_READER
    default_value: Any = MISSING

    def is_multival(self):
        return self.n_values != 1


@dataclass
class OptionDef(ArgumentDef):
    names: List[str]
    help: str = ""
    default_value: Any = MISSING
    repeatable: bool = False
    mutex_group: Optional[str] = None
    fields: Optional[List[ArgumentDef]] = None
    fields_provider: Optional[ArgumentFieldsProvider] = None
    reader: ArgumentReader = _STR_ARG_READER
    value_hint: str = ""

    def __post_init__(self):
        if not self.names:
            raise UnsupportedOperationException("at least one name is required for option definition")

    def is_multival(self):
        return self.repeatable

    def is_flag(self) -> bool:
        return isinstance(self.reader, FlagReader)


@dataclass
class DynamicArgumentsDef(ArgumentDef):
    provider: Mapper[Command, Iterable[ArgumentDef]]
    name: str = "__dynamic__"

    def is_required(self) -> bool:
        return True


@dataclass
class CommandDef:
    path: List[str]
    execution: Callable
    arguments_def: Iterable[ArgumentDef] = field(default_factory=tuple)
    help: str = ""
    short_desc: str = ""
    dynamic: bool = False

    def __post_init__(self):
        assert not self.dynamic or not self.arguments_def, "dynamic command providers cannot have arguments"


dynamic = DynamicArgumentsDef
_F = TypeVar("_F", FunctionType, Callable)
_DYNAMIC_COMMAND_FUNCTION = TypeVar(
    "_DYNAMIC_COMMAND_FUNCTION", bound=CommandsProvider)
_COMMA_RX = re.compile(r"\s*,\s*")


def _coerce_reader(reader: Union[ArgumentReader, Type, None] = None):
    if reader is None:
        return _STR_ARG_READER
    elif inspect.isclass(reader):
        return DefaultArgumentReader(reader)
    return reader


# noinspection PyShadowingBuiltins
def positional(
        name: str, help: str = "", n_values: Union[int, Literal["*"]] = 1, fields: Optional[List[ArgumentDef]] = None,
        fields_provider: Optional[ArgumentFieldsProvider] = None, reader: Union[ArgumentReader, Type, None] = None,
        default: Any = MISSING
):
    return PositionalArgumentDef(
        name, help=help, n_values=n_values, fields=fields, fields_provider=fields_provider,
        reader=_coerce_reader(reader), default_value=default
    )


# noinspection PyShadowingBuiltins
def flag(
        names: str, *, help: str = "", mutex_group: Optional[str] = None,
        fields: Optional[List[ArgumentDef]] = None,
        fields_provider: Optional[ArgumentFieldsProvider] = None) -> OptionDef:
    return OptionDef(_COMMA_RX.split(names), help=help, default_value=False, mutex_group=mutex_group, fields=fields,
                     fields_provider=fields_provider, reader=_FLAG_READER)


# noinspection PyShadowingBuiltins
def option(
        names: str, *, help: str = "", default: Any = MISSING, repeatable: bool = False,
        mutex_group: Optional[str] = None, fields: Optional[List[ArgumentDef]] = None,
        fields_provider: Optional[ArgumentFieldsProvider] = None,
        reader: Union[ArgumentReader, Type, None] = None) -> OptionDef:
    return OptionDef(
        _COMMA_RX.split(names), help, default, repeatable, mutex_group, fields=fields,
        fields_provider=fields_provider, reader=_coerce_reader(reader))


# noinspection PyShadowingBuiltins
def command(path: str, *argument_definitions: ArgumentDef, short_desc: str = "") -> Callable[[_F], _F]:
    def decorate(f: _F) -> _F:
        _COMMAND_SYM.setattr(
            f, CommandDef(path.split(), f, argument_definitions, (f.__doc__ or short_desc).strip(), short_desc))
        return f

    return decorate


def dynamic_commands(
        prefix: str, short_desc: str = "") -> Callable[[_DYNAMIC_COMMAND_FUNCTION], _DYNAMIC_COMMAND_FUNCTION]:
    def decorate(f: _F) -> _F:
        _COMMAND_SYM.setattr(f, CommandDef(
            prefix.split(), f, help=(f.__doc__ or short_desc).strip(), short_desc=short_desc, dynamic=True))
        return f

    return decorate


@dataclass
class CommandAST:
    path: Tuple[str, ...]
    command_def: Optional[CommandDef] = None
    children: Optional[Dict[str, CommandAST]] = None
    dynamic: bool = False

    @cached_property
    def options(self) -> Dict[str, OptionDef]:
        if not self.command_def:
            return {}

        return {
            o_name: o for o in self.command_def.arguments_def
            if isinstance(o, OptionDef)
            for o_name in o.names}

    @cached_property
    def positional_args(self) -> Sequence[PositionalArgumentDef]:
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
                if not node.children:
                    node.children = {}

                if not (next_node := node.children.get(p)):
                    next_node = node.children[p] = CommandAST((*node.path, p))
                node = next_node

            node.dynamic = command_.dynamic
            if node.dynamic and node.children:
                colliding: CommandAST = first_or_raise(node.children.values())
                raise UnsupportedOperationException(
                    f"Dynamic Command {' '.join(command_.path)} collides with {' '.join(colliding.path)}")

            node.command_def = command_

        return result


def command_definitions_from(env: Union[Iterable[Any], Dict[str, Any]]) -> List[CommandDef]:
    if isinstance(env, Mapping):
        env = env.values()

    return [command_ for v in env if (command_ := _COMMAND_SYM.getattr(v))]


class ArgumentsBuffer:
    def __init__(self, args: List[str], index: int = 0):
        self._args = args
        self._index = index

    def skip(self):
        self._index += 1

    def next_or_none(self) -> Optional[str]:
        if self._index < len(self._args):
            result = self._args[self._index]
            self._index += 1
            return result
        return None

    def peek_or_none(self) -> Optional[str]:
        if self._index < len(self._args):
            return self._args[self._index]
        return None

    def next_or_raise(self, err: str) -> str:
        if (result := self.next_or_none()) is not None:
            return result
        raise CommandParsingError(err)

    def next_option_key(self):
        if not (option_ := self.peek_or_none()):
            raise CommandParsingError("option expected")

        okey, _, oval = option_.partition("=")
        if oval:
            self._args[self._index] = oval.strip()
        else:
            self._index += 1

        return okey.strip()

    def remaining(self) -> int:
        return len(self._args) - self._index

    def has_remaining(self) -> bool:
        return len(self._args) > self._index

    def copy(self) -> ArgumentsBuffer:
        return ArgumentsBuffer(self._args, self._index)

    def throw(self, msg: str) -> NoReturn:
        raise CommandParsingError(
            f"{msg} at: \n"
            f"{' '.join(it for it in self._args[:self._index - 1])} [{self._args[self._index]}]")


class DynamicCommandLine:
    def __init__(
            self, args_buffer: ArgumentsBuffer, commands: List[CommandDef], base_command: Optional[Command] = None):
        self._buffer = args_buffer
        self._commands = commands
        self._command = base_command or Command(CommandAST.create(commands))
        self._positional_index = 0
        self._global_options = {
            oname: o for o in [flag('-h,--help')] for oname in o.names
        }

    @staticmethod
    def _generate_defaults_for(argument_def: ArgumentDef) -> Any:
        if argument_def.is_required():
            raise CommandParsingError(f"missing required argument: {argument_def.display_name}")

        return argument_def.default_value

    def _expand_dynamic(
            self, dynamic_arg_def: Union[DynamicArgumentsDef]):

        command_def = self._command.ast.command_def
        old_args = command_def.arguments_def

        dynamic_args: Iterable[ArgumentDef] = dynamic_arg_def.provider(self._command)

        abs_dynamic_position = seq(old_args).index_of_matching(lambda it: it is dynamic_arg_def)

        expanded_args = [*old_args[:abs_dynamic_position], *dynamic_args, *old_args[abs_dynamic_position + 1:]]
        dynamic_command_def = replace(command_def, arguments_def=expanded_args)

        self._command = replace(self._command, ast=replace(self._command.ast, command_def=dynamic_command_def))

    def _read_subfields(self, arg_def: ArgumentDef, value: Any) -> Any:

        if arg_def.fields_provider:
            subfields = arg_def.fields_provider.provide(self._command, arg_def, value)
            for subfield in subfields:
                if subfield.has_subfields():
                    raise UnsupportedOperationException(
                        f"fields of an argument cannot have sub-fields: "
                        f"{arg_def.display_name}::{subfield.display_name} has.")

            # noinspection PyDataclass
            new_arg_def = replace(arg_def, fields=subfields, fields_provider=None, reader=ConstantReader(str(value)))
            ast = self._command.ast
            self._command.ast = replace(
                ast, command_def=replace(
                    ast.command_def, arguments_def=[
                        it if it is not arg_def else new_arg_def for it in ast.command_def.arguments_def]))
            arg_def = new_arg_def

        if (subfields := arg_def.fields) is not None:
            value = {'value': value}

            subfields_map: Dict[str, ArgumentDef] = {name: it for it in subfields for name in it.defined_names}

            while (next_ := self._buffer.peek_or_none()) and next_.startswith("+"):
                option_ = self._buffer.next_option_key()
                if not (option_def := subfields_map.get(option_)):
                    raise CommandParsingError(f"unrecognized field: {option_} for target: {arg_def.display_name}")

                value[option_def.field_name] = option_def.read_value(self._command, self._buffer)

            for subfield in subfields:
                if subfield.field_name not in value:
                    value[subfield.field_name] = self._generate_defaults_for(subfield)

        return value

    def _read_positional(self):
        argument: PositionalArgumentDef = self._command.ast.positional_args[self._positional_index]
        nvalues = argument.n_values
        values = []

        while self._buffer.has_remaining() and (nvalues == "*" or len(values) < nvalues):
            values.append(self._read_subfields(argument, argument.read_value(self._command, self._buffer)))

        if nvalues == "*":
            ...
        elif nvalues != len(values):
            raise CommandParsingError(
                f"insufficient values for positional argument {argument.display_name}, expecting {nvalues}")
        elif nvalues == 1:
            values = values[0]

        self._command.arguments[argument.field_name] = values

        self._positional_index += 1
        self._expand_positional_dynamics()

    def _expand_positional_dynamics(self):
        while (pi := self._positional_index) < len(pargs := self._command.ast.positional_args) and \
                (dp := as_instance(pargs[pi], DynamicArgumentsDef)):
            self._expand_dynamic(dp)

    def _read_option_value(self, option_def: OptionDef) -> Any:
        value = self._read_subfields(option_def, option_def.read_value(self._command, self._buffer))

        if option_def.repeatable:
            get_or_put(self._command.arguments, option_def.field_name, list).append(value)
        else:
            self._command.arguments[option_def.field_name] = value

    def _get_option(self, key: str) -> OptionDef:
        node = self._command.ast
        if not (option_def := node.options.get(key) or self._global_options.get(key)):
            print(f"options: {node.options} as ast: {node.path} | cdef={node.command_def}")
            raise CommandParsingError(f"unknown option: {key}")
        return option_def

    def _read_option_or_flag(self):
        node, command_ = self._command.ast, self._command
        next_ = self._buffer.next_option_key()

        if next_.startswith("--"):  # long option
            self._read_option_value(self._get_option(next_))

        elif next_.startswith("-"):
            need_value: Optional[OptionDef] = None
            for option_ in next_[1:]:
                if need_value:
                    raise CommandParsingError(f"missing value for option {need_value.display_name}")

                option_def = self._get_option(f"-{option_}")
                if option_def.is_flag():
                    command_.arguments[option_def.field_name] = self._read_subfields(option_def, True)
                else:
                    need_value = option_def

            if need_value:
                self._read_option_value(need_value)

    def parse(self) -> Command:
        self._expand_positional_dynamics()

        try:
            while next_ := self._buffer.peek_or_none():
                node = self._command.ast

                if next_.startswith("-"):  # long option
                    self._read_option_or_flag()
                elif next_.startswith("+"):
                    raise CommandParsingError(
                        f"field ({next_}) must come after a supporting argument")
                elif node.children and (subcommand := node.children.get(next_)):
                    self._buffer.skip()
                    self.finilize_command()
                    self._command = Command(subcommand, path=(*self._command.path, next_), parent=self._command)
                    self._positional_index = 0
                    node = subcommand
                elif node.positional_args and self._positional_index < len(node.positional_args):
                    self._read_positional()
                else:
                    self._buffer.throw(f"does not know how to handle {next_}")

                if node.dynamic:
                    dynamic_commands_: List[CommandDef] = node.command_def.execution(self._command, self._buffer)
                    dynamic_commands_ast = CommandAST.create(dynamic_commands_, node.path)
                    parsed_command = replace(self._command, ast=dynamic_commands_ast)

                    if len(dynamic_commands_) == 1 and len(dynamic_commands_[0].path) == 0:  # self replacement
                        self._command = parsed_command
                    else:
                        dynamic_commands_ast.command_def = node.command_def  # set parent command to all child commands
                        return DynamicCommandLine(self._buffer, dynamic_commands_, parsed_command).parse()

            node = self._command.ast
            if not node.command_def:
                raise CommandParsingError(f"no such command {' '.join(node.path)}")

            self.finilize_command()

        except CommandParsingError as e:
            self._command.parse_error = e
        return self._command

    def finilize_command(self):
        # validate mutex groups and fill in defaults for unset options and flags
        mutex = {}
        command_args = c.arguments_def if (c := self._command.ast.command_def) else ()
        all_args = seq(self._global_options.values()).unique_by(id).chain(command_args)
        for argument_def in all_args:
            if not isinstance(argument_def, OptionDef):
                continue

            if argument_def.field_name not in self._command.arguments:
                self._command.arguments[argument_def.field_name] = self._generate_defaults_for(argument_def)
            elif argument_def.mutex_group:
                if preassigned := mutex.get(argument_def.mutex_group):
                    raise CommandParsingError(
                        f"these options are mutual exclusive: {argument_def.display_name}, {preassigned}")
                mutex[argument_def.mutex_group] = argument_def.display_name
        # validate that all positional arguments are assigned or set default
        for pi in range(self._positional_index, len(self._command.ast.positional_args)):
            p = self._command.ast.positional_args[pi]
            self._command.arguments[p.field_name] = self._generate_defaults_for(p)

    @classmethod
    def create(cls, commands: List[CommandDef], args: Optional[List[str]] = None) -> DynamicCommandLine:
        if args is None:
            args = sys.argv

        return cls(ArgumentsBuffer(args), commands)


def _identifierify(txt: str) -> str:
    return re.sub(r'\W+|^(?=\d+)', '_', txt)

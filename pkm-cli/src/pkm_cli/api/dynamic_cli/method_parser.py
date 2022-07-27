import inspect
import typing
from collections import defaultdict
from textwrap import dedent
from typing import List, Dict, Set, Type

from pkm.utils.commons import MISSING
from pkm.utils.types import Func
from pkm_cli.api.dynamic_cli.command_parser import CommandDef, ArgumentDef, positional, Command, flag, option, OptionDef


def _adjust_types(types: Dict[str, Type]) -> Dict[str, Type]:
    for arg, type_ in list(types.items()):
        if type_ == typing.Union or typing.get_origin(type_) == typing.Union:
            type_args = [t for t in typing.get_args(type_) if t.__name__ != 'NoneType']
            if type_args:
                types[arg] = type_args[0]

    return types


def fields_from_method(mtd: Func) -> List[OptionDef]:
    doc = _parse_doc(mtd.__doc__ or "")
    fields: List[OptionDef] = []

    args_spec = inspect.getfullargspec(mtd)
    arg_types = _adjust_types(typing.get_type_hints(mtd))

    def field_name(arg_: str) -> str:
        return f"+{arg_.replace('_', '-')}"

    for arg in args_spec.args:
        fields.append(
            option(field_name(arg), reader=arg_types.get(arg, str), help=doc.get(arg, "")))

    if arg := args_spec.varargs:
        fields.append(option(
            field_name(arg), reader=arg_types.get(arg, str), repeatable=True, help=doc.get(arg, "")))

    kwdefaults = args_spec.kwonlydefaults
    missing = object()
    for kwarg in args_spec.kwonlyargs:
        kwarg_type = arg_types.get(kwarg, str)
        kwarg_default = kwdefaults.get(kwarg, missing)
        kwarg_doc = doc.get(kwarg, "")
        if kwarg_type is bool and kwarg_default is False:
            fields.append(flag(field_name(kwarg), help=kwarg_doc))
        else:
            option_ = option(field_name(kwarg), reader=kwarg_type, help=kwarg_doc)
            if kwarg_default is not missing:
                option_.default_value = kwarg_default

            fields.append(option_)

    return fields


def command_definition_from_method(mtd: Func, path: str = "") -> CommandDef:
    if not path:
        path = mtd.__name__

    doc = _parse_doc(mtd.__doc__ or "")
    cli_args: List[ArgumentDef] = []

    args_spec = inspect.getfullargspec(mtd)
    arg_types = _adjust_types(typing.get_type_hints(mtd))

    # positionals:
    arg_defaults = args_spec.defaults or ()
    positional_defaults = ([MISSING] * (len(args_spec.args) - len(arg_defaults))) + list(arg_defaults)
    for arg, default in zip(args_spec.args, positional_defaults):
        cli_args.append(
            positional(arg.replace("_", "-"), reader=arg_types.get(arg, str), default=default, help=doc.get(arg, "")))

    if arg := args_spec.varargs:
        cli_args.append(positional(
            arg.replace("_", "-"), reader=arg_types.get(arg, str), n_values="*", help=doc.get(arg, "")))

    kwdefaults = args_spec.kwonlydefaults
    option_names = _generate_option_names(args_spec.kwonlyargs)
    missing = object()
    for kwarg in args_spec.kwonlyargs:
        kwarg_type = arg_types.get(kwarg, str)
        kwarg_default = kwdefaults.get(kwarg, missing)
        kwarg_doc = doc.get(kwarg, "")
        kwarg_names = option_names[kwarg]
        if kwarg_type is bool and kwarg_default is False:
            cli_args.append(flag(kwarg_names, help=kwarg_doc))
        else:
            option_ = option(kwarg_names, reader=kwarg_type, help=kwarg_doc)
            if kwarg_default is not missing:
                option_.default_value = kwarg_default

            cli_args.append(option_)
    allowed_args = {it.field_name for it in cli_args}

    def execution(cmd: Command):
        return mtd(**{k: v for k, v in cmd.arguments.items() if k in allowed_args})

    desc = doc.get("", "")
    short_desc = _doc_to_short_desc(desc)
    return CommandDef(path.split(), execution, cli_args, desc, short_desc)


def _doc_to_short_desc(doc: str):
    desc_lines = doc.splitlines(keepends=False)
    # single line or space line after the first line will make the first line a short description
    if len(desc_lines) == 1 or (len(desc_lines) > 1 and not (desc_lines[1])):
        return desc_lines[0]
    return ""


def _generate_option_names(args: List[str]) -> Dict[str, str]:
    result: Dict[str, List[str]] = defaultdict(list)
    taken: Set[str] = set()

    def assign(arg_: str, *names: str):
        result[arg_].extend(names)
        taken.update(names)

    for arg in args:
        if len(arg) == 1:
            assign(arg, f"-{arg}")

    for arg in args:
        if len(arg) != 1:
            long_name = f"--{arg.replace('_', '-')}"
            for char in arg:
                if char.isalpha() and (short_name := f"-{char}") not in taken:
                    assign(arg, long_name, short_name)
                    break
            else:
                assign(arg, long_name)

    return {key: ','.join(value) for key, value in result.items()}


def _parse_doc(doc: str) -> Dict[str, str]:
    doc = dedent(doc).strip()
    result = {}
    section = ""
    section_key = ""

    def push():
        result[section_key.strip()] = section.strip()

    for line in doc.splitlines():
        if line.startswith(":param "):
            push()
            section_key, _, section = line[len(":param "):].partition(":")
        elif line.startswith(":return:"):
            push()
            section_key, section = "return", line[len(":return:"):]
        else:
            section = f"{section}\n{line}"

    push()
    return result

import inspect
from collections import defaultdict
from typing import Dict, List

from pkm.utils.formatting import camel_case_to_upper_snake_case
from pkm.utils.seqs import seq
from pkm_cli.dynamic_cli.parser import Command, OptionDef, FlagDef, ArgumentDef


def generate_arguments_overview(command: Command) -> str:
    node = command.ast
    lines = []

    secsep = ""
    options, flags = seq(node.options.values()).unique_by(id).partition_by_type(OptionDef)
    if flags:
        lines.append(f"{secsep}Flags: ")
        secsep = "\n"
        padding = max(len(it.display_name) for it in flags) + 2
        for flag in flags:
            lines.append(f"  {flag.display_name :{padding}} {flag.help}")

    if options:
        lines.append(f"{secsep}Options: ")
        secsep = "\n"
        padding = max(len(it.display_name) for it in options) + 2
        for option in options:
            lines.append(f"  {option.display_name:{padding}} {option.help}")

    if node.positional_args:
        lines.append(f"{secsep}Positional Arguments: ")
        secsep = "\n"
        padding = max(len(it.display_name) for it in node.positional_args) + 2
        for positional in node.positional_args:
            lines.append(f"  {positional.display_name :{padding}} {positional.help}")

    if node.children:
        lines.append(f"{secsep}Sub-Commands: ")
        padding = max(len(it) for it in node.children) + 2
        for subc, subc_node in node.children.items():
            short_desc = subc_node.command_def.short_desc if subc_node.command_def else ""
            lines.append(f"  {subc :{padding}} {short_desc}")

    return '\n'.join(lines)


def generate_usage(command: Command) -> str:
    node = command.ast
    command_def = node.command_def
    argument_tokens = []

    path = ' '.join(node.path)
    unique_options = seq(node.options.values()).unique_by(id).to_list()

    options_by_mutex: Dict[str, List[ArgumentDef]] = defaultdict(list)
    no_mutex = []
    for option_ in unique_options:
        if isinstance(option_, (OptionDef, FlagDef)) and (mutex_group := option_.mutex_group):
            options_by_mutex[mutex_group].append(option_)
        else:
            no_mutex.append(option_)

    _create_option_usage_tokens(argument_tokens, no_mutex)
    for mutex, group in options_by_mutex.items():
        group_tokens = []
        _create_option_usage_tokens(group_tokens, group)
        if mutex:
            argument_tokens.append(f"[{' | '.join(it.strip('[]') for it in group_tokens)}]")
        else:
            argument_tokens.extend(group_tokens)

    for positional in node.positional_args:
        ...

    if node.children:
        subcommand = "SUB_COMMAND"
        if node.command_def and not command_def.is_dynamic():
            subcommand = f"[{subcommand}]"
        argument_tokens.append(subcommand)

    usage = f"Usage: {path} {' '.join(argument_tokens)}"
    return usage


def _create_option_usage_tokens(tokens: List[str], options):
    options, flags = seq(options).partition_by_type(OptionDef)
    combined_flags_tokens = []
    for flag in flags:
        flag_short_name = flag.short_name()
        if len(flag_short_name) == 2:
            combined_flags_tokens.append(flag_short_name[1])
        else:
            tokens.append(f"[{flag_short_name}]")
    if combined_flags_tokens:
        tokens.append(f"[-{''.join(combined_flags_tokens)}]")
    for option_ in options:
        val_hint = "VAL"
        if inspect.isclass(option_.mapper):
            val_hint = camel_case_to_upper_snake_case(option_.mapper.__name__)

        option_str = f"{option_.short_name()} {val_hint}"
        if not option_.is_required():
            option_str = f"[{option_str}]"
        elif option_.is_multival():
            option_str = f"({option_str})"

        if option_.is_multival():
            option_str = f"{option_str}*"
        tokens.append(option_str)

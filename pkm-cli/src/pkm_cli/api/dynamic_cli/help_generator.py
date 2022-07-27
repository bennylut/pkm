from collections import defaultdict
from typing import Dict, List

from pkm.utils.commons import MISSING
from pkm.utils.seqs import seq
from pkm_cli.api.dynamic_cli.command_parser import Command, OptionDef, ArgumentDef, ConstantReader


def generate_arguments_overview(command: Command) -> str:
    def header(arg: ArgumentDef):
        if isinstance(arg, OptionDef) and arg.is_flag():
            return arg.display_name
        return f"{arg.display_name} <{arg.reader.value_hint()}>"

    node = command.ast
    lines = []

    secsep = ""
    options = seq(node.options.values()).unique_by(id).to_list()

    if options:
        lines.append(f"{secsep}Options: ")
        secsep = "\n"

        option_display_names = [header(option) for option in options]
        for dname, option in zip(option_display_names, options):
            lines.append(f"  {dname}")
            if option.help:
                lines.append(f"      {option.help}")

    if node.positional_args:
        lines.append(f"{secsep}Positional Arguments: ")
        secsep = "\n"
        positional_display_names = [header(p) for p in node.positional_args]
        for dname, positional in zip(positional_display_names, node.positional_args):
            lines.append(f"  {dname}")
            if positional.help:
                lines.append(f"      {positional.help}")

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
        if isinstance(option_, OptionDef) and (mutex_group := option_.mutex_group):
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
        positional_str = positional.name
        if isinstance(positional.reader, ConstantReader):
            positional_str = positional.reader.constant

        prs = "<>" if positional.default_value is MISSING else "[]"

        if positional.fields:
            argument_tokens.append(f"{prs[0]}{positional_str}")
            _create_option_usage_tokens(argument_tokens, positional.fields)
            argument_tokens[-1] = f"{argument_tokens[-1]}{prs[1]}"
        elif positional.fields_provider:
            argument_tokens.append(f"{prs[0]}{positional_str} +?{prs[1]}")
        else:
            argument_tokens.append(positional_str if prs == "<>" else f"[{positional_str}]")

        if positional.n_values == "*":
            argument_tokens.append("...")
        elif positional.n_values != 1:
            argument_tokens.append(f"x{positional.n_values}")

    if node.children:
        subcommand = "SUB_COMMAND"
        if node.command_def and not command_def.dynamic:
            subcommand = f"[{subcommand}]"
        argument_tokens.append(subcommand)

    usage = f"Usage: {path} {' '.join(argument_tokens)}"
    return usage


def _create_option_usage_tokens(tokens: List[str], options: List[ArgumentDef]):
    combindeable_flags, options = seq(options).partition_by(lambda it: it.is_flag() and not it.has_subfields())
    combined_flags_tokens = []
    for flag in combindeable_flags:
        flag_shortest_name = flag.short_name() or flag.long_name()
        if len(flag_shortest_name) == 2:
            combined_flags_tokens.append(flag_shortest_name[1])
        else:
            tokens.append(f"[{flag_shortest_name}]")
    if combined_flags_tokens:
        tokens.append(f"[-{''.join(combined_flags_tokens)}]")

    for option_ in options:
        option_short_name = option_.short_name()
        if val_hint := option_.reader.value_hint():
            sep = " " if option_short_name.startswith("-") else "="
            option_str = f"{option_short_name}{sep}{val_hint}"
        else:
            option_str = f"{option_short_name}"

        if option_.fields_provider:
            option_str = f"{option_str} +?"
        elif option_.fields:
            field_tokens = []
            _create_option_usage_tokens(field_tokens, option_.fields)
            option_str = f"{option_str} {' '.join(field_tokens)}"

        if not option_.is_required():
            option_str = f"[{option_str}]"
        elif option_.is_multival():
            option_str = f"({option_str})"

        if option_.is_multival():
            option_str = f"{option_str}*"
        tokens.append(option_str)

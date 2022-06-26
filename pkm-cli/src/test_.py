from pathlib import Path
from typing import List

from pkm_cli.dynamic_cli.parser import Command, command, option, flag, commands_from, DynamicCommandLine, CommandDef


@command(
    "pkm",
    flag("-v, --verbose", help="run with verbose output"),
    option("-c, --context", help="path to the context to run this command under", default_value=None,
           mutex_group="context", mapper=Path),
    flag('-g, --global-context', help="use the global environment context", mutex_group="context"),
    flag("-T, --without-tasks", help="dont run command-attached tasks"),
    flag("-p, --profiler", help="run with cprofiler and print results")
)
def pkm(cmd: Command):
    """
    pkm - python package management for busy developers
    """

    print("hello from pkm")


@command("pkm clean *", short_desc="cleanup files created by pkm")
def pkm_clean(cmd: Command) -> List[CommandDef]:
    @command("dist")
    def clean_dist(cmd_: Command):
        ...

    @command("shared")
    def clean_shared(cmd_: Command):
        ...

    @command("cache")
    def clean_cache(cmd_: Command):
        ...

    pkm = cmd.parent_by_path("pkm")
    if pkm.v:
        return commands_from([clean_dist, clean_shared])
    return commands_from([clean_cache, clean_dist])


@command("pkm status")
def pkm_status(cmd: Command):
    ...


commands = commands_from(globals())
DynamicCommandLine(["pkm", "clean"], commands).print_help()

# support:
# help
# bash completion
# support for method cli
# sphinx docgen
# when no such command suggest options / did you mean...
# replace value error with parse error, unify exceptions to show parse carret
# consider shortening dsl

# @command("x y", arg("z") option("+y") <- this means it attached to z
# pkm install -r pypi +url=...

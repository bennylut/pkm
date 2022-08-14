from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Callable, List
from unittest import TestCase

from pkm.utils.seqs import seq
from pkm_cli.api.dynamic_cli.command_parser import command, Command, DynamicCommandLine, command_definitions_from, flag, option, \
    positional, CommandDef, dynamic, ArgumentDef, ChoicesReader, dynamic_commands


# noinspection PyMethodMayBeStatic,PyBroadException
class TestDynamicCLI(TestCase):

    def test_basic_types(self):
        commands = make_commands(
            command("cmd", option("-i", reader=int), positional("f", reader=Path))
        )

        cmd: Command = DynamicCommandLine.create(commands, ["cmd", "-i", "7", "/x/y"]).execute()
        assert cmd.i == 7 and isinstance(cmd.f, Path)

    def test_mutex_groups(self):
        commands = make_commands(
            command("cmd", option("-x", mutex_group="x", default=None), flag("-f", mutex_group="x"), flag("-y"))
        )

        DynamicCommandLine.create(commands, ["cmd", "-x", "v", "-y"]).execute()
        DynamicCommandLine.create(commands, ["cmd", "-f", "-y"]).execute()
        with expect_failure("should fail due to mutex group"):
            DynamicCommandLine.create(commands, ["cmd", "-f", "-x", "bla"]).execute()

    def test_contextual_subcommands(self):
        success = False

        @command("a b")
        def ab(cmd: Command):
            cmd.parent.arguments["xxx"] = cmd.parent.arguments["yyy"]

        @command("a")
        def a(cmd: Command):
            nonlocal success
            cmd.arguments["yyy"] = "zzz"
            yield
            success = cmd.arguments["xxx"] == "zzz"

        DynamicCommandLine.create(command_definitions_from(locals()), ["a", "b"]).execute()
        assert success

    def test_nvalues(self):
        commands = make_commands(
            command("a b", positional("x", n_values=3), flag("-y"), positional("z")),
            command("with-att", positional("x", n_values=3, fields=[option("+name", default="default")]))
        )

        cmd: Command = DynamicCommandLine.create(commands, ["a", "b", "1", "2", "3", "-y", "4"]).execute()
        assert cmd.x == ["1", "2", "3"] and cmd.y and cmd.z == "4"

        cmd: Command = DynamicCommandLine.create(
            commands, ["with-att", "first", "+name=first-name", "second", "third", "+name=last-name"]).execute()
        assert cmd.x[0]["value"] == "first" and cmd.x[0]["name"] == "first-name"
        assert cmd.x[1]["value"] == "second" and cmd.x[1]["name"] == "default"
        assert cmd.x[2]["value"] == "third" and cmd.x[2]["name"] == "last-name"

    def test_repeats(self):
        commands = make_commands(
            command("a b", option('-v, --vv', repeatable=True), option("-x"))
        )

        cmd: Command = DynamicCommandLine.create(commands, ["a", "b", "-v", "1", "-x", "2", "-v", "3"]).execute()
        assert cmd.vv == ["1", "3"]

    def test_equals(self):
        commands = make_commands(
            command("a b", option('-n, --name'), flag("-f,--ff"))
        )

        cmd: Command = DynamicCommandLine.create(commands, ["a", "b", "--name=bla", "-f"]).execute()
        assert cmd.name == "bla" and cmd.ff

    def test_choices(self):
        commands = make_commands(
            command("a b", option('-n, --name', reader=ChoicesReader(['x', 'y'])), )
        )

        with expect_failure('should have failed due to illegal option value'):
            DynamicCommandLine.create(commands, ["a", "b", "-n", "z"]).execute()  # ensure that passes

        DynamicCommandLine.create(commands, ["a", "b", "-n", "x"]).execute()  # ensure that passes

    def test_field_providers(self):
        def provider(_: Command, __, ___) -> List[ArgumentDef]:
            return [option("+name"), flag("-x")]

        commands = make_commands(
            command("cmd",
                    flag("-r,--rr", fields_provider=provider))
        )

        DynamicCommandLine.create(commands, ["cmd"]).execute()  # ensure that passes

        cmd: Command = DynamicCommandLine.create(commands, ["cmd", "-r", "+name=aaa"]).execute()  # ensure that passes
        assert cmd.rr['value'] and cmd.rr['name'] == 'aaa'

        with expect_failure("should fail as no name is provided"):
            DynamicCommandLine.create(commands, ["cmd", "-r"]).execute()  # ensure that passes

    def test_fields(self):
        commands = make_commands(
            command("a b",
                    flag("-r,--rr", fields=[option("+name"), flag("+f"), option("+x", default="yyy")]))
        )

        DynamicCommandLine.create(commands, ["a", "b"]).execute()  # ensure that passes

        with expect_failure("should have failed due to missing attached argument name"):
            DynamicCommandLine.create(commands, ["a", "b", "-r"]).execute()

        cmd: Command = DynamicCommandLine.create(commands, ["a", "b", "-r", "+name=xxx", "+f"]).execute()
        assert cmd.rr and cmd.rr['name'] == "xxx" and cmd.rr["f"] is True and cmd.rr["x"] == "yyy"

    def test_dynamic_arguments(self):
        def args_provider(cmd_: Command) -> List[ArgumentDef]:
            return seq(cmd_.c.split()).map(positional).to_list()

        commands = make_commands(command("a b", positional("c"), dynamic(args_provider)))

        cmd: Command = DynamicCommandLine.create(commands, ["a", "b", "x y", "1", "2"]).execute()
        assert cmd.x == "1" and cmd.y == "2"

    def test_dynamic_commands(self):
        @dynamic_commands("a")
        def a(_: Command, __: List[str]) -> List[CommandDef]:
            return make_commands(command("x"), command("y", positional("some-arg")))

        commands = command_definitions_from(locals())

        cmd: Command = DynamicCommandLine.create(commands, ["a", "x"]).execute()
        assert cmd.path == ("a", "x")

        cmd: Command = DynamicCommandLine.create(commands, ["a", "y", "some-value"]).execute()
        assert cmd.some_arg == "some-value"

    def test_positional_arguments(self):
        commands = make_commands(
            command("a b", positional("bla-bli"), option("-x,--xxx"), flag("-v,--vvv"))
        )

        cmd = DynamicCommandLine.create(commands, ["a", "b", "-x", "hello", "bla-bli-value"]).execute()
        assert cmd.xxx == 'hello' and cmd.bla_bli == "bla-bli-value"

        cmd = DynamicCommandLine.create(commands, ["a", "b", "bla-bli-value", "-x", "hello"]).execute()
        assert cmd.xxx == 'hello' and cmd.bla_bli == "bla-bli-value"

        with expect_failure("should have been failed due to missing required value"):
            DynamicCommandLine.create(commands, ["a", "b", "-x", "hello"]).execute()

    def test_options(self):
        commands = make_commands(
            command("a b", option('-x, --xxx', default='some-value'), option("-r, --required"), flag("-f, --fff"))
        )

        abcmd = DynamicCommandLine.create(commands, ["a", "b", "-r", "hello"]).execute()
        assert abcmd.required == 'hello' and abcmd.xxx == 'some-value'

        with expect_failure("should have been failed due to missing required value"):
            DynamicCommandLine.create(commands, ["a", "b"]).execute()

        abcmd = DynamicCommandLine.create(commands, ["a", "b", "-fr", "hello", "-x", "another-value"]).execute()
        assert abcmd and abcmd.fff and abcmd.xxx == 'another-value' and abcmd.required == 'hello'

    def test_simple_command(self):
        commands = make_commands(command(""))
        assert DynamicCommandLine.create(commands, []).execute()

    def test_subpath_simple_command(self):
        commands_executed = []

        @command("a")
        def a(_: Command):
            commands_executed.append("a")

        @command("a b")
        def ab(_: Command):
            commands_executed.append("b")

        DynamicCommandLine.create(command_definitions_from(locals()), ["a", "b"]).execute()
        assert commands_executed == ["a", "b"]

    def test_flags(self):
        abcmd: Optional[Command] = None
        acmd: Optional[Command] = None

        @command("a", flag('-v,--vvv'))
        def a(cmd: Command):
            nonlocal acmd
            acmd = cmd

        @command("a b", flag('-h,--help'), flag('-x,--xxx'), flag('-y,--yyy'))
        def ab(cmd: Command):
            nonlocal abcmd
            abcmd = cmd

        commands = command_definitions_from(locals())

        DynamicCommandLine.create(commands, ["a", "b"]).execute()
        assert abcmd and acmd

        abcmd, acmd = None, None
        DynamicCommandLine.create(commands, ["a", "b", "-x"]).execute()
        assert abcmd and abcmd.xxx
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine.create(commands, ["a", "b", "-x", "-h"]).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine.create(commands, ["a", "b", "-xh"]).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine.create(commands, ["a", "-v", "b", "-xh"]).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and acmd.vvv

        with expect_failure("should not have accepted v as a flag for a b"):
            DynamicCommandLine.create(commands, ["a", "b", "-xhv"]).execute()


def make_commands(*commands: Callable) -> List[CommandDef]:
    return command_definitions_from(c(return_cmd) for c in commands)


def return_cmd(cmd: Command) -> Command:
    return cmd


@contextmanager
def expect_failure(reason: str):
    try:
        yield
    except:  # noqa
        ...
    else:
        raise AssertionError(reason)

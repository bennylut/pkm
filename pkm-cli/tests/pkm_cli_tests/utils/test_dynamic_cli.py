from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Callable, List
from unittest import TestCase

from pkm.utils.seqs import seq
from pkm_cli.dynamic_cli.parser import command, Command, DynamicCommandLine, commands_from, flag, option, \
    positional, CommandDef, dynamic, ArgumentDef


# noinspection PyMethodMayBeStatic,PyBroadException
class TestDynamicCLI(TestCase):

    def test_basic_types(self):
        commands = make_commands(
            command("cmd", option("-i", mapper=int), positional("f", mapper=Path))
        )

        cmd: Command = DynamicCommandLine(["cmd", "-i", "7", "/x/y"], commands).execute()
        assert cmd.i == 7 and isinstance(cmd.f, Path)

    def test_mutex_groups(self):
        commands = make_commands(
            command("cmd", option("-x", mutex_group="x", default_value=None), flag("-f", mutex_group="x"), flag("-y"))
        )

        DynamicCommandLine(["cmd", "-x", "v", "-y"], commands).execute()
        DynamicCommandLine(["cmd", "-f", "-y"], commands).execute()
        with expect_failure("should fail due to mutex group"):
            DynamicCommandLine(["cmd", "-f", "-x", "bla"], commands).execute()

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

        DynamicCommandLine(["a", "b"], commands_from(locals())).execute()
        assert success

    def test_nvalues(self):
        commands = make_commands(
            command("a b", positional("x", n_values=3), flag("-y"), positional("z")),
            command("with-att", positional("x", n_values=3, fields=[option("+name", default_value="default")]))
        )

        cmd: Command = DynamicCommandLine(["a", "b", "1", "2", "3", "-y", "4"], commands).execute()
        assert cmd.x == ["1", "2", "3"] and cmd.y and cmd.z == "4"

        cmd: Command = DynamicCommandLine(
            ["with-att", "first", "+name=first-name", "second", "third", "+name=last-name"], commands).execute()
        assert cmd.x[0]["value"] == "first" and cmd.x[0]["name"] == "first-name"
        assert cmd.x[1]["value"] == "second" and cmd.x[1]["name"] == "default"
        assert cmd.x[2]["value"] == "third" and cmd.x[2]["name"] == "last-name"

    def test_repeats(self):
        commands = make_commands(
            command("a b", option('-v, --vv', repeatable=True), option("-x"))
        )

        cmd: Command = DynamicCommandLine(["a", "b", "-v", "1", "-x", "2", "-v", "3"], commands).execute()
        assert cmd.vv == ["1", "3"]

    def test_equals(self):
        commands = make_commands(
            command("a b", option('-n, --name'), flag("-f,--ff"))
        )

        cmd: Command = DynamicCommandLine(["a", "b", "--name=bla", "-f"], commands).execute()
        assert cmd.name == "bla" and cmd.ff

    def test_choices(self):
        commands = make_commands(
            command("a b", option('-n, --name', choices=['x', 'y']), )
        )

        with expect_failure('should have failed due to illegal option value'):
            DynamicCommandLine(["a", "b", "-n", "z"], commands).execute()  # ensure that passes

        DynamicCommandLine(["a", "b", "-n", "x"], commands).execute()  # ensure that passes

    def test_field_providers(self):
        def provider(_: Command) -> List[ArgumentDef]:
            return [option("+name"), flag("-x")]

        commands = make_commands(
            command("cmd",
                    flag("-r,--rr", fields_provider=provider))
        )

        DynamicCommandLine(["cmd"], commands).execute()  # ensure that passes

        cmd: Command = DynamicCommandLine(["cmd", "-r", "+name=aaa"], commands).execute()  # ensure that passes
        assert cmd.rr['value'] and cmd.rr['name'] == 'aaa'

        with expect_failure("should fail as no name is provided"):
            DynamicCommandLine(["cmd", "-r"], commands).execute()  # ensure that passes

    def test_fields(self):
        commands = make_commands(
            command("a b",
                    flag("-r,--rr", fields=[option("+name"), flag("+f"), option("+x", default_value="yyy")]))
        )

        DynamicCommandLine(["a", "b"], commands).execute()  # ensure that passes

        with expect_failure("should have failed due to missing attached argument name"):
            DynamicCommandLine(["a", "b", "-r"], commands).execute()

        cmd: Command = DynamicCommandLine(["a", "b", "-r", "+name=xxx", "+f"], commands).execute()
        assert cmd.rr and cmd.rr['name'] == "xxx" and cmd.rr["f"] is True and cmd.rr["x"] == "yyy"

    def test_dynamic_arguments(self):
        def args_provider(cmd_: Command) -> List[ArgumentDef]:
            return seq(cmd_.c.split()).map(positional).to_list()

        commands = make_commands(command("a b", positional("c"), dynamic(args_provider)))

        cmd: Command = DynamicCommandLine(["a", "b", "x y", "1", "2"], commands).execute()
        assert cmd.x == "1" and cmd.y == "2"

    def test_dynamic_commands(self):
        @command("a *")
        def a(_: Command) -> List[CommandDef]:
            return make_commands(command("x"), command("y", positional("some-arg")))

        with expect_failure("dynamic commands should not allow the definition of arguments"):
            make_commands(command("b *", positional("x"), flag("-a,--aa")))

        commands = commands_from(locals())

        cmd: Command = DynamicCommandLine(["a", "x"], commands).execute()
        assert cmd.path == ("a", "x")

        cmd: Command = DynamicCommandLine(["a", "y", "some-value"], commands).execute()
        assert cmd.some_arg == "some-value"

    def test_positional_arguments(self):
        commands = make_commands(
            command("a b", positional("bla-bli"), option("-x,--xxx"), flag("-v,--vvv"))
        )

        cmd = DynamicCommandLine(["a", "b", "-x", "hello", "bla-bli-value"], commands).execute()
        assert cmd.xxx == 'hello' and cmd.bla_bli == "bla-bli-value"

        cmd = DynamicCommandLine(["a", "b", "bla-bli-value", "-x", "hello"], commands).execute()
        assert cmd.xxx == 'hello' and cmd.bla_bli == "bla-bli-value"

        with expect_failure("should have been failed due to missing required value"):
            DynamicCommandLine(["a", "b", "-x", "hello"], commands).execute()

    def test_options(self):
        commands = make_commands(
            command("a b", option('-x, --xxx', default_value='some-value'), option("-r, --required"), flag("-f, --fff"))
        )

        abcmd = DynamicCommandLine(["a", "b", "-r", "hello"], commands).execute()
        assert abcmd.required == 'hello' and abcmd.xxx == 'some-value'

        with expect_failure("should have been failed due to missing required value"):
            DynamicCommandLine(["a", "b"], commands).execute()

        abcmd = DynamicCommandLine(["a", "b", "-fr", "hello", "-x", "another-value"], commands).execute()
        assert abcmd and abcmd.fff and abcmd.xxx == 'another-value' and abcmd.required == 'hello'

    def test_simple_command(self):
        commands = make_commands(command(""))
        assert DynamicCommandLine([], commands).execute()

    def test_subpath_simple_command(self):
        commands_executed = []

        @command("a")
        def a(_: Command):
            commands_executed.append("a")

        @command("a b")
        def ab(_: Command):
            commands_executed.append("b")

        DynamicCommandLine(["a", "b"], commands_from(locals())).execute()
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

        commands = commands_from(locals())

        DynamicCommandLine(["a", "b"], commands).execute()
        assert abcmd and acmd

        abcmd, acmd = None, None
        DynamicCommandLine(["a", "b", "-x"], commands).execute()
        assert abcmd and abcmd.xxx
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine(["a", "b", "-x", "-h"], commands).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine(["a", "b", "-xh"], commands).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and not acmd.xxx

        abcmd, acmd = None, None
        DynamicCommandLine(["a", "-v", "b", "-xh"], commands).execute()
        assert abcmd and abcmd.xxx and abcmd.help
        assert acmd and acmd.vvv

        with expect_failure("should not have accepted v as a flag for a b"):
            DynamicCommandLine(["a", "b", "-xhv"], commands).execute()


def make_commands(*commands: Callable) -> List[CommandDef]:
    return commands_from(c(return_cmd) for c in commands)


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

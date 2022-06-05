from typing import List, Callable

from argparse import ArgumentParser, Namespace

_PYPI_LIST_EP = "https://pypi.org/pypi/pkm/json"


def _list(args: Namespace):
    ...


def _install(args: Namespace):
    ...


def main(args: List[str]):
    arg_parser = ArgumentParser()
    subparsers = arg_parser.add_subparsers()

    def subparser(name: str, handler: Callable[[Namespace], None]) -> ArgumentParser:
        result: ArgumentParser = subparsers.add_parser(name)
        result.set_defaults(func=handler)
        return result

    # list
    list_subparser = subparser("list", _list)

    # install
    install_subparser = subparser("install", _install)
    install_subparser.add_argument("version", default="latest")

    parsed = arg_parser.parse_args(args)
    if 'func' in parsed:
        parsed.func(parsed)
    else:
        arg_parser.print_help()

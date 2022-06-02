from dataclasses import dataclass

from pkm.api.environments.environment import Environment

a, b = 1, 2
h = 5  # documentation


class XXX:
    def hello(self):
        ...

    def world(self, x: int = 7) -> str:
        ...


@dataclass
class YYY(XXX):
    def __init__(self, a: str, b: int = 10):
        ...

    @property
    def zzz(self) -> int:
        ...


class ZZZ(Environment):
    ...


x: int = 7
y: str = "10"  # description of assignment

# description before assignment
z = 7


def noanot_func1(x=10, /, a=[], b='100'):
    ...


def noanot_func2(x, a, b, *c, **d):
    ...


def noanot_func3(x, a, b, *, d=1, c="100", **e):
    """
    some information about some function

    :param x:
    :param a:
    :param b:
    :param d: the only documented parameter
    :param c:
    :param e:
    :return: documentation for the return value
    """


def function_with_long_name_and_annotations(
        some_large_annotation_value: str = "this is a long default value", some_other_name: int = 7777) -> str:
    ...


def global_function(
        a: str, b: str, c: int = 7) -> str:
    print("hello there")

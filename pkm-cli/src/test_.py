foo_call = None


def foo(store: bool, x, y, z):
    global foo_call
    if store:
        foo_call = locals()


foo(True, 1, 2, 3)
foo(False, 4, 5, 6)
print(foo_call)

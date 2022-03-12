# x = "a.b.c".split(".")
# y = "a.b.c.d".split(".")
#
# index = next((i for i, p in enumerate(zip(x, y)) if p[0] != p[1]), min(len(x), len(y)))
# print(index)

import importlib
importlib.import_module()
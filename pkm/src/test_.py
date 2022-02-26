def x():
    for i in range(19):
        yield i


a = x()
i1 = iter(a)
i2 = iter(a)
print(next(i1), next(i2))

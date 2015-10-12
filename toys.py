import os, binascii

"""
And God said,Let there be light: and there was light.
In the world of python, you get anything when you get Anything
"""


class Anything(object):
    max_iteration_length = 5
    random_value = True

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        return Anything()

    def __call__(self, *args, **kwargs):
        return Anything()

    def __getitem__(self, item):
        return Anything()

    def __str__(self):
        if self.random_value:
            return binascii.b2a_hex(os.urandom(3))
        else:
            return "<Anything>"

    def __iter__(self):
        self._cu = self.max_iteration_length
        return self

    def next(self):
        if self._cu:
            self._cu -= 1
            return Anything()
        else:
            raise StopIteration

    def items(self):
        return [(i, Anything()) for i in range(self.max_iteration_length)]

    __repr__ = __str__


if __name__ == "__main__":
    print {1: 2}.items()
    print Anything()[1]
    print list(Anything())
    print dict(Anything())
    print set(Anything())
    print Anything()
    for i in Anything():
        print type(i)
    for k, v in Anything().items():
        print type(k), type(v)

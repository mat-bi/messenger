class DBIterator:
    def __init__(self, list):
        self._current = 0
        self._list = list

    def __next__(self):
        if self._current >= len(self._list):
            raise StopIteration
        self._current += 1
        return self._list[self._current - 1]


class DBList(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __iter__(self):
        return DBIterator(list=self.func(*self.args, **self.kwargs))


def fetch(func):
    def func_wrapper(self, *args, **kwargs):
        if self._obj is None:
            self._obj = self.func(*self.args, **self.kwargs)
            del self.func
            del self.args
            del self.kwargs
        return func(self, *args, **kwargs)

    return func_wrapper


class DBObject(object):
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._obj = None

    @fetch
    def __getattr__(self, item):
        return getattr(self._obj, item)

    @fetch
    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self._obj == other._obj
        return self._obj == other

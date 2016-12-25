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
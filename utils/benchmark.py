import time
from contextlib import contextmanager
from datetime import timedelta


class Benchmark:
    def __init__(self):
        self._data = {}
        self._data["runtimes"] = {}

    @contextmanager
    def __call__(self, name):
        with self._benchmark_runtime(name):
            yield

    @contextmanager
    def _benchmark_runtime(self, name):
        begin = time.time()
        yield
        end = time.time()
        self._data["runtimes"][name] = timedelta(seconds=end - begin)

    @property
    def runtimes(self):
        return self._data["runtimes"]


@contextmanager
def benchmark(name, data):
    begin = time.time()
    yield
    end = time.time()
    data[name] = timedelta(end - begin)

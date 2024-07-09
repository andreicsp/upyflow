"""
Test utilities to allow for compatibility between CPython and MicroPython.
"""
import sys

if sys.implementation.name == 'micropython':
    CFG_DIR = '/lib/tests/mpyflow/config'
else:
    import os.path
    CFG_DIR = os.path.join(os.path.dirname(__file__), 'config')


def get_config_file(name):
    return CFG_DIR + '/' + name + '.json'


try:
    import pytest
    raises = pytest.raises
except ImportError:
    class ExceptionAssertion:
        def __init__(self, exc_type, match=None):
            self.exc_type = exc_type
            self.match = match

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is None:
                raise AssertionError(f"Expected exception {self.exc_type}")
            if exc_type != self.exc_type:
                raise AssertionError(f"Expected exception {self.exc_type}, got {exc_type}")
            if self.match is not None:
                if self.match not in str(exc_value):
                    raise AssertionError(f"Expected exception message to contain {self.match}, got {exc_value}")
            return True

    raises = ExceptionAssertion


# Title: upyflow - MicroPython Workflow Engine
# Copyright: (c) 2024 Andrei Dumitrache
# License: MIT License
"""
upyflow - Runtime utilities

Collection of runtime utilities defined according to the Python
platorm being used.
"""

import gc
import sys

# Define the getLogger function based on the platform

try:
    # If the logging module is available, use it
    import logging
    getLogger = logging.getLogger
except ImportError:
    # Otherwise, define a simple fallback logger that prints to the console
    class PrintLogger:
        _loggers = {}
        def __init__(self, name): self.name = name
        def debug(self, msg): print(f"[DEBUG] {self.name}: {msg}")
        def info(self, msg): print(f"[INFO] {self.name}: {msg}")
        def warn(self, msg): print(f"[WARN] {self.name}: {msg}")
        def error(self, msg): print(f"[ERROR] {self.name}: {msg}")

        @classmethod
        def getLogger(cls, name):
            if name not in cls._loggers:
                cls._loggers[name] = PrintLogger(name)
            return cls._loggers[name]


    getLogger = PrintLogger.getLogger


# Define memory usage function based on the platform
if sys.implementation.name == "micropython":
    get_alloc_mem = gc.mem_alloc
else:
    import os

    import psutil

    get_alloc_mem = lambda : psutil.Process(os.getpid()).memory_info().rss

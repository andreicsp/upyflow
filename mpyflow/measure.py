"""
MPyFlow - Measure module

Utilities for measuring performance of code executed in the process of running
a flow. 

This module provides a context manager that can be used to measure the
performance of a block of code, capturing the time it took to execute, and 
the change in memory usage.
"""
import gc
from time import time_ns

from mpyflow.runtime import get_alloc_mem, getLogger


class PerformanceContext:
    def __init__(self, msg: str, logger=None, capture_mem=False, silent=False):
        """
        Initializes a new performance context.

        :param msg: Text describing the block of code being measured. 
            Logged at the DEBUG level when the context is entered
            Logged again and at the INFO level when the context is exited with performance information.
        :param logger: The logger to use for logging messages. Defaults to the root logger.
        :param capture_mem: Whether to capture memory usage before and after the block of code is executed.
            Recommended off in non-microcontroller environments as it measures the memory usage of the entire system.
        :param silent: Whether to suppress the log messages.
        """
        self.start = 0.0
        self.end = 0.0
        self.logger = logger or getLogger(__name__)
        self.msg = msg
        self.capture_mem = capture_mem
        self.mem_before = 0
        self.mem_after = 0
        self.silent = silent

    @property
    def elapsed(self):
        """Time elapsed in nanoseconds."""
        return self.end - self.start
    
    @property
    def mem_usage(self):
        """Memory usage in bytes."""
        return self.mem_after - self.mem_before

    def __enter__(self):
        self.start = time_ns()
        if not self.silent:
            self.logger.debug(self.msg)
        if self.capture_mem:
            gc.collect()
            self.mem_before = get_alloc_mem()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        additional_info = ""
        if self.capture_mem:
            gc.collect()
            self.mem_after = get_alloc_mem()
            additional_info = f" (Memory usage: {self.mem_usage} bytes)"

        self.end = time_ns()
        if not self.silent:
            self.logger.info(f"{self.msg} took {self.elapsed / 1_000_000}ms{additional_info}")

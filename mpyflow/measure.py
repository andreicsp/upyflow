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

ACTION_CALL = 'call'
ACTION_RUN = 'run'
ACTION_IMPORT = 'import'


class Formatter:
    _default = None

    def format_start(self, action, detail):
        return f"{action} {detail}"

    def format_end(self, action, detail, elapsed, mem_usage, exc_type=None, exc_val=None):
        metrics = f"[{elapsed / 1_000_000} ms" + f", {mem_usage} bytes]" if mem_usage >= 0 else "]"
        error = f" {exc_type.__name__}: {exc_val}" if exc_type is not None else ""
        return f"{action} {detail}{error} {metrics}"


default_formatter = Formatter()


class PerformanceContext:

    def __init__(
            self, detail: str, action: str = ACTION_RUN, logger=None, formatter=None, capture_mem=False, silent=False):
        """
        Initializes a new performance context.

        :param detail: Text describing the block of code being measured.
            Logged at the DEBUG level when the context is entered
            Logged again and at the INFO level when the context is
            exited with performance information.
        :param action: Type of action being performed.
        :param logger: The logger to use for logging messages.
            Defaults to the root logger.
        :param formatter: The formatter to use for formatting measurement messages.
        :param capture_mem: Whether to capture memory usage before
            and after the block of code executes.
            Recommended off in non-microcontroller environments as it
            measures the memory usage of the entire system.
        :param silent: Whether to suppress the log messages.
        """
        self.start = 0.0
        self.end = 0.0
        self.logger = logger or getLogger(__name__)
        self.detail = detail
        self.action = action
        self.capture_mem = capture_mem
        self.mem_before = 0
        self.mem_after = 0
        self.formatter = formatter or default_formatter
        self.silent = silent

    @property
    def elapsed(self):
        """Time elapsed in nanoseconds."""
        return self.end - self.start

    @property
    def mem_usage(self):
        """Memory usage in bytes."""
        return (self.mem_after - self.mem_before) if self.capture_mem else -1

    def __enter__(self):
        self.start = time_ns()
        if not self.silent:
            self.logger.debug(self.formatter.format_start(action=self.action, detail=self.detail))
        if self.capture_mem:
            gc.collect()
            self.mem_before = get_alloc_mem()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.capture_mem:
            gc.collect()
            self.mem_after = get_alloc_mem()

        self.end = time_ns()
        if not self.silent:
            log_method = self.logger.info if exc_type is None else self.logger.error
            log_method(
                self.formatter.format_end(
                    action=self.action, detail=self.detail,
                    elapsed=self.elapsed, mem_usage=self.mem_usage,
                    exc_type=exc_type, exc_val=exc_val
                )
            )

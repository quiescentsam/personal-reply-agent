from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_on_main_thread(func: Callable[[], T | None]) -> None:
    from Foundation import NSOperationQueue

    NSOperationQueue.mainQueue().addOperationWithBlock_(func)

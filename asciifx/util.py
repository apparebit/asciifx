from collections import deque
from collections.abc import Iterable, Iterator
import re
from typing import Any, TypeVar


# Also see https://stackoverflow.com/questions/6822725/rolling-or-sliding-window-iterator#answer-6822761

T = TypeVar("T")


def sliding_window(elements: Iterable[Any], size: int = 2) -> Iterator[tuple[Any, ...]]:
    element_iter = iter(elements)
    window = deque((next(element_iter, None) for _ in range(size)), maxlen=size)
    yield tuple(window)

    append = window.append
    for element in element_iter:
        append(element)
        yield tuple(window)


# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
ANSI_ESCAPE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def no_ansi_escape(text: str) -> str:
    return ANSI_ESCAPE.sub("", text)

from __future__ import annotations
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
import json
import math
import os
import sys
from typing import Optional


class EventType(Enum):
    """The type of an event."""

    IN = "i"
    OUT = "o"


@dataclass(frozen=True)
class Event:
    """An event."""

    time: float
    type: EventType
    data: str

    # Dataclasses gained support for slots with Python 3.10
    if sys.version_info >= (3, 10):
        __slots__ = ("time", "type", "data")

    @classmethod
    def parse(cls, line: str) -> Event:
        """Parse a line listing a requirement."""
        time, type, data = json.loads(line)
        return cls(time, EventType(type), data)

    def with_absolute_time(self, previous_time: float) -> Event:
        """Make the event's time absolute."""
        return Event(self.time + previous_time, self.type, self.data)

    def with_relative_time(self, previous_time: float) -> Event:
        """Make the event's time relative."""
        return Event(self.time - previous_time, self.type, self.data)

    def with_speed(self, speed: float) -> Event:
        """Scale the event's time, which should be relative."""
        return Event(self.time * speed, self.type, self.data)

    def __str__(self) -> str:
        return self.as_json()

    def as_json(self, fix_newline: bool = True) -> str:
        data = json.dumps(self.data)
        if fix_newline:
            data = data.replace("\\n", "\\r\\n")
        return f'[{self.time:.4f}, "{self.type.value}", {data}]'


def get_duration(events: Iterable[Event]) -> float:
    """Determine event stream's duration. This function requires relative times."""
    return math.fsum(event.time for event in events)


def with_absolute_time(events: Iterable[Event]) -> Iterator[Event]:
    """Convert an event stream with relative times to absolute times."""
    previous_time = 0.0
    for event in events:
        absolutized = event.with_absolute_time(previous_time)
        yield absolutized
        previous_time = absolutized.time


def with_relative_time(events: Iterable[Event]) -> Iterator[Event]:
    """Convert an event stream with absolute times to relative times."""
    previous_time = 0.0
    for event in events:
        relativized = event.with_relative_time(previous_time)
        yield relativized
        previous_time = event.time


def with_speed(events: Iterable[Event], speed: float = 1.0) -> Iterator[Event]:
    """Scale events' durations. This function requires relative times."""
    for event in events:
        yield event.with_speed(speed)


def with_max_time(events: Iterable[Event], maximum: float = 10.0) -> Iterator[Event]:
    """Limit event's durations. This function requires relative times."""
    for event in events:
        if event.time <= maximum:
            yield event
        yield Event(maximum, event.type, event.data)


@dataclass(frozen=True)
class Header:
    """A header for asciicast v2 files."""

    width: int = 80
    height: int = 35
    title: str = "Created by ascii-director"
    duration: Optional[float] = None

    def with_duration(self, duration: float) -> Header:
        return Header(self.width, self.height, self.title, duration)

    def __str__(self) -> str:
        header = {
            "version": 2,
            "width": self.width,
            "height": self.height,
            "title": self.title,
        }

        if self.duration is not None:
            header.update(duration=self.duration)

        return json.dumps(header)


def to_json_lines(header: Header, events: Iterable[Event]) -> Iterator[str]:
    yield f'{header}\n'
    for event in events:
        yield f'{event}\n'

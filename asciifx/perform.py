from collections.abc import Iterable, Iterator

from .animator import Animator, Controller
from .event import Header, to_json_lines, with_absolute_time
from .repl import PyRepl


def perform(
    lines: Iterable[str],
    *,
    keypress_speed: float = 1.0,
    speed: float = 1.0,
    width: int = 80,
    height: int = 35,
    title: str = "Created by ascii-fx",
) -> Iterator[str]:
    # Play back script in interpreter REPL.
    repl = PyRepl()
    interactions = repl.simulate_all(lines)

    # Convert to events with timing information.
    controller = Controller()
    animator = Animator(controller, speed=speed, keypress_speed=keypress_speed)
    relative_events = animator.render_all(interactions)

    # Convert to newline-separated JSON.
    header = Header(width, height, title)
    absolute_events = with_absolute_time(relative_events)
    return to_json_lines(header, absolute_events)

from collections.abc import Iterable, Iterator

from .animator import Animator, Controller
from .event import Header, to_json_lines, with_absolute_times
from .repl import PyRepl


def perform(
    lines: Iterable[str],
    *,
    width: int = 80,
    height: int = 35,
    title: str = "Created by ascii-fx",
) -> Iterator[str]:
    repl = PyRepl()
    interactions = repl.simulate_all(lines)

    controller = Controller()
    animator = Animator(controller)
    relative_events = animator.render_all(interactions)

    header = Header(width, height, title)
    absolute_events = with_absolute_times(relative_events)

    return to_json_lines(header, absolute_events)

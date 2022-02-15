from collections.abc import Iterable, Sequence

from .animator import Animator, Controller
from .event import Header, to_json_lines, with_absolute_time
from .repl import PyRepl, Repl


def perform(
    lines: Iterable[str],
    *,
    keypress_speed: float = 1.0,
    speed: float = 1.0,
    width: int = 80,  # If non-positive, replaced by observed width of asciicast.
    height: int = 35,  # If non-positive, replaced by observed height of asciicast.
    title: str = "Created by ascii-fx",
    AnimatorClass: type[Animator] = Animator,
    ControllerClass: type[Controller] = Controller,
    ReplClass: type[Repl] = PyRepl,
) -> tuple[Sequence[str], int, int]:
    """
    Turn a script into an asciicast performance. This function feeds the given
    script line by line into a new instance of the given REPL. It then animates
    the resulting interactions with new instances of the given animator and
    controller. Finally, it converts the resulting events into newline-delimited
    JSON. This function returns the sequence of events as newline-delimited
    JSON, the maximum number of columns taken up by the asciicast, and the
    number of lines taken up by the asciicast.
    """
    # Play back script in interpreter REPL.
    repl = ReplClass()
    interactions = repl.simulate_all(lines)

    # Convert to events with timing information.
    controller = ControllerClass()
    animator = AnimatorClass(controller, speed=speed, keypress_speed=keypress_speed)
    relative_events = animator.render_all(interactions)

    # Fix width and height if necessary
    if width <= 0:
        width = animator.width + 1
    if height <= 0:
        height = animator.height + 1

    # Convert to newline-separated JSON.
    header = Header(width, height, title)
    absolute_events = with_absolute_time(relative_events)
    events = [*to_json_lines(header, absolute_events)]

    return events, animator.width, animator.height

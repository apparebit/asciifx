"""
The animator module defines brings the simulated interactive session to life.
Critically, that implies synthesizing timings that control the delay before text
can be displayed next. The timings are:

  * Delay before displaying the prompt.
  * Delay before displaying the first letter of input. This delay is due to the
    human user reading the output of previous interaction and thinking about
    what to type next.
  * Delay before displaying the next letter of input. This delay reflects the
    keystroke dynamics of the human user entering code.
  * Delay before displaying output. This delay reflects compute time.


## Input Delay

The input delay is the time during which the simulated human catches up with the
output of the interpreter from the *preceding* interaction and then decides what
to enter as input for the current interaction. So if the human reads the entire
output, a longer output implies a longer delay. But they may skim more material
with increasing length as well. So a longer output implies a decreasing increase
in delay.


## Keypress Delay

The harder ones to simulate semi-realistically are the input and keypress delays
because they need to simulate a human. A cursory literature search produced two
papers that focus on free text input, not passwords, and are based on large
datasets — thus making them attractive as foundations for a simulator:

 1. [On the shape of timings distributions in free-text keystroke dynamics
    profiles](https://www.cell.com/heliyon/fulltext/S2405-8440(21)02516-0) by
    Nahuel González, Enrique P. Calot, Jorge S. Ierache, and Waldo Hasperué.
    Heliyon, volume 7, issue 11.
 2. [Observations on Typing from 136 Million
    Keystrokes](https://userinterfaces.aalto.fi/136Mkeystrokes/resources/chi-18-analysis.pdf)
    by Vivek Dhakal, Anna Maria Feit, Per Ola Kristensson, and Antti Oulasvirta.
    ACM CHI 2018.

The first paper explores the fit of propability distributions for keypress
dynamics. It considers both flight times (key down to key down) and hold times
(key down to key up), evaluating how several probability distributions in both a
two-parameter and a three-parameter version fit the experimental data. The paper
concludes that the log-logistic distribution provides the best fit for both
flight and hold times. The Dagum distribution is a close second and the
log-normal distribution also performs well.

The second paper provides a plethora of metrics for a very large dataset.
Notably, it includes the impact of handedness on inter-key intervals (IKI;
JavaScript keypress event to keypress event, i.e., equivalent to flight times).
In particular, it partitions bigrams into four sets, namely left hand only,
right hand only, alternating hands, and same letter. It then shows distinct
means and standard deviations for each partition.

However, those results do come with two important caveats: First, the text
corpus did not include all possible bigrams, resulting in a lack of data for
some bigrams. Second, the mapping between keys and hands differs between
individuals and may even be fluid for the same individual. As a result, some
bigrams fell into several partitions and were also excluded from the summary
statistics.

The association between keys and hands may be inconsistent for regular, flat
keyboards. However, for contoured or split keyboards, the separation into two
independent halves forces a static association. `Animator` builds on this
observation and reuses the layout of the [Kinesis contoured
keyboard](https://kinesis-ergo.com/shop/advantage2/) to assign ASCII letters to
hands.

Since there are no readily apparent formulas for deriving the parameters of the
log-logistic or Dagum distributions from a given mean and standard deviation,
`Animator` uses the log-normal distribution for now. Furthermore, it assumes
that reported IKI statistics generalize to all bigrams — mapped to hands based
on the layout of the Kinesis contoured keyboard.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import inspect
import math
import random
import re
from typing import Callable, Optional

from .event import Event, EventType
from .repl import Interaction


OUT = EventType.OUT


class InvalidPragma(Exception):
    pass


class Controller:
    """
    Support for handling pragmas, which may modify the timing of the simulation
    or suppress part of it altogether. Pragmas are embedded as comments in the
    stream of interactions and can have zero or one arguments. Methods that do
    not implement a pragma must either start with an underscore `_` or, if they
    are public, start with `do_`. The rest
    """

    SYNTAX = re.compile(
        r"^\#\[(?P<command>[^ \t=]+)(?:[ \t]*[=][ \t]*(?P<param>[^\]]+))?\]\n$"
    )

    def __init__(self) -> None:
        self._lines: int = 0

    def do_register(self, animator: Animator) -> Controller:
        self._animator = animator
        return self

    def do_handle_pragma(self, line: str) -> bool:
        self._lines += 1

        if (match := self.SYNTAX.match(line)) is None:
            return False

        command, argument = match.groups()
        command = command.strip()

        method = getattr(self, command.replace("-", "_"), None)
        if method is None or not callable(method) or command.startswith(("_", "do_")):
            raise InvalidPragma(
                f'#[{command}] on line {self._lines} is not recognized '
                'as a valid pragma.'
            )

        parameter_count = len(inspect.signature(method).parameters)
        argument = argument if argument is None else argument.strip()

        if parameter_count == 0:
            if argument is not None:
                raise InvalidPragma(
                    f'#[{command}] on line {self._lines} has no arguments '
                    f'but "{argument}" is provided.'
                )
            method()
        elif parameter_count == 1:
            if argument is None:
                raise InvalidPragma(
                    f'#[{command}] on line {self._lines} requires an argument '
                    'but none is provided.'
                )
            method(argument)
        else:
            assert False, f"Pragma implementation has {parameter_count} parameters."

        return True

    def _parse_float(self, command: str, argument: str) -> float:
        try:
            return float(argument)
        except ValueError as x:
            raise InvalidPragma(
                f'#[{command}] on line {self._lines} requires floating point '
                f'number but got "{argument}".'
            ) from x

    def on(self) -> None:
        self._animator.is_silent = False

    def off(self) -> None:
        self._animator.is_silent = True

    def think_time(self, data: str) -> None:
        self._animator.next_thought_delay = self._parse_float("think-time", data)

    def speed(self, data: str) -> None:
        self._animator.speed = self._parse_float("speed", data)

    def keypress_speed(self, data: str) -> None:
        self._animator.keypress_speed = self._parse_float("keypress-speed", data)


def as_lognorm_params(mean: float, stddev: float) -> tuple[float, float]:
    # See https://en.wikipedia.org/wiki/Log-normal_distribution#Definitions
    # Also note that second conversion formula has sigma^2 on left side.
    return (
        math.log(mean**2.0 / math.sqrt(mean**2.0 + stddev**2.0)),
        math.sqrt(math.log(1 + stddev**2.0 / mean**2.0)),
    )


class Animator:
    """
    The animator. This class uses a simplified and known to be inaccurate model
    of human keystroke dynamics to animate interpreter input. It also uses an
    even simpler model to suggest delays for reading and thinking. While those
    models are baked into the class, the class is also designed for subclassing
    and selective overriding of behaviors.
    """

    # fmt: off
    LEFT_HAND: str = (
        "=12345qwertasdfgzxcvb`§"
        "+!@#$%QWERTASDFGZXCVB~±"
    )
    RIGHT_HAND: str = (
        "67890-yuiop\\hjkl;'nm,./[]"
        '^&*()_YUIOP||HJKL:"NM<>?{} '
    )
    # fmt: on

    # These are the mean and standard deviation of the distribution

    # Need ln(mu^2/sqrt(mu^2 + s^2))  ln(1+ s^2/mu^2)

    LEFT_IKI: tuple[float, float] = as_lognorm_params(124.37, 25.90)
    RIGHT_IKI: tuple[float, float] = as_lognorm_params(117.24, 25.03)
    ALTERNATE_IKI: tuple[float, float] = as_lognorm_params(108.62, 17.57)
    SAME_LETTER_IKI: tuple[float, float] = as_lognorm_params(144.79, 27.46)

    PROMPT_DELAY: float = 0.001
    INPUT_DELAY: float = 1.0
    OUTPUT_BASE_DELAY: float = 0.050
    OUTPUT_INCR_DELAY: float = 0.200
    END_DELAY: float = 5.0

    def __init__(
        self,
        controller: Controller,
        *,
        keypress_speed: float = 1.0,
        speed: float = 1.0,
    ) -> None:
        self._controller: Controller = controller.do_register(self)
        self._previous_interaction: Optional[Interaction] = None
        self._random_delay: Callable[[float, float], float] = random.lognormvariate

        self.is_silent: bool = False
        self.next_thought_delay: Optional[float] = None
        self.keypress_speed: float = keypress_speed
        self.speed: float = speed

    @property
    def previous_interaction(self) -> Optional[Interaction]:
        return self._previous_interaction

    def render_all(self, interactions: Iterable[Interaction]) -> Iterator[Event]:
        """Render the interaction stream into an event stream with relative time."""
        for interaction in interactions:
            yield from self.render(interaction)
        yield self.event(self.END_DELAY, "")

    def render(self, interaction: Interaction) -> Iterator[Event]:
        """Render a single interaction."""
        prompt, input, output = interaction
        if self._controller.do_handle_pragma(input) or self.is_silent:
            # Directives and silent interactions should not influence timings.
            # Hence they are skipped as previous interactions.
            return

        yield from self.render_prompt(prompt)
        yield from self.render_input(input)
        yield from self.render_output(output)

        self._previous_interaction = interaction
        self.next_thought_delay = None

    def render_prompt(self, prompt: str) -> Iterator[Event]:
        """Render the prompt."""
        yield self.event(self.delay_prompt(), prompt)

    def render_input(self, input: str) -> Iterator[Event]:
        """Render the input."""
        letters = iter(input)

        previous_letter = next(letters, "")
        if self.next_thought_delay is None:
            delay = self.delay_input()
        else:
            delay = self.next_thought_delay
        yield self.event(delay, previous_letter)

        for pending_letter in letters:
            delay = self.delay_keypress(previous_letter, pending_letter)
            yield self.event(delay, pending_letter)
            previous_letter = pending_letter

    def render_output(self, output: str) -> Iterator[Event]:
        """Render the output."""
        for index, section in enumerate(self.section_output(output)):
            delay = self.delay_output(index, output)
            yield self.event(delay, section)

    def event(self, time: float, data: str) -> Event:
        return Event(time * self.speed, OUT, data)

    def section_output(self, output: str) -> Iterator[str]:
        """Split interpreter output into sections."""
        yield output

    def delay_prompt(self) -> float:
        return self.PROMPT_DELAY

    def delay_input(self) -> float:
        previously = self.previous_interaction
        if (
            previously is None
            or previously.input.strip() == ""
            or previously.output.strip() == ""
        ):
            return self.delay_keypress("\n", "\n")

        # Delay increases with line count whereas increase decreases with line count.
        line_count = previously.output.count("\n")
        return 1.0 + math.log(line_count)

    def delay_keypress(self, previous: str, current: str) -> float:
        # IKI mean and stddev are in milliseconds. Adjust delay accordingly.
        if previous == current:
            delay = self._random_delay(*self.SAME_LETTER_IKI) / 1000.0
        if previous in self.LEFT_HAND and current in self.LEFT_HAND:
            delay = self._random_delay(*self.LEFT_IKI) / 1000.0
        if previous in self.RIGHT_HAND and current in self.RIGHT_HAND:
            delay = self._random_delay(*self.RIGHT_IKI) / 1000.0
        else:
            delay = self._random_delay(*self.ALTERNATE_IKI) / 1000.0

        return delay * self.keypress_speed

    def delay_output(self, index: int, section: str) -> float:
        if index == 0:
            return self.OUTPUT_BASE_DELAY
        return self.OUTPUT_INCR_DELAY

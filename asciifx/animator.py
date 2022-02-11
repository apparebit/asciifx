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

Since mean and standard deviation are unsuitable as parameters for the
log-logistic and Dagum distributions, `Animator` uses the log-normal
distribution instead. Furthermore, it generalizes the IKI statistics to all
bigrams — using the Kinesis contoured keyboard for selecting hands.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import inspect
import math
import random
import re
from typing import Optional

from .event import Event, EventType
from .repl import Interaction


OUT = EventType.OUT


class Controller:
    """
    Support for handling pragmas, which may modify the timing of the simulation
    or suppress part of it altogether. Pragmas are embedded as comments in the
    stream of interactions.
    """

    SYNTAX = re.compile(
        r"^\#\[(?P<command>[a-z]+)(?:[ \t]*[=][ \t]*(?P<param>[^\]]+))?\]\n$"
    )

    def __init__(self) -> None:
        pass

    def register(self, animator: Animator) -> Controller:
        self._animator = animator
        return self

    def handle_pragma(self, line: str) -> bool:
        if (match := self.SYNTAX.match(line)) is None:
            return False

        command = match.group("command")
        if command == "handle" or command.startswith("_") or not hasattr(self, command):
            return False

        method = getattr(self, command)
        param_count = len(inspect.signature(method).parameters)
        if param_count == 0:
            method()
            return True
        elif param_count == 1:
            method(match.group("param"))
            return True
        else:
            return False

    def on(self) -> None:
        self._animator.set_silent(False)

    def off(self) -> None:
        self._animator.set_silent(True)

    def think(self, data: str) -> None:
        self._animator.set_thinking(float(data))


def as_lognorm_params(mean: float, stddev: float) -> tuple[float, float]:
    return (
        math.log(mean**2.0 / math.sqrt(mean**2.0 + stddev**2.0)),
        math.log(1 + stddev**2.0 / mean**2.0),
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

    def __init__(self, controller: Controller) -> None:
        self._controller: Controller = controller.register(self)
        self._is_silent: bool = False
        self._thinking: Optional[float] = None
        self._previous_interaction: Optional[Interaction] = None
        self._random_delay = random.lognormvariate

    @property
    def is_silent(self) -> bool:
        return self._is_silent

    def set_silent(self, silent: bool) -> Animator:
        self._is_silent = silent
        return self

    @property
    def previous_interaction(self) -> Optional[Interaction]:
        return self._previous_interaction

    def set_thinking(self, duration: float) -> Animator:
        self._thinking = duration
        return self

    def render_all(self, interactions: Iterable[Interaction]) -> Iterator[Event]:
        """Render the interaction stream into an event stream with relative time."""
        for interaction in interactions:
            yield from self.render(interaction)
        yield Event(self.END_DELAY, OUT, "")

    def render(self, interaction: Interaction) -> Iterator[Event]:
        """Render a single interaction."""
        prompt, input, output = interaction
        if self._controller.handle_pragma(input) or self._is_silent:
            # Directives and silent interactions should not influence timings.
            # Hence they are skipped as previous interactions.
            return

        yield from self.render_prompt(prompt)
        yield from self.render_input(input)
        yield from self.render_output(output)

        self._previous_interaction = interaction
        self._thinking = None

    def render_prompt(self, prompt: str) -> Iterator[Event]:
        """Render the prompt."""
        yield Event(self.delay_prompt(), OUT, prompt)

    def render_input(self, input: str) -> Iterator[Event]:
        """Render the input."""
        letters = iter(input)

        previous_letter = next(letters, "")
        if self._thinking is None:
            delay = self.delay_input()
        else:
            delay = self._thinking
        yield Event(delay, OUT, previous_letter)

        for pending_letter in letters:
            delay = self.delay_keypress(previous_letter, pending_letter)
            yield Event(delay, OUT, pending_letter)
            previous_letter = pending_letter

    def render_output(self, output: str) -> Iterator[Event]:
        """Render the output."""
        for index, section in enumerate(self.section_output(output)):
            delay = self.delay_output(index, output)
            yield Event(delay, OUT, section)

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
            return self._random_delay(*self.SAME_LETTER_IKI) / 1000.0
        if previous in self.LEFT_HAND and current in self.LEFT_HAND:
            return self._random_delay(*self.LEFT_IKI) / 1000.0
        if previous in self.RIGHT_HAND and current in self.RIGHT_HAND:
            return self._random_delay(*self.RIGHT_IKI) / 1000.0
        return self._random_delay(*self.ALTERNATE_IKI) / 1000.0

    def delay_output(self, index: int, section: str) -> float:
        if index == 0:
            return self.OUTPUT_BASE_DELAY
        return self.OUTPUT_INCR_DELAY

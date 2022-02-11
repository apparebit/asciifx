from abc import ABC, abstractmethod
from code import InteractiveConsole
from collections.abc import Iterable, Iterator
from contextlib import redirect_stderr, redirect_stdout
import io
import re
from typing import NamedTuple


class Interaction(NamedTuple):
    prompt: str
    input: str
    output: str


class Repl(ABC):
    """The superclass of REPL implementations."""

    def simulate_all(self, lines: Iterable[str]) -> Iterator[Interaction]:
        for line in lines:
            if self.will_terminate(line):
                yield Interaction(f"{self.prompt()} ", line, "")
                return

            yield self.simulate(line)

    def simulate(self, line: str) -> Interaction:
        """
        Simulate operation of the REPL on the given line. This method returns
        a triple with the prompt, the input (line), and some oracle's output.
        """
        prompt = self.prompt()

        buffer = io.StringIO()
        with redirect_stderr(buffer):
            with redirect_stdout(buffer):
                self.eval(line)

        return Interaction(f"{prompt} ", line, buffer.getvalue())

    @abstractmethod
    def prompt(self) -> str:
        ...

    @abstractmethod
    def will_terminate(self, line: str) -> bool:
        ...

    @abstractmethod
    def eval(self, line: str) -> None:
        ...


class PyRepl(Repl):
    """A Python REPL."""

    QUIT_INVOCATION = re.compile(r"^( |\t)*quit\(\)( |:|$)")

    def __init__(self) -> None:
        self._interpreter = InteractiveConsole()
        self._more = False

    def prompt(self) -> str:
        return "..." if self._more else ">>>"

    def will_terminate(self, line: str) -> bool:
        return self.QUIT_INVOCATION.match(line) is not None

    def eval(self, line: str) -> None:
        self._more = self._interpreter.push(line[:-1])

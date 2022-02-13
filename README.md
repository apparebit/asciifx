# asciifx

[asciinema](https://asciinema.org) is a great tool for recording, viewing, and
sharing live terminal performances. But sometimes, a performance really needs to
be carefully scripted and its staging carefully controlled. That's when you turn
to ***asciifx***.

In particular, asciifx turns plain Python scripts into [version 2
asciicasts](https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md)
of what might be a person executing the script line by line in an interactive
Python interpreter. It features semi-realistic keystroke dynamics as well as
pauses for reading interpreter output. Beyond this first use-case, asciifx has
well-defined internal interfaces that make extension straight-forward.


## An Example

Consider this Python script to show off the libray that inspired this package,
[konsole](https://github.com/apparebit/konsole):

```python
#[keypress-speed=0.5]
#[off]
import konsole
konsole.config(use_color=True)
#[on]
konsole.info("fyi", detail=["for", "your", "information"])
konsole.warning("beware")
konsole.error("bad")
konsole.critical("enough already!!!")
quit()
```

The comments may look like [Rust
annotations](https://doc.rust-lang.org/rust-by-example/attribute.html) but still
are valid Python. In the context of asciifx, they also are called pragmas and
control the performance. `keypress-speed` speeds up simulated keypresses because
they just aren't *that* interesting to watch. `off`/`on` prevent the import and
configuration of konsole from appearing in the final asciicast, though the two
statements are executed nonetheless.

With that, we are ready to run asciifx:

```sh
$ python -m asciifx -o output.cast input.py
```

You can watch the resulting asciicast with asciinema — or convert it to SVG with
[svg-term-cli](https://github.com/marionebl/svg-term-cli):

![An interactive Python session using
konsole](https://raw.githubusercontent.com/apparebit/asciifx/boss/example/image.svg)


## Pragmas

To be recognized by asciifx, a pragma must appear on a line, by itself. asciifx
supports the following pragmas:

  * `#[off]` suspends rendering to asciicast events.
  * `#[on]` restores the rendering of asciicast events.
  * `#[think-time=FLOAT]` inserts a pause of *FLOAT* seconds after the next
    interaction's interpreter prompt.
  * `#[speed=FLOAT]` adjusts overall duration by multiplying all delays by *FLOAT*.
  * `#[keypress-speed=FLOAT]` adjusts keypress duration by multiplying keypress delays
    by *FLOAT*.

Whereas `think-time` takes an absolute value in seconds, `speed` and
`keypress-speed` take relative, multiplicative values. To make these semantics
obvious even to casual users, `think-time` ends with `time`, whereas `speed` and
`keypress-speed` end with `speed`. The `speed` and `keypress-speed` pragmas
multiply by their arguments instead of the inverse of their arguments because
that makes jumping through time trivial: Just set `speed` or `keypress-speed` to
zero! At the same time, beware that the combined impact of `speed` and
`keypress-speed` is multiplicative on the duration between keypresses.


## An Itch to Scratch

asciifx exists because I had an itch to scratch: creating an animated screenshot
to show off konsole. Python's REPL is great for showing off an interface, since
it displays the result of each statement right after executing, and
[asciinema](https://github.com/asciinema/asciinema) is great for recording such
interactions. The problem is that getting such a performance right pretty much
requires scripting everything beforehand. But if it's already scripted, it makes
little sense to type out the code again at a Python REPL.

So I scoped out writing my own tool: Python's [code
module](https://docs.python.org/3/library/code.html) has all the REPL support
I'd need, nicely abstracted. [asciicast
v2](https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md) is
an eminently reasonable file format to target. All that was missing was a
suitable model for human keystroke dynamics. After a quick literature search,
even that model seemed within reach.

Alas, turning scientific writing into executable code easily becomes an exercise
in frustration. There is ambiguous language in the definition of critical
metrics when perfectly well-defined terminology and metrics exist. (Yes, IKI is
the same as flight time shifted by hold time. No, "keypress event" is not an
abstract event related to pressing keys but an actual, [deprecated JavaScript
event](https://developer.mozilla.org/en-US/docs/Web/API/Document/keypress_event).)
There also are probability distributions that are surprisingly hostile to casual
human use. (No, μ and σ are *not* the mean and standard deviation of the
log-normal distribution. Yes, they are the customary parameters for that
distribution nonetheless. Converting mean and standard deviation to these
parameters is left as an exercise for the reader. 😈)

---

© 2022 [Robert Grimm](https://apparebit.com).
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
[GitHub](https://github.com/apparebit/asciifx).

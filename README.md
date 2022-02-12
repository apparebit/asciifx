# ascii-fx

[asciinema](https://asciinema.org) is a great tool for recording, viewing, and
sharing live terminal performances. But sometimes, a performance really needs to
be carefully scripted and its staging carefully controlled. That's when you turn
to ***ascii-fx***.

The first use case and hence entire reason for the existence of this tool cum
library is to turn plain Python scripts into [version 2
asciicasts](https://github.com/asciinema/asciinema/blob/develop/doc/asciicast-v2.md)
of what might be a person executing the script line by line in an interactive
Python interpreter. Notably, the asciicast features semi-realistic keystroke
dynamics as well as pauses for reading interpreter output.

ascii-fx recognizes three pragmas that control how interactions are animated for
the asciicast. The pragmas must take up the entire line by themselves to be
recognized. They are:

  * `#[off]` suspends rendering to asciicast events.
  * `#[on]` restores the rendering of asciicast events.
  * `#[think=M.N]` inserts a pause of M.N seconds after the next interaction's interpreter prompt.

Use the first two pragmas to hide configuration and scaffolding. Use the third
pragma to override ascii-fx's default pause.

When we execute `python -m asciifx --scale 0.5 example.py` with the example script
reading:

```python
#[off]
import konsole
konsole.config(use_color=True)
#[on]
konsole.info("fyi", detail=["for", "your", "information"])
konsole.warning("beware")
#[think=0.3]
konsole.error("bad")
konsole.critical("enough already!!!")
quit()
```

The result is an asciicast that looks like the image below, only that the image
below has been further converted into an animated SVG with help of
`svg-term-cli`.

![An interactive Python session using
konsole](https://raw.githubusercontent.com/apparebit/ascii-fx/boss/example.svg)

---

© 2022 [Robert Grimm](https://apparebit.com).
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) license.
[GitHub](https://github.com/apparebit/ascii-fx).

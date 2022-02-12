import konsole

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from .perform import perform


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="ascii-fx",
        description="turns Python scripts into simulated interactive sessions",
    )

    parser.add_argument(
        "script",
        help="The Python script to convert into a simulated interactive session",
    )
    parser.add_argument(
        "--scale",
        type=float,
        help="Speed up the asciicast by a factor < 1.0, slow it down by a factor > 1.0",
    )
    parser.add_argument(
        "--width",
        default=80,
        type=int,
        help="Set the asciicast terminal width",
    )
    parser.add_argument(
        "--height", default=35, type=int, help="Set the asciicast terminal height"
    )
    parser.add_argument("--title", type=str, help="Set the asciicast title")

    return parser


def main() -> None:
    parser = create_parser()
    options = parser.parse_args()
    if not options.title:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        options.title = f'Created by asciicast on {now} from "{options.script}"'

    try:
        path = Path(options.script)

        with open(path, mode="r", encoding="utf8") as input:
            output = [
                *perform(
                    input,
                    width=options.width,
                    height=options.height,
                    title=options.title,
                )
            ]

        with open(path.with_suffix(".cast"), mode="w", encoding="utf8") as file:
            file.writelines(output)

    except FileNotFoundError as x:
        konsole.critical('Unable to find file "%s"', x.filename)
    except Exception as x:
        konsole.critical("Something went badly wrong: %s", str(x), exc_info=x)


main()

import konsole

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from .animator import InvalidPragma
from .perform import perform


def create_parser() -> ArgumentParser:
    parser = ArgumentParser(
        prog="ascii-fx",
        description="Turn a Python script into a simulated interactive session. The "
        "resulting asciicast is written to the current working directory by default.",
    )

    parser.add_argument(
        "input",
        help="Select the Python script to convert.",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Adjust overall speed by multiplying delays between events by value.",
    )
    parser.add_argument(
        "--keypress-speed",
        type=float,
        default=1.0,
        help="Adjust speed of keystrokes by multiplying delay between them by value.",
    )
    parser.add_argument(
        "--width",
        default=80,
        type=int,
        help="Set the asciicast terminal width.",
    )
    parser.add_argument(
        "--height", default=35, type=int, help="Set the asciicast terminal height."
    )
    parser.add_argument("--title", type=str, help="Set the asciicast title.")
    parser.add_argument(
        "-o",
        "--out",
        dest="output",
        help="Provide the path to the resulting asciicast.",
    )

    return parser


def main() -> None:
    parser = create_parser()
    options = parser.parse_args()

    if not options.title:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        options.title = f'Created by ascii-fx on {now} from "{options.input}"'

    try:
        input_path = Path(options.input).resolve()

        with open(input_path, mode="r", encoding="utf8") as file:
            output = [
                *perform(
                    file,
                    speed=options.speed,
                    keypress_speed=options.keypress_speed,
                    width=options.width,
                    height=options.height,
                    title=options.title,
                )
            ]

        if options.output:
            output_path = Path(options.output).resolve()
        else:
            output_path = Path.cwd() / input_path.with_suffix(".cast").name

        with open(output_path, mode="w", encoding="utf8") as file:
            file.writelines(output)

    except FileNotFoundError as x:
        konsole.critical('Unable to find file "%s"', x.filename)
    except InvalidPragma as x:
        konsole.critical(x.args[0])
    except Exception as x:
        konsole.critical('Unexpected error: %s', str(x), exc_info=x)
    else:
        konsole.info('Successfully created "%s"', output_path)


main()

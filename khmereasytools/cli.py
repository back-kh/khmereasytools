"""UTF-8 stdin/file interface with machine-readable reports."""

import argparse
import json
import sys

from . import __version__
from .segmentation import khseg_spans
from .text_quality import khaudit, khdigits, khnormalize


def _jsonable(value):
    if hasattr(value, "_asdict"):
        return {key: _jsonable(item) for key, item in value._asdict().items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspect and prepare Khmer text locally.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    for command in ("audit", "normalize", "digits", "segment"):
        subparser = commands.add_parser(command)
        subparser.add_argument("file", nargs="?", default="-", help="UTF-8 file, or - for stdin")
        if command == "normalize":
            subparser.add_argument("--zero-width-space", choices=("preserve", "space", "remove"), default="preserve")
            subparser.add_argument("--digits", choices=("preserve", "ascii", "khmer"), default="preserve")
            subparser.add_argument("--collapse-spaces", action="store_true")
            subparser.add_argument("--strip", action="store_true")
            subparser.add_argument("--keep-bom", action="store_true")
            subparser.add_argument("--keep-newlines", action="store_true")
            subparser.add_argument("--remove-inherent-vowels", action="store_true")
            subparser.add_argument("--text-only", action="store_true", help="Emit cleaned text instead of a JSON edit report")
        elif command == "digits":
            subparser.add_argument("--target", choices=("ascii", "khmer"), default="ascii")
        elif command == "segment":
            subparser.add_argument("--word", action="append", default=[], help="Add a domain word; repeat as needed")
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.file == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            # Do not let universal newline conversion erase source offsets.
            with open(args.file, encoding="utf-8", newline="") as handle:
                text = handle.read()
        if args.command == "audit":
            result = khaudit(text)
        elif args.command == "segment":
            result = khseg_spans(text, custom_words=args.word)
        elif args.command == "digits":
            result = khdigits(text, target=args.target)
        else:
            result = khnormalize(
                text, zero_width_space=args.zero_width_space, digits=args.digits,
                collapse_spaces=args.collapse_spaces, strip=args.strip,
                remove_bom=not args.keep_bom,
                normalize_newlines=not args.keep_newlines,
                remove_inherent_vowels=args.remove_inherent_vowels,
            )
            if args.text_only:
                result = result.text
        if not isinstance(result, str):
            result = json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n"
        sys.stdout.buffer.write(result.encode("utf-8"))
        return 0
    except (OSError, UnicodeError) as exc:
        print("khmereasytools: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

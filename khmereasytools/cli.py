"""UTF-8 stdin/file interface with machine-readable reports."""

import argparse
import json
import sys

from . import __version__
from .segmentation import khseg_spans
from .tagging import khtag
from .ocr import OCRError, khocr_overlay
from .documents import khanalyze
from .search import khsearch
from .translation import TranslationError, khtranslate
from .local_model import LocalModel, LocalModelError
from .rag import khrag
from .sentences import khsentences
from .extraction import khextract
from .processing import khprocess
from .diagnostics import khdoctor
from .text_quality import khaudit, khdigits, khnormalize


def _jsonable(value):
    if hasattr(value, "_asdict"):
        return {key: _jsonable(item) for key, item in value._asdict().items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _local_model(args):
    if args.model is None:
        if args.base_url is not None:
            raise ValueError("--base-url requires an explicit --model")
        return None
    options = {"timeout": args.timeout}
    if args.base_url is not None:
        options["base_url"] = args.base_url
    return LocalModel(args.model, **options)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Everyday Khmer text, search, and document tools.")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    for command in ("audit", "normalize", "digits", "segment", "tag", "sentences", "extract",
                    "process", "doctor", "ocr", "search", "rag", "translate"):
        aliases = {"ocr": ["ket-ocr"], "tag": ["ket-tagger"]}
        subparser = commands.add_parser(command, aliases=aliases.get(command, []))
        if command == "doctor":
            subparser.add_argument("--json", action="store_true", help="Print a machine-readable setup report")
            subparser.add_argument("--require", action="append", default=[],
                                   choices=("core", "ocr", "pdf", "pos", "translation"),
                                   help="Exit with an error if this feature is not configured; repeat as needed")
        elif command == "process":
            subparser.add_argument("file", help="UTF-8 text, image or PDF to process locally")
            subparser.add_argument("--json", action="store_true", help="Include sentences, tokens, entities and diagnostics")
            subparser.add_argument("--pages", help="PDF page numbers, e.g. 1,2")
            subparser.add_argument("--lang", help="OCR language, e.g. khm+eng")
            subparser.add_argument("--date-order", choices=("DMY", "MDY"),
                                   help="Explicit order for ambiguous dates (default: leave unresolved)")
        elif command == "ocr":
            subparser.add_argument("file", help="Image or PDF to read locally")
            subparser.add_argument("--layout", action="store_true", help="Return page layout and Khmer diagnostics as JSON")
            subparser.add_argument("--pages", help="PDF page numbers, e.g. 1,2 (default: all pages)")
            subparser.add_argument("--lang", default="khm", help="OCR language, e.g. khm+eng for mixed text")
            subparser.add_argument("--psm", type=int, default=3, help=argparse.SUPPRESS)
            subparser.add_argument("--timeout", type=float, default=60.0, help=argparse.SUPPRESS)
            subparser.add_argument("--min-confidence", type=float, default=0.0, help=argparse.SUPPRESS)
            subparser.add_argument("--preprocess", choices=("auto", "none", "grayscale", "threshold"), default="auto", help=argparse.SUPPRESS)
            subparser.add_argument("--reading-order", choices=("engine", "columns"), default="engine", help=argparse.SUPPRESS)
            subparser.add_argument("--frame", type=int, default=None, help=argparse.SUPPRESS)
            subparser.add_argument("--no-segment", action="store_true", help=argparse.SUPPRESS)
            subparser.add_argument("--overlay", help="Write a line-box review PNG (image input only)")
        elif command in ("search", "rag"):
            subparser.add_argument("query", help="Khmer or Latin search terms")
            subparser.add_argument("files", nargs="+", help="UTF-8 text files to search locally")
            subparser.add_argument("--limit", type=int, default=3 if command == "rag" else 5)
            if command == "search":
                subparser.add_argument("--all", action="store_true", help="Require every query term")
            else:
                subparser.add_argument("--model", help="Installed local Ollama model; omit for retrieval only")
                subparser.add_argument("--base-url", help="Local Ollama origin (default: http://127.0.0.1:11434)")
                subparser.add_argument("--timeout", type=float, default=120.0)
        else:
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
            subparser.add_argument("--dictionary", choices=("expanded", "legacy"), default="expanded")
            subparser.add_argument("--strategy", choices=("frequency", "coverage", "longest"), default="frequency")
        elif command == "tag":
            subparser.add_argument("--term", action="append", default=[], metavar="WORD=TAG",
                                   help="Local POS override, e.g. និមល=PROPN; repeat as needed")
        elif command == "translate":
            subparser.add_argument("--to", dest="target", default="en", help="Target language code (default: en)")
            subparser.add_argument("--from", dest="source", default="km", help="Source language code, or auto (default: km)")
            subparser.add_argument("--timeout", type=float, default=30.0)
            subparser.add_argument("--model", help="Use an installed local Ollama model instead of Google")
            subparser.add_argument("--base-url", help="Local Ollama origin (default: http://127.0.0.1:11434)")
        elif command == "extract":
            subparser.add_argument("--kind", action="append", choices=("url", "email", "phone", "date", "number"),
                                   help="Return only this kind; repeat as needed")
            subparser.add_argument("--date-order", choices=("DMY", "MDY"))
    args = parser.parse_args(argv)
    if args.command == "ket-ocr":
        args.command = "ocr"
    elif args.command == "ket-tagger":
        args.command = "tag"
    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "doctor":
            report = khdoctor()
            if args.json:
                output = json.dumps(_jsonable(report), ensure_ascii=False, indent=2) + "\n"
            else:
                lines = ["Khmer Easy Tools {} | Python {} | {}".format(report.version, report.python, report.platform)]
                for check in report.checks:
                    lines.append("{}: {} — {}".format(check.name, check.status, check.message))
                    if check.hint:
                        lines.append("  " + check.hint)
                output = "\n".join(lines) + "\n"
            sys.stdout.buffer.write(output.encode("utf-8"))
            return 2 if any(check.name in args.require and check.status not in ("ready", "configured")
                            for check in report.checks) else 0
        if args.command == "process":
            options = {"lang": args.lang} if args.lang is not None else {}
            selected = [int(page.strip()) for page in args.pages.split(",")] if args.pages is not None else None
            report = khprocess(args.file, pages=selected, date_order=args.date_order, **options)
            output = (json.dumps(_jsonable(report), ensure_ascii=False, indent=2) + "\n") if args.json else report.text
            sys.stdout.buffer.write(output.encode("utf-8"))
            return 0
        if args.command in ("search", "rag"):
            documents = {}
            for path in args.files:
                with open(path, encoding="utf-8", newline="") as handle:
                    documents[path] = handle.read()
            if args.command == "rag":
                model = _local_model(args)
                hits = khrag(args.query, documents, limit=args.limit, generator=model)
            else:
                hits = khsearch(args.query, documents, limit=args.limit, match="all" if args.all else "any")
            sys.stdout.buffer.write((json.dumps(_jsonable(hits), ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            return 0
        if args.command == "ocr":
            selected = [int(page.strip()) for page in args.pages.split(",")] if args.pages is not None else None
            options = dict(lang=args.lang, psm=args.psm, timeout=args.timeout,
                           min_confidence=args.min_confidence, preprocess=args.preprocess,
                           reading_order=args.reading_order, segment=args.layout and not args.no_segment)
            if args.frame is not None:
                options["frame"] = args.frame
            result = khanalyze(args.file, pages=selected, **options)
            if args.overlay:
                if result.source_type != "image":
                    raise ValueError("--overlay takes image input; PDF geometry is available with --layout")
                khocr_overlay(args.file, result.pages[0].layout, args.overlay, frame=args.frame or 0)
            output = (json.dumps(_jsonable(result), ensure_ascii=False, indent=2) + "\n") if args.layout else result.text
            sys.stdout.buffer.write(output.encode("utf-8"))
            return 0
        if args.file == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            # Do not let universal newline conversion erase source offsets.
            with open(args.file, encoding="utf-8", newline="") as handle:
                text = handle.read()
        if args.command == "audit":
            result = khaudit(text)
        elif args.command == "segment":
            result = khseg_spans(text, custom_words=args.word, dictionary=args.dictionary, strategy=args.strategy)
        elif args.command == "tag":
            lexicon = {}
            for term in args.term:
                if "=" not in term:
                    raise ValueError("--term must have the form WORD=TAG, e.g. និមល=PROPN")
                word, label = term.rsplit("=", 1)
                lexicon[word] = label
            result = khtag(text, with_spans=True, lexicon=lexicon)
        elif args.command == "sentences":
            result = khsentences(text, with_spans=True)
        elif args.command == "extract":
            result = khextract(text, kinds=args.kind, date_order=args.date_order)
        elif args.command == "digits":
            result = khdigits(text, target=args.target)
        elif args.command == "translate":
            model = _local_model(args)
            result = khtranslate(text, target=args.target, source=None if args.source == "auto" else args.source,
                                 timeout=args.timeout, local_model=model)
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
    except (OSError, UnicodeError, ValueError, ImportError, OCRError, TranslationError, LocalModelError) as exc:
        print("khmereasytools: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

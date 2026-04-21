"""CLI entrypoint."""

from __future__ import annotations

import sys

from pykara.errors import (
    DocumentReadError,
    PykaraError,
    ValidationError,
)
from pykara.interfaces.cli.args import build_parser
from pykara.interfaces.cli.pipeline import (
    load_declarations,
    load_document,
    run_engine,
    run_validation,
    write_output,
)


def main() -> int:
    """Run the CLI and return the process exit code.

    Returns:
        Process exit code compatible with shell execution.
    """

    args = build_parser().parse_args()

    try:
        document = load_document(args.input)
        declarations = load_declarations(document)
        report = run_validation(document, declarations)
    except DocumentReadError as error:
        print(
            f"error: could not read '{error.path}': {error}",
            file=sys.stderr,
        )
        return 1
    except PykaraError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if report.has_errors and not args.warn_only:
        for violation in report.errors:
            message = (
                f"[{violation.code}] {violation.message}  ({violation.context})"
            )
            print(
                message,
                file=sys.stderr,
            )
        return 2

    if report.has_errors and args.warn_only:
        for violation in report.errors:
            print(
                f"warning [{violation.code}]: {violation.message}",
                file=sys.stderr,
            )

    for violation in report.warnings:
        print(
            f"warning [{violation.code}]: {violation.message}",
            file=sys.stderr,
        )

    try:
        fx_events = run_engine(
            document,
            declarations,
            seed=args.seed,
            font_dirs=tuple(path.resolve() for path in args.font_dir),
        )
        write_output(document, fx_events, args.output, args.json)
    except ValidationError as error:
        for violation in error.report.errors:
            print(
                f"[{violation.code}] {violation.message}",
                file=sys.stderr,
            )
        return 2
    except PykaraError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"ok: {len(fx_events)} fx line(s) written to '{args.output}'")
    return 0

"""Stable package entrypoint for the current Jeff v1 operator surface."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from jeff import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m jeff",
        description=(
            "Start the current Jeff v1 CLI-first backbone. "
            "This startup path bootstraps an explicit in-memory demo workspace and does not persist state."
        ),
        epilog=(
            "Examples:\n"
            "  python -m jeff --help\n"
            "  python -m jeff --bootstrap-check\n"
            "  python -m jeff --command \"/help\"\n"
            "  python -m jeff --command \"/show run-1\" --json\n"
            "  python -m jeff"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="show the current package version and exit")
    parser.add_argument(
        "--bootstrap-check",
        action="store_true",
        help="run deterministic startup checks and exit",
    )
    parser.add_argument(
        "--command",
        metavar="COMMAND",
        help="run one CLI command against the explicit in-memory demo context and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="render one-shot command output as JSON where the command supports it",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"jeff {__version__}")
        return 0
    if args.json and args.command is None:
        parser.error("--json requires --command")

    try:
        from jeff.bootstrap import build_demo_interface_context, run_startup_preflight
        from jeff.interface import JeffCLI
    except Exception as exc:
        return _print_error(f"startup imports failed: {exc}")

    try:
        checks = run_startup_preflight()
        if args.bootstrap_check:
            print("bootstrap checks passed")
            for check in checks:
                print(f"- {check}")
            print("- startup path uses explicit in-memory demo state only")
            return 0

        context = build_demo_interface_context()
        cli = JeffCLI(context=context)

        if args.command is not None:
            output = cli.run_one_shot(args.command, json_output=args.json)
            if output:
                print(output)
            return 0

        if not sys.stdin.isatty():
            parser.print_help()
            print("\nNo interactive terminal detected. Use --command for one-shot mode.")
            return 0

        return _run_interactive(cli)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    except Exception as exc:
        return _print_error(str(exc))


def _run_interactive(cli) -> int:
    from jeff.interface.render import color_enabled, format_error_text, format_hint_text, format_info_text, format_prompt_text

    use_stdout_color = color_enabled(stream_isatty=sys.stdout.isatty())
    use_stderr_color = color_enabled(stream_isatty=sys.stderr.isatty())

    print(format_info_text("Jeff v1 interactive shell", use_color=use_stdout_color))
    print(format_info_text("Startup bootstrapped an explicit in-memory demo workspace with no persistence.", use_color=use_stdout_color))
    print(format_hint_text("This shell is command-driven. Use slash commands like /help or /project list.", use_color=use_stdout_color))
    print(format_hint_text("Plain text is not a supported command surface. Type 'exit' or 'quit' to leave.", use_color=use_stdout_color))

    while True:
        try:
            command_line = input(f"{format_prompt_text(cli.prompt, use_color=use_stdout_color)} ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            return 130

        normalized = command_line.strip()
        if not normalized:
            continue
        if normalized in {"exit", "quit"}:
            return 0

        try:
            output = cli.run_one_shot(normalized)
        except Exception as exc:
            print(format_error_text(str(exc), use_color=use_stderr_color), file=sys.stderr)
            continue
        if output:
            print(output)


def _print_error(message: str) -> int:
    from jeff.interface.render import color_enabled, format_error_text

    print(format_error_text(message, use_color=color_enabled(stream_isatty=sys.stderr.isatty())), file=sys.stderr)
    return 2

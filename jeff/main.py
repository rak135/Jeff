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
            "This startup path loads or initializes a persisted runtime workspace under .jeff_runtime/. "
            "Local runtime config in jeff.runtime.toml enables the bounded repo-local validation /run objective path and research commands."
        ),
        epilog=(
            "Examples:\n"
            "  python -m jeff --help\n"
            "  python -m jeff --bootstrap-check\n"
            "  python -m jeff --reset-runtime --bootstrap-check\n"
            "  python -m jeff --command \"/help\"\n"
            "  python -m jeff --project project-1 --work wu-1 --command \"/run list\" --json\n"
            "  python -m jeff\n"
            "\n"
            "PowerShell quoting:\n"
            "  In PowerShell, inner quotes in --command need backtick escaping:\n"
            '  python -m jeff --command "/research docs `"`"summary`"`" README.md"\n'
            "\n"
            "Console script:\n"
            "  After pip install -e . the jeff entry point is available as a bare command.\n"
            "  Without the install, use python -m jeff."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="store_true", help="show the current package version and exit")
    parser.add_argument(
        "--bootstrap-check",
        action="store_true",
        help="run deterministic startup checks and report runtime, /run, research, and memory status",
    )
    parser.add_argument(
        "--reset-runtime",
        action="store_true",
        help="delete the local .jeff_runtime workspace and rebuild it on next startup",
    )
    parser.add_argument(
        "--command",
        metavar="COMMAND",
        action="append",
        help="run one CLI command against the persisted runtime context; may be repeated",
    )
    parser.add_argument("--project", metavar="PROJECT_ID", help="set one-shot or startup project scope locally")
    parser.add_argument("--work", metavar="WORK_UNIT_ID", help="set one-shot or startup work_unit scope locally")
    parser.add_argument("--run", metavar="RUN_ID", help="set one-shot or startup run scope locally")
    parser.add_argument(
        "--json",
        action="store_const",
        const=True,
        default=None,
        help="render one-shot command output as JSON where the command supports it",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"jeff {__version__}")
        return 0
    if args.json is True and args.command is None:
        parser.error("--json requires --command")
    if args.work is not None and args.project is None:
        parser.error("--work requires --project")
    if args.run is not None and args.work is None:
        parser.error("--run requires --work")

    try:
        from jeff.bootstrap import build_startup_interface_context, run_startup_preflight
        from jeff.interface import CliSession, JeffCLI, SessionScope
        from jeff.runtime_persistence import PersistedRuntimeStore
    except Exception as exc:
        return _print_error(f"startup imports failed: {exc}")

    try:
        if args.reset_runtime:
            runtime_store = PersistedRuntimeStore.from_base_dir()
            runtime_store.reset_runtime_home()
            print(f"reset local runtime workspace at {runtime_store.home.root_dir}")
        checks = run_startup_preflight()
        if args.bootstrap_check:
            print("bootstrap checks passed")
            for check in checks:
                print(f"- {check}")
            return 0

        context = build_startup_interface_context()
        cli = JeffCLI(
            context=context,
            session=CliSession(
                scope=SessionScope(project_id=args.project, work_unit_id=args.work, run_id=args.run)
            ),
        )

        if args.command is not None:
            outputs: list[str] = []
            for command in args.command:
                output = cli.run_one_shot(command, json_output=args.json)
                if output:
                    outputs.append(output)
            if outputs:
                print("\n".join(outputs))
            return 0

        if not sys.stdin.isatty():
            parser.print_help()
            print(
                "\nNo interactive terminal detected. Use --command for one-shot mode; "
                "/project use, /work use, and /run use stay process-local to this Jeff process."
            )
            print('Example: python -m jeff --project project-1 --work wu-1 --command "/run list" --json')
            return 0

        return _run_interactive(cli)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130
    except Exception as exc:
        return _print_error(str(exc))


def _run_interactive(cli) -> int:
    from jeff.interface.render import color_enabled, format_error_text, format_hint_text, format_info_text, format_prompt_text
    from jeff.cognitive import ResearchOperatorSurfaceError, ResearchSynthesisRuntimeError

    use_stdout_color = color_enabled(stream_isatty=sys.stdout.isatty())
    use_stderr_color = color_enabled(stream_isatty=sys.stderr.isatty())

    print(format_info_text("Jeff v1 interactive shell", use_color=use_stdout_color))
    print(
        format_info_text(
            cli.context.startup_summary
            or "Startup loaded the persisted Jeff runtime workspace.",
            use_color=use_stdout_color,
        )
    )
    if cli.context.infrastructure_services is None:
        print(
            format_info_text(
                "Research runtime config is not loaded; add jeff.runtime.toml to enable research CLI.",
                use_color=use_stdout_color,
            )
        )
    else:
        print(
            format_info_text(
                "Research runtime config loaded from jeff.runtime.toml.",
                use_color=use_stdout_color,
            )
        )
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
            result = cli.execute(
                normalized,
                live_debug_emitter=lambda line: print(line),
            )
            output = result.text
        except (ResearchSynthesisRuntimeError, ResearchOperatorSurfaceError) as exc:
            rendered = cli.render_research_error(exc)
            if cli.session.json_output:
                print(rendered)
            else:
                print(format_error_text(rendered, use_color=use_stderr_color), file=sys.stderr)
            continue
        except Exception as exc:
            print(format_error_text(str(exc), use_color=use_stderr_color), file=sys.stderr)
            continue
        if output:
            print(output)


def _print_error(message: str) -> int:
    from jeff.interface.render import color_enabled, format_error_text

    print(format_error_text(message, use_color=color_enabled(stream_isatty=sys.stderr.isatty())), file=sys.stderr)
    return 2

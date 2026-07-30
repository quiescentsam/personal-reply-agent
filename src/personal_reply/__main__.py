import argparse
import sys

MENUBAR_FLAGS = frozenset({"-v", "--verbose", "-h", "--help"})


def _menubar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m personal_reply",
        description="Launch the Personal Reply menubar app.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print RAG retrieval, mode, and prompt details to the terminal on each suggest",
    )
    return parser


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] not in ("ingest", "suggest", "contacts"):
        args, unknown = _menubar_parser().parse_known_args()
        if unknown:
            _menubar_parser().error(f"unrecognized arguments: {' '.join(unknown)}")
        from personal_reply.menubar import main as menubar_main

        menubar_main(verbose=args.verbose)
        return

    if len(sys.argv) > 1:
        from personal_reply.cli import main as cli_main

        raise SystemExit(cli_main())

    from personal_reply.menubar import main as menubar_main

    menubar_main(verbose=False)


if __name__ == "__main__":
    main()

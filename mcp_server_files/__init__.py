from .server import serve


def main():
    """MCP File Server - lokaler Dateisystemzugriff für MCP-Clients"""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        description="Gibt einem MCP-Client Lesezugriff auf das lokale Dateisystem."
    )
    parser.add_argument(
        "--allowed-dir",
        type=str,
        action="append",
        dest="allowed_dirs",
        metavar="DIR",
        help="Erlaubtes Verzeichnis (kann mehrfach angegeben werden).",
    )

    args = parser.parse_args()
    try:
        asyncio.run(serve(args.allowed_dirs))
    except ValueError as e:
        import sys
        print(f"Fehler: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

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
    asyncio.run(serve(args.allowed_dirs))


if __name__ == "__main__":
    main()

# CLAUDE.md – MCP File Server

## Zweck

MCP-Server, der einer KI (primär LM Studio) Lesezugriff auf das lokale Dateisystem gibt. Kommunikation über das Model Context Protocol (MCP) via stdio.

## Projektstruktur

```
mcp_server_files/               ← Projekt-Root
├── pyproject.toml              ← Package-Metadaten (setuptools, name: mcp-server-files)
├── README.md
├── CLAUDE.md
└── mcp_server_files/           ← Python-Package
    ├── __init__.py             ← main()-Funktion, Argument-Parsing
    ├── __main__.py             ← ermöglicht python -m mcp_server_files
    └── server.py               ← gesamte MCP-Server-Logik
```

## Einstiegspunkte

- `mcp_server_files/__init__.py` – `main()`-Funktion, parsed `--allowed-dir` (mehrfach möglich) via argparse
- `mcp_server_files/__main__.py` – ermöglicht `python -m mcp_server_files`
- `mcp_server_files/server.py` – gesamte MCP-Server-Logik in `serve(allowed_dirs: list[str])`

## Bereitgestellte Tools

| Tool | Eingabe-Parameter | Beschreibung |
|---|---|---|
| `list_directory` | `path` | Inhalt eines Verzeichnisses auflisten |
| `read_file` | `path`, `max_length`, `start_index` | Datei lesen mit Paginierung |
| `directory_tree` | `path`, `max_depth` | Rekursiver Verzeichnisbaum |

## Sicherheitsmodell

`_check_path()` in `server.py` löst jeden Pfad mit `Path.resolve()` auf und prüft, ob er ein Kind eines der `allowed_dirs` ist. Symlinks werden dadurch automatisch aufgelöst. Zugriff außerhalb → `McpError(INVALID_PARAMS)`.

## Abhängigkeiten

Nur `mcp` und `pydantic` werden benötigt (keine externen HTTP-Bibliotheken).

## Typischer Startbefehl

```bash
python -m mcp_server_files --allowed-dir /home/jms/develop --allowed-dir /home/jms/dokumente
```

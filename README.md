# MCP File Server

Ein MCP-Server (Model Context Protocol), der einer KI (z. B. LM Studio) Lesezugriff auf das lokale Dateisystem gibt.

## Funktionen

| Tool | Beschreibung |
|---|---|
| `list_directory` | Listet den Inhalt eines Verzeichnisses (Dateien + Unterordner) auf |
| `read_file` | Liest den Textinhalt einer Datei; unterstützt Paginierung über `start_index` |
| `directory_tree` | Gibt einen rekursiven Verzeichnisbaum als Text aus (konfigurierbare Tiefe) |

Binärdateien werden erkannt und abgelehnt. Zugriffe außerhalb der erlaubten Verzeichnisse werden verweigert (Path-Traversal-Schutz).

## Installation

```bash
pip install mcp
# oder in einem virtualenv:
python -m venv .venv && source .venv/bin/activate
pip install mcp pydantic
```

## Starten

```bash
# Ein Verzeichnis erlauben
python -m mcp_server_files --allowed-dir /home/user/dokumente

# Mehrere Verzeichnisse erlauben
python -m mcp_server_files \
    --allowed-dir /home/user/dokumente \
    --allowed-dir /home/user/projekte
```

## Konfiguration in LM Studio

In LM Studio die Datei `mcp.json` entsprechend befüllen:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": [
        "-m",
        "mcp_server_files",
        "--allowed-dir",
        "/home/user/Documents",
        "--allowed-dir",
        "/home/user/develop"
      ]
    }
  }
}
```

Danach LM Studio neu starten. Die Tools `list_directory`, `read_file` und `directory_tree` stehen der KI automatisch zur Verfügung.

## Sicherheitshinweise

- Der Server gewährt nur **Lesezugriff** – es gibt keine Schreib- oder Löschoperationen.
- Nur Pfade **innerhalb** der per `--allowed-dir` angegebenen Verzeichnisse sind erreichbar.
- Symlinks werden aufgelöst, bevor der Pfad geprüft wird.

## Struktur

```
mcp_server_files/               ← Projekt-Root
├── pyproject.toml
├── README.md
└── mcp_server_files/           ← Python-Package
    ├── __init__.py             ← Einstiegspunkt & Argument-Parsing
    ├── __main__.py             ← Ermöglicht python -m mcp_server_files
    └── server.py               ← MCP-Server-Logik
```

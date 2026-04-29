from pathlib import Path
from typing import Annotated

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import (
    ErrorData,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from pydantic import BaseModel, Field


def _check_path(path: str, allowed_dirs: list[Path]) -> Path:
    """Resolve path and verify it's within an allowed directory."""
    resolved = Path(path).resolve()
    for allowed in allowed_dirs:
        try:
            resolved.relative_to(allowed)
            return resolved
        except ValueError:
            continue
    allowed_str = ", ".join(str(d) for d in allowed_dirs)
    raise McpError(ErrorData(
        code=INVALID_PARAMS,
        message=f"Path '{path}' is outside all allowed directories: {allowed_str}",
    ))


class ListDirectory(BaseModel):
    path: Annotated[str, Field(description="Directory path to list")]


class ReadFile(BaseModel):
    path: Annotated[str, Field(description="File path to read")]
    max_length: Annotated[
        int,
        Field(default=10000, description="Maximum number of characters to return.", gt=0, lt=1000000),
    ]
    start_index: Annotated[
        int,
        Field(default=0, description="Start reading at this character index (for pagination).", ge=0),
    ]


class DirectoryTree(BaseModel):
    path: Annotated[str, Field(description="Root directory path for the tree")]
    max_depth: Annotated[
        int,
        Field(default=3, description="Maximum recursion depth (1 = immediate children only).", gt=0, le=10),
    ]


def _build_tree(path: Path, allowed_dirs: list[Path], depth: int, max_depth: int, prefix: str = "") -> list[str]:
    lines = []
    try:
        entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except PermissionError:
        return [f"{prefix}[Zugriff verweigert]"]

    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        if entry.is_dir():
            lines.append(f"{prefix}{connector}{entry.name}/")
            if depth < max_depth:
                extension = "    " if i == len(entries) - 1 else "│   "
                lines.extend(_build_tree(entry, allowed_dirs, depth + 1, max_depth, prefix + extension))
        else:
            size = entry.stat().st_size
            lines.append(f"{prefix}{connector}{entry.name} ({size} B)")
    return lines


async def serve(allowed_dirs: list[str] | None = None) -> None:
    """Run the filesystem MCP server.

    Args:
        allowed_dirs: List of directory paths the server is allowed to access.
    """
    if not allowed_dirs:
        raise ValueError("Mindestens ein --allowed-dir muss angegeben werden.")

    resolved_dirs = [Path(d).resolve() for d in allowed_dirs]
    for d in resolved_dirs:
        if not d.exists() or not d.is_dir():
            raise ValueError(f"Allowed-Dir existiert nicht oder ist kein Verzeichnis: {d}")

    server = Server("mcp-files")
    dirs_str = ", ".join(str(d) for d in resolved_dirs)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_directory",
                description=(
                    f"Lists the contents (files and subdirectories) of a directory. "
                    f"Allowed directories: {dirs_str}"
                ),
                inputSchema=ListDirectory.model_json_schema(),
            ),
            Tool(
                name="read_file",
                description=(
                    f"Reads the text content of a file. Supports pagination via start_index. "
                    f"Allowed directories: {dirs_str}"
                ),
                inputSchema=ReadFile.model_json_schema(),
            ),
            Tool(
                name="directory_tree",
                description=(
                    f"Returns a recursive directory tree as text. "
                    f"Allowed directories: {dirs_str}"
                ),
                inputSchema=DirectoryTree.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        if name == "list_directory":
            try:
                args = ListDirectory(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            path = _check_path(args.path, resolved_dirs)
            if not path.exists():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Pfad existiert nicht: {path}"))
            if not path.is_dir():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Kein Verzeichnis: {path}"))

            entries = []
            try:
                for entry in sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                    if entry.is_dir():
                        entries.append(f"[DIR]  {entry.name}/")
                    else:
                        entries.append(f"[FILE] {entry.name}  ({entry.stat().st_size} B)")
            except PermissionError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Zugriff verweigert: {e}"))

            text = f"Inhalt von '{path}':\n" + ("\n".join(entries) if entries else "(leer)")
            return [TextContent(type="text", text=text)]

        elif name == "read_file":
            try:
                args = ReadFile(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            path = _check_path(args.path, resolved_dirs)
            if not path.exists():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Datei existiert nicht: {path}"))
            if not path.is_file():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Kein reguläre Datei: {path}"))

            try:
                raw = path.read_bytes()
            except OSError as e:
                raise McpError(ErrorData(code=INTERNAL_ERROR, message=f"Lesefehler: {e}"))

            # Detect binary files
            if b"\x00" in raw[:8192]:
                raise McpError(ErrorData(
                    code=INVALID_PARAMS,
                    message=f"'{path}' ist eine Binärdatei und kann nicht als Text gelesen werden.",
                ))

            content = raw.decode("utf-8", errors="replace")
            original_length = len(content)

            if args.start_index >= original_length:
                text = "<error>Kein weiterer Inhalt verfügbar.</error>"
            else:
                chunk = content[args.start_index:args.start_index + args.max_length]
                text = f"Inhalt von '{path}':\n{chunk}"
                remaining = original_length - (args.start_index + len(chunk))
                if len(chunk) == args.max_length and remaining > 0:
                    next_start = args.start_index + len(chunk)
                    text += (
                        f"\n\n<error>Inhalt abgeschnitten. "
                        f"Rufe read_file mit start_index={next_start} auf, um mehr zu erhalten.</error>"
                    )

            return [TextContent(type="text", text=text)]

        elif name == "directory_tree":
            try:
                args = DirectoryTree(**arguments)
            except ValueError as e:
                raise McpError(ErrorData(code=INVALID_PARAMS, message=str(e)))

            path = _check_path(args.path, resolved_dirs)
            if not path.exists():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Pfad existiert nicht: {path}"))
            if not path.is_dir():
                raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Kein Verzeichnis: {path}"))

            lines = [str(path) + "/"]
            lines.extend(_build_tree(path, resolved_dirs, depth=1, max_depth=args.max_depth))
            return [TextContent(type="text", text="\n".join(lines))]

        else:
            raise McpError(ErrorData(code=INVALID_PARAMS, message=f"Unbekanntes Tool: {name}"))

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)

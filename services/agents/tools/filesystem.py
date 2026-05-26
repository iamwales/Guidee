from pathlib import Path

# Sandboxed to user home Guidee folder in production
ALLOWED_ROOT = Path.home() / "Guidee"


def _safe_path(path: str) -> Path:
    resolved = (ALLOWED_ROOT / path).resolve()
    if not str(resolved).startswith(str(ALLOWED_ROOT.resolve())):
        raise PermissionError("Path outside allowed directory")
    return resolved


async def read_file(path: str) -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"error": f"File not found: {path}"}
    content = p.read_text(encoding="utf-8", errors="replace")
    return {"path": str(p), "content": content[:50000]}


async def write_file(path: str, content: str) -> dict:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "written": len(content)}


async def list_directory(path: str = ".") -> dict:
    p = _safe_path(path)
    if not p.is_dir():
        return {"error": "Not a directory"}
    entries = [
        {"name": e.name, "is_dir": e.is_dir()}
        for e in sorted(p.iterdir())[:100]
    ]
    return {"path": str(p), "entries": entries}

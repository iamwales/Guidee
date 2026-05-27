import csv
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from config import get_settings

TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".log", ".py", ".js", ".ts"}
SPREADSHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def allowed_roots() -> list[Path]:
    settings = get_settings()
    roots = []
    for raw in settings.file_agent_allowed_roots.split(","):
        raw = raw.strip()
        if not raw:
            continue
        roots.append(Path(raw).expanduser().resolve())
    return roots or [(Path.home() / "Guidee").resolve()]


def safe_path(path: str) -> Path:
    candidate = Path(path).expanduser()
    roots = allowed_roots()
    if not candidate.is_absolute():
        candidate = roots[0] / candidate
    resolved = candidate.resolve()
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise PermissionError("Path outside allowed file-agent roots")
    return resolved


def file_type(path: Path) -> str:
    return path.suffix.lower().lstrip(".") or "text"


async def read_file(path: str) -> dict:
    try:
        p = safe_path(path)
    except PermissionError as exc:
        return {"error": str(exc), "path": path}

    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}
    if p.stat().st_size > get_settings().file_agent_max_read_bytes:
        return {"error": "File exceeds maximum read size", "path": str(p)}

    try:
        content = extract_text(p)
    except Exception as exc:
        return {"error": str(exc), "path": str(p), "type": file_type(p)}

    return {
        "path": str(p),
        "type": file_type(p),
        "content": content[:50000],
        "truncated": len(content) > 50000,
    }


async def write_file(
    path: str,
    content: str,
    confirmed: bool = False,
    overwrite: bool = False,
) -> dict:
    try:
        p = safe_path(path)
    except PermissionError as exc:
        return {"error": str(exc), "path": path}

    exists = p.exists()
    if exists and not overwrite:
        return {
            "error": "File exists; set overwrite=true to replace it",
            "path": str(p),
        }
    if exists and overwrite and not confirmed:
        return {
            "error": "confirmation_required",
            "message": "Overwriting a file requires confirmation",
            "path": str(p),
        }

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "written": len(content), "overwritten": exists}


async def edit_file(
    path: str,
    find: str,
    replace: str,
    confirmed: bool = False,
) -> dict:
    if not confirmed:
        return {
            "error": "confirmation_required",
            "message": "Editing a file requires confirmation",
            "path": path,
        }
    existing = await read_file(path)
    if existing.get("error"):
        return existing
    text = existing.get("content", "")
    if find not in text:
        return {"error": "Text to replace was not found", "path": existing["path"]}
    updated = text.replace(find, replace, 1)
    return await write_file(existing["path"], updated, confirmed=True, overwrite=True)


async def list_directory(path: str = ".") -> dict:
    try:
        p = safe_path(path)
    except PermissionError as exc:
        return {"error": str(exc), "path": path}
    if not p.is_dir():
        return {"error": "Not a directory", "path": str(p)}
    entries = [
        {
            "name": entry.name,
            "is_dir": entry.is_dir(),
            "type": file_type(entry),
            "size": entry.stat().st_size if entry.is_file() else None,
        }
        for entry in sorted(p.iterdir())[:100]
    ]
    return {"path": str(p), "entries": entries}


async def summarize_file(path: str) -> dict:
    data = await read_file(path)
    if data.get("error"):
        return data
    content = data.get("content", "")
    sentences = re.split(r"(?<=[.!?])\s+", content.strip())
    summary = " ".join(sentences[:5]) if sentences else content[:1000]
    return {**data, "summary": summary[:2000]}


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".csv":
        return extract_csv(path)
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".xlsx":
        return extract_xlsx(path)
    if ext == ".pdf":
        return extract_pdf(path)
    raise ValueError(f"Unsupported file type: {ext or 'unknown'}")


def extract_csv(path: Path) -> str:
    rows = []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        for idx, row in enumerate(reader):
            if idx >= 200:
                break
            rows.append("\t".join(row))
    return "\n".join(rows)


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        texts = [node.text or "" for node in paragraph.iter(f"{WORD_NS}t")]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def extract_xlsx(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        shared = read_shared_strings(archive)
        sheet_names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        )
        lines = []
        for sheet_name in sheet_names[:3]:
            root = ElementTree.fromstring(archive.read(sheet_name))
            lines.append(f"# {Path(sheet_name).stem}")
            for row in root.iter(f"{SPREADSHEET_NS}row"):
                values = [
                    cell_value(cell, shared)
                    for cell in row.iter(f"{SPREADSHEET_NS}c")
                ]
                if any(values):
                    lines.append("\t".join(values))
    return "\n".join(lines)


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
    values = []
    for item in root.iter(f"{SPREADSHEET_NS}si"):
        text = "".join(
            node.text or "" for node in item.iter(f"{SPREADSHEET_NS}t")
        )
        values.append(text)
    return values


def cell_value(cell: ElementTree.Element, shared: list[str]) -> str:
    value = cell.find(f"{SPREADSHEET_NS}v")
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        index = int(value.text)
        return shared[index] if index < len(shared) else ""
    return value.text


def extract_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ValueError("Install pypdf to read PDF files") from exc
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages[:20])


def format_tool_result(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)

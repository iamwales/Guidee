import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

spec = importlib.util.spec_from_file_location(
    "guidee_filesystem",
    SERVICE_ROOT / "tools" / "filesystem.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Unable to load filesystem module")
filesystem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(filesystem)


class FileSettings:
    def __init__(self, root: Path):
        self.file_agent_allowed_roots = str(root)
        self.file_agent_max_read_bytes = 5_000_000


class FilesystemTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.settings_patch = patch.object(
            filesystem,
            "get_settings",
            return_value=FileSettings(self.root),
        )
        self.settings_patch.start()

    def tearDown(self):
        self.settings_patch.stop()
        self.tmp.cleanup()

    async def test_reads_text_markdown_and_csv(self):
        (self.root / "note.md").write_text("# Title\nBody", encoding="utf-8")
        (self.root / "data.csv").write_text("name,value\nGuidee,1\n", encoding="utf-8")

        markdown = await filesystem.read_file("note.md")
        csv_data = await filesystem.read_file("data.csv")

        self.assertIn("# Title", markdown["content"])
        self.assertIn("Guidee\t1", csv_data["content"])

    async def test_reads_docx_and_xlsx_without_optional_dependencies(self):
        self._write_docx(self.root / "sample.docx", "Hello from docx")
        self._write_xlsx(self.root / "sample.xlsx", "Guidee")

        docx = await filesystem.read_file("sample.docx")
        xlsx = await filesystem.read_file("sample.xlsx")

        self.assertIn("Hello from docx", docx["content"])
        self.assertIn("Guidee", xlsx["content"])

    async def test_blocks_paths_outside_sandbox(self):
        result = await filesystem.read_file("../outside.txt")

        self.assertIn("outside allowed", result["error"])

    async def test_overwrite_and_edit_require_confirmation(self):
        (self.root / "note.txt").write_text("before", encoding="utf-8")

        overwrite = await filesystem.write_file(
            "note.txt",
            "after",
            overwrite=True,
        )
        edit = await filesystem.edit_file("note.txt", "before", "after")

        self.assertEqual(overwrite["error"], "confirmation_required")
        self.assertEqual(edit["error"], "confirmation_required")

    async def test_summarize_file_returns_short_summary(self):
        (self.root / "note.txt").write_text(
            "First sentence. Second sentence. Third sentence.",
            encoding="utf-8",
        )

        result = await filesystem.summarize_file("note.txt")

        self.assertIn("First sentence.", result["summary"])

    def _write_docx(self, path: Path, text: str) -> None:
        document = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>"
            "</w:document>"
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", document)

    def _write_xlsx(self, path: Path, text: str) -> None:
        shared = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<si><t>{text}</t></si>"
            "</sst>"
        )
        sheet = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetData><row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData>'
            "</worksheet>"
        )
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("xl/sharedStrings.xml", shared)
            archive.writestr("xl/worksheets/sheet1.xml", sheet)


if __name__ == "__main__":
    unittest.main()

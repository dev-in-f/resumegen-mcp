import io
import os
from datetime import datetime
from importlib import resources
from pathlib import Path

import pypdfium2 as pdfium
import yaml
from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from resumegen._cli.shared import _load_yaml_to_data_model
from resumegen._core.config import Config, ResumeData
from resumegen._core.pdf import render_pdf

WORKSPACE = Path(os.getenv("RESUMEGEN_DATA_DIR", "/data"))
MASTER_DATA_PATH = Path(
    os.getenv("RESUMEGEN_MASTER_DATA_PATH", "/data/master-resume.yaml")
)
TAILORED_YAML_PATH = Path(os.getenv("RESUMEGEN_TAILORED_YAML_PATH", "/data/tailored/"))
mcp = MCPServer(
    "resumegen",
    instructions="Read the master resume data,"
    " build ResumeData using ONLY facts from it,"
    " call render_resume, fix any errors, then offer preview_resume. "
    "Never invent employers, titles, dates, or credentials",
)
TEXT_EXTS = {
    ".json",
    ".yaml",
    ".yml",
    ".html",
}
EXTS = TEXT_EXTS | {".pdf"}
MAX_BITES = 5_000_000
READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, open_world_hint=False)


def safe_path(name, exts=EXTS, must_exist=True):
    path = (WORKSPACE / name).resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ToolError("Path is outside of workspace.")
    if path.suffix not in exts:
        raise ToolError(f"Allowed types: {sorted(exts)}")
    if must_exist and not path.exists():
        raise ToolError(f"Not found: {name}. Try list_files")
    return path


def rel(path: Path) -> str:
    return path.relative_to(WORKSPACE).as_posix()


def contained(path: Path) -> Path:
    p = path.resolve()
    if not p.is_relative_to(WORKSPACE):
        raise ToolError("Path is outside of workspace.")
    return p


def load_config() -> Config:
    config_path = os.getenv("RESUMEGEN_CONFIG_PATH")
    if config_path:
        with contained(Path(config_path)).open() as f:
            data = yaml.safe_load(f)
            return _load_yaml_to_data_model(data, Config)
    return Config()


def iso(timestamp: float) -> str:
    tz = datetime.now().astimezone().tzinfo
    return datetime.fromtimestamp(timestamp, tz=tz).isoformat()


def render_preview(pdf_path: Path, page: int = 0, dpi: int = 300) -> tuple[bytes, int]:
    """Render one PDF page as an image and return the PNG bytes and total pages."""
    pdf = pdfium.PdfDocument(pdf_path)
    total_pages = len(pdf)
    if not 0 <= page < total_pages:
        raise ToolError(f"Page {page} out of range (0-{total_pages - 1}).")
    page_bitmap = pdf[page].render(scale=dpi / 72)  # type: ignore
    buffer = io.BytesIO()
    page_bitmap.to_pil().save(buffer, format="PNG")
    return buffer.getvalue(), total_pages


@mcp.tool(annotations=READ_ONLY)
def get_master_resume_data() -> CallToolResult:
    """Retrieve the master resume data (the only source of truth for tailoring)"""
    text = safe_path(MASTER_DATA_PATH).read_text()
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=yaml.safe_load(text),
    )


@mcp.tool(annotations=READ_ONLY)
def list_files(subdir: str = "") -> list[dict]:
    """List workspace files: name (relative), size, modified time."""
    base = contained(WORKSPACE / subdir)
    return [
        {"name": rel(f), "size": f.stat().st_size, "modified": iso(f.stat().st_mtime)}
        for f in sorted(base.rglob("*"))
        if f.suffix in EXTS
    ]


@mcp.tool(annotations=READ_ONLY)
def read_file(name: str) -> str:
    """Read a text file (YAML/JSON/HTML). For PDFs use preview_resume."""
    path = safe_path(name)
    if path.stat().st_size > MAX_BITES:
        raise ToolError(f"File too large: {name}")
    return path.read_text()


@mcp.tool(annotations=WRITE)
def render_resume(
    resume_data: ResumeData,
    output_file: str,
    dry_run: bool = False,
) -> CallToolResult:
    """Render ResumeData to an accessible PDF in the workspace.
    Validation errors come back automatically: fix the named fields and retry."""
    config = load_config()
    pdf_path, report = render_pdf(
        resume_data,
        config.output_dir,
        output_file,
        config.template_name,
        config.template_dir,
        dry_run,
    )
    return CallToolResult(
        content=[TextContent(type="text", text=str(pdf_path))],
        structured_content={"report": report.get_report_string() if report else None},
    )


@mcp.tool(annotations=WRITE)
def save_tailored_yaml(resume_data: ResumeData, output_file: str) -> CallToolResult:
    """Save the tailored resume data to the designated YAML path."""
    output_path = TAILORED_YAML_PATH / output_file
    with output_path.open("w") as f:
        resume_data_dict = resume_data.model_dump()
        f.write(yaml.safe_dump(resume_data_dict))
    return CallToolResult(
        content=[TextContent(type="text", text=str(output_path))],
        structured_content={"path": str(output_path)},
    )


@mcp.tool(annotations=READ_ONLY)
def preview_resume(pdf_path: str, page: int = 0, dpi: int = 300) -> list:
    """Render one PDF page as an image to check layout."""
    png_bytes, total_pages = render_preview(
        safe_path(pdf_path, {".pdf"}), page=page, dpi=dpi
    )
    return [Image(data=png_bytes, format="png"), f"Page {page} of {total_pages}"]


@mcp.resource("resumegen://schema/resume-data", mime_type="application/json")
def resume_schema():
    return resources.read_text("resumegen", "schemas/resume-data.json")


@mcp.resource("resumegen://master-resume-data", mime_type="application/yaml")
def master_resume_data():
    with MASTER_DATA_PATH.open() as f:
        return f.read()


@mcp.resource("resumegen://files/{+path}")
def workspace_file(path: str) -> str | bytes:
    """Any workspace file; PDFs are returned as blobs"""
    try:
        p = safe_path(path)
    except ToolError as e:
        raise ResourceError(str(e)) from e
    if p.suffix == ".pdf":
        return p.read_bytes()
    return p.read_bytes() if p.suffix == ".pdf" else p.read_text()


if __name__ == "__main__":
    mcp.run(transport="stdio")

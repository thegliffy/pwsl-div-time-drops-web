"""FastAPI web UI for PWSL Time Drop Finder."""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from app.time_drops_core import event_number, generate_labels_pdf, process_file

MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="PWSL Time Drop Finder", version="1.0.0")


def sanitize_filename(raw: str | None) -> str:
    """Force a safe .pdf-terminated base name (no path components)."""
    name = (raw or "").strip()
    name = Path(name).name if name else "time_drop_labels"
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    name = SAFE_NAME_RE.sub("_", name).strip("._")
    return name or "time_drop_labels"


def cleanup_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/generate")
async def generate(
    file: UploadFile = File(...),
    min_drop: float = Form(1.0),
    filename: str = Form("time_drop_labels"),
):
    if min_drop < 0:
        raise HTTPException(status_code=400, detail="Minimum time drop must be 0 or greater.")

    original_name = file.filename or "upload.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a PDF file (Meet Maestro Personal Best / Improvement labels).",
        )

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a PDF.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).",
        )

    work_dir = Path(tempfile.mkdtemp(prefix="pwsl-time-drops-"))
    upload_path = work_dir / "upload.pdf"
    out_name = sanitize_filename(filename)
    out_path = work_dir / f"{out_name}.pdf"

    try:
        upload_path.write_bytes(data)
        results = process_file(upload_path, min_drop)

        if not results:
            cleanup_dir(work_dir)
            return JSONResponse(
                status_code=400,
                content={
                    "detail": (
                        f"No qualifying swims found with a drop of {min_drop}s or more "
                        "in that file."
                    ),
                    "count": 0,
                },
            )

        results.sort(key=lambda r: (event_number(r["event"]), r["name"]))
        generate_labels_pdf(results, out_path)

        return FileResponse(
            path=out_path,
            media_type="application/pdf",
            filename=f"{out_name}.pdf",
            headers={"X-Qualifying-Count": str(len(results))},
            background=BackgroundTask(cleanup_dir, work_dir),
        )
    except ValueError as exc:
        cleanup_dir(work_dir)
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    except Exception as exc:
        cleanup_dir(work_dir)
        raise HTTPException(status_code=500, detail=f"Something went wrong: {exc}") from exc


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

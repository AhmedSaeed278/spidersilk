"""FastAPI entrypoint."""

from __future__ import annotations

import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__, s3_client
from .config import Settings, get_settings
from .csv_parser import CsvParseError, parse_all

logger = logging.getLogger("spidersilk")

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


def _seed_public_assets(settings: Settings) -> None:
    """Copy bundled static assets into the shared volume mounted at PUBLIC_DIR.

    Nginx (sidecar) serves /static/* from this directory. This is how the two
    containers cooperate via a single shared emptyDir volume.
    """
    src = PACKAGE_DIR / "static"
    dst = Path(settings.public_dir) / "static"
    try:
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target = dst / item.name
            if target.exists():
                continue
            shutil.copy2(item, target)
        logger.info("Seeded public assets into %s", dst)
    except OSError as exc:
        logger.warning("Could not seed public assets to %s: %s", dst, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=get_settings().log_level)
    _seed_public_assets(get_settings())
    yield


app = FastAPI(
    title="Spidersilk CSV Service",
    version=__version__,
    lifespan=lifespan,
)


# When running outside the cluster (no shared volume), fall back to the package static dir.
_fallback_static = PACKAGE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(_fallback_static)), name="static")


@app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
def healthz() -> str:
    return "ok"


@app.get("/readyz", response_class=PlainTextResponse, include_in_schema=False)
def readyz() -> str:
    return "ready"


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"version": __version__},
    )


@app.get("/files", response_class=HTMLResponse)
def list_files(request: Request) -> HTMLResponse:
    try:
        objects = s3_client.list_objects(limit=200)
    except Exception as exc:
        logger.exception("Listing S3 failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return TEMPLATES.TemplateResponse(
        request,
        "list.html",
        {"objects": objects, "bucket": get_settings().s3_bucket},
    )


@app.post("/upload", response_class=HTMLResponse)
async def upload(
    request: Request,
    file: Annotated[UploadFile, File(...)],
) -> HTMLResponse:
    settings = get_settings()

    if file.content_type and file.content_type not in settings.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content type: {file.content_type}",
        )

    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    if len(body) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size ({settings.max_upload_bytes} bytes)",
        )

    try:
        rows = parse_all(body)
    except CsvParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    safe_name = Path(file.filename or "upload.csv").name
    ts = datetime.now(UTC).strftime("%Y/%m/%d/%H%M%S")
    key = f"{settings.s3_prefix}{ts}-{uuid.uuid4().hex[:8]}-{safe_name}"
    try:
        s3_client.put_object(key, body, content_type="text/csv")
    except Exception as exc:
        logger.exception("S3 upload failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return TEMPLATES.TemplateResponse(
        request,
        "view.html",
        {
            "rows": rows,
            "key": key,
            "filename": safe_name,
            "row_count": len(rows),
        },
    )


@app.exception_handler(HTTPException)
async def _http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def run() -> None:
    """Entrypoint for `spidersilk` console script (used in Dockerfile CMD)."""
    import uvicorn

    uvicorn.run(
        "spidersilk.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=get_settings().log_level.lower(),
    )

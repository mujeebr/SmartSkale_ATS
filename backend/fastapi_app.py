"""FastAPI endpoints for the resume–JD matching service."""

from __future__ import annotations

from typing import Annotated, Any, Dict
from fastapi.middleware.cors import CORSMiddleware

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.openapi.utils import get_openapi

from src.container import get_resume_matching_service

app = FastAPI(title="Resume Matcher API (FastAPI)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:3000", "https://your-frontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _custom_openapi() -> Dict[str, Any]:
    """Return a patched OpenAPI schema so Swagger renders file uploads correctly."""
    if app.openapi_schema:
        return app.openapi_schema  # type: ignore[return-value]

    schema = get_openapi(title=app.title, version="1.0.0", routes=app.routes)

    try:
        body_schema_ref = schema["paths"]["/match-files"]["post"]["requestBody"][
            "content"
        ]["multipart/form-data"]["schema"]["$ref"]
        name = body_schema_ref.split("/")[-1]
        comp = schema["components"]["schemas"][name]
        files_items = comp["properties"]["files"]["items"]
        files_items["format"] = "binary"
        files_items.pop("contentMediaType", None)
    except Exception:
        pass

    app.openapi_schema = schema  # type: ignore[assignment]
    return schema  # type: ignore[return-value]


app.openapi = _custom_openapi  # type: ignore[assignment]


@app.get("/health")
def health() -> dict:
    """Simple health-check endpoint used for uptime and readiness probes."""
    return {"status": "ok"}


@app.post("/match")
async def match(
    jd_text: Annotated[str, Form(...)],
    resume_text: Annotated[str, Form(...)],
) -> dict:
    """Evaluate a single resume provided as plain text against a job description."""
    svc = get_resume_matching_service()
    return svc.match_text(jd_text=jd_text, resume_text=resume_text)


@app.post("/match-files")
async def match_files(
    jd_text: Annotated[str, Form(...)],
    files: Annotated[list[UploadFile], File(...)],
) -> list[dict]:
    """Evaluate one or more uploaded resume files against a job description."""
    svc = get_resume_matching_service()
    pairs: list[tuple[str, bytes]] = [(f.filename, await f.read()) for f in files]
    return svc.match_files(jd_text=jd_text, files=pairs)

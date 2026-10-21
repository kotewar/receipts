"""The demo page: the report a client receives, and the receipts behind it."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .page import PAGE

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "demo.json"

app = FastAPI(title="Receipts")


@app.get("/api/report")
def report() -> dict:
    if not DEMO.exists():
        raise HTTPException(503, "No demo run built. Run scripts/build_demo.py first.")
    return json.loads(DEMO.read_text())


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE

import os
import time
import asyncio
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Contador Instagram API — 1+")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Estado global ──────────────────────────────────────────
_cache: dict = {}
_clients: list = []
_current_count: int = 0
_current_username: str = ""
POLL_INTERVAL = 10  # segundos entre consultas a Instagram

# ── Instagram Graph API ────────────────────────────────────
def fetch_followers_from_api() -> dict:
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Configura ACCESS_TOKEN en Railway.")
    url = f"https://graph.instagram.com/me?fields=followers_count,username&access_token={token}"
    res

import os
import time
import asyncio
import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Contador Instagram API 1+")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_cache = {}
_clients = []
_current_count = 0
_current_username = ""
POLL_INTERVAL = 10


def fetch_followers_from_api():
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Configura ACCESS_TOKEN en Railway.")
    url = f"https://graph.instagram.com/me?fields=followers_count,username&access_token={token}"
    response = requests.get(url, timeout=10)
    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=500, detail=f"Error Instagram API: {data['error']['message']}")
    return {"followers_count": data["followers_count"], "username": data["username"]}


async def broadcast(count):
    global _current_count
    _current_count = count
    dead = []
    for queue in _clients:
        try:
            await queue.put(count)
        except Exception:
            dead.append(queue)
    for q in dead:
        _clients.remove(q)


async def poll_instagram():
    global _current_count, _current_username
    while True:
        try:
            data = fetch_followers_from_api()
            new_count = data["followers_count"]
            _current_username = data["username"]
            _cache["data"] = {"data": data, "timestamp": time.time()}
            if new_count != _current_count:
                await broadcast(new_count)
            _current_count = new_count
        except Exception as e:
            print(f"[Poll] Error: {e}")
        await asyncio.sleep(POLL_INTERVAL)


@app.on_event("startup")
async def startup():
    asyncio.create_task(poll_instagram())


@app.get("/followers")
def get_followers():
    if _current_count:
        return {
            "followers_count": _current_count,
            "username": _current_username,
            "cached": True,
            "timestamp": int(time.time())
        }
    data = fetch_followers_from_api()
    return {**data, "cached": False, "timestamp": int(time.time())}


@app.get("/stream")
async def stream(request: Request):
    queue = asyncio.Queue()
    _clients.append(queue)

    async def event_generator():
        yield f"data: {_current_count}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    count = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {count}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            if queue in _clients:
                _clients.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.get("/webhook")
async def webhook_verify(request: Request):
    params = dict(request.query_params)
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "1mas_webhook_token")
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == verify_token:
        return int(params["hub.challenge"])
    raise HTTPException(status_code=403, detail="Token invalido")


@app.post("/webhook")
async def webhook_receive(request: Request):
    return {"status": "ok"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "contador-1mas",
        "clients": len(_clients),
        "count": _current_count,
        "username": _current_username
    }


@app.get("/", response_class=HTMLResponse)
def dashboard():
    token = os.getenv("ACCESS_TOKEN", "")
    ready = bool(_current_username and token)
    color = "#00ff88" if ready else "#ff4444"
    text = f"Monitoreando @{_current_username}" if ready else "Configura ACCESS_TOKEN"
    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>1+ Admin</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a0a; color:#f0f0f0; font-family:monospace;
       min-height:100vh; display:flex; align-items:center; justify-content:center; }}
.card {{ background:#141414; border:1px solid #222; border-radius:16px; padding:2rem; width:420px; }}
h1 {{ font-size:1.2rem; margin-bottom:1rem; }}
.status {{ display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; margin-bottom:1rem; }}
.dot {{ width:8px; height:8px; border-radius:50%; background:{color}; }}
.row {{ font-size:0.75rem; color:#555; padding:0.4rem 0; border-bottom:1px solid #1a1a1a; }}
</style></head>
<body><div class="card">
<h1>1+ Panel de Admin</h1>
<div class="status"><div class="dot"></div><span>{text}</span></div>
<div class="row">GET /followers</div>
<div class="row">GET /stream</div>
<div class="row">GET /health</div>
</div></body></html>"""
    return HTMLResponse(content=html)

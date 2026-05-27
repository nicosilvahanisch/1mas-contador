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
CACHE_TTL = 60
_clients: list = []          # conexiones SSE activas
_current_count: int = 0      # último follower count conocido

# ── Instagram Graph API ────────────────────────────────────
def fetch_followers_from_api() -> dict:
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Configura ACCESS_TOKEN en Railway.")
    url = f"https://graph.instagram.com/me?fields=followers_count,username&access_token={token}"
    response = requests.get(url)
    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=500, detail=f"Error Instagram API: {data['error']['message']}")
    return {"followers_count": data["followers_count"], "username": data["username"]}


# ── Notificar a todos los clientes SSE ────────────────────
async def broadcast(count: int):
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


# ── Endpoints ─────────────────────────────────────────────

@app.get("/followers")
def get_followers():
    """Endpoint clásico con caché — para el ESP32 y consultas manuales."""
    now = time.time()
    cached = _cache.get("data")
    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return {**cached["data"], "cached": True, "timestamp": int(cached["timestamp"])}
    data = fetch_followers_from_api()
    _cache["data"] = {"data": data, "timestamp": now}
    return {**data, "cached": False, "timestamp": int(now)}


@app.get("/stream")
async def stream(request: Request):
    """SSE — el demo HTML se conecta acá y recibe updates en tiempo real."""
    queue: asyncio.Queue = asyncio.Queue()
    _clients.append(queue)

    async def event_generator():
        # Enviar el count actual inmediatamente al conectarse
        yield f"data: {_current_count}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    count = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {count}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive cada 30s para que Railway no cierre la conexión
                    yield ": keepalive\n\n"
        finally:
            if queue in _clients:
                _clients.remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/webhook")
async def webhook_receive(request: Request):
    """Meta envía aquí los eventos cuando alguien sigue la cuenta."""
    body = await request.json()

    # Meta manda un array de 'entry' con cambios
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "followers_count":
                new_count = change["value"].get("followers_count")
                if new_count is not None:
                    await broadcast(new_count)
                    # Actualizar caché también
                    _cache["data"] = {
                        "data": {"followers_count": new_count, "username": os.getenv("IG_TARGET_USERNAME", "")},
                        "timestamp": time.time()
                    }

    return {"status": "ok"}


@app.get("/webhook")
async def webhook_verify(request: Request):
    """Meta verifica el endpoint con un GET antes de activar el webhook."""
    params = dict(request.query_params)
    verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "1mas_webhook_token")

    if (params.get("hub.mode") == "subscribe" and
            params.get("hub.verify_token") == verify_token):
        return int(params["hub.challenge"])

    raise HTTPException(status_code=403, detail="Token inválido")


@app.get("/health")
def health():
    return {"status": "ok", "service": "contador-1mas", "clients": len(_clients), "count": _current_count}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    target = os.getenv("IG_TARGET_USERNAME", "")
    token = os.getenv("ACCESS_TOKEN", "")
    ready = bool(target and token)
    status_color = "#00ff88" if ready else "#ff4444"
    status_text = f"Monitoreando @{target} ✓" if ready else "Configura ACCESS_TOKEN e IG_TARGET_USERNAME"
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>1+ Admin</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; color:#f0f0f0; font-family:monospace;
         min-height:100vh; display:flex; align-items:center; justify-content:center; }}
  .card {{ background:#141414; border:1px solid #222; border-radius:16px; padding:2rem; width:420px; }}
  h1 {{ font-size:1.2rem; margin-bottom:1rem; }}
  .status {{ display:flex; align-items:center; gap:0.5rem; font-size:0.8rem; margin-bottom:1rem; }}
  .dot {{ width:8px; height:8px; border-radius:50%; background:{status_color}; }}
  .row {{ font-size:0.75rem; color:#555; padding:0.4rem 0; border-bottom:1px solid #1a1a1a; }}
</style></head>
<body><div class="card">
  <h1>1+ Panel de Admin</h1>
  <div class="status"><div class="dot"></div><span>{status_text}</span></div>
  <div class="row">GET /followers — follower count con caché</div>
  <div class="row">GET /stream — SSE tiempo real</div>
  <div class="row">GET/POST /webhook — webhook Meta</div>
  <div class="row">GET /health — estado del servicio</div>
</div></body></html>""")

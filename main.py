import os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI(title="Contador Instagram API — 1+")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict = {}
CACHE_TTL = 60


def get_followers_graph_api() -> dict:
    token = os.getenv("ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Configura ACCESS_TOKEN en Railway.")

    url = f"https://graph.instagram.com/me?fields=followers_count,username&access_token={token}"
    response = requests.get(url)
    data = response.json()

    if "error" in data:
        raise HTTPException(status_code=500, detail=f"Error Instagram API: {data['error']['message']}")

    return {
        "followers_count": data["followers_count"],
        "username": data["username"],
    }


@app.get("/followers")
def get_followers():
    now = time.time()
    cached = _cache.get("data")

    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return {**cached["data"], "cached": True, "timestamp": int(cached["timestamp"])}

    data = get_followers_graph_api()
    _cache["data"] = {"data": data, "timestamp": now}
    return {**data, "cached": False, "timestamp": int(now)}


@app.get("/health")
def health():
    return {"status": "ok", "service": "contador-1mas"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    target = os.getenv("IG_TARGET_USERNAME", "")
    token = os.getenv("ACCESS_TOKEN", "")
    ready = bool(target and token)
    status_color = "#00ff88" if ready else "#ff4444"
    status_text = f"Monitoreando @{target} ✓" if ready else "Configura ACCESS_TOKEN e IG_TARGET_USERNAME"
    return HTMLResponse(content=f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>1+ Contador Instagram</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:#0a0a0a; color:#f0f0f0; font-family:'Inter',sans-serif;
         min-height:100vh; display:flex; align-items:center; justify-content:center; padding:2rem; }}
  .card {{ background:#141414; border:1px solid #222; border-radius:16px; padding:2.5rem; width:100%; max-width:500px; }}
  h1 {{ font-size:1.6rem; font-weight:600; margin-bottom:0.5rem; }}
  .status {{ display:flex; align-items:center; gap:0.6rem; background:#1a1a1a;
             border:1px solid #222; border-radius:8px; padding:0.8rem 1rem; margin:1.5rem 0; font-size:0.85rem; }}
  .dot {{ width:8px; height:8px; border-radius:50%; background:{status_color}; box-shadow:0 0 8px {status_color}; }}
  .test-btn {{ display:block; width:100%; padding:0.9rem; background:#1e3a2e; color:#00ff88;
               border:1px solid #00ff8833; border-radius:8px; font-size:0.8rem; cursor:pointer; }}
  #result {{ margin-top:1rem; padding:1rem; background:#0d1f17; border:1px solid #1a3329;
             border-radius:8px; font-size:0.8rem; color:#00ff88; display:none; white-space:pre; }}
</style>
</head>
<body>
<div class="card">
  <h1>1+ Contador Instagram</h1>
  <div class="status"><div class="dot"></div><span>{status_text}</span></div>
  <button class="test-btn" onclick="test()">▶ TEST → /followers</button>
  <div id="result"></div>
</div>
<script>
async function test() {{
  const el = document.getElementById('result');
  el.style.display = 'block';
  el.textContent = 'Consultando...';
  try {{
    const r = await fetch('/followers');
    el.textContent = JSON.stringify(await r.json(), null, 2);
  }} catch(e) {{ el.textContent = 'Error: ' + e.message; }}
}}
</script>
</body>
</html>""")

import os
import time
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Contador Instagram API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Cache simple en memoria: {token: {count, timestamp}}
_cache: dict = {}
CACHE_TTL = 60  # segundos entre consultas a Instagram


def get_followers_from_instagram(access_token: str) -> dict:
    """Consulta Instagram Graph API y retorna seguidores + nombre de cuenta."""
    url = "https://graph.instagram.com/me"
    params = {
        "fields": "followers_count,username",
        "access_token": access_token,
    }
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(url, params=params)
            data = r.json()

        if "error" in data:
            code = data["error"].get("code", 0)
            msg = data["error"].get("message", "Error desconocido")
            if code in (190, 102):
                raise HTTPException(status_code=401, detail=f"Token inválido o expirado: {msg}")
            raise HTTPException(status_code=400, detail=f"Error de Instagram API: {msg}")

        return {
            "followers_count": data.get("followers_count", 0),
            "username": data.get("username", ""),
        }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout al consultar Instagram. Reintenta.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@app.get("/followers")
def get_followers(token: str = None):
    """
    Retorna el número de seguidores.
    
    - Si se pasa ?token=TU_TOKEN usa ese token.
    - Si no, usa el token del entorno (ACCESS_TOKEN).
    
    Respuesta: {"followers_count": 1234, "username": "micafe", "cached": false, "timestamp": 1234567890}
    """
    access_token = token or os.getenv("ACCESS_TOKEN")
    if not access_token:
        raise HTTPException(
            status_code=400,
            detail="No hay token configurado. Pasa ?token=TU_TOKEN o configura ACCESS_TOKEN en Railway."
        )

    now = time.time()
    cached = _cache.get(access_token)

    if cached and (now - cached["timestamp"]) < CACHE_TTL:
        return {**cached["data"], "cached": True, "timestamp": int(cached["timestamp"])}

    data = get_followers_from_instagram(access_token)
    _cache[access_token] = {"data": data, "timestamp": now}

    return {**data, "cached": False, "timestamp": int(now)}


@app.get("/health")
def health():
    """Endpoint de salud para Railway."""
    return {"status": "ok", "service": "contador-instagram"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Mini dashboard de administración."""
    token = os.getenv("ACCESS_TOKEN", "")
    has_token = bool(token)
    return HTMLResponse(content=render_dashboard(has_token))


def render_dashboard(has_token: bool) -> str:
    status_color = "#00ff88" if has_token else "#ff4444"
    status_text = "Token configurado ✓" if has_token else "Sin token — configura ACCESS_TOKEN en Railway"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contador Instagram — Admin</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;600&display=swap');
  
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  
  body {{
    background: #0a0a0a;
    color: #f0f0f0;
    font-family: 'Inter', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }}

  .card {{
    background: #141414;
    border: 1px solid #222;
    border-radius: 16px;
    padding: 2.5rem;
    width: 100%;
    max-width: 500px;
    box-shadow: 0 0 60px rgba(0,0,0,0.5);
  }}

  .logo {{
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.2em;
    color: #666;
    text-transform: uppercase;
    margin-bottom: 2rem;
  }}

  h1 {{
    font-size: 1.6rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #fff 60%, #888);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}

  .subtitle {{ color: #555; font-size: 0.9rem; margin-bottom: 2rem; }}

  .status {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    background: #1a1a1a;
    border: 1px solid #222;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    margin-bottom: 1.5rem;
    font-size: 0.85rem;
  }}

  .dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {status_color};
    box-shadow: 0 0 8px {status_color};
    flex-shrink: 0;
  }}

  .endpoints {{ margin-top: 1.5rem; }}
  .endpoints h2 {{ font-size: 0.7rem; letter-spacing: 0.15em; color: #444; text-transform: uppercase; margin-bottom: 0.8rem; }}

  .endpoint {{
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid #1a1a1a;
    font-size: 0.85rem;
  }}

  .method {{
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    background: #1e3a2e;
    color: #00ff88;
    flex-shrink: 0;
  }}

  .path {{ color: #ccc; font-family: 'Space Mono', monospace; font-size: 0.8rem; }}
  .desc {{ color: #555; font-size: 0.8rem; margin-left: auto; }}

  .test-btn {{
    display: block;
    width: 100%;
    margin-top: 1.5rem;
    padding: 0.9rem;
    background: #1e3a2e;
    color: #00ff88;
    border: 1px solid #00ff8833;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
    letter-spacing: 0.05em;
  }}
  .test-btn:hover {{ background: #2a5040; border-color: #00ff8866; }}

  #result {{
    margin-top: 1rem;
    padding: 1rem;
    background: #0d1f17;
    border: 1px solid #1a3329;
    border-radius: 8px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: #00ff88;
    display: none;
    white-space: pre;
    overflow-x: auto;
  }}

  .footer {{ margin-top: 2rem; font-size: 0.75rem; color: #333; text-align: center; }}
</style>
</head>
<body>
<div class="card">
  <div class="logo">● Contador Instagram</div>
  <h1>Panel de Admin</h1>
  <p class="subtitle">Backend API — Estado del servicio</p>

  <div class="status">
    <div class="dot"></div>
    <span>{status_text}</span>
  </div>

  <div class="endpoints">
    <h2>Endpoints disponibles</h2>
    <div class="endpoint">
      <span class="method">GET</span>
      <span class="path">/followers</span>
      <span class="desc">Retorna seguidores</span>
    </div>
    <div class="endpoint">
      <span class="method">GET</span>
      <span class="path">/followers?token=XXX</span>
      <span class="desc">Con token custom</span>
    </div>
    <div class="endpoint">
      <span class="method">GET</span>
      <span class="path">/health</span>
      <span class="desc">Estado del servicio</span>
    </div>
  </div>

  <button class="test-btn" onclick="testEndpoint()">▶ TEST → /followers</button>
  <div id="result"></div>
</div>

<div class="footer">Contador Instagram · by Nico Silva · Santiago, Chile</div>

<script>
async function testEndpoint() {{
  const el = document.getElementById('result');
  el.style.display = 'block';
  el.textContent = 'Consultando...';
  try {{
    const r = await fetch('/followers');
    const data = await r.json();
    el.textContent = JSON.stringify(data, null, 2);
  }} catch(e) {{
    el.textContent = 'Error: ' + e.message;
  }}
}}
</script>
</body>
</html>"""

# Contador Instagram — Backend

Backend API que retorna el número de seguidores de Instagram en tiempo real.
Stack: Python + FastAPI + Railway.

---

## Endpoints

| Método | URL | Descripción |
|--------|-----|-------------|
| GET | `/followers` | Retorna seguidores (usa token del entorno) |
| GET | `/followers?token=XXX` | Retorna seguidores con token custom |
| GET | `/health` | Estado del servicio |
| GET | `/` | Panel de administración |

### Ejemplo de respuesta `/followers`
```json
{
  "followers_count": 1234,
  "username": "micafeteria",
  "cached": false,
  "timestamp": 1714320000
}
```

---

## Cómo correr localmente

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar token
cp .env.example .env
# Edita .env y pon tu ACCESS_TOKEN real

# 3. Correr servidor
uvicorn main:app --reload
```

Abre http://localhost:8000

---

## Deploy en Railway

1. Crea cuenta en railway.app (gratis)
2. New Project → Deploy from GitHub → selecciona este repo
3. En Settings → Variables, agrega:
   - `ACCESS_TOKEN` = tu token de Instagram
4. Railway detecta el `Procfile` automáticamente y despliega

Tu URL quedará algo como: `https://contador-instagram-production.up.railway.app`

---

## Cómo obtener el Access Token de Instagram

1. Ve a developers.facebook.com
2. Crea una App → tipo "Business"
3. Agrega producto "Instagram Graph API"
4. En Graph API Explorer, selecciona tu app
5. Permisos necesarios: `instagram_basic`, `pages_read_engagement`
6. Genera token → luego conviértelo a larga duración (60 días):

```
GET https://graph.instagram.com/access_token
  ?grant_type=ig_exchange_token
  &client_id={APP_ID}
  &client_secret={APP_SECRET}
  &access_token={SHORT_TOKEN}
```

---

## Renovación de token

El token dura 60 días. El backend devuelve error 401 cuando expira.
En ese caso el cliente necesita renovar su token y actualizarlo en Railway.

Próximamente: endpoint `/refresh-token` para renovación automática.

---

## Uso desde el dispositivo (ESP32 / Raspberry Pi)

```python
# Python / MicroPython
import urequests  # MicroPython
BACKEND_URL = "https://TU-APP.up.railway.app/followers"
r = urequests.get(BACKEND_URL)
data = r.json()
followers = data["followers_count"]
```

```cpp
// Arduino / ESP32
HTTPClient http;
http.begin("https://TU-APP.up.railway.app/followers");
int httpCode = http.GET();
String payload = http.getString();
// parsear JSON con ArduinoJson
```

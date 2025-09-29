# Izipay Mini Demo (FastAPI + React) — 1 producto

> **Objetivo:** probar el flujo mínimo de pago con Izipay en **sandbox** usando un solo producto. Incluye backend (FastAPI) + frontend (React) y endpoints para **session** y **webhook**.
>
> **Importante:** Los parámetros exactos, nombres de campos y URL base del checkout **varían según el modo de Izipay** (Web-Core embebido vs Redirect). En este demo están como **placeholders** para que pegues los que Izipay te entregue en su panel / docs. El esqueleto ya maneja firma HMAC, idempotencia y webhook.

---

## Estructura del proyecto

```
izipay-mini-demo/
├─ backend/
│  ├─ app/
│  │  └─ main.py
│  ├─ requirements.txt
│  ├─ env.example
│  └─ README.md
└─ frontend/
   ├─ index.html
   ├─ package.json
   ├─ vite.config.js
   ├─ env.example
   └─ src/
      ├─ main.jsx
      └─ App.jsx
```

---

## Cómo correr local

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env && # edita valores
# export $(cat .env | xargs)  # si usas Linux/macOS y shell compatible
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm i
cp env.example .env
npm run dev
```

Abre `http://localhost:5173`.

> Para probar **webhook** real, expón el backend con ngrok / cloudflared y registra `https://<tu-url>/api/payments/webhook` en el panel de Izipay.

---

## Qué debes cambiar para Izipay real (sandbox)

1. **`IZIPAY_CHECKOUT_BASE_URL`** en el `.env` del backend → pon la URL real del **checkout sandbox** que corresponda a tu modalidad (redirect).
2. **Firma `sign()`** → ajusta el **orden y campos** exactamente como exige Izipay (Hash/HMAC).
3. **`returnUrl`** (si tu modalidad lo usa) → agrega el campo en `payload` y/o en la construcción de la URL.
4. **Webhook** → Izipay enviará `code`/`message` y cabeceras de firma; si usa otro header/nombre, actualiza el validador.

---

## Despliegue gratis (sugerido)

* **Backend**: Render (Web Service). Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
* **Frontend**: Vercel. Env: `VITE_API_BASE=https://<tu-backend>.onrender.com`

Registra en Izipay:

* Webhook: `https://<tu-backend>.onrender.com/api/payments/webhook`
* returnUrl: `https://<tu-frontend>.vercel.app/thank-you` (o la ruta que definas).

---

## Notas de seguridad

* **Nunca** pongas claves en el frontend.
* Firma y validación HMAC siempre en el **servidor**.
* El **estado final** de la orden se toma del **webhook**, no del front.

---

¡Listo! Con esto ya puedes crear órdenes, redirigir al checkout y recibir el webhook. Solo te falta pegar los valores reales de Izipay (sandbox) en el `.env` y ajustar la firma/URL según su modalidad.

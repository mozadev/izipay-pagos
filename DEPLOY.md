# Deploy en Render - Izipay Backend

## Pasos para desplegar:

### 1. Subir a GitHub
- Sube este proyecto a GitHub (si no lo has hecho)

### 2. Crear cuenta en Render
- Ve a: https://render.com
- Regístrate con GitHub

### 3. Crear Web Service
- New → Web Service
- Connect GitHub → selecciona tu repo
- Configuración:
  - **Name:** izipay-backend
  - **Environment:** Python 3
  - **Build Command:** `pip install -r backend/requirements.txt`
  - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - **Working Directory:** `backend`

### 4. Variables de Entorno
Configura estas variables en Render:
- `IZIPAY_MERCHANT`: Tu código de comercio
- `IZIPAY_HMAC_KEY`: Tu llave HMAC
- `IZIPAY_CTX_MODE`: TEST (o PRODUCTION)
- `IZIPAY_PAYMENT_URL`: https://secure.micuentaweb.pe/vads-payment/
- `RETURN_URL`: URL de tu frontend/thank-you
- `ALLOWED_ORIGINS`: Dominios permitidos (separados por coma)
- `DB_PATH`: /opt/render/project/src/mini_demo.db

### 5. Deploy
- Click "Create Web Service"
- Render construirá y desplegará tu app
- Obtendrás una URL como: `https://izipay-backend.onrender.com`

### 6. Configurar Webhook en Izipay
- URL del webhook: `https://tu-app.onrender.com/api/payments/webhook`

### 7. Para tu compañero
- `VITE_API_BASE`: `https://tu-app.onrender.com`

## URLs importantes:
- **API Health:** `https://tu-app.onrender.com/api/health`
- **API Docs:** `https://tu-app.onrender.com/docs`
- **Webhook:** `https://tu-app.onrender.com/api/payments/webhook`
- **Orders:** `https://tu-app.onrender.com/api/orders`

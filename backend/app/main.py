import os
import hmac
import hashlib
import base64
import random
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)  # carga backend/.env

# =========================
# ENV
# =========================
MERCHANT_CODE = os.getenv("IZIPAY_MERCHANT", "TEST_SITE")  
HMAC_KEY = os.getenv("IZIPAY_HMAC_KEY", "")               
PAYMENT_URL = os.getenv("IZIPAY_PAYMENT_URL", "https://secure.micuentaweb.pe/vads-payment/")
CTX_MODE = os.getenv("IZIPAY_CTX_MODE", "TEST")
RETURN_URL = os.getenv("RETURN_URL", "http://localhost:5173/thank-you")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
DEBUG_SIGNATURE = os.getenv("DEBUG_SIGNATURE", "0") == "1"

# =========================
# APP
# =========================
app = FastAPI(title="Izipay Mini Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# DB (SQLite simple)
# =========================
DB_PATH = os.getenv("DB_PATH", "./mini_demo.db")
os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    """
    CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY,
        amount INTEGER NOT NULL,
        currency TEXT NOT NULL,
        status TEXT NOT NULL,
        idempotency_key TEXT,
        provider_tx TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
)
conn.commit()

# =========================
# Utils
# =========================
def now_utc_iso() -> str:
    # Usar zona horaria local en lugar de UTC
    return datetime.now().isoformat()

def gen_trans_id() -> str:
    """6 dígitos numéricos (único por día recomendado)."""
    return f"{random.randint(0, 999999):06d}"

def trans_date() -> str:
    """UTC yyyymmddHHMMss."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

# Orden EXACTO requerido por la pasarela (y el error que viste)
VADS_ORDER = [
    "vads_action_mode","vads_amount","vads_ctx_mode","vads_currency",
    "vads_order_id","vads_page_action","vads_payment_config","vads_site_id",
    "vads_trans_date","vads_trans_id","vads_url_return","vads_version",
]

def sign_vads(vads: dict) -> str:
    """
    Firma para pago alojado (V2):
    signature = Base64( HMAC_SHA256(
        key = certificate (HMAC_KEY),
        data = valores(vads_ en VADS_ORDER) unidos con '+'  +  '+' + certificate
    ))
    """
    certificate = HMAC_KEY
    if not certificate:
        raise RuntimeError("Falta IZIPAY_HMAC_KEY (certificate) en .env")

    data = "+".join(str(vads[k]) for k in VADS_ORDER)
    data_to_sign = f"{data}+{certificate}"

    mac = hmac.new(certificate.encode("utf-8"),
                   data_to_sign.encode("utf-8"),
                   hashlib.sha256).digest()
    sig = base64.b64encode(mac).decode("utf-8")

    if DEBUG_SIGNATURE:
        # Útil para comparar con la cadena que muestra el error de Izipay
        print("TO_SIGN =", data_to_sign)
        print("SIGNATURE =", sig)
    return sig

# (placeholder para tu IPN actual; no afecta al pago alojado)
def sign(fields: dict) -> str:
    canonical = "|".join([
        MERCHANT_CODE,
        fields["orderId"],
        str(fields["amount"]),
        fields["currency"],
    ])
    return hmac.new(HMAC_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()

# =========================
# Modelos y producto demo
# =========================
class CreateSessionIn(BaseModel):
    product_id: Optional[str] = None

PRODUCT = {
    "id": "rent-001",
    "name": "Reserva de alquiler (demo)",
    "price": 1500,          # centavos (S/ 15.00)
    "currency": "PEN",
}

# =========================
# Rutas
# =========================
@app.get("/api/health")
def health():
    return {"ok": True, "time": now_utc_iso()}

@app.get("/api/product")
def get_product():
    return PRODUCT

@app.post("/api/payments/session")
def create_payment_session(_: CreateSessionIn):
    import uuid
    order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
    amount = PRODUCT["price"]          # centavos
    currency_num = 604                 # PEN

    # Guarda orden PENDING
    conn.execute(
        "INSERT INTO orders(order_id, amount, currency, status, idempotency_key, provider_tx, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (order_id, amount, "PEN", "PENDING", uuid.uuid4().hex, None, now_utc_iso(), now_utc_iso()),
    )
    conn.commit()

    # Campos mínimos vads_*
    vads = {
        "vads_site_id": MERCHANT_CODE,
        "vads_ctx_mode": CTX_MODE,
        "vads_version": "V2",
        "vads_page_action": "PAYMENT",
        "vads_action_mode": "INTERACTIVE",
        "vads_payment_config": "SINGLE",
        "vads_trans_id": gen_trans_id(),
        "vads_trans_date": trans_date(),
        "vads_amount": amount,
        "vads_currency": currency_num,
        "vads_order_id": order_id,
        "vads_url_return": RETURN_URL,   # puedes añadir url_success/refused/cancel si quieres
    }
    vads["signature"] = sign_vads(vads)

    # El front debe hacer POST (form) a PAYMENT_URL con estos campos
    return {"payment_url": PAYMENT_URL, "vads": vads, "orderId": order_id}

class WebhookBody(BaseModel):
    transactionId: Optional[str] = None
    code: str
    message: Optional[str] = None
    orderId: str
    amount: int
    currency: str

@app.post("/api/payments/webhook")
async def izipay_webhook(request: Request):
    # Log para ver qué está enviando Izipay
    print("=== WEBHOOK RECIBIDO ===")
    print(f"Headers: {dict(request.headers)}")
    print(f"Method: {request.method}")
    
    # Obtener el body como texto para ver el formato real
    body_text = await request.body()
    print(f"Body raw: {body_text}")
    
    # Intentar parsear como form data (Izipay usa form data)
    try:
        form_data = await request.form()
        print(f"Form data: {dict(form_data)}")
        
        # Buscar campos importantes de Izipay
        order_id = form_data.get("vads_order_id") or form_data.get("orderId")
        status = form_data.get("vads_trans_status") or form_data.get("status")
        trans_id = form_data.get("vads_trans_id") or form_data.get("transactionId")
        
        print(f"Order ID: {order_id}")
        print(f"Status: {status}")
        print(f"Transaction ID: {trans_id}")
        
        # Actualizar la orden si encontramos los datos
        if order_id:
            new_status = "SUCCEEDED" if status in ["AUTHORISED", "CAPTURED", "00"] else "FAILED"
            conn.execute(
                "UPDATE orders SET status=?, provider_tx=?, updated_at=? WHERE order_id=?",
                (new_status, trans_id, now_utc_iso(), order_id),
            )
            conn.commit()
            print(f"Orden {order_id} actualizada a {new_status}")
        
    except Exception as e:
        print(f"Error procesando form data: {e}")
    
    print("========================")
    
    return {"ok": True, "message": "Webhook recibido"}

@app.get("/api/orders")
def get_all_orders():
    """Obtiene todas las órdenes de la base de datos"""
    cur = conn.execute(
        "SELECT order_id, amount, currency, status, provider_tx, created_at, updated_at FROM orders ORDER BY created_at DESC"
    )
    rows = cur.fetchall()
    orders = []
    for r in rows:
        orders.append({
            "orderId": r[0],
            "amount": r[1],
            "currency": r[2],
            "status": r[3],
            "provider_tx": r[4],
            "created_at": r[5],
            "updated_at": r[6],
        })
    return {"orders": orders, "total": len(orders)}

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    cur = conn.execute(
        "SELECT order_id, amount, currency, status, provider_tx, created_at, updated_at FROM orders WHERE order_id=?",
        (order_id,),
    )
    r = cur.fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="order not found")
    return {
        "orderId": r[0],
        "amount": r[1],
        "currency": r[2],
        "status": r[3],
        "provider_tx": r[4],
        "created_at": r[5],
        "updated_at": r[6],
    }

# Dev-only: simular webhook
@app.post("/api/dev/simulate-webhook")
def simulate_webhook(orderId: str, ok: bool = True):
    status = "SUCCEEDED" if ok else "FAILED"
    conn.execute(
        "UPDATE orders SET status=?, provider_tx=?, updated_at=? WHERE order_id=?",
        (status, "SIMULATED", now_utc_iso(), orderId),
    )
    conn.commit()
    return {"ok": True, "status": status}

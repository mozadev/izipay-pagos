import os
import hmac
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)  # <- carga backend/.env


# === Env ===
MERCHANT_CODE = os.getenv("IZIPAY_MERCHANT", "TEST_MERCHANT")
HASH_KEY = os.getenv("IZIPAY_HASH_KEY", "CHANGE_ME")
CHECKOUT_BASE_URL = os.getenv("IZIPAY_CHECKOUT_BASE_URL", "https://SET-ME")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# === App ===
app = FastAPI(title="Izipay Mini Demo")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === DB (SQLite super simple) ===
DB_PATH = os.getenv("DB_PATH", "/tmp/mini_demo.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

# === Util ===

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sign(fields: dict) -> str:
    """Firma HMAC-SHA256 sobre un string canónico.
    ⚠️ Ajusta el orden/campos exactamente como exija Izipay para tu modalidad.
    """
    canonical = "|".join([
        MERCHANT_CODE,
        fields["orderId"],
        str(fields["amount"]),
        fields["currency"],
    ])
    return hmac.new(HASH_KEY.encode(), canonical.encode(), hashlib.sha256).hexdigest()


# === Modelos ===
class CreateSessionIn(BaseModel):
    product_id: Optional[str] = None  # demo: ignorado (un solo producto)

# Un solo producto de demo
PRODUCT = {
    "id": "rent-001",
    "name": "Reserva de alquiler (demo)",
    "price": 1500,  # centavos: 1500 = S/ 15.00
    "currency": "PEN",
}


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
    amount = PRODUCT["price"]
    currency = PRODUCT["currency"]

    # guarda orden PENDING
    conn.execute(
        "INSERT INTO orders(order_id, amount, currency, status, idempotency_key, provider_tx, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (order_id, amount, currency, "PENDING", uuid.uuid4().hex, None, now_utc_iso(), now_utc_iso()),
    )
    conn.commit()

    payload = {
        "merchantCode": MERCHANT_CODE,
        "orderId": order_id,
        "amount": amount,
        "currency": currency,
        # añade cualquier otro campo requerido por tu modalidad (descripcion, returnUrl, etc.)
    }
    payload["signature"] = sign({
        "orderId": order_id,
        "amount": amount,
        "currency": currency,
    })

    # En muchas integraciones redirect construirás una URL tipo: base + query
    # ⚠️ Reemplaza CHECKOUT_BASE_URL por la URL real de Izipay (sandbox) que corresponda a tu modalidad.
    from urllib.parse import urlencode

    checkout_url = f"{CHECKOUT_BASE_URL}?" + urlencode({
        "merchantCode": payload["merchantCode"],
        "orderId": payload["orderId"],
        "amount": payload["amount"],
        "currency": payload["currency"],
        "signature": payload["signature"],
    })

    return {
        "orderId": order_id,
        "checkout_url": checkout_url,
        "payload": payload,
    }


class WebhookBody(BaseModel):
    transactionId: Optional[str] = None
    code: str
    message: Optional[str] = None
    orderId: str
    amount: int
    currency: str


@app.post("/api/payments/webhook")
def izipay_webhook(body: WebhookBody, x_signature: Optional[str] = Header(default=None)):
    # valida firma (placeholder: ajusta a la especificación real de Izipay)
    expected = sign({
        "orderId": body.orderId,
        "amount": body.amount,
        "currency": body.currency,
    })
    if not x_signature or not hmac.compare_digest(x_signature, expected):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # determina estado
    status = "SUCCEEDED" if body.code == "00" else "FAILED"

    cur = conn.execute("SELECT order_id FROM orders WHERE order_id=?", (body.orderId,))
    row = cur.fetchone()
    if not row:
        # si no existe, evita 404 para permitir reintentos del IPN, pero registra
        conn.execute(
            "INSERT OR IGNORE INTO orders(order_id, amount, currency, status, idempotency_key, provider_tx, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (body.orderId, body.amount, body.currency, status, None, body.transactionId, now_utc_iso(), now_utc_iso()),
        )
    else:
        conn.execute(
            "UPDATE orders SET status=?, provider_tx=?, updated_at=? WHERE order_id=?",
            (status, body.transactionId, now_utc_iso(), body.orderId),
        )
    conn.commit()

    return {"ok": True}


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


# === Endpoint dev para simular webhook (no usar en prod) ===
@app.post("/api/dev/simulate-webhook")
def simulate_webhook(orderId: str, ok: bool = True):
    code = "00" if ok else "05"
    body = WebhookBody(transactionId="SIMULATED", code=code, message="sim", orderId=orderId, amount=PRODUCT["price"], currency=PRODUCT["currency"])  # type: ignore
    # sin validar firma aquí (solo dev)
    status = "SUCCEEDED" if ok else "FAILED"
    conn.execute(
        "UPDATE orders SET status=?, provider_tx=?, updated_at=? WHERE order_id=?",
        (status, body.transactionId, now_utc_iso(), orderId),
    )
    conn.commit()
    return {"ok": True, "status": status}

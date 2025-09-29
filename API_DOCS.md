# API de Pagos Izipay - Documentación

## Base URL
```
https://izipay-backend.onrender.com
```

## Endpoints

### 1. Crear Sesión de Pago
**POST** `/api/payments/session`

#### Parámetros (opcionales):
```json
{
  "amount": 2500,                    // Monto en centavos (opcional)
  "currency": "PEN",                 // Moneda: PEN, USD, EUR (opcional)
  "description": "Mi producto",      // Descripción (opcional)
  "return_url": "https://mi-sitio.com/thank-you"  // URL de retorno (opcional)
}
```

#### Respuesta:
```json
{
  "payment_url": "https://secure.micuentaweb.pe/vads-payment/",
  "vads": {
    "vads_site_id": "TEST_SITE",
    "vads_ctx_mode": "TEST",
    "vads_version": "V2",
    "vads_page_action": "PAYMENT",
    "vads_action_mode": "INTERACTIVE",
    "vads_payment_config": "SINGLE",
    "vads_trans_id": "123456",
    "vads_trans_date": "20250929120000",
    "vads_amount": 2500,
    "vads_currency": 604,
    "vads_order_id": "ORD-ABC123",
    "vads_url_return": "https://mi-sitio.com/thank-you",
    "signature": "firma_hmac_aqui"
  },
  "orderId": "ORD-ABC123"
}
```

#### Ejemplo de uso:
```javascript
const response = await fetch('https://izipay-backend.onrender.com/api/payments/session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    amount: 2500,        // S/ 25.00
    currency: "PEN",
    description: "Mi producto",
    return_url: "https://mi-sitio.com/thank-you"
  })
});

const data = await response.json();

// Redirigir a Izipay
const form = document.createElement('form');
form.method = 'POST';
form.action = data.payment_url;
Object.entries(data.vads).forEach(([key, value]) => {
  const input = document.createElement('input');
  input.type = 'hidden';
  input.name = key;
  input.value = value;
  form.appendChild(input);
});
document.body.appendChild(form);
form.submit();
```

### 2. Consultar Orden
**GET** `/api/orders/{orderId}`

#### Respuesta:
```json
{
  "orderId": "ORD-ABC123",
  "amount": 2500,
  "currency": "PEN",
  "status": "SUCCEEDED",
  "provider_tx": "617992",
  "created_at": "2025-09-29T21:37:54.612415",
  "updated_at": "2025-09-29T21:39:49.841882"
}
```

### 3. Listar Todas las Órdenes
**GET** `/api/orders`

#### Respuesta:
```json
{
  "orders": [...],
  "total": 1
}
```

### 4. Estado de la API
**GET** `/api/health`

#### Respuesta:
```json
{
  "ok": true,
  "time": "2025-09-29T21:29:46.062297"
}
```

## Valores por Defecto
Si no envías parámetros, se usan estos valores:
- **amount**: 1500 (S/ 15.00)
- **currency**: "PEN"
- **description**: "Reserva de alquiler (demo)"
- **return_url**: "http://localhost:5173/thank-you"

## Monedas Soportadas
- **PEN**: 604 (Soles Peruanos)
- **USD**: 840 (Dólares Americanos)
- **EUR**: 978 (Euros)

## Webhook
El webhook está configurado en:
```
https://izipay-backend.onrender.com/api/payments/webhook
```

## Documentación Interactiva
Visita: https://izipay-backend.onrender.com/docs

import { useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(false)
  const [order, setOrder] = useState(null)

  useEffect(() => {
    fetch(`${API_BASE}/api/product`).then(r => r.json()).then(setProduct)
  }, [])

  const buy = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/payments/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      })
      const data = await res.json()

      // Si el backend devuelve el flujo antiguo (redirect simple)
      if (data.checkout_url) {
        setOrder({ id: data.orderId })
        window.location.href = data.checkout_url
        return
      }

      // Flujo pago alojado (vads-payment): POST con vads_*
      const { payment_url, vads, orderId } = data
      setOrder({ id: orderId })

      const form = document.createElement('form')
      form.method = 'POST'
      form.action = payment_url
      Object.entries(vads).forEach(([k, v]) => {
        const inp = document.createElement('input')
        inp.type = 'hidden'
        inp.name = k
        inp.value = String(v)
        form.appendChild(inp)
      })
      document.body.appendChild(form)
      form.submit()
    } catch (err) {
      console.error(err)
      alert('Error iniciando el pago')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ fontFamily: 'system-ui', padding: 24, maxWidth: 560, margin: '0 auto' }}>
      <h1>Izipay Mini Demo</h1>
      {product && (
        <div style={{border:'1px solid #ddd', borderRadius:12, padding:16}}>
          <h2>{product.name}</h2>
          <p><b>Precio: </b>S/ {(product.price/100).toFixed(2)} {product.currency}</p>
          <button onClick={buy} disabled={loading} style={{padding:'10px 16px', borderRadius:8}}>
            {loading ? 'Creando orden…' : 'Pagar con Izipay'}
          </button>
          {order && <p style={{marginTop:8}}>Order ID: {order.id}</p>}
        </div>
      )}
      <hr />
      <h3>Gracias</h3>
      <p>Tras pagar, Izipay te devolverá al <code>RETURN_URL</code> configurado en el backend.</p>
    </div>
  )
}

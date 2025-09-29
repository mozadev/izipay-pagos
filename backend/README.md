# Backend — FastAPI

## Run local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat env.example | xargs)  # o crea tu .env
uvicorn app.main:app --reload --port 8000
```

# Exponer webhook (opción)
# cloudflared tunnel --url http://localhost:8000

from fastapi import FastAPI
import os
from openai import OpenAI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Strad Mind is alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/mad/handshake")
def mad_handshake():
    """
    Verifica:
    - se a OPENAI_API_KEY está presente
    - se conseguimos falar com a API da OpenAI (lista alguns modelos)
    """
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "where": "server", "error": "OPENAI_API_KEY not set"}

    try:
        client = OpenAI(api_key=key)
        models = client.models.list()
        sample = [m.id for m in models.data[:5]]
        return {
            "ok": True,
            "models": sample,
            "status": "connected",
            "engine": "OpenAI"
        }
    except Exception as e:
        return {"ok": False, "where": "openai", "error": str(e)}

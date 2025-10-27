import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="Strad Mind")

# CORS liberado por enquanto (depois afinamos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Básico ----------
@app.get("/")
def read_root():
    return {"message": "Strad Mind is alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ---------- Handshake OpenAI ----------
@app.get("/mad/handshake")
def mad_handshake():
    """Confere OPENAI_API_KEY e lista alguns modelos."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "where": "server", "error": "OPENAI_API_KEY not set"}

    try:
        client = OpenAI(api_key=key)
        models = client.models.list()
        sample = [m.id for m in models.data[:5]]
        return {"ok": True, "models": sample, "status": "connected", "engine": "OpenAI"}
    except Exception as e:
        return {"ok": False, "where": "openai", "error": str(e)}

# ---------- Chat ----------
class ChatIn(BaseModel):
    message: str
    model: str | None = "gpt-4o-mini"  # pode trocar por "gpt-4o" se quiser

class ChatOut(BaseModel):
    ok: bool
    reply: str | None = None
    model: str | None = None
    error: str | None = None

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    try:
        client = OpenAI(api_key=key)
        comp = client.chat.completions.create(
            model=body.model or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are Strad Mind, a concise helpful assistant."},
                {"role": "user", "content": body.message},
            ],
            temperature=0.4,
        )
        text = comp.choices[0].message.content
        return ChatOut(ok=True, reply=text, model=comp.model)
    except Exception as e:
        # devolve erro legível no JSON
        raise HTTPException(status_code=500, detail=f"openai_error: {e}")

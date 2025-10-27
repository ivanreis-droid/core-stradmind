# core-stradmind/main.py
# Strad Mind — núcleo leve (v1.0.7) com memória curta embutida
# Features: 4Fs (Frame · Friction · Flow · Fact), User Gate (A/B/C/D),
# Masters’ Gate, assinatura "Balance and Drive", Eco Mode, D6.
# Sem dependências exóticas: FastAPI + Uvicorn apenas.

from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime, timezone
import os

# -----------------------------------------------------------------------------
# Configurações simples
# -----------------------------------------------------------------------------
APP_VERSION = "1.0.7"
ECO_MODE = os.getenv("ECO", "true").lower() in ("1", "true", "yes")
APP_NAME = "Strad Mind — Core"
TZ = timezone.utc  # manter UTC internamente; clientes podem converter

# -----------------------------------------------------------------------------
# Memória curta (rotativa) — mínimo necessário para estado vivo
# -----------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(TZ).isoformat()

class ShortMemory(BaseModel):
    # “Memória curta”: última decisão, 1 número, 1 pendência
    last_decision: Optional[str] = None
    last_number: Optional[str] = None
    last_pending: Optional[str] = None
    # carimbos Balance/Drive do frame atual
    balance_gate: Optional[str] = None
    drive_launch: Optional[str] = None
    # rastro simples dos últimos ciclos (limite baixo)
    trail: List[Dict[str, Any]] = Field(default_factory=list, max_items=5)

    def push_trail(self, item: Dict[str, Any]):
        # mantém leve (máx 5)
        self.trail.append(item)
        if len(self.trail) > 5:
            self.trail = self.trail[-5:]

# Estado vivo (em memória)
STATE = {
    "version": APP_VERSION,
    "eco": ECO_MODE,
    "short": ShortMemory(),
    "frame": {
        "id": None,
        "theme": None,
        "angle": None,
        "mood": None,
        "rhythm": "⚡",
        "opened_at": None,
        "closed_at": None,
        "status": "idle",  # idle|open|in_friction|in_flow|in_fact|closed
    },
    "friction": {
        # item em avaliação na Friction
        "idea_id": None,
        "idea": None,
        "provisional_status": "🔵",  # 🔵/🟡/🟢
        "evidence_refs": [],
        "user_gate": None,  # A|B|C|D
        "follow_up_questions": [],
        "transformation": None,  # blue_to_yellow
    },
    "masters_gate": {
        "facts_verified": None,
        "feasible": None,
        "within_frame": None,
        "notes": None,
        "friction_gate": None,  # passed|failed|bypassed_by_user
        "checked_at": None,
    },
    "d6": None,  # última decisão em 6
}

# -----------------------------------------------------------------------------
# Modelos de entrada/saída
# -----------------------------------------------------------------------------
class FrameOpenIn(BaseModel):
    theme: str = Field(..., description="Tema do frame")
    angle: str = Field("Conceito", description="Ângulo/Lente")
    mood: str = Field("leve", description="Clima")
    rhythm: str = Field("⚡", description="Ritmo (⚡/⬆️)")

class FrictionIn(BaseModel):
    idea_id: str
    idea: str
    evidence_refs: Optional[List[str]] = Field(default_factory=list)

class UserGateIn(BaseModel):
    choice: Literal["A", "B", "C", "D"]  # Verify | Park | Discard | Bypass

class MastersGateIn(BaseModel):
    facts_verified: bool
    feasible: bool
    within_frame: bool
    notes: Optional[str] = None

class FlowIn(BaseModel):
    coherence_note: Optional[str] = None

class FactIn(BaseModel):
    acceptance_criterion: str

class D6Out(BaseModel):
    semaphore: str  # 🔵/🟡/🟢
    decision: str
    reasons: List[str]
    next_actions: List[Dict[str, str]]  # [{"acao": "...", "dono":"...", "quando":"..."}]
    user_gate: Literal["A", "B", "C", "D"]
    masters_gate: Literal["Passed", "Bypassed"]
    stamped_at: str

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------
app = FastAPI(title=APP_NAME, version=APP_VERSION)

# -----------------------------------------------------------------------------
# Utilidades internas
# -----------------------------------------------------------------------------
def set_balance():
    STATE["short"].balance_gate = now_iso()

def set_drive():
    STATE["short"].drive_launch = now_iso()

def reset_friction():
    STATE["friction"].update({
        "idea_id": None,
        "idea": None,
        "provisional_status": "🔵",
        "evidence_refs": [],
        "user_gate": None,
        "follow_up_questions": [],
        "transformation": None,
    })
    STATE["masters_gate"].update({
        "facts_verified": None,
        "feasible": None,
        "within_frame": None,
        "notes": None,
        "friction_gate": None,
        "checked_at": None,
    })

def eco_filter(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not STATE["eco"]:
        return payload
    # no Eco Mode, devolve só o essencial
    keys = ["ok", "stage", "semaphore", "time", "frame_id", "hint"]
    return {k: payload.get(k) for k in keys if k in payload}

# -----------------------------------------------------------------------------
# Básicos
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "name": APP_NAME,
        "version": APP_VERSION,
        "eco": STATE["eco"],
        "time": now_iso(),
        "stage": STATE["frame"]["status"],
    }

@app.get("/v1/state")
def get_state():
    # endpoint completo (sem corte eco) para debug/observabilidade leve
    out = {
        "version": STATE["version"] if "version" in STATE else APP_VERSION,
        "eco": STATE["eco"],
        "time": now_iso(),
        "frame": STATE["frame"],
        "short": STATE["short"].model_dump(),
        "friction": STATE["friction"],
        "masters_gate": STATE["masters_gate"],
        "d6": STATE["d6"],
    }
    return out

@app.post("/v1/reset")
def reset_all():
    global STATE
    mem = ShortMemory()
    STATE = {
        "version": APP_VERSION,
        "eco": ECO_MODE,
        "short": mem,
        "frame": {
            "id": None, "theme": None, "angle": None, "mood": None,
            "rhythm": "⚡", "opened_at": None, "closed_at": None, "status": "idle"
        },
        "friction": {
            "idea_id": None, "idea": None, "provisional_status": "🔵",
            "evidence_refs": [], "user_gate": None, "follow_up_questions": [],
            "transformation": None,
        },
        "masters_gate": {
            "facts_verified": None, "feasible": None, "within_frame": None,
            "notes": None, "friction_gate": None, "checked_at": None,
        },
        "d6": None,
    }
    return {"ok": True, "stage": "idle", "time": now_iso()}

# -----------------------------------------------------------------------------
# 4Fs — Frame
# -----------------------------------------------------------------------------
@app.post("/v1/frame/open")
def open_frame(data: FrameOpenIn):
    if STATE["frame"]["status"] in ("open", "in_friction", "in_flow", "in_fact"):
        # fecha o anterior com Balance se estava aberto
        STATE["frame"]["closed_at"] = now_iso()
        set_balance()
        STATE["frame"]["status"] = "closed"
        STATE["short"].push_trail({
            "type": "frame_close_auto",
            "at": STATE["frame"]["closed_at"],
            "theme": STATE["frame"]["theme"],
        })
    # abre novo + Drive
    frame_id = f"frame-{datetime.now(TZ).strftime('%Y%m%d-%H%M%S')}"
    STATE["frame"].update({
        "id": frame_id,
        "theme": data.theme,
        "angle": data.angle,
        "mood": data.mood,
        "rhythm": data.rhythm,
        "opened_at": now_iso(),
        "closed_at": None,
        "status": "open",
    })
    set_drive()
    reset_friction()
    payload = {
        "ok": True,
        "stage": "open",
        "frame_id": frame_id,
        "hint": "Frame aberto — Drive lançado",
        "time": now_iso(),
        "balance_gate": STATE["short"].balance_gate,
        "drive_launch": STATE["short"].drive_launch,
    }
    return eco_filter(payload)

@app.post("/v1/frame/close")
def close_frame():
    STATE["frame"]["closed_at"] = now_iso()
    STATE["frame"]["status"] = "closed"
    set_balance()
    out = {
        "ok": True,
        "stage": "closed",
        "frame_id": STATE["frame"]["id"],
        "time": now_iso(),
        "balance_gate": STATE["short"].balance_gate,
    }
    return eco_filter(out)

# -----------------------------------------------------------------------------
# 4Fs — Friction (inclui User Gate + Masters’ Gate)
# -----------------------------------------------------------------------------
@app.post("/v1/friction/submit")
def friction_submit(data: FrictionIn):
    STATE["frame"]["status"] = "in_friction"
    STATE["friction"].update({
        "idea_id": data.idea_id,
        "idea": data.idea,
        "evidence_refs": data.evidence_refs or [],
        "provisional_status": "🔵",
        "follow_up_questions": [
            "O que provaria isso verdadeiro em 1 métrica?",
        ],
        "transformation": None,
    })
    out = {
        "ok": True,
        "stage": "in_friction",
        "semaphore": "🔵",
        "time": now_iso(),
        "frame_id": STATE["frame"]["id"],
        "hint": "Ideia recebida; peça o User Gate.",
    }
    return eco_filter(out)

@app.post("/v1/friction/user_gate")
def friction_user_gate(g: UserGateIn):
    STATE["friction"]["user_gate"] = g.choice
    # transformação 🔵→🟡 se houver clareza mínima e escolha A|D
    if g.choice in ("A", "D"):
        STATE["friction"]["provisional_status"] = "🟡"
        STATE["friction"]["transformation"] = "blue_to_yellow"
    out = {
        "ok": True,
        "stage": "in_friction",
        "semaphore": STATE["friction"]["provisional_status"],
        "user_gate": g.choice,
        "time": now_iso(),
        "hint": "Se A, rode Masters’ Gate. Se D, irá como bypass.",
    }
    return eco_filter(out)

@app.post("/v1/friction/masters_gate")
def friction_masters_gate(m: MastersGateIn):
    STATE["masters_gate"].update({
        "facts_verified": m.facts_verified,
        "feasible": m.feasible,
        "within_frame": m.within_frame,
        "notes": m.notes,
        "checked_at": now_iso(),
    })
    # resultado
    passed = m.facts_verified and m.feasible and m.within_frame
    if STATE["friction"]["user_gate"] == "D":
        STATE["masters_gate"]["friction_gate"] = "bypassed_by_user"
    else:
        STATE["masters_gate"]["friction_gate"] = "passed" if passed else "failed"
    out = {
        "ok": True,
        "stage": "in_friction",
        "friction_gate": STATE["masters_gate"]["friction_gate"],
        "time": now_iso(),
        "hint": "Se passed/bypassed, siga para Flow.",
    }
    return eco_filter(out)

# -----------------------------------------------------------------------------
# 4Fs — Flow
# -----------------------------------------------------------------------------
@app.post("/v1/flow/check")
def flow_check(f: FlowIn):
    # só avança se Gate passou ou foi bypassado
    gate = STATE["masters_gate"]["friction_gate"]
    if gate not in ("passed", "bypassed_by_user"):
        return {"ok": False, "error": "Friction gate não passou.", "time": now_iso()}
    STATE["frame"]["status"] = "in_flow"
    # coerência mínima: assinatura deve continuar viva (tem Drive ativo)
    alive = STATE["short"].drive_launch is not None
    out = {
        "ok": True,
        "stage": "in_flow",
        "signature_alive": alive,
        "coherence_note": f.coherence_note,
        "time": now_iso(),
        "hint": "Se signature_alive, pode ir para Fact.",
    }
    return eco_filter(out)

# -----------------------------------------------------------------------------
# 4Fs — Fact (+ emissão de D6)
# -----------------------------------------------------------------------------
@app.post("/v1/fact/validate", response_model=D6Out)
def fact_validate(final: FactIn):
    if STATE["frame"]["status"] not in ("in_flow", "in_fact"):
        # permitir selar mesmo se cliente veio direto, mas marcamos status
        STATE["frame"]["status"] = "in_fact"

    # Selo final (🟢) somente se Gate passou/bypass e assinatura viva
    gate = STATE["masters_gate"]["friction_gate"]
    signature_alive = STATE["short"].drive_launch is not None
    green = gate in ("passed", "bypassed_by_user") and signature_alive

    semaphore = "🟢" if green else STATE["friction"]["provisional_status"]

    # Decisão em 6 (D6)
    decision = f"Validar ciclo com assinatura Balance and Drive e critério: {final.acceptance_criterion}"
    reasons = [
        "Friction gate resolvido (passed/bypassed).",
        "Assinatura viva ao longo do Flow.",
        "Critério de aceitabilidade declarado (Fact).",
    ]
    next_actions = [
        {"acao": "Registrar número da semana", "dono": "Regenerador", "quando": "T+1d"},
        {"acao": "Publicar rito (1 número, 1 decisão)", "dono": "Operacional", "quando": "T+2d"},
    ]

    d6 = {
        "semaphore": semaphore,
        "decision": decision,
        "reasons": reasons,
        "next_actions": next_actions,
        "user_gate": STATE["friction"]["user_gate"] or "B",
        "masters_gate": "Bypassed" if gate == "bypassed_by_user" else "Passed",
        "stamped_at": now_iso(),
    }
    STATE["d6"] = d6

    # atualizar memória curta
    STATE["short"].last_decision = decision
    STATE["short"].last_number = final.acceptance_criterion  # aqui tratamos como número-âncora do ciclo
    STATE["short"].last_pending = None

    # fechar frame com Balance
    STATE["frame"]["closed_at"] = now_iso()
    STATE["frame"]["status"] = "closed"
    set_balance()
    STATE["short"].push_trail({
        "type": "d6",
        "at": d6["stamped_at"],
        "semaphore": semaphore,
        "decision": decision,
    })

    return D6Out(**d6)

# -----------------------------------------------------------------------------
# Ping e Pulse
# -----------------------------------------------------------------------------
@app.get("/v1/ping")
def ping():
    return {"ok": True, "pong": True, "time": now_iso(), "eco": STATE["eco"]}

@app.get("/v1/pulse")
def pulse():
    # Pulso rápido para UI
    return {
        "ok": True,
        "time": now_iso(),
        "frame_status": STATE["frame"]["status"],
        "balance_gate": STATE["short"].balance_gate,
        "drive_launch": STATE["short"].drive_launch,
        "last_decision": STATE["short"].last_decision,
        "last_number": STATE["short"].last_number,
    }

# -----------------------------------------------------------------------------
# Exec local (Render ignora e roda via ASGI)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=False)

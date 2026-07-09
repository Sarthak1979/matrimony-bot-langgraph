"""FastAPI chat backend. Endpoints: POST /chat, POST /upload"""
import os
# --- macOS SSL fix: force Python to use certifi's certificate bundle ---
# Without this, HTTPS calls to Airtable/OpenRouter fail with
# "NO_CERTIFICATE_OR_CRL_FOUND" on python.org / pyenv installs that ship
# without system certificates. We OVERRIDE (not setdefault) so a stale/wrong
# env var can't keep breaking us.
try:
    import certifi
    _ca = certifi.where()
    os.environ["SSL_CERT_FILE"] = _ca
    os.environ["SSL_CERT_DIR"] = os.path.dirname(_ca)
    os.environ["REQUESTS_CA_BUNDLE"] = _ca
    os.environ["CURL_CA_BUNDLE"] = _ca
    # Make Python's default SSL context use certifi too (covers httpx/openai)
    import ssl
    ssl._create_default_https_context = lambda *a, **k: ssl.create_default_context(cafile=_ca)
    print(f"[SSL] Using certifi bundle: {_ca}")
except Exception as e:
    print(f"[SSL] certifi setup skipped: {e}")

import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from memory.memory_store import get_session, save_session, clear_session
from graphs.bot_graph import graph

app = FastAPI(title="Sri Vasavi Matrimony Bot")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Serve uploaded files back to the UI (so the review card can preview the photo
# before it's pushed to Airtable on submit).
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


class ChatRequest(BaseModel):
    session_id: str
    message: str = ""


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    awaiting: str = "text"
    current_flow: str = ""
    is_registered: bool = False
    is_approved: bool = False


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        state = get_session(req.session_id)
        state["user_input"] = req.message
        state["session_id"] = req.session_id
        result = graph.invoke(state)
        save_session(req.session_id, result)
        return ChatResponse(
            session_id=req.session_id,
            reply=result.get("reply", ""),
            awaiting=result.get("awaiting", "text"),
            current_flow=result.get("current_flow", ""),
            is_registered=result.get("is_registered", False),
            is_approved=result.get("is_approved", False),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ChatResponse(
            session_id=req.session_id,
            reply=(
                "⚠️ Something went wrong on our side. Please try again, "
                "or reply *menu* to start over."
            ),
            awaiting="text",
            current_flow="",
            is_registered=False,
            is_approved=False,
        )


@app.post("/upload", response_model=ChatResponse)
async def upload(
    session_id: str = Form(...),
    kind: str = Form(...),  # "biodata" or "photo"
    file: UploadFile = File(...),
):
    suffix = Path(file.filename or "upload").suffix or ".bin"
    fname = f"{uuid.uuid4().hex}{suffix}"
    saved = UPLOAD_DIR / fname
    contents = await file.read()
    saved.write_bytes(contents)

    state = get_session(session_id)
    state["session_id"] = session_id
    state["uploaded_file_path"] = str(saved)
    state["uploaded_file_url"] = f"http://localhost:8000/uploads/{fname}"
    state["uploaded_file_kind"] = kind
    state["user_input"] = ""
    result = graph.invoke(state)
    save_session(session_id, result)
    return ChatResponse(
        session_id=session_id,
        reply=result.get("reply", ""),
        awaiting=result.get("awaiting", "text"),
        current_flow=result.get("current_flow", ""),
        is_registered=result.get("is_registered", False),
        is_approved=result.get("is_approved", False),
    )


@app.post("/reset")
def reset(req: ChatRequest):
    clear_session(req.session_id)
    return {"ok": True}


class PollResponse(BaseModel):
    is_registered: bool = False
    is_approved: bool = False
    just_approved: bool = False  # True only on the transition pending->approved
    is_rejected: bool = False
    just_rejected: bool = False  # True only on the transition ->rejected


@app.post("/poll", response_model=PollResponse)
def poll(req: ChatRequest):
    """Lightweight check for approval status changes — used by the UI to
    auto-announce approval/rejection without the user typing anything.
    Does NOT advance the conversation."""
    from tools.airtable_tools import lookup_user_by_session
    from config.constants import AIRTABLE_FIELDS

    record, _ = lookup_user_by_session(req.session_id)
    if not record:
        return PollResponse()

    fields = record.get("fields", {})
    approval = str(fields.get(AIRTABLE_FIELDS["admin_approval"], "Pending")).strip().lower()
    is_approved = (approval == "approved")
    is_rejected = (approval in ("rejected", "reject", "declined"))

    state = get_session(req.session_id)
    approved_announced = state.get("approval_announced", False)
    rejected_announced = state.get("rejection_announced", False)

    just_approved = is_approved and not approved_announced
    just_rejected = is_rejected and not rejected_announced

    if just_approved:
        state["approval_announced"] = True
        state["is_approved"] = True
        state["is_registered"] = True
        if record.get("id"):
            state["airtable_record_id"] = record["id"]
        state["current_flow"] = "main_menu"
        save_session(req.session_id, state)

    if just_rejected:
        state["rejection_announced"] = True
        state["is_approved"] = False
        save_session(req.session_id, state)

    return PollResponse(
        is_registered=True,
        is_approved=is_approved,
        just_approved=just_approved,
        is_rejected=is_rejected,
        just_rejected=just_rejected,
    )


@app.get("/")
def root():
    return {"status": "ok", "service": "Sri Vasavi Matrimony Bot"}


if __name__ == "__main__":
    import uvicorn
    from config.settings import settings
    uvicorn.run("main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
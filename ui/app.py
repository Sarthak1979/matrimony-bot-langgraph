"""Sri Vasavi Matrimony Bot — Streamlit chat UI.

Design direction: warm, ceremonial, trustworthy — drawn from South Indian
wedding traditions (marigold, kumkum maroon, sandalwood cream, temple gold).
Serif display face (Playfair) for headings paired with a clean sans body.
Rich cards for matches and for the registration review screen.
"""
import json
import os
import random
import time
import requests
import streamlit as st

API_BASE = "http://localhost:8000"
RICH_CARD_PREFIX = "<<MATCH_CARDS>>"
MY_CARD_PREFIX = "<<MY_PROFILE_CARD>>"
REVIEW_CARD_PREFIX = "<<REVIEW_CARD>>"

st.set_page_config(
    page_title="Sri Vasavi Matrimony",
    page_icon="🪔",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------------- Styling ----------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Mukta:wght@300;400;500;600&display=swap');

:root {
    --maroon: #7a1f2b;
    --maroon-deep: #5c1620;
    --marigold: #e8a33d;
    --marigold-soft: #f4c77b;
    --cream: #fdf8f0;
    --sand: #f5ead7;
    --ink: #2b1d18;
    --muted: #8a7560;
}

/* App background — warm sandalwood wash */
.stApp {
    background:
        radial-gradient(circle at 15% 0%, #fbeecf55 0%, transparent 40%),
        radial-gradient(circle at 90% 10%, #f4d9b033 0%, transparent 35%),
        var(--cream);
}

/* Headings use the serif display face */
h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: var(--maroon) !important; }
body, p, div, span, label, .stMarkdown { font-family: 'Mukta', sans-serif; color: var(--ink); }

/* Main title block */
.svm-header {
    text-align: center;
    padding: 0.4rem 0 0.2rem 0;
    border-bottom: 2px solid var(--marigold);
    margin-bottom: 0.5rem;
}
.svm-header .lamp { font-size: 2.1rem; line-height: 1; }
.svm-header h1 {
    font-size: 2.05rem !important;
    margin: 0.1rem 0 0 0 !important;
    letter-spacing: 0.01em;
}
.svm-header .tag {
    font-family: 'Mukta', sans-serif;
    font-size: 0.82rem;
    color: var(--muted);
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

/* Chat bubbles */
[data-testid="stChatMessage"] {
    background: #ffffff;
    border: 1px solid #ecdcc2;
    border-radius: 14px;
    box-shadow: 0 1px 3px rgba(122,31,43,0.06);
    padding: 0.35rem 0.6rem;
}

/* Profile / match / review cards */
.svm-card {
    background: linear-gradient(180deg, #ffffff 0%, #fffaf2 100%);
    border: 1px solid #e7cfa6;
    border-left: 5px solid var(--maroon);
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    margin: 0.7rem 0;
    box-shadow: 0 4px 16px rgba(122,31,43,0.08);
}
.svm-card .name {
    font-family: 'Playfair Display', serif;
    font-size: 1.45rem;
    font-weight: 700;
    color: var(--maroon);
    margin: 0 0 0.1rem 0;
}
.svm-card .sub { color: var(--muted); font-size: 0.86rem; margin-bottom: 0.7rem; }

.svm-row { display: flex; padding: 0.18rem 0; border-bottom: 1px dotted #eadbc2; }
.svm-row:last-child { border-bottom: none; }
.svm-row .k {
    flex: 0 0 42%;
    color: var(--muted);
    font-weight: 500;
    font-size: 0.9rem;
}
.svm-row .v { flex: 1; color: var(--ink); font-weight: 500; font-size: 0.92rem; }

.svm-photo {
    width: 100%;
    border-radius: 12px;
    border: 3px solid var(--marigold-soft);
    object-fit: cover;
    aspect-ratio: 3/4;
}
.svm-photo-empty {
    width: 100%; aspect-ratio: 3/4; border-radius: 12px;
    background: repeating-linear-gradient(45deg, #f6ecd9, #f6ecd9 10px, #f1e3cb 10px, #f1e3cb 20px);
    display: flex; align-items: center; justify-content: center;
    color: var(--muted); font-size: 0.8rem; text-align: center;
    border: 2px dashed #d9c39b;
}

.svm-section-title {
    font-family: 'Playfair Display', serif;
    color: var(--maroon);
    font-size: 1.15rem;
    font-weight: 600;
    margin: 0.2rem 0 0.4rem 0;
    display: flex; align-items: center; gap: 0.4rem;
}

.svm-badge {
    display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
}
.svm-badge.ok { background: #e6f4ea; color: #1d7a3a; border: 1px solid #b6e0c4; }
.svm-badge.no { background: #fbe9e9; color: #b3261e; border: 1px solid #f0c2c0; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--maroon) 0%, var(--maroon-deep) 100%);
}
[data-testid="stSidebar"] * { color: #fdeccd !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #ffffff !important; font-family: 'Playfair Display', serif !important;
}
[data-testid="stSidebar"] .stButton button {
    background: var(--marigold); color: var(--maroon-deep) !important;
    border: none; border-radius: 10px; font-weight: 600; width: 100%;
    transition: transform 0.08s ease, box-shadow 0.15s ease;
}
[data-testid="stSidebar"] .stButton button:hover {
    box-shadow: 0 3px 10px rgba(0,0,0,0.25); transform: translateY(-1px);
}
[data-testid="stSidebar"] .stTextInput input {
    background: #ffffff15; border: 1px solid #ffffff44; color: #fff !important; border-radius: 8px;
}
.svm-sid {
    background: #ffffff14; border: 1px solid #ffffff33; border-radius: 10px;
    padding: 0.5rem 0.7rem; font-family: 'Mukta', monospace; font-size: 1.2rem;
    letter-spacing: 0.08em; text-align: center; font-weight: 600;
}

/* Chat input — ensure typed text is visible (dark ink on cream) */
[data-testid="stChatInput"] {
    border: 1.5px solid var(--marigold) !important;
    border-radius: 14px;
    background: #fffdf8 !important;
}
[data-testid="stChatInput"] textarea {
    color: var(--ink) !important;
    -webkit-text-fill-color: var(--ink) !important;
    caret-color: var(--maroon) !important;
    font-family: 'Mukta', sans-serif !important;
    font-size: 1rem !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #b09a7f !important;
    -webkit-text-fill-color: #b09a7f !important;
}

/* File uploader (drag & drop) — make text readable on its light box */
[data-testid="stFileUploader"] {
    background: #fffaf2 !important;
    border: 2px dashed var(--marigold) !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] section {
    background: transparent !important;
}
[data-testid="stFileUploader"] * {
    color: var(--ink) !important;
}
[data-testid="stFileUploaderDropzoneInstructions"] *,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {
    color: #6b5742 !important;
}
[data-testid="stFileUploader"] button {
    background: var(--marigold) !important;
    color: var(--maroon-deep) !important;
    border: none !important;
    font-weight: 600 !important;
}

/* Copy button for session id */
.svm-sid-wrap { display: flex; gap: 0.4rem; align-items: stretch; }
.svm-sid-wrap .svm-sid { flex: 1; }

/* Typing / thinking indicator */
.svm-typing { font-size: 1.1rem; letter-spacing: 2px; padding: 4px 0; }
.svm-typing .dot {
    display: inline-block; opacity: 0.3; color: #b8860b;
    animation: svmBlink 1.2s infinite;
}
.svm-typing .dot:nth-child(2) { animation-delay: 0.2s; }
.svm-typing .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes svmBlink {
    0%, 60%, 100% { opacity: 0.25; }
    30% { opacity: 1; }
}

/* Hide Streamlit chrome */
#MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ---------------- Header ----------------
st.markdown("""
<div class="svm-header">
    <div class="lamp">🪔</div>
    <h1>Sri Vasavi Matrimony</h1>
    <div class="tag">Charitable Trust · by KVRSA Raju</div>
</div>
""", unsafe_allow_html=True)


def _new_session_id() -> str:
    return str(random.randint(9000000000, 9999999999))


# ---------------- Session resolution ----------------
qp = st.query_params
url_sid = qp.get("sid", None)

if "session_id" not in st.session_state:
    if url_sid and url_sid.isdigit() and len(url_sid) == 10:
        st.session_state.session_id = url_sid
    else:
        st.session_state.session_id = _new_session_id()

if qp.get("sid") != st.session_state.session_id:
    qp["sid"] = st.session_state.session_id

if "messages" not in st.session_state:
    st.session_state.messages = []
if "awaiting" not in st.session_state:
    st.session_state.awaiting = "text"


def call_chat(message: str):
    try:
        r = requests.post(
            f"{API_BASE}/chat",
            json={"session_id": st.session_state.session_id, "message": message},
            timeout=90,
        )
        return r.json()
    except Exception as e:
        return {"reply": f"⚠️ Couldn't reach the server. Please make sure the backend is running. ({e})", "awaiting": "text"}


def call_upload(file, kind: str):
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {"session_id": st.session_state.session_id, "kind": kind}
        r = requests.post(f"{API_BASE}/upload", files=files, data=data, timeout=180)
        return r.json()
    except Exception as e:
        return {"reply": f"⚠️ Upload didn't go through. Please try again. ({e})", "awaiting": "text"}


def append_bot_reply(reply: str):
    """Append a bot reply to the message list. If the reply contains the
    <<SPLIT>> marker, break it into multiple separate chat bubbles. Only the
    LAST bubble gets the typing animation."""
    parts = [p.strip() for p in str(reply).split("<<SPLIT>>") if p.strip()]
    if not parts:
        parts = [""]
    for part in parts:
        st.session_state.messages.append(("bot", part))
    # Stream only the final bubble
    st.session_state.stream_idx = len(st.session_state.messages) - 1


# ---------------- Rendering helpers ----------------
LABELS = {
    "full_name": "Full Name", "country_of_person": "City & Country",
    "country_of_parents": "Parents' City", "dob": "Date of Birth",
    "time_of_birth": "Time of Birth", "place_of_birth": "Place of Birth",
    "height": "Height", "nakshatra": "Nakshatra", "rashi": "Rashi",
    "swa_gothram": "Swa Gothram", "maternal_gothram": "Maternal Gothram",
    "qualification": "Qualification", "profession": "Profession",
    "salary_package": "Annual Income", "father_name": "Father's Name",
    "mother_name": "Mother's Name", "father_occupation": "Father's Occupation",
    "mother_occupation": "Mother's Occupation", "property_details": "Property",
}


def _height_label(h_cm):
    try:
        h_cm = float(h_cm)
        feet = int(h_cm / 2.54) // 12
        inches = round(h_cm / 2.54) - feet * 12
        return f"{feet}'{inches}\" ({int(h_cm)} cm)"
    except (TypeError, ValueError):
        return str(h_cm)


def _esc(s):
    return str(s).replace("<", "&lt;").replace(">", "&gt;")


def _render_match_cards(cards, heading='💞 Suggested Matches'):
    st.markdown(f'<div class="svm-section-title">{heading}</div>', unsafe_allow_html=True)
    for c in cards:
        col1, col2 = st.columns([1, 1.9])
        with col1:
            if c.get("photo_url"):
                try:
                    st.image(c["photo_url"], use_container_width=True)
                except Exception:
                    st.markdown('<div class="svm-photo-empty">Photo</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="svm-photo-empty">No photo<br>provided</div>', unsafe_allow_html=True)
        with col2:
            rows = ""
            pairs = [
                ("Age", f"{c.get('age','—')} years"),
                ("Height", _height_label(c.get("height_cm")) if c.get("height_cm") else "—"),
                ("Nakshatra", c.get("nakshatra", "—")),
                ("Rashi", c.get("rashi", "—")),
                ("Education", c.get("qualification", "—")),
                ("Profession", c.get("profession", "—")),
                ("Place", c.get("place", "—")),
            ]
            if c.get("country") and c["country"] != "N/A":
                pairs.append(("Country", c["country"]))
            for k, v in pairs:
                rows += f'<div class="svm-row"><div class="k">{k}</div><div class="v">{_esc(v)}</div></div>'
            st.markdown(
                f'<div class="svm-card"><div class="name">{_esc(c.get("name","—"))}</div>{rows}</div>',
                unsafe_allow_html=True,
            )


def _render_review_card(data):
    if data.get("photo_just_received"):
        st.success("Photo received successfully")
    st.markdown('<div class="svm-section-title">📋 Review Your Profile</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1.9])
    with col1:
        shown = False
        # Prefer the local file path (most reliable — no HTTP needed)
        local = data.get("photo_local_path")
        if local and os.path.exists(local):
            try:
                st.image(local, use_container_width=True)
                shown = True
            except Exception:
                shown = False
        if not shown and data.get("photo_url"):
            try:
                st.image(data["photo_url"], use_container_width=True)
                shown = True
            except Exception:
                shown = False
        if not shown:
            status = "Photo ready ✓" if data.get("photo_uploaded") else "No photo yet"
            st.markdown(f'<div class="svm-photo-empty">{status}</div>', unsafe_allow_html=True)
    with col2:
        order = ["full_name", "dob", "time_of_birth", "place_of_birth", "height",
                 "nakshatra", "rashi", "swa_gothram", "maternal_gothram",
                 "qualification", "profession", "salary_package",
                 "country_of_person", "country_of_parents",
                 "father_name", "father_occupation", "mother_name", "mother_occupation",
                 "property_details"]
        rows = ""
        for key in order:
            if key in data and str(data.get(key, "")).strip() not in ("", "—"):
                rows += (
                    f'<div class="svm-row"><div class="k">{LABELS.get(key,key)}</div>'
                    f'<div class="v">{_esc(data.get(key,"—"))}</div></div>'
                )
        badge = ('<span class="svm-badge ok">Photo uploaded</span>'
                 if data.get("photo_uploaded")
                 else '<span class="svm-badge no">Photo missing</span>')
        rows += f'<div class="svm-row"><div class="k">Photo</div><div class="v">{badge}</div></div>'
        st.markdown(
            f'<div class="svm-card"><div class="name">{_esc(data.get("full_name","Your Profile"))}</div>{rows}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        "Looks right? Reply **YES** to submit for approval, or **NO** to make changes."
    )


def _md(text: str) -> str:
    """Convert single newlines to markdown hard line-breaks so every line
    (and every list item) renders on its own line."""
    # Two trailing spaces before a newline = hard break in markdown
    return text.replace("\n", "  \n")


def render_bot_message(content: str):
    # Safety: never display the internal split marker
    content = str(content).replace("<<SPLIT>>", "\n\n")
    # The card sentinels may occasionally be preceded by text; find them anywhere.
    if MY_CARD_PREFIX in content:
        pre, _, rest = content.partition(MY_CARD_PREFIX)
        if pre.strip():
            st.markdown(_md(pre.strip()))
        split = rest.split("\n", 1)
        try:
            cards = json.loads(split[0])
        except Exception:
            st.markdown(_md(content)); return
        _render_match_cards(cards, heading='📋 Your Profile')
        if len(split) > 1 and split[1].strip():
            st.markdown(_md(split[1]))
    elif RICH_CARD_PREFIX in content:
        pre, _, rest = content.partition(RICH_CARD_PREFIX)
        if pre.strip():
            st.markdown(_md(pre.strip()))
        split = rest.split("\n", 1)
        try:
            cards = json.loads(split[0])
        except Exception:
            st.markdown(_md(content)); return
        _render_match_cards(cards)
        if len(split) > 1 and split[1].strip():
            st.markdown(_md(split[1]))
    elif REVIEW_CARD_PREFIX in content:
        pre, _, rest = content.partition(REVIEW_CARD_PREFIX)
        if pre.strip():
            st.markdown(_md(pre.strip()))
        try:
            data = json.loads(rest)
        except Exception:
            st.markdown(_md(content)); return
        _render_review_card(data)
    else:
        st.markdown(_md(content))


def _is_card(content: str) -> bool:
    return (RICH_CARD_PREFIX in content or REVIEW_CARD_PREFIX in content
            or MY_CARD_PREFIX in content)


def stream_bot_message(content: str):
    """Render a bot reply with a live typing effect for plain text.
    Card replies (match/review) render instantly — typing them char-by-char
    would look broken."""
    content = str(content).replace("<<SPLIT>>", "\n\n")
    if _is_card(content):
        render_bot_message(content)
        return
    placeholder = st.empty()
    shown = ""
    # Stream word-by-word for a natural, fast typing feel
    tokens = content.split(" ")
    for i, tok in enumerate(tokens):
        shown += (tok if i == 0 else " " + tok)
        placeholder.markdown(_md(shown) + " ▌")
        # Tiny pause; cap total so long messages don't drag
        time.sleep(min(0.02, 1.2 / max(len(tokens), 1)))
    placeholder.markdown(_md(shown))


def thinking_indicator():
    """Show an animated 'typing…' bubble while the bot is processing."""
    placeholder = st.empty()
    placeholder.markdown(
        '<div class="svm-typing">🪔 <span class="dot">●</span>'
        '<span class="dot">●</span><span class="dot">●</span></div>',
        unsafe_allow_html=True,
    )
    return placeholder


# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### Your Session")
    # Session ID with a copy button (HTML component so JS clipboard works)
    sid = st.session_state.session_id
    st.components.v1.html(f"""
    <div style="display:flex;gap:6px;align-items:stretch;font-family:'Mukta',sans-serif;">
      <div id="svmsid" style="flex:1;background:#ffffff14;border:1px solid #ffffff33;
           border-radius:10px;padding:9px 12px;font-size:1.2rem;letter-spacing:0.08em;
           text-align:center;font-weight:600;color:#fdeccd;">{sid}</div>
      <button onclick="
          navigator.clipboard.writeText('{sid}');
          const b=this; const t=b.innerText; b.innerText='✓';
          setTimeout(()=>b.innerText=t,1200);
        " style="background:#e8a33d;color:#5c1620;border:none;border-radius:10px;
          padding:0 14px;font-weight:700;cursor:pointer;font-size:0.95rem;">Copy</button>
    </div>
    """, height=52)
    st.caption("This 10-digit ID is how we find your profile. Keep it to return later.")

    st.markdown("---")
    st.markdown("**Already registered?**")
    manual_sid = st.text_input(
        "Enter your 10-digit ID", value="", placeholder="e.g. 9931705323",
        max_chars=10, key="manual_sid_input", label_visibility="collapsed",
    )
    if st.button("Open my profile"):
        if manual_sid.isdigit() and len(manual_sid) == 10:
            st.session_state.session_id = manual_sid
            st.session_state.messages = []
            st.session_state.awaiting = "text"
            qp["sid"] = manual_sid
            st.rerun()
        else:
            st.warning("Please enter exactly 10 digits.")

    st.markdown("---")
    if st.button("✨ Start fresh"):
        try:
            requests.post(f"{API_BASE}/reset", json={"session_id": st.session_state.session_id})
        except Exception:
            pass
        new_sid = _new_session_id()
        st.session_state.session_id = new_sid
        st.session_state.messages = []
        st.session_state.awaiting = "text"
        qp["sid"] = new_sid
        st.rerun()

    if st.button("🔄 Reload conversation"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.caption("Need help? Call admin")
    st.markdown("**📞 +91 8660038025**")


def call_poll():
    """Check if the user just got approved by admin."""
    try:
        r = requests.post(
            f"{API_BASE}/poll",
            json={"session_id": st.session_state.session_id, "message": ""},
            timeout=30,
        )
        return r.json()
    except Exception:
        return {"is_registered": False, "is_approved": False, "just_approved": False}


# ---------------- Conversation ----------------
if not st.session_state.messages:
    resp = call_chat("")
    append_bot_reply(resp.get("reply", ""))
    st.session_state.pop("stream_idx", None)  # don't animate the very first load
    st.session_state.awaiting = resp.get("awaiting", "text")
    # Seed approval state from the first response so we don't falsely announce
    # for users who were ALREADY approved before this session loaded.
    if resp.get("is_approved"):
        st.session_state.approval_shown = True

# Track whether we've already shown the approval celebration this session
if "approval_shown" not in st.session_state:
    st.session_state.approval_shown = False


def _inject_approval_message():
    """Add the celebration + fresh menu to the conversation."""
    celebrate = call_chat("__approved__")
    st.session_state.messages.append((
        "bot",
        "🎉 *Wonderful news — your profile has been approved by our admin!* 🎉\n\n"
        "You can now search for matches. Here's your menu:"
    ))
    st.session_state.messages.append(("bot", celebrate.get("reply", "")))
    st.session_state.awaiting = celebrate.get("awaiting", "text")
    st.session_state.approval_shown = True


# Auto-checking fragment: polls the backend every 5s WITHOUT a full reload.
# When admin approval is detected, it flips a flag and triggers a single rerun
# so the celebration message is injected into the main conversation.
@st.fragment(run_every=5)
def _approval_watcher():
    if st.session_state.get("approval_shown") or st.session_state.get("rejection_shown"):
        return  # already announced; stop checking
    poll = call_poll()
    if poll.get("just_approved"):
        st.session_state.approval_shown = True
        st.session_state._pending_approval_inject = True
        st.rerun(scope="app")
    elif poll.get("just_rejected"):
        st.session_state.rejection_shown = True
        st.session_state._pending_rejection_inject = True
        st.rerun(scope="app")


# If the watcher flagged a fresh approval, inject the message now (main run)
if st.session_state.get("_pending_approval_inject"):
    st.session_state._pending_approval_inject = False
    _inject_approval_message()

if st.session_state.get("_pending_rejection_inject"):
    st.session_state._pending_rejection_inject = False
    st.session_state.messages.append((
        "bot",
        "🙏 *Update on your profile*\n\n"
        "We're sorry — after review, your profile could not be approved at this time. "
        "This can happen for various reasons.\n\n"
        "Please contact our admin to understand more and resolve any issues:\n"
        "📞 *+91 8660038025*"
    ))
    st.session_state.awaiting = "text"

num_msgs = len(st.session_state.messages)
stream_idx = st.session_state.pop("stream_idx", None)

for i, (role, content) in enumerate(st.session_state.messages):
    avatar = "🪔" if role == "bot" else "🙏"
    with st.chat_message("assistant" if role == "bot" else "user", avatar=avatar):
        if role == "bot":
            # Stream only the one freshly-received bot message
            if stream_idx is not None and i == stream_idx:
                stream_bot_message(content)
            else:
                render_bot_message(content)
        else:
            st.markdown(content)

# File uploader when expected
if st.session_state.awaiting in ("biodata", "photo"):
    label = (
        "Upload your biodata (PDF or image)"
        if st.session_state.awaiting == "biodata"
        else "Upload a recent photo (JPG or PNG)"
    )
    accept = (["pdf", "png", "jpg", "jpeg"] if st.session_state.awaiting == "biodata"
              else ["png", "jpg", "jpeg"])
    file = st.file_uploader(label, type=accept, key=f"upload_{len(st.session_state.messages)}")
    if file is not None:
        st.session_state.messages.append(("user", f"📎 Sent: {file.name}"))
        with st.chat_message("assistant", avatar="🪔"):
            ph = thinking_indicator()
            resp = call_upload(file, st.session_state.awaiting)
            ph.empty()
        append_bot_reply(resp.get("reply", ""))
        st.session_state.awaiting = resp.get("awaiting", "text")
        st.rerun()

user_text = st.chat_input("Type your reply…")
if user_text:
    st.session_state.messages.append(("user", user_text))
    # Show the user's message + a thinking bubble immediately
    with st.chat_message("user", avatar="🙏"):
        st.markdown(user_text)
    with st.chat_message("assistant", avatar="🪔"):
        ph = thinking_indicator()
        resp = call_chat(user_text)
        ph.empty()
    append_bot_reply(resp.get("reply", ""))
    st.session_state.awaiting = resp.get("awaiting", "text")
    st.rerun()

# Run the background approval watcher only while waiting for admin decision.
if not st.session_state.get("approval_shown") and not st.session_state.get("rejection_shown"):
    _approval_watcher()
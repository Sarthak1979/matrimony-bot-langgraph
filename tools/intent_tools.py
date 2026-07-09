"""Natural-language intent classification.

Maps free-text user input ("register my profile", "i wanna search", "rgister")
to a known menu intent. Uses a fast keyword matcher first, then falls back to
GPT-4o (via OpenRouter) for fuzzy/natural cases.

Intents returned:
  "register", "search", "admin", "faq", "menu", "yes", "no", "more", "skip",
  "update", or "" (unknown).
"""
from typing import Optional, List
from openai import OpenAI
from config.settings import settings


def _get_client() -> Optional[OpenAI]:
    if not settings.OPENAI_API_KEY:
        return None
    base_url = settings.openai_base_url
    if base_url:
        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://srivasavi-matrimony.local",
                "X-Title": "Sri Vasavi Matrimony Bot",
            },
        )
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# ---------- Fast keyword matcher (no API call needed) ----------

_KEYWORDS = {
    "register": ["register", "registration", "sign up", "signup", "enroll", "new profile",
                 "create profile", "make profile", "rgister", "regiser", "registr"],
    "search": ["search", "find match", "find a match", "matches", "look for", "find me",
                "show match", "partner", "groom", "bride", "serch", "saerch"],
    "admin": ["admin", "talk to admin", "contact", "support", "help me", "call", "human"],
    "faq": ["faq", "faqs", "question", "questions", "doubt", "query", "queries", "help"],
    "menu": ["menu", "main menu", "home", "back", "go back", "start over", "options"],
    "update": ["update", "edit", "change", "modify", "correct"],
    "yes": ["yes", "yeah", "yep", "yup", "confirm", "submit", "ok", "okay", "sure", "haan", "ha"],
    "no": ["no", "nope", "nah", "cancel", "change", "edit", "nahi"],
    "more": ["more", "next", "show more", "more matches", "another"],
    "skip": ["skip", "none", "no preference", "any", "pass"],
}


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance — how many single-char edits to turn a into b."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(
                prev[j] + 1,          # deletion
                cur[j - 1] + 1,       # insertion
                prev[j - 1] + (ca != cb),  # substitution
            ))
        prev = cur
    return prev[-1]


def _keyword_intent(text: str) -> str:
    t = text.strip().lower()
    if not t:
        return ""
    # Exact single-word hits first
    for intent, words in _KEYWORDS.items():
        if t in words:
            return intent
    # Substring hits (longer phrases)
    best = ""
    best_len = 0
    for intent, words in _KEYWORDS.items():
        for w in words:
            if w in t and len(w) > best_len:
                best = intent
                best_len = len(w)
    if best:
        return best
    # Fuzzy: tolerate spelling mistakes (e.g. 'registr', 'serch', 'fak', 'admn')
    # Compare each word of the input to each keyword; accept close matches.
    words_in = [w for w in t.split() if len(w) >= 3]
    fuzzy_best = ""
    fuzzy_score = 999
    for intent, words in _KEYWORDS.items():
        for kw in words:
            if " " in kw or len(kw) < 4:
                continue  # only fuzzy-match single, reasonably long words
            for w in words_in:
                d = _edit_distance(w, kw)
                # allow ~25% of the word length in edits (min 1, max 3)
                tol = max(1, min(3, len(kw) // 4 + 1))
                if d <= tol and d < fuzzy_score:
                    fuzzy_score = d
                    fuzzy_best = intent
    return fuzzy_best


# ---------- AI fallback ----------

def _ai_intent(text: str, allowed: List[str]) -> str:
    try:
        client = _get_client()
        if client is None:
            return ""
        allowed_str = ", ".join(allowed)
        system = (
            "You are an intent classifier for a matrimony chatbot menu. "
            f"Map the user's message to EXACTLY ONE of these intents: {allowed_str}, or 'unknown'. "
            "The user may use natural language, Hinglish, or have typos. "
            "Reply with ONLY the intent word, nothing else.\n"
            "Examples:\n"
            "'i want to register my profile' -> register\n"
            "'rgister' -> register\n"
            "'find me a bride' -> search\n"
            "'show me matches' -> search\n"
            "'i need to talk to someone' -> admin\n"
            "'what are the charges' -> faq\n"
            "'go back' -> menu\n"
            "'yes please submit' -> yes\n"
            "'no change it' -> no\n"
            "'tell me a joke' -> unknown"
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text[:200]},
            ],
            temperature=0,
            max_tokens=5,
            timeout=8,
        )
        out = resp.choices[0].message.content.strip().lower()
        out = "".join(c for c in out if c.isalpha())
        if out in allowed:
            return out
        return ""
    except Exception as e:
        print(f"[Intent] AI fallback unavailable ({e}); keyword match only.")
        return ""


def classify_intent(text: str, allowed: Optional[List[str]] = None, use_ai: bool = True) -> str:
    """Return the best-matching intent for free-text input.
    `allowed` restricts which intents are valid in the current context.
    Tries keyword match first (instant), then AI for natural language.
    Never raises — returns '' on any failure."""
    try:
        if allowed is None:
            allowed = list(_KEYWORDS.keys())
        # 1. Fast keyword path
        kw = _keyword_intent(text)
        if kw and kw in allowed:
            return kw
        # 2. AI fallback for natural language / typos
        if use_ai and len(text.strip()) >= 2:
            ai = _ai_intent(text, allowed)
            if ai and ai in allowed:
                return ai
        return ""
    except Exception as e:
        print(f"[Intent] classify error ({e})")
        return ""
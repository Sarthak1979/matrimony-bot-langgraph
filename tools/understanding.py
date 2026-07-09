"""The bot's 'brain' for understanding messy human input.

Instead of rigid exact-match checks, this module interprets what the user
*meant* using three layers, in order:

  1. Normalised + fuzzy match   (handles 'briiiide', 'grooom', 'bridee')
  2. AI interpretation          (handles 'the girl', 'ladki', 'my daughter')
  3. Caller decides             (we return a guess + confidence so the node
                                 can ask "Did you mean ...?" when unsure)

It is generic: give it the user's text and a dict of {canonical: [synonyms]}
and it returns (match, confidence) where confidence is 'high' | 'maybe' | ''.
"""
from typing import Dict, List, Optional, Tuple
import re

from tools.intent_tools import _edit_distance, _get_client
from config.settings import settings


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, and collapse repeated letters so that
    'briiiide!!!' -> 'bride' (repeated runs shrunk to max 2, then 1 for match)."""
    t = text.strip().lower()
    t = re.sub(r"[^a-z\s]", "", t)            # drop digits/punctuation/emoji
    t = re.sub(r"(.)\1{2,}", r"\1", t)         # 'briiiide' -> 'bride', 'grooom' -> 'grom'
    return t.strip()


def _collapse_all(word: str) -> str:
    """Collapse every repeated letter to a single one: 'grooom' -> 'grom',
    'bride' -> 'bride'. Used for very loose comparison."""
    return re.sub(r"(.)\1+", r"\1", word)


def fuzzy_match(text: str, options: Dict[str, List[str]]) -> Tuple[Optional[str], str]:
    """Match user text against {canonical: [synonyms]} using normalisation +
    edit distance. Returns (canonical_or_None, confidence)."""
    norm = _normalise(text)
    if not norm:
        return None, ""

    words = norm.split()

    # ---- Layer 1: exact / substring on normalised text ----
    for canonical, syns in options.items():
        for syn in syns:
            s = _normalise(syn)
            if not s:
                continue
            if norm == s:
                return canonical, "high"
            # whole-word containment (so 'i am a bride' matches 'bride')
            if s in words or s in norm.split():
                return canonical, "high"

    # ---- Layer 2: collapsed-letter compare (briiiide -> bride) ----
    norm_collapsed = _collapse_all(norm)
    for canonical, syns in options.items():
        for syn in syns:
            s = _collapse_all(_normalise(syn))
            if not s:
                continue
            if norm_collapsed == s:
                return canonical, "high"
            for w in words:
                if _collapse_all(w) == s:
                    return canonical, "high"

    # ---- Layer 3: fuzzy edit distance per word ----
    best_canon = None
    best_dist = 999
    for canonical, syns in options.items():
        for syn in syns:
            s = _normalise(syn)
            if len(s) < 3:
                continue
            for w in words:
                if len(w) < 3:
                    continue
                d = _edit_distance(_collapse_all(w), _collapse_all(s))
                if d < best_dist:
                    best_dist = d
                    best_canon = canonical
    if best_canon is not None:
        if best_dist == 0:
            return best_canon, "high"
        if best_dist == 1:
            return best_canon, "high"     # one typo away — confident
        if best_dist == 2:
            return best_canon, "maybe"    # close — ask to confirm
    return None, ""


def ai_interpret(text: str, options: Dict[str, List[str]], context: str = "") -> Tuple[Optional[str], str]:
    """Use the LLM to interpret free-form input into one of the canonical
    options. Returns (canonical_or_None, 'high'|'')."""
    try:
        client = _get_client()
        if client is None:
            return None, ""
        canon_list = list(options.keys())
        labels = ", ".join(canon_list)
        sys_prompt = (
            "You map a user's reply to EXACTLY ONE allowed option for a matrimony "
            f"chatbot. Allowed options: {labels}, or 'unknown'.\n"
            + (f"Question context: {context}\n" if context else "")
            + "The user may use other languages (Hindi/Telugu/Hinglish), synonyms, "
            "or misspellings. Reply with ONLY the option word, nothing else."
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:200]},
            ],
            temperature=0,
            max_tokens=5,
            timeout=8,
        )
        out = resp.choices[0].message.content.strip().lower()
        out = re.sub(r"[^a-z]", "", out)
        for c in canon_list:
            if out == _normalise(c) or out == c.lower():
                return c, "high"
        return None, ""
    except Exception as e:
        print(f"[Understanding] AI interpret failed: {e}")
        return None, ""


def understand_choice(
    text: str,
    options: Dict[str, List[str]],
    context: str = "",
    use_ai: bool = True,
) -> Tuple[Optional[str], str]:
    """Top-level brain: combine fuzzy + AI.

    Returns (canonical, confidence):
      - (value, 'high')  -> accept it
      - (value, 'maybe') -> ask 'Did you mean <value>?'
      - (None, '')       -> truly didn't understand
    """
    # Fast local understanding first
    val, conf = fuzzy_match(text, options)
    if conf == "high":
        return val, "high"

    # If fuzzy is unsure, ask the AI
    if use_ai:
        ai_val, ai_conf = ai_interpret(text, options, context)
        if ai_conf == "high":
            return ai_val, "high"

    # Fuzzy had a 'maybe' — surface it for a confirmation prompt
    if conf == "maybe":
        return val, "maybe"

    return None, ""


# ---------------- Off-topic detection (agent-like behaviour) ----------------

# Question/chit-chat words that signal the user is asking something off-topic
# rather than answering the current field.
_QUESTION_CUES = (
    "weather", "joke", "who are you", "what are you", "how are you",
    "your name", "time is it", "what time", "news", "cricket", "movie",
    "song", "story", "love you", "married", "do you", "can you", "tell me about",
    "what is", "whats", "what's", "why ", "how do", "meaning of", "capital of",
    "temperature", "rain", "modi", "president", "game", "play",
)


def looks_off_topic(text: str, field_hint: str = "") -> bool:
    """Heuristic: does this look like an off-topic question rather than an
    answer to the current field? Conservative — only flags clear chit-chat."""
    t = text.strip().lower()
    if len(t) < 3:
        return False
    # A trailing question mark + a question cue is a strong signal
    has_q = t.endswith("?") or t.startswith(("what", "who", "why", "how", "when", "where", "do you", "can you", "is it", "are you"))
    cue = any(c in t for c in _QUESTION_CUES)
    return bool(cue and (has_q or len(t.split()) >= 3))


def answer_off_topic(text: str, current_question: str) -> str:
    """Reply like a warm human agent: briefly acknowledge the off-topic question,
    then steer back to the current registration question. Uses AI if available."""
    try:
        client = _get_client()
        if client is None:
            return ""
        sys_prompt = (
            "You are a warm, friendly human matchmaking assistant at Sri Vasavi "
            "Matrimony. The user asked something off-topic while you were collecting "
            "their profile details. In 1-2 short, natural sentences: gently and kindly "
            "acknowledge their message (you may give a very brief friendly reply), then "
            "warmly bring them back to the registration. Do NOT fully answer the "
            "off-topic question. Sound human and caring, not robotic."
            f"\n\nThe question you need them to answer next is: \"{current_question}\""
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:200]},
            ],
            temperature=0.7,
            max_tokens=90,
            timeout=8,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Understanding] off-topic answer failed: {e}")
        return ""


# ---------------- Place validation ----------------

def is_real_place(text: str, expect_city_country: bool = False) -> Tuple[bool, str]:
    """Use the LLM to check whether `text` is a plausible real place
    (city / town / village, optionally 'City, Country'). Returns (ok, reason).
    Fails OPEN (returns True) if AI is unavailable, so users are never blocked
    by an outage — the gibberish check already caught obvious junk upstream."""
    try:
        client = _get_client()
        if client is None:
            return True, ""  # fail open
        rule = ("The user should name a real city, town, or village"
                + (" AND a country, in the form 'City, Country'." if expect_city_country
                   else "."))
        sys_prompt = (
            "You validate a place name for a matrimony profile. "
            + rule +
            " Reply with ONLY one word: 'valid' if it is a real, recognizable place "
            "(spelling may be imperfect), or 'invalid' if it is gibberish, random "
            "letters, or clearly not a place. Be lenient with small towns and villages."
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": text[:120]},
            ],
            temperature=0,
            max_tokens=4,
            timeout=8,
        )
        out = resp.choices[0].message.content.strip().lower()
        if "invalid" in out:
            return False, "not a recognizable place"
        return True, ""
    except Exception as e:
        print(f"[Understanding] place check failed: {e}")
        return True, ""  # fail open
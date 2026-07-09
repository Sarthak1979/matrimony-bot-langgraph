"""Welcome, main menu, FAQs, admin, and the master router."""
from state.bot_state import BotState
from config.settings import settings
from config.constants import AIRTABLE_FIELDS
from tools.airtable_tools import lookup_user_by_session


WELCOME_MESSAGE = (
    "👋 *Hi there!* 🙏\n\n"
    "*Namaste and welcome to Sri Vasavi Matrimony Charitable Trust by KVRSA Raju!* 💍\n\n"
    "We are here to help you find the right match for a happy and prosperous marriage.\n\n"
    "📋 *Important Notice:*\n"
    "By continuing with registration, you agree that:\n"
    "✓ Your profile data will be reviewed by our admin\n"
    "✓ Your basic details will be shared with verified community members\n"
    "✓ Your contact information will remain private\n"
    "✓ Data is used only for matrimony purposes within our community\n\n"
    "✨ *Please choose an option:*\n"
    "1️⃣ Register my Profile\n"
    "2️⃣ Search for Matches\n"
    "3️⃣ Talk to Admin\n"
    "4️⃣ FAQs\n\n"
    "👉 Reply with the option number."
)


def _main_menu_message(name: str = "") -> str:
    greeting = f"👋 Hi {name}!\n\n" if name else ""
    return greeting + _main_menu_message_body()


def _main_menu_message_body() -> str:
    return (
        "✨ *Main Menu* ✨\n\n"
        "1️⃣ Update Profile\n"
        "2️⃣ Search for Matches\n"
        "3️⃣ Talk to Admin\n"
        "4️⃣ FAQs\n\n"
        "Reply with the option number."
    )


PENDING_MESSAGE = (
    "🙏 *Dear Member,*\n\n"
    "Your profile is currently *pending admin approval*.\n"
    "Once approved, you'll be able to access the search feature. 💍\n\n"
    f"For urgent assistance, contact admin: {settings.ADMIN_PHONE}\n\n"
    "Thank you for your patience!"
)


REJECTED_MESSAGE = (
    "🙏 *Update on your profile*\n\n"
    "We're sorry — after review, your profile *could not be approved* at this time. "
    "This can happen for various reasons.\n\n"
    "Please contact our admin to understand more and resolve any issues:\n"
    f"📞 {settings.ADMIN_PHONE}"
)


ADMIN_MESSAGE = (
    "📞 *Talk to Admin*\n\n"
    "Thanks for reaching out! An admin will connect with you shortly.\n"
    f"For urgent assistance, contact: {settings.ADMIN_PHONE}\n\n"
    "Reply *menu* to return."
)


FAQ_MENU = (
    "❓ *Frequently Asked Questions* ❓\n\n"
    "1️⃣ 📝 Registration\n"
    "2️⃣ 🔍 Search & Matching\n"
    "3️⃣ 🔒 Privacy\n"
    "4️⃣ ✏️ Updates\n"
    "5️⃣ 📞 Support\n"
    "6️⃣ 📖 Show All FAQs\n\n"
    "Reply with the number, or *menu* to go back."
)


FAQ_REGISTRATION = (
    "📝 *Registration FAQs*\n\n"
    "❓ *How do I register?*\n"
    "✅ Reply *1* from the main menu to start registration.\n\n"
    "❓ *Can I upload my biodata?*\n"
    "✅ Yes! PDF or Image biodata uploads are supported.\n\n"
    "❓ *How long does approval take?*\n"
    "⏳ Approval typically takes *24-48 hours*.\n\n"
    "Reply *faq* to see more topics, or *menu* to return."
)


FAQ_SEARCH = (
    "🔍 *Search & Matching FAQs*\n\n"
    "❓ *When can I search for matches?*\n"
    "✅ Search is available *only after admin approval*.\n\n"
    "❓ *What filters can I use?*\n"
    "🎯 You can filter by *Age*, *Nakshatra*, and *Rashi*.\n\n"
    "❓ *How many profiles can I view?*\n"
    "♾️ Unlimited matching profiles based on your filters.\n\n"
    "Reply *faq* to see more topics, or *menu* to return."
)


FAQ_PRIVACY = (
    "🔒 *Privacy FAQs*\n\n"
    "❓ *Are my contact and family details private?*\n"
    "🔐 Yes! Contact and family details are *never* shared in search results.\n\n"
    "❓ *What information is visible in search?*\n"
    "👁️ Only basic profile info (name, age, education, etc.) is visible.\n\n"
    "❓ *Is the platform secure?*\n"
    "🛡️ Yes — it's a secure community platform with verified members.\n\n"
    "Reply *faq* to see more topics, or *menu* to return."
)


FAQ_UPDATES = (
    "✏️ *Profile Updates FAQs*\n\n"
    "❓ *Can I update my profile?*\n"
    "✅ Yes, anytime from the main menu (option 1).\n\n"
    "❓ *What fields can I change?*\n"
    "📝 You can change your photo and all profile details.\n\n"
    "❓ *Do updates require re-approval?*\n"
    "⚠️ Some major changes may require admin re-approval.\n\n"
    "Reply *faq* to see more topics, or *menu* to return."
)


FAQ_SUPPORT = (
    "📞 *Support FAQs*\n\n"
    "❓ *How do I contact admin?*\n"
    f"📱 Call *{settings.ADMIN_PHONE}* anytime.\n\n"
    "❓ *When is support available?*\n"
    "🕐 During business hours.\n\n"
    "Reply *faq* to see more topics, or *menu* to return."
)


def _faq_all() -> str:
    return (
        FAQ_REGISTRATION + "\n\n" + "═" * 30 + "\n\n" +
        FAQ_SEARCH + "\n\n" + "═" * 30 + "\n\n" +
        FAQ_PRIVACY + "\n\n" + "═" * 30 + "\n\n" +
        FAQ_UPDATES + "\n\n" + "═" * 30 + "\n\n" +
        FAQ_SUPPORT
    )


# ---------- Conversational helpers (make the bot feel human) ----------

import re as _re

_GREETING_WORDS = {
    "hi", "hello", "hey", "hii", "hiii", "helo", "hlo", "hyy", "hy",
    "namaste", "namaskar", "vanakkam", "good morning", "good afternoon",
    "good evening", "gm", "ge", "hola", "yo", "heya",
}

_THANKS_WORDS = {
    "thanks", "thank you", "thankyou", "thnx", "thx", "ty", "tysm",
    "thank u", "thanku", "shukriya", "dhanyavad", "dhanyawad", "great thanks",
    "thanks a lot", "thank you so much", "much appreciated", "appreciate it",
}

_BYE_WORDS = {"bye", "goodbye", "see you", "see ya", "tata", "cya", "good night", "gn"}


def _strip_smalltalk(text: str) -> str:
    """Remove leading greeting/thanks words so 'hi 1' -> '1',
    'hello i want to register' -> 'i want to register'."""
    t = text.strip().lower()
    # Remove greeting/filler words from the start, repeatedly
    fillers = (list(_GREETING_WORDS) + ["please", "pls", "plz", "i", "want", "to",
               "wanna", "would", "like", "can", "you", "me", "kindly", "just"])
    # Only strip a leading greeting token, then return the rest
    words = t.split()
    while words and words[0].strip(",.!") in _GREETING_WORDS:
        words = words[1:]
    return " ".join(words).strip()


def _is_only_greeting(text: str) -> bool:
    t = text.strip().lower().strip(",.!?")
    return t in _GREETING_WORDS


def _is_only_thanks(text: str) -> bool:
    t = text.strip().lower().strip(",.!?")
    return t in _THANKS_WORDS


def _is_only_bye(text: str) -> bool:
    t = text.strip().lower().strip(",.!?")
    return t in _BYE_WORDS


def _extract_menu_number(text: str) -> str:
    """If the message contains a standalone 1-4 (e.g. 'hi 1', 'option 2'),
    return that digit; else ''."""
    m = _re.search(r"\b([1-4])\b", text)
    return m.group(1) if m else ""


# ---------- Router ----------

def router_node(state: BotState) -> BotState:
    session_id = state.get("session_id", "")
    ui = state.get("user_input", "").strip().lower()

    # Always refresh registration + approval from Airtable
    record, profile_type = lookup_user_by_session(session_id)
    if record:
        state["is_registered"] = True
        state["airtable_record_id"] = record["id"]
        state["category"] = profile_type
        fields = record.get("fields", {})
        approval = fields.get(AIRTABLE_FIELDS["admin_approval"], "Pending")
        approval_norm = str(approval).strip().lower()
        state["is_approved"] = (approval_norm == "approved")
        state["is_rejected"] = (approval_norm == "rejected")
        if "collected_data" not in state:
            state["collected_data"] = {}
        name = fields.get(AIRTABLE_FIELDS["full_name"])
        if name:
            state["collected_data"]["full_name"] = name
    else:
        state["is_registered"] = False
        state["is_approved"] = False
        state["is_rejected"] = False

    # Universal commands work from any flow
    # Special: UI sends this right after detecting admin approval
    if ui == "__approved__":
        state["approval_announced"] = True
        return _go_to_menu(state)

    if ui in ("menu", "main menu", "home", "start"):
        return _go_to_menu(state)
    if ui in ("faq", "faqs", "help"):
        return _go_to_faq(state)

    flow = state.get("current_flow", "welcome")

    # --- Conversational small talk (only when NOT mid-form) ---
    # Mid-flow (registration/search/update) we let the flow handle input.
    if flow not in ("registration", "search", "update"):
        raw = state.get("user_input", "").strip()
        name = state.get("collected_data", {}).get("full_name", "")
        first_name = name.split()[0] if name else ""

        # Pure "thank you"
        if _is_only_thanks(raw):
            warm = f"You're most welcome{', ' + first_name if first_name else ''}! 🙏"
            if state.get("is_registered") and not state.get("is_approved") and not state.get("is_rejected"):
                state["reply"] = warm + "\n\nThanks for your patience while our admin reviews your profile. 💍"
            elif state.get("is_registered"):
                state["reply"] = warm + "\n\n" + _main_menu_message(name)
                state["current_flow"] = "main_menu"
            else:
                state["reply"] = warm + " Whenever you're ready, reply *1* to register. 😊"
            state["awaiting"] = "text"
            return state

        # Pure "bye"
        if _is_only_bye(raw):
            state["reply"] = (
                f"Take care{', ' + first_name if first_name else ''}! 🙏 "
                "Come back anytime — your session stays saved. 💍"
            )
            state["awaiting"] = "text"
            return state

        # Pure greeting (no other intent)
        if _is_only_greeting(raw):
            if state.get("is_registered") and state.get("is_approved"):
                state["reply"] = f"👋 Hello{', ' + first_name if first_name else ''}! Good to see you again.\n\n" + _main_menu_message_body()
                state["current_flow"] = "main_menu"
            elif state.get("is_registered") and state.get("is_rejected"):
                state["reply"] = REJECTED_MESSAGE
                state["current_flow"] = "pending"
            elif state.get("is_registered"):
                state["reply"] = PENDING_MESSAGE
                state["current_flow"] = "pending"
            else:
                # New visitor — short, warm greeting in its OWN bubble, then the
                # options in a SECOND bubble (UI splits on <<SPLIT>>).
                state["reply"] = (
                    "👋 *Namaste!* 🙏 Lovely to have you here."
                    "<<SPLIT>>"
                    "I can help you find a life partner within our community. "
                    "What would you like to do?\n\n"
                    "1️⃣ Register my Profile\n"
                    "2️⃣ Search for Matches\n"
                    "3️⃣ Talk to Admin\n"
                    "4️⃣ FAQs\n\n"
                    "👉 Just reply with a number, or tell me in your own words. 😊"
                )
                state["current_flow"] = "welcome"
            state["awaiting"] = "text"
            return state

        # Greeting + intent mixed in (e.g. "hi 1", "hello i want to register")
        if any(raw.lower().startswith(g) for g in _GREETING_WORDS):
            num = _extract_menu_number(raw)
            stripped = _strip_smalltalk(raw)
            if num:
                state["user_input"] = num
                ui = num
            elif stripped:
                state["user_input"] = stripped
                ui = stripped.lower()

    # If we're mid-flow, hand off to that flow
    if flow == "registration":
        return state
    if flow == "search":
        return state
    if flow == "update":
        return state

    # FAQ sub-menu navigation
    if flow == "faq_menu":
        return _handle_faq_choice(state, ui)

    # Welcome
    if flow == "welcome" or not flow:
        if state.get("is_registered"):
            if state.get("is_approved"):
                state["current_flow"] = "main_menu"
                name = state.get("collected_data", {}).get("full_name", "")
                state["reply"] = _main_menu_message(name)
            elif state.get("is_rejected"):
                state["current_flow"] = "pending"
                state["reply"] = REJECTED_MESSAGE
            else:
                state["current_flow"] = "pending"
                state["reply"] = PENDING_MESSAGE
            state["awaiting"] = "text"
            return state
        if not ui:
            state["reply"] = WELCOME_MESSAGE
            state["awaiting"] = "text"
            state["current_flow"] = "welcome"
            return state
        return _handle_welcome_choice(state, ui)

    if flow == "pending":
        if state.get("is_approved"):
            state["current_flow"] = "main_menu"
            name = state.get("collected_data", {}).get("full_name", "")
            state["reply"] = (
                "🎉 *Great news! Your profile has been approved!*\n\n"
                + _main_menu_message(name)
            )
        elif state.get("is_rejected"):
            state["reply"] = REJECTED_MESSAGE
        else:
            state["reply"] = PENDING_MESSAGE
        state["awaiting"] = "text"
        return state

    if flow == "main_menu":
        return _handle_main_menu_choice(state, ui)

    # Fallback: gently redirect
    return _gentle_redirect(state)


def _go_to_menu(state: BotState) -> BotState:
    state["current_step"] = ""
    state["search_step"] = None
    if state.get("is_registered"):
        state["current_flow"] = "main_menu"
        name = state.get("collected_data", {}).get("full_name", "")
        state["reply"] = _main_menu_message(name)
    else:
        state["current_flow"] = "welcome"
        state["reply"] = WELCOME_MESSAGE
    state["awaiting"] = "text"
    return state


def _go_to_faq(state: BotState) -> BotState:
    state["current_flow"] = "faq_menu"
    state["reply"] = FAQ_MENU
    state["awaiting"] = "text"
    return state


def _handle_faq_choice(state: BotState, ui: str) -> BotState:
    mapping = {
        "1": FAQ_REGISTRATION,
        "2": FAQ_SEARCH,
        "3": FAQ_PRIVACY,
        "4": FAQ_UPDATES,
        "5": FAQ_SUPPORT,
        "6": _faq_all(),
    }
    if ui in mapping:
        state["reply"] = mapping[ui]
        state["awaiting"] = "text"
        return state
    # Try to answer a natural-language FAQ question
    faq_answer = _match_faq_question(state.get("user_input", ""))
    if faq_answer:
        state["reply"] = faq_answer + "\n\n" + FAQ_MENU
        state["awaiting"] = "text"
        return state
    # Unknown input in FAQ menu — show menu again
    state["reply"] = "🤔 I didn't understand that.\n\n" + FAQ_MENU
    state["awaiting"] = "text"
    return state


def _match_faq_question(text: str) -> str:
    """Detect a natural-language FAQ question and return an answer, or ''."""
    t = text.lower()
    # (keywords, answer)
    faqs = [
        (["how", "register"], "📝 To register, reply *1* from the main menu and follow the steps. You can upload a biodata (PDF/image) or fill details manually."),
        (["upload", "biodata"], "📄 Yes — you can upload your biodata as a PDF or image, and I'll extract the details automatically."),
        (["how long", "approval"], "⏳ Profile approval usually takes *24–48 hours*. You'll be notified here automatically once approved."),
        (["approval", "time"], "⏳ Profile approval usually takes *24–48 hours*."),
        (["when", "search"], "🔍 Search becomes available *after admin approval* of your profile."),
        (["filter", "search"], "🎯 You can filter matches by *Age*, *Nakshatra*, and *Rashi*."),
        (["how many", "profile"], "♾️ You can view unlimited matching profiles based on your filters."),
        (["private", "contact"], "🔐 Yes — your contact and family details are kept private and never shown in search results."),
        (["secure", "safe"], "🛡️ Yes, this is a secure community platform with verified members."),
        (["update", "profile"], "✏️ Yes — you can update your profile anytime from the main menu (option 1)."),
        (["change", "photo"], "📸 Yes — you can change your photo and other details from the Update Profile option."),
        (["contact", "admin"], "📞 You can reach our admin anytime at *+91 8660038025*."),
        (["support", "help"], "📞 For support, call our admin at *+91 8660038025* during business hours."),
    ]
    for keywords, answer in faqs:
        if all(k in t for k in keywords):
            return answer
    return ""


def _conversational_deflection(user_text: str) -> str:
    """For clearly off-topic chit-chat (weather, jokes, general questions),
    give a warm one-line acknowledgement, then steer back to matrimony.
    Uses AI if available; falls back to a friendly canned line."""
    try:
        from tools.intent_tools import _get_client
        from config.settings import settings
        client = _get_client()
        if client is None:
            return ""
        sys_prompt = (
            "You are a warm, friendly matrimony assistant for Sri Vasavi Matrimony. "
            "The user said something off-topic (not about matrimony/registration/matches). "
            "Reply in ONE short, polite sentence acknowledging them warmly, then gently "
            "steer back to helping them with matrimony. Do NOT answer the off-topic "
            "question in detail. Keep it under 30 words. Be human and kind."
        )
        resp = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_text[:200]},
            ],
            temperature=0.6,
            max_tokens=60,
            timeout=8,
        )
        out = resp.choices[0].message.content.strip()
        return out
    except Exception as e:
        print(f"[Deflection] AI unavailable ({e})")
        return ""


def _gentle_redirect(state: BotState) -> BotState:
    """Off-topic input — answer as an FAQ if possible, else acknowledge warmly
    (ChatGPT-style) and steer back to the matrimony task."""
    ui_raw = state.get("user_input", "")
    name = state.get("collected_data", {}).get("full_name", "")

    # 1) If it's actually a matrimony FAQ, answer it directly
    faq_answer = _match_faq_question(ui_raw)
    if faq_answer:
        if state.get("is_registered"):
            state["reply"] = faq_answer + "\n\n" + _main_menu_message(name)
            state["current_flow"] = "main_menu"
        else:
            state["reply"] = faq_answer + "\n\nReply *1* to register, or ask another question."
            state["current_flow"] = "welcome"
        state["awaiting"] = "text"
        return state

    # 2) Off-topic chit-chat — warm acknowledgement + steer back
    ack = _conversational_deflection(ui_raw)
    if not ack:
        ack = "😊 That's a little outside what I can help with — but I'm here for your matrimony journey!"

    if state.get("is_registered"):
        state["reply"] = ack + "\n\n" + _main_menu_message(name)
        state["current_flow"] = "main_menu"
    else:
        state["reply"] = (
            ack + "\n\n"
            "Shall we continue? 💍\n"
            "1️⃣ Register my Profile\n"
            "2️⃣ Search for Matches\n"
            "3️⃣ Talk to Admin\n"
            "4️⃣ FAQs"
        )
        state["current_flow"] = "welcome"
    state["awaiting"] = "text"
    return state


def _handle_welcome_choice(state: BotState, ui: str) -> BotState:
    # Map free-text/natural language to a number choice
    if ui not in ("1", "2", "3", "4"):
        from tools.intent_tools import classify_intent
        intent = classify_intent(ui, allowed=["register", "search", "admin", "faq", "menu"])
        ui = {"register": "1", "search": "2", "admin": "3", "faq": "4"}.get(intent, ui)

    if ui == "1":
        state["current_flow"] = "registration"
        state["current_step"] = ""
        state["reply"] = ""
        return state
    if ui == "2":
        if not state.get("is_registered"):
            state["reply"] = (
                "🚫 You need to *register first* before searching for matches.\n\n"
                + WELCOME_MESSAGE
            )
            state["awaiting"] = "text"
            return state
        if not state.get("is_approved"):
            state["reply"] = REJECTED_MESSAGE if state.get("is_rejected") else PENDING_MESSAGE
            state["awaiting"] = "text"
            return state
        state["current_flow"] = "search"
        state["search_step"] = "age"
        state["search_age_min"] = None
        state["search_age_max"] = None
        state["search_nakshatra"] = None
        state["search_rashi"] = None
        state["shown_record_ids"] = []
        return state
    if ui == "3":
        state["reply"] = ADMIN_MESSAGE
        state["awaiting"] = "text"
        return state
    if ui == "4":
        return _go_to_faq(state)
    return _gentle_redirect(state)


def _handle_main_menu_choice(state: BotState, ui: str) -> BotState:
    # Map free-text/natural language to a number choice
    if ui not in ("1", "2", "3", "4"):
        from tools.intent_tools import classify_intent
        intent = classify_intent(ui, allowed=["update", "search", "admin", "faq", "menu"])
        ui = {"update": "1", "search": "2", "admin": "3", "faq": "4"}.get(intent, ui)

    if ui == "1":
        state["current_flow"] = "update"
        state["current_step"] = "show_profile"
        state["update_field_name"] = None
        state["reply"] = ""
        return state
    if ui == "2":
        if not state.get("is_approved"):
            state["reply"] = REJECTED_MESSAGE if state.get("is_rejected") else PENDING_MESSAGE
            state["awaiting"] = "text"
            return state
        state["current_flow"] = "search"
        state["search_step"] = "age"
        state["search_age_min"] = None
        state["search_age_max"] = None
        state["search_nakshatra"] = None
        state["search_rashi"] = None
        state["shown_record_ids"] = []
        return state
    if ui == "3":
        state["reply"] = ADMIN_MESSAGE
        state["awaiting"] = "text"
        return state
    if ui == "4":
        return _go_to_faq(state)
    return _gentle_redirect(state)
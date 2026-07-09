"""Search flow: only for approved users.
Features:
  - Re-verifies approval from DB every turn
  - Returns rich card data (photo + bio) instead of plain text
  - Tracks already-shown matches; user can ask for "more" to get fresh ones
"""
from state.bot_state import BotState
from config.constants import AIRTABLE_FIELDS, NAKSHATRA_LIST, RASHI_LIST
from validators.field_validators import validate_age_range
from validators.autocorrect import autocorrect_nakshatra, autocorrect_rashi
from tools.airtable_tools import search_matches, get_approval_status


# Sentinel reply prefix that Streamlit UI recognizes to render rich cards
RICH_CARD_PREFIX = "<<MATCH_CARDS>>"


def search_node(state: BotState) -> BotState:
    step = state.get("search_step") or "age"
    ui = state.get("user_input", "").strip()
    category = state.get("category", "Groom")
    record_id = state.get("airtable_record_id", "")

    # CRITICAL: re-verify approval from DB every turn
    if record_id:
        live_status = str(get_approval_status(category, record_id)).strip().lower()
        if live_status != "approved":
            if live_status == "rejected":
                state["reply"] = (
                    "🙏 *Update on your profile*\n\n"
                    "We're sorry — your profile could not be approved at this time.\n"
                    "Please contact our admin to resolve this:\n"
                    "📞 +91 8660038025"
                )
            else:
                state["reply"] = (
                    "🙏 Your profile is currently pending admin approval.\n"
                    "Once approved, you'll be able to search for matches.\n\n"
                    "For urgent assistance, contact admin: +91 8660038025"
                )
            state["current_flow"] = "main_menu"
            state["search_step"] = None
            state["awaiting"] = "text"
            return state

    # First entry: bot was just delegated to from main_menu with ui "2"
    is_first_entry = (
        step == "age"
        and state.get("search_age_min") is None
        and (ui == "" or ui == "2")
    )
    if is_first_entry:
        state["reply"] = (
            "✨ *Search for Matches* ✨\n\n"
            "Let's find you a match based on your preferences.\n\n"
            "1️⃣ Please enter your *preferred age RANGE* — a minimum and a maximum age.\n\n"
            "📝 Format: *min-max*\n"
            "✅ Examples: *25-30*,  *28-35*,  *30 to 40*\n"
            "⚠️ Please enter a *range*, not a single age."
        )
        state["search_step"] = "age"
        state["awaiting"] = "text"
        return state

    if step == "age":
        ok, age_tuple = validate_age_range(ui)
        if not ok:
            # Friendly, specific hint — especially if they typed a single number
            if ui.strip().isdigit():
                state["reply"] = (
                    f"🙏 You entered a single age (*{ui.strip()}*), but I need a *range*.\n\n"
                    "Please give a minimum and maximum age.\n"
                    f"📝 Example: if you're open to ages around {ui.strip()}, try "
                    f"*{max(18, int(ui.strip())-3)}-{int(ui.strip())+3}*."
                )
            else:
                state["reply"] = (
                    "❌ I couldn't read that age range.\n\n"
                    "📝 Format: *min-max*\n"
                    "✅ Examples: *25-30*,  *28-35*,  *30 to 40*"
                )
            state["awaiting"] = "text"
            return state
        state["search_age_min"], state["search_age_max"] = age_tuple
        state["search_step"] = "nakshatra"
        nlines = ["2️⃣ *Preferred Nakshatra* (optional)\n",
                  "Type *skip* to see all, or choose one:\n"]
        for i, n in enumerate(NAKSHATRA_LIST, 1):
            nlines.append(f"{i}. {n}")
        nlines.append("\nReply with a number, the name, or *skip*.")
        state["reply"] = "\n".join(nlines)
        state["awaiting"] = "text"
        return state

    if step == "nakshatra":
        if ui.lower() == "skip":
            state["search_nakshatra"] = None
        else:
            n = autocorrect_nakshatra(ui)
            if not n:
                state["reply"] = "❌ Could not recognize that Nakshatra. Type the name or *skip*."
                state["awaiting"] = "text"
                return state
            state["search_nakshatra"] = n
        state["search_step"] = "rashi"
        rlines = ["3️⃣ *Preferred Rashi* (optional)\n",
                  "Type *skip* to see all, or choose one:\n"]
        for i, r in enumerate(RASHI_LIST, 1):
            rlines.append(f"{i}. {r}")
        rlines.append("\nReply with a number, the name, or *skip*.")
        state["reply"] = "\n".join(rlines)
        state["awaiting"] = "text"
        return state

    if step == "rashi":
        if ui.lower() == "skip":
            state["search_rashi"] = None
        else:
            r = autocorrect_rashi(ui)
            if not r:
                state["reply"] = "❌ Could not recognize that Rashi. Type the name or *skip*."
                state["awaiting"] = "text"
                return state
            state["search_rashi"] = r
        # Reset shown-records list for a NEW search
        state["shown_record_ids"] = []
        return _execute_search(state)

    if step == "results":
        # User is looking at results - decide what to do based on their input
        if ui.lower() in ("more", "more matches", "next", "show more"):
            return _execute_search(state)
        if ui.lower() in ("menu", "main menu", "home"):
            state["current_flow"] = "main_menu"
            state["search_step"] = None
            state["reply"] = "Returning to main menu..."
            state["awaiting"] = "text"
            return state
        # Off-topic at results stage - gentle nudge
        state["reply"] = (
            "🤔 You're looking at search results.\n\n"
            "Reply *more* to see more matches, or *menu* to go back to main menu."
        )
        state["awaiting"] = "text"
        return state

    # Default
    state["search_step"] = "age"
    state["reply"] = "Let's start your search. Please enter age range like 25-30."
    state["awaiting"] = "text"
    return state


def _execute_search(state: BotState) -> BotState:
    category = state.get("category", "Groom")
    shown = state.get("shown_record_ids") or []

    # Fetch more than we need so we can filter out already-shown ones
    matches = search_matches(
        seeker_profile_type=category,
        age_min=state.get("search_age_min", 18),
        age_max=state.get("search_age_max", 100),
        nakshatra=state.get("search_nakshatra"),
        rashi=state.get("search_rashi"),
        limit=50,
    )

    # Filter out already-shown
    fresh = [m for m in matches if m["record"]["id"] not in shown]
    next_batch = fresh[:2]   # Show 2 at a time

    if not next_batch:
        if shown:
            state["reply"] = (
                "🙏 No more matches available with your current filters.\n\n"
                "You've seen all approved profiles matching your criteria.\n"
                "For more options, contact admin: *+91 8660038025*\n\n"
                "Reply *menu* to go back."
            )
        else:
            state["reply"] = (
                "😔 No matches found with your current criteria.\n\n"
                "Try a wider age range, or contact admin for help.\n"
                "Reply *menu* to go back."
            )
        # Reset to allow new search
        state["search_step"] = "results"
        state["current_flow"] = "search"
        state["awaiting"] = "text"
        return state

    # Build rich card payload (JSON-like list) AFTER the prefix sentinel.
    # Streamlit UI will detect the prefix and render cards.
    import json
    cards = []
    for m in next_batch:
        f = m["record"].get("fields", {})
        # Photo: first attachment's URL
        photo_url = None
        photo_field = f.get(AIRTABLE_FIELDS["person_image"]) or []
        if isinstance(photo_field, list) and photo_field:
            photo_url = photo_field[0].get("url")
        cards.append({
            "name": str(f.get(AIRTABLE_FIELDS["full_name"], "N/A")),
            "age": m["age"],
            "height_cm": f.get(AIRTABLE_FIELDS["height"], None),
            "nakshatra": str(f.get(AIRTABLE_FIELDS["nakshatra"], "N/A")),
            "rashi": str(f.get(AIRTABLE_FIELDS["rashi"], "N/A")),
            "qualification": str(f.get(AIRTABLE_FIELDS["qualification"], "N/A")),
            "profession": str(f.get(AIRTABLE_FIELDS["profession"], "N/A")),
            "place": str(f.get(AIRTABLE_FIELDS["place_of_birth"], "N/A")),
            "country": str(f.get(AIRTABLE_FIELDS["country_of_person"], "N/A")),
            "photo_url": photo_url,
        })
        shown.append(m["record"]["id"])

    state["shown_record_ids"] = shown

    remaining = len(fresh) - len(next_batch)
    footer_lines = [
        "",
        f"💍 *Showing {len(next_batch)} match(es).*"
        + (f" {remaining} more available." if remaining > 0 else " No more left."),
        "",
        "👉 Reply *more* to see more matches",
        "👉 Reply *menu* to go back to main menu",
        "👉 To connect, contact admin: *+91 8660038025*",
    ]

    state["reply"] = RICH_CARD_PREFIX + json.dumps(cards) + "\n" + "\n".join(footer_lines)
    state["search_step"] = "results"
    state["current_flow"] = "search"
    state["awaiting"] = "text"
    return state
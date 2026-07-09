"""Update profile flow.

User journey:
  1. User picks 'Update Profile' from main menu
  2. Bot shows their FULL PROFILE CARD with photo first
  3. Bot asks which field they want to change
  4. User types field name -> bot prompts for new value with current shown
  5. User provides value -> validated -> written back to Airtable
  6. Loop: ask if they want to update more, or return to menu

Works for both approved AND pending users.
"""
import json
from state.bot_state import BotState
from config.constants import (
    FIELD_KEYWORD_MAP, RESTRICTED_FIELDS, FIELD_LABELS,
    NAKSHATRA_LIST, RASHI_LIST, SALARY_BANDS, PROPERTY_BANDS, AIRTABLE_FIELDS,
)
from validators.field_validators import (
    validate_full_name, validate_dob, validate_time_of_birth,
    validate_place_of_birth, validate_height, validate_gothram,
    validate_text_min_2, validate_alpha_name, validate_contact_number,
    validate_menu_choice, calculate_age,
)
from validators.autocorrect import autocorrect_nakshatra, autocorrect_rashi
from tools.airtable_tools import update_profile_field, _table
from datetime import datetime


# Distinct sentinel: the user's OWN profile card (rendered as "Your Profile",
# not "Suggested Matches").
RICH_CARD_PREFIX = "<<MATCH_CARDS>>"
MY_CARD_PREFIX = "<<MY_PROFILE_CARD>>"


def _build_my_card(state: BotState) -> str:
    """Build a rich card JSON for the user's OWN profile, fetched fresh from Airtable."""
    record_id = state.get("airtable_record_id")
    if not record_id:
        return ""
    try:
        record = _table().get(record_id)
    except Exception as e:
        print(f"[Update] could not fetch own record: {e}")
        return ""
    f = record.get("fields", {})
    photo_url = None
    photo_field = f.get(AIRTABLE_FIELDS["person_image"]) or []
    if isinstance(photo_field, list) and photo_field:
        photo_url = photo_field[0].get("url")
    age_val = f.get(AIRTABLE_FIELDS["age"])
    if isinstance(age_val, str):
        import re
        m = re.search(r"(\d{1,3})", age_val)
        age_val = int(m.group(1)) if m else "N/A"
    card = {
        "name": str(f.get(AIRTABLE_FIELDS["full_name"], "N/A")),
        "age": age_val if age_val is not None else "N/A",
        "height_cm": f.get(AIRTABLE_FIELDS["height"]),
        "nakshatra": str(f.get(AIRTABLE_FIELDS["nakshatra"], "N/A")),
        "rashi": str(f.get(AIRTABLE_FIELDS["rashi"], "N/A")),
        "qualification": str(f.get(AIRTABLE_FIELDS["qualification"], "N/A")),
        "profession": str(f.get(AIRTABLE_FIELDS["profession"], "N/A")),
        "place": str(f.get(AIRTABLE_FIELDS["place_of_birth"], "N/A")),
        "country": str(f.get(AIRTABLE_FIELDS["country_of_person"], "N/A")),
        "photo_url": photo_url,
    }
    return MY_CARD_PREFIX + json.dumps([card])


def update_node(state: BotState) -> BotState:
    step = state.get("current_step") or "show_profile"
    ui = state.get("user_input", "").strip()
    record_id = state.get("airtable_record_id")
    category = state.get("category", "Groom")

    if not record_id:
        state["reply"] = "🚫 You need to register first."
        state["current_flow"] = "welcome"
        state["awaiting"] = "text"
        return state

    # ---------- Show profile card on first entry ----------
    if step == "show_profile" or step == "":
        card = _build_my_card(state)
        footer = (
            "\n\n📋 *Your current profile is shown above.*\n\n"
            "Which field would you like to update?\n"
            "Type a field name (e.g. *height*, *qualification*, *contact*, *nakshatra*, *photo*).\n"
            "Or reply *menu* to go back."
        )
        state["reply"] = (card + footer) if card else (
            "📋 Your profile is shown above.\n\n"
            "Which field would you like to update? Type a field name.\n"
            "Or reply *menu* to go back."
        )
        state["current_step"] = "select_field"
        state["awaiting"] = "text"
        return state

    # ---------- Field selection ----------
    if step == "select_field":
        lowered = ui.lower()
        field_key = None
        # Sort by length descending so "father name" matches before "name"
        for kw in sorted(FIELD_KEYWORD_MAP.keys(), key=len, reverse=True):
            if kw in lowered:
                field_key = FIELD_KEYWORD_MAP[kw]
                break
        if not field_key:
            state["reply"] = (
                "❌ I didn't recognize that field.\n\n"
                "Try: *height*, *qualification*, *contact*, *nakshatra*, *rashi*, "
                "*profession*, *salary*, *photo*, etc.\n\n"
                "Or reply *menu* to go back."
            )
            state["awaiting"] = "text"
            return state
        if field_key in RESTRICTED_FIELDS:
            state["reply"] = (
                "🚫 That field cannot be updated by users (admin-only).\n"
                "Please contact admin: +91 8660038025"
            )
            state["awaiting"] = "text"
            return state

        state["update_field_name"] = field_key
        state["current_step"] = "enter_new_value"
        label = FIELD_LABELS.get(field_key, field_key)

        if field_key == "person_image":
            state["reply"] = f"📸 Please upload your new photo (JPG/PNG)."
            state["awaiting"] = "photo"
            return state
        if field_key == "nakshatra":
            lines = [f"🌟 Please select your new *{label}*:\n"]
            for i, n in enumerate(NAKSHATRA_LIST, 1):
                lines.append(f"{i}. {n}")
            lines.append("\nReply with the number (1-27) or the name.")
            state["reply"] = "\n".join(lines)
        elif field_key == "rashi":
            lines = [f"♋ Please select your new *{label}*:\n"]
            for i, r in enumerate(RASHI_LIST, 1):
                lines.append(f"{i}. {r}")
            lines.append("\nReply with the number (1-12) or the name.")
            state["reply"] = "\n".join(lines)
        elif field_key == "salary_package":
            lines = [f"💰 Please select your new *{label}*:\n"]
            for i, s in enumerate(SALARY_BANDS, 1):
                lines.append(f"{i}️⃣ {s}")
            state["reply"] = "\n".join(lines)
        elif field_key == "property_details":
            lines = [f"🏡 Please select your new *{label}*:\n"]
            for i, p in enumerate(PROPERTY_BANDS, 1):
                lines.append(f"{i}️⃣ {p}")
            state["reply"] = "\n".join(lines)
        else:
            state["reply"] = f"👉 Please provide the new *{label}*."
        state["awaiting"] = "text" if field_key != "person_image" else "photo"
        return state

    # ---------- Enter new value ----------
    if step == "enter_new_value":
        field_key = state.get("update_field_name", "")

        # Photo update via file upload
        if field_key == "person_image":
            file_path = state.get("uploaded_file_path")
            if not file_path:
                state["reply"] = "📸 I'm waiting for your photo. Please upload a JPG or PNG."
                state["awaiting"] = "photo"
                return state
            from tools.airtable_tools import attach_file_from_path
            ok = attach_file_from_path(category, record_id, "person_image", file_path)
            state["uploaded_file_path"] = None
            state["uploaded_file_kind"] = None
            if ok:
                state["reply"] = (
                    "✅ *Photo updated successfully!*\n\n"
                    "Want to update another field? Type the field name, or *menu* to return."
                )
            else:
                state["reply"] = "⚠️ Photo upload failed. Please try again or contact admin."
            state["current_step"] = "select_field"
            state["awaiting"] = "text"
            return state

        ok, value = _validate_update(field_key, ui, state.get("collected_data", {}))
        if not ok:
            state["reply"] = value
            state["awaiting"] = "text"
            return state
        try:
            update_profile_field(category, record_id, field_key, value)
            state["collected_data"][field_key] = value
            label = FIELD_LABELS.get(field_key, field_key)
            state["reply"] = (
                f"✅ *{label}* updated to: *{value}*\n\n"
                "Want to update another field? Type the field name, or *menu* to return."
            )
            state["current_step"] = "select_field"
            state["awaiting"] = "text"
        except Exception as e:
            state["reply"] = f"⚠️ Update failed: {e}"
            state["awaiting"] = "text"
        return state

    # Default fallback
    state["reply"] = "Which field would you like to update? (or reply *menu*)"
    state["current_step"] = "select_field"
    state["awaiting"] = "text"
    return state


def _validate_update(field_key: str, ui: str, data: dict):
    if field_key == "full_name":
        return validate_full_name(ui)
    if field_key == "dob":
        return validate_dob(ui)
    if field_key == "time_of_birth":
        return validate_time_of_birth(ui)
    if field_key == "place_of_birth":
        return validate_place_of_birth(ui)
    if field_key == "height":
        return validate_height(ui)
    if field_key == "swa_gothram":
        return validate_gothram(ui)
    if field_key == "maternal_gothram":
        ok, normalized = validate_gothram(ui)
        if not ok:
            return False, normalized
        swa = data.get("swa_gothram", "")
        if swa and normalized.strip().lower() == swa.strip().lower():
            return False, "❌ Maternal Gothram cannot match Swa Gothram."
        return True, normalized
    if field_key in ("qualification", "profession", "father_occupation", "mother_occupation"):
        return validate_text_min_2(ui)
    if field_key in ("father_name", "mother_name"):
        return validate_alpha_name(ui)
    if field_key == "contact_number":
        return validate_contact_number(ui)
    if field_key in ("country_of_person", "country_of_parents"):
        if len(ui.strip()) < 3:
            return False, "❌ Please share a valid City, Country."
        return True, ui.strip().title()
    if field_key == "nakshatra":
        n = autocorrect_nakshatra(ui)
        if not n:
            return False, "❌ Could not recognize that Nakshatra."
        return True, n
    if field_key == "rashi":
        r = autocorrect_rashi(ui)
        if not r:
            return False, "❌ Could not recognize that Rashi."
        return True, r
    if field_key == "salary_package":
        from nodes.registration_node import _match_band
        matched = _match_band(ui, SALARY_BANDS)
        if not matched:
            return False, f"❌ Reply with a number 1-{len(SALARY_BANDS)} or paste the option text."
        return True, matched
    if field_key == "property_details":
        from nodes.registration_node import _match_band
        matched = _match_band(ui, PROPERTY_BANDS)
        if not matched:
            return False, f"❌ Reply with a number 1-{len(PROPERTY_BANDS)} or paste the option text."
        return True, matched
    return True, ui.strip()
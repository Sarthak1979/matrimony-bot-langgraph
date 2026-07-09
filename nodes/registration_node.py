"""Registration flow node. Drives the user through all registration steps."""
from typing import Dict, Any
from datetime import datetime

from state.bot_state import BotState
from config.constants import (
    NAKSHATRA_LIST, RASHI_LIST, SALARY_BANDS, PROPERTY_BANDS,
    REGISTRATION_STEPS, FIELD_LABELS, OCR_EXTRACTABLE_FIELDS,
)
from validators.field_validators import (
    validate_full_name, validate_dob, validate_time_of_birth,
    validate_place_of_birth, validate_height, validate_gothram,
    validate_maternal_gothram, validate_text_min_2, validate_alpha_name,
    validate_menu_choice, calculate_age,
)
from validators.autocorrect import autocorrect_nakshatra, autocorrect_rashi
from tools.airtable_tools import (
    create_profile, attach_file_from_path,
    create_draft_profile, update_profile_field,
)
from tools.ocr_tools import extract_biodata_fields


# Sentinel for review card rendering (UI detects this prefix)
REVIEW_CARD_PREFIX = "<<REVIEW_CARD>>"


def _match_band(user_input: str, bands: list) -> str | None:
    """Match user input to a band option. Accepts:
       - Number 1..N matching the band index
       - Exact band text (pasted)
       - Case-insensitive substring match against band text
    """
    ui = (user_input or "").strip()
    if not ui:
        return None
    # Number match
    if ui.isdigit():
        idx = int(ui) - 1
        if 0 <= idx < len(bands):
            return bands[idx]
        return None
    # Exact text match
    for band in bands:
        if ui == band:
            return band
    # Loose match: normalise dashes and case
    def norm(s):
        return (s.lower()
                .replace("–", "-").replace("—", "-")
                .replace("\u2013", "-").replace("\u2014", "-"))
    ui_n = norm(ui)
    for band in bands:
        if norm(band) == ui_n:
            return band
    # Substring (e.g. user typed "12-25 lakhs")
    for band in bands:
        if ui_n in norm(band):
            return band
    return None


# ---------- Prompts shown to user per step ----------

def _prompt_for_step(step: str, data: Dict[str, Any]) -> str:
    if step == "profile_type":
        return "👰 *Whose profile are you registering?*\n\n1️⃣ Bride\n2️⃣ Groom\n\nReply with 1 or 2."
    if step == "country_of_person":
        return ("🌍 Please share *your City and Country of Residence*.\n"
                "📝 Format: *City, Country*\n"
                "Example: *Indore, India*")
    if step == "country_of_parents":
        return ("🌍 Please share your *Parents' City and Country of Residence*.\n"
                "📝 Format: *City, Country*\n"
                "Example: *Mumbai, India*")
    if step == "registration_method":
        return (
            "📋 *How would you like to register?*\n\n"
            "1️⃣ Upload your biodata (PDF or Image)\n"
            "2️⃣ Fill details manually\n\n"
            "Reply with 1 or 2."
        )
    if step == "full_name":
        return "👤 Please provide your *Full Name*."
    if step == "dob":
        return "🎂 Please share your *Date of Birth* in DD-MM-YYYY format.\n(Example: 15-08-1995)"
    if step == "time_of_birth":
        return "🕒 Please share your *Time of Birth* (12-hour format).\n(Example: 08:30 AM or 06:45 PM)\n\n_Time of Birth is mandatory._"
    if step == "place_of_birth":
        return "📍 Please share your *Place of Birth*."
    if step == "height":
        return "📏 Please share your *Height*.\n(Example: 5'8\" — feet 3-7, inches 0-11)"
    if step == "nakshatra":
        lines = ["🌟 Please select your *Nakshatra (Birth Star)*:\n"]
        for i, n in enumerate(NAKSHATRA_LIST, 1):
            lines.append(f"{i}. {n}")
        lines.append("\nReply with the number (1-27) or the name.")
        return "\n".join(lines)
    if step == "rashi":
        lines = ["♋ Please select your *Rashi (Zodiac Sign)*:\n"]
        for i, r in enumerate(RASHI_LIST, 1):
            lines.append(f"{i}. {r}")
        lines.append("\nReply with the number (1-12) or the name.")
        return "\n".join(lines)
    if step == "swa_gothram":
        return "🪶 Please share your *Swa Gothram*."
    if step == "maternal_gothram":
        return "🌿 Please share your *Maternal Gothram*.\n_Must be different from Swa Gothram._"
    if step == "qualification":
        return "🎓 Please share your *Education / Qualification*."
    if step == "profession":
        return "💼 Please share your *Profession / Work*."
    if step == "salary_package":
        lines = ["💰 Please select your *Annual Income*:\n"]
        for i, s in enumerate(SALARY_BANDS, 1):
            lines.append(f"{i}️⃣ {s}")
        lines.append("\nReply with the number.")
        return "\n".join(lines)
    if step == "father_name":
        return "👨 Please share your *Father's Name*."
    if step == "mother_name":
        return "👩 Please share your *Mother's Name*."
    if step == "father_occupation":
        return "👔 Please share your *Father's Occupation*."
    if step == "mother_occupation":
        return "👗 Please share your *Mother's Occupation*."
    if step == "property_details":
        lines = ["🏡 Please select your *Property Value Range*:\n"]
        for i, p in enumerate(PROPERTY_BANDS, 1):
            lines.append(f"{i}️⃣ {p}")
        lines.append("\nReply with the number.")
        return "\n".join(lines)
    if step == "person_image":
        return "📸 Please upload a *recent clear photo* (JPG/PNG).\n\n_Photo is mandatory._"
    if step == "review":
        return _build_review_screen(data)
    return ""


def _build_review_screen(data: Dict[str, Any]) -> str:
    """Build review as a structured rich card (rendered nicely by the UI)."""
    import json
    urls = data.get("_photo_urls", [])
    photo_url = urls[0] if urls else data.get("_photo_url")
    review = {
        "full_name": data.get("full_name", "—"),
        "country_of_person": data.get("country_of_person", "—"),
        "country_of_parents": data.get("country_of_parents", "—"),
        "dob": data.get("dob", "—"),
        "time_of_birth": data.get("time_of_birth", "—"),
        "place_of_birth": data.get("place_of_birth", "—"),
        "height": data.get("height", "—"),
        "nakshatra": data.get("nakshatra", "—"),
        "rashi": data.get("rashi", "—"),
        "swa_gothram": data.get("swa_gothram", "—"),
        "maternal_gothram": data.get("maternal_gothram", "—"),
        "qualification": data.get("qualification", "—"),
        "profession": data.get("profession", "—"),
        "salary_package": data.get("salary_package", "—"),
        "father_name": data.get("father_name", "—"),
        "mother_name": data.get("mother_name", "—"),
        "father_occupation": data.get("father_occupation", "—"),
        "mother_occupation": data.get("mother_occupation", "—"),
        "property_details": data.get("property_details", "—"),
        "photo_uploaded": bool(data.get("_photo_paths") or data.get("_photo_path")),
        "photo_count": len(data.get("_photo_paths", [])) or (1 if data.get("_photo_path") else 0),
        "photo_just_received": bool(data.get("_photo_just_received")),
        "photo_url": photo_url,
        "photo_urls": urls,
        "photo_local_path": data.get("_photo_path"),
    }
    return REVIEW_CARD_PREFIX + json.dumps(review)


# ---------- Step input processing ----------

def _process_step_input(step: str, user_input: str, data: Dict[str, Any]):
    """Returns (ok, value_or_error_message, override_next_step_or_None)."""
    ui = user_input.strip()

    if step == "profile_type":
        ok, choice = validate_menu_choice(ui, 2)
        if ok:
            return True, ("Bride" if choice == 1 else "Groom"), None
        # Brain: understand briiiide, grooom, ladki, my daughter, etc.
        from tools.understanding import understand_choice
        opts = {
            "Bride": ["bride", "girl", "woman", "female", "daughter", "ladki",
                       "dulhan", "she", "her", "sister", "bahen"],
            "Groom": ["groom", "boy", "man", "male", "son", "ladka",
                       "dulha", "he", "him", "brother", "bhai"],
        }
        guess, conf = understand_choice(ui, opts, context="Whose profile: Bride or Groom?")
        if conf == "high":
            return True, guess, None
        if conf == "maybe":
            # Ask for confirmation: store guess, signal via override sentinel
            return False, f"__CONFIRM__{guess}__Did you mean *{guess}*? (reply *yes* or *no*)", None
        return False, (
            "🙏 I want to get this right. Whose profile is this?\n"
            "Reply *1* for Bride 👰 or *2* for Groom 🤵 (you can also just type 'bride' or 'groom')."
        ), None

    if step in ("country_of_person", "country_of_parents"):
        # Must be in "City, Country" format — both parts required
        if "," not in ui:
            return False, (
                "❌ Please enter *both City and Country*, separated by a comma.\n"
                "📝 Format: *City, Country*\n"
                "Example: *Indore, India*"
            ), None
        parts = [p.strip() for p in ui.split(",")]
        city = parts[0]
        country = parts[1] if len(parts) > 1 else ""
        if len(city) < 2 or len(country) < 2:
            return False, (
                "❌ Both City and Country are required.\n"
                "📝 Format: *City, Country*\n"
                "Example: *Mumbai, India*"
            ), None
        # Reject obvious gibberish in either part
        from validators.field_validators import _looks_like_gibberish
        if _looks_like_gibberish(city) or _looks_like_gibberish(country):
            return False, (
                "❌ That doesn't look like a real city and country.\n"
                "📝 Format: *City, Country*\n"
                "Example: *Indore, India*"
            ), None
        # AI check that it's a genuine place (fails open if AI unavailable)
        from tools.understanding import is_real_place
        ok_place, _ = is_real_place(f"{city}, {country}", expect_city_country=True)
        if not ok_place:
            return False, (
                f"🤔 I couldn't recognize *{city.title()}, {country.title()}* as a real place.\n"
                "Please enter a valid *City, Country*.\n"
                "Example: *Hyderabad, India*"
            ), None
        # Re-join cleanly as "City, Country" (Title Case)
        return True, f"{city.title()}, {country.title()}", None

    if step == "registration_method":
        ok, choice = validate_menu_choice(ui, 2)
        if ok:
            return True, ("upload" if choice == 1 else "manual"), None
        from tools.understanding import understand_choice
        opts = {
            "upload": ["upload", "pdf", "image", "photo", "file", "biodata",
                        "document", "scan", "attach"],
            "manual": ["manual", "myself", "type", "fill", "enter", "by hand",
                        "write", "manually", "typing"],
        }
        guess, conf = understand_choice(ui, opts, context="Upload biodata or fill manually?")
        if conf == "high":
            return True, guess, None
        if conf == "maybe":
            return False, f"__CONFIRM__{guess}__Did you mean *{guess}*? (reply *yes* or *no*)", None
        return False, (
            "🙏 How would you like to register?\n"
            "Reply *1* to upload a biodata file 📄, or *2* to fill details manually ✍️."
        ), None

    if step == "full_name":
        return (*validate_full_name(ui), None)

    if step == "dob":
        return (*validate_dob(ui), None)

    if step == "time_of_birth":
        return (*validate_time_of_birth(ui), None)

    if step == "place_of_birth":
        ok, val = validate_place_of_birth(ui)
        if not ok:
            return False, val, None
        # AI check it's a genuine city/town/village (fails open if AI down)
        from tools.understanding import is_real_place
        ok_place, _ = is_real_place(val, expect_city_country=False)
        if not ok_place:
            return False, (
                f"🤔 I couldn't recognize *{val}* as a real place.\n"
                "Please enter a valid city, town, or village name."
            ), None
        return True, val, None

    if step == "height":
        return (*validate_height(ui), None)

    if step == "nakshatra":
        canonical = autocorrect_nakshatra(ui)
        if not canonical:
            return False, "❌ Could not recognize that Nakshatra. Please reply with the number (1-27) or correct name.", None
        return True, canonical, None

    if step == "rashi":
        canonical = autocorrect_rashi(ui)
        if not canonical:
            return False, "❌ Could not recognize that Rashi. Please reply with the number (1-12) or correct name.", None
        return True, canonical, None

    if step == "swa_gothram":
        return (*validate_gothram(ui), None)

    if step == "maternal_gothram":
        return (*validate_maternal_gothram(ui, data.get("swa_gothram", "")), None)

    if step in ("qualification", "profession", "father_occupation", "mother_occupation"):
        return (*validate_text_min_2(ui), None)

    if step == "salary_package":
        matched = _match_band(ui, SALARY_BANDS)
        if not matched:
            return False, f"❌ Please reply with a number 1-{len(SALARY_BANDS)} or paste the option text.", None
        return True, matched, None

    if step in ("father_name", "mother_name"):
        return (*validate_alpha_name(ui), None)

    if step == "property_details":
        matched = _match_band(ui, PROPERTY_BANDS)
        if not matched:
            return False, f"❌ Please reply with a number 1-{len(PROPERTY_BANDS)} or paste the option text.", None
        return True, matched, None

    return False, "❌ Unknown step.", None


# ---------- Build remaining steps (skip already-known fields) ----------

def _build_remaining_steps(data: Dict[str, Any], from_step: str | None = None) -> list:
    all_steps = REGISTRATION_STEPS
    if from_step and from_step in all_steps:
        start = all_steps.index(from_step) + 1
    else:
        start = 0
    out = []
    for s in all_steps[start:]:
        if s in ("review", "submit", "person_image"):
            out.append(s)
            continue
        # Already known? Skip - except nakshatra/rashi which are always manual
        if s in ("nakshatra", "rashi"):
            if not data.get(s):
                out.append(s)
            continue
        if not data.get(s):
            out.append(s)
    return out


# ---------- Photo upload handler ----------

def _handle_photo_upload(state: BotState) -> BotState:
    file_path = state.get("uploaded_file_path")
    file_url = state.get("uploaded_file_url")
    data = state["collected_data"]

    if not file_path:
        state["reply"] = "📸 I'm waiting for your photo. Please upload a JPG or PNG image."
        state["awaiting"] = "photo"
        return state

    # Store the single photo (path for Airtable upload, url for preview)
    data["_photo_path"] = file_path
    data["_photo_paths"] = [file_path]
    data["_photo_url"] = file_url
    data["_photo_urls"] = [file_url] if file_url else []
    data["_photo_just_received"] = True

    state["uploaded_file_path"] = None
    state["uploaded_file_url"] = None
    state["uploaded_file_kind"] = None

    # Go straight to review (review card is the sole content so UI renders it)
    state["current_step"] = "review"
    state["reply"] = _prompt_for_step("review", data)
    state["awaiting"] = "text"
    return state


# ---------- The MAIN registration node ----------

def _detect_inline_edit(user_input: str, data: Dict[str, Any]) -> str | None:
    """Detect a mid-registration request like 'update my height' / 'change dob' /
    'I want to correct my qualification'. Returns the field key to edit, or None.

    Conservative: requires an explicit edit verb AND a recognized field name, so a
    normal answer (e.g. a city called 'Change') is never mistaken for an edit."""
    from config.constants import FIELD_KEYWORD_MAP, RESTRICTED_FIELDS
    t = user_input.strip().lower()
    if len(t) < 6:
        return None
    edit_verbs = ("update", "change", "edit", "correct", "modify", "fix", "rectify",
                  "wrong", "mistake", "re-enter", "reenter", "wapas", "badal", "sahi karo")
    if not any(v in t for v in edit_verbs):
        return None
    # Find which field they mean (longest keyword first for specificity)
    field_key = None
    for keyword in sorted(FIELD_KEYWORD_MAP.keys(), key=len, reverse=True):
        if keyword in t:
            field_key = FIELD_KEYWORD_MAP[keyword]
            break
    if not field_key or field_key in RESTRICTED_FIELDS:
        return None
    return field_key


def registration_node(state: BotState) -> BotState:
    data = state.get("collected_data", {})
    step = state.get("current_step", "")
    user_input = state.get("user_input", "")

    # Entry: starting fresh
    if not step or step == "":
        state["current_step"] = "profile_type"
        state["current_flow"] = "registration"
        state["reply"] = _prompt_for_step("profile_type", data)
        state["awaiting"] = "text"
        state["collected_data"] = {}
        return state

    # Photo step
    if step == "person_image":
        return _handle_photo_upload(state)

    # Upload flow: biodata file was uploaded
    if step == "registration_method" and state.get("uploaded_file_kind") == "biodata":
        return _process_biodata_upload(state)

    # Review step
    if step == "review":
        return _handle_review_input(state)

    # Submit step
    if step == "submit":
        return _submit_profile(state)

    # Review-field-select substep
    if step == "review_field_select":
        return _handle_review_field_select(state)

    # --- Mid-registration "update my <field>" request ---
    # If the user wants to fix an already-answered field while in the middle of
    # registration, jump to that field, then return to where they left off.
    edit_target = _detect_inline_edit(user_input, data)
    if edit_target and step not in ("profile_type",):
        state["resume_step_after_edit"] = step
        state["current_step"] = edit_target
        state["reply"] = (
            f"Sure! Let's update your *{FIELD_LABELS.get(edit_target, edit_target)}*. 🙏\n\n"
            + _prompt_for_step(edit_target, data)
        )
        state["awaiting"] = "photo" if edit_target == "person_image" else "text"
        return state

    # --- Handle a pending "Did you mean X?" confirmation from last turn ---
    pending = state.get("pending_confirm")
    if pending:
        from validators.field_validators import _is_refusal  # reuse
        ans = user_input.strip().lower()
        yes_words = ("yes", "y", "yeah", "yep", "yup", "haan", "ha", "sahi", "correct", "right", "ok", "okay")
        no_words = ("no", "n", "nope", "nahi", "nhi", "wrong", "galat")
        from tools.understanding import fuzzy_match as _fm
        is_yes = ans in yes_words or _fm(ans, {"yes": list(yes_words)})[1] == "high"
        is_no = ans in no_words or _fm(ans, {"no": list(no_words)})[1] == "high"
        if is_yes:
            confirmed_value = pending["value"]
            confirm_step = pending["step"]
            state["pending_confirm"] = None
            # Feed the confirmed value forward as if validated
            return _commit_validated_value(state, confirm_step, confirmed_value, data)
        elif is_no:
            state["pending_confirm"] = None
            state["reply"] = "No problem! 🙏 Please type your answer again, clearly."
            state["awaiting"] = "text"
            return state
        # If they typed something else, treat it as a fresh answer below
        state["pending_confirm"] = None

    # Normal validation flow
    ok, value, _override = _process_step_input(step, user_input, data)

    # Brain asked for a confirmation? value carries "__CONFIRM__<guess>__<message>"
    if not ok and isinstance(value, str) and value.startswith("__CONFIRM__"):
        body = value[len("__CONFIRM__"):]
        guess, _, msg = body.partition("__")
        state["pending_confirm"] = {"step": step, "value": guess}
        state["reply"] = msg
        state["awaiting"] = "text"
        return state

    if not ok:
        # Real-agent behaviour: if the failed input is actually an off-topic
        # question (not a botched answer), answer it warmly and re-ask — instead
        # of robotically repeating the format error.
        from tools.understanding import looks_off_topic, answer_off_topic
        current_q = _prompt_for_step(step, data)
        if looks_off_topic(user_input):
            warm = answer_off_topic(user_input, current_q)
            if not warm:
                warm = ("😊 That's a little off-topic, but I'm happy to chat after we "
                        "finish your profile! Let's continue. 🙏")
            state["reply"] = warm + "\n\n" + current_q
            state["awaiting"] = "photo" if step == "person_image" else "text"
            return state

        state["reply"] = value
        state["invalid_count"] = state.get("invalid_count", 0) + 1
        if state["invalid_count"] >= 3:
            from config.settings import settings
            state["reply"] += f"\n\n💡 Need help? Contact admin: {settings.ADMIN_PHONE}"
        state["awaiting"] = "text"
        return state

    state["invalid_count"] = 0
    return _commit_validated_value(state, step, value, data)


def _commit_validated_value(state: BotState, step: str, value, data: Dict[str, Any]) -> BotState:
    """Save a validated value, persist to Airtable, and advance to the next step.
    Shared by the normal flow and the 'Did you mean?' confirmation path."""
    # Save value
    if step == "profile_type":
        state["category"] = value
        data["profile_type"] = value
        # Create the Airtable draft row NOW so all later answers save live
        try:
            rec_id = create_draft_profile(value, state.get("session_id", ""))
            state["airtable_record_id"] = rec_id
            state["is_registered"] = True
        except Exception as e:
            print(f"[Registration] draft create failed: {e}")
    elif step == "registration_method":
        state["registration_method"] = value
        if value == "upload":
            state["reply"] = (
                "📤 Please upload your biodata file now (PDF or Image).\n\n"
                "_I'll extract the details automatically and only ask for what's missing._"
            )
            state["awaiting"] = "biodata"
            state["collected_data"] = data
            return state
    else:
        data[step] = value

    # After DOB, compute age
    if step == "dob":
        try:
            dob_dt = datetime.strptime(value, "%d-%m-%Y")
            data["age"] = calculate_age(dob_dt)
        except ValueError:
            pass

    # --- REAL-TIME AIRTABLE SAVE ---
    # Persist this answer immediately so the admin sees it live in Airtable.
    rec_id = state.get("airtable_record_id")
    if rec_id and step not in ("profile_type", "registration_method"):
        try:
            update_profile_field(state.get("category", "Groom"), rec_id, step, value)
        except Exception as e:
            print(f"[Registration] live save failed for {step}: {e}")

    state["collected_data"] = data

    # If this was an inline "update my X" edit, return to where the user left off.
    resume = state.get("resume_step_after_edit")
    if resume:
        state["resume_step_after_edit"] = None
        # If the field they were originally on is now filled, move forward from it;
        # otherwise re-ask that same step.
        if data.get(resume) and resume not in ("nakshatra", "rashi", "person_image", "review"):
            remaining = _build_remaining_steps(data, from_step=resume)
            target = remaining[0] if remaining else "review"
        else:
            target = resume
        state["current_step"] = target
        prefix = "✅ Updated! Let's continue where we left off. 🙏\n\n"
        if target == "review":
            state["reply"] = _prompt_for_step("review", data)
        else:
            state["reply"] = prefix + _prompt_for_step(target, data)
        state["awaiting"] = "photo" if target == "person_image" else "text"
        return state

    # If updating from review, go back to review
    if state.get("in_review_update_mode"):
        state["in_review_update_mode"] = False
        state["current_step"] = "review"
        data["_photo_just_received"] = False  # don't re-show "photo received"
        state["reply"] = _prompt_for_step("review", data)
        state["awaiting"] = "text"
        return state

    # Move to next step
    remaining = _build_remaining_steps(data, from_step=step)
    if not remaining:
        state["current_step"] = "review"
        state["reply"] = _prompt_for_step("review", data)
        state["awaiting"] = "text"
        return state

    next_step = remaining[0]
    state["current_step"] = next_step
    state["reply"] = _prompt_for_step(next_step, data)
    state["awaiting"] = "photo" if next_step == "person_image" else "text"
    return state


# ---------- Biodata upload (OCR) ----------

def _process_biodata_upload(state: BotState) -> BotState:
    file_path = state.get("uploaded_file_path")
    if not file_path:
        state["reply"] = "📤 Please upload your biodata file."
        state["awaiting"] = "biodata"
        return state

    extracted = extract_biodata_fields(file_path)
    if "_error" in extracted:
        state["reply"] = (
            f"⚠️ I couldn't read that file: {extracted['_error']}\n\n"
            "Let's continue manually instead.\n\n" + _prompt_for_step("full_name", {})
        )
        state["current_step"] = "full_name"
        state["registration_method"] = "manual"
        state["awaiting"] = "text"
        state["uploaded_file_path"] = None
        state["uploaded_file_kind"] = None
        return state

    data = state.get("collected_data", {})
    # Save biodata path for later attachment to Airtable
    data["_biodata_path"] = file_path

    # Merge extracted into collected_data (defensive: strip nakshatra/rashi)
    for k, v in extracted.items():
        if k in OCR_EXTRACTABLE_FIELDS and v:
            data[k] = v

    # Compute age
    if "dob" in data:
        try:
            dob_dt = datetime.strptime(data["dob"], "%d-%m-%Y")
            data["age"] = calculate_age(dob_dt)
        except (ValueError, TypeError):
            pass

    state["collected_data"] = data
    state["uploaded_file_path"] = None
    state["uploaded_file_kind"] = None

    # --- REAL-TIME AIRTABLE SAVE for all extracted fields ---
    rec_id = state.get("airtable_record_id")
    if rec_id:
        for k in OCR_EXTRACTABLE_FIELDS:
            if data.get(k):
                try:
                    update_profile_field(state.get("category", "Groom"), rec_id, k, data[k])
                except Exception as e:
                    print(f"[Registration] OCR live save failed for {k}: {e}")

    found_count = sum(1 for k in OCR_EXTRACTABLE_FIELDS if data.get(k))
    state["reply"] = (
        f"✅ I extracted *{found_count} fields* from your biodata!\n\n"
        "Now I'll only ask for what's missing — starting with Nakshatra and Rashi "
        "(these are always asked manually)."
    )

    remaining = _build_remaining_steps(data, from_step="registration_method")
    if not remaining:
        state["current_step"] = "review"
        state["reply"] += "\n\n" + _prompt_for_step("review", data)
    else:
        state["current_step"] = remaining[0]
        state["reply"] += "\n\n" + _prompt_for_step(remaining[0], data)
    state["awaiting"] = "photo" if state["current_step"] == "person_image" else "text"
    return state


# ---------- Review handler ----------

def _handle_review_input(state: BotState) -> BotState:
    ui = state.get("user_input", "").strip().lower()
    data = state.get("collected_data", {})

    yes_words = ("yes", "y", "submit", "confirm", "ok", "okay", "sure", "yeah", "yep",
                 "haan", "ha", "done", "correct", "go ahead", "proceed", "looks good", "good")
    no_words = ("no", "n", "change", "edit", "modify", "nope", "nahi", "wrong", "incorrect")

    is_yes = ui in yes_words or any(w in ui for w in ("submit", "confirm", "looks good", "go ahead", "proceed"))
    is_no = ui in no_words or any(w in ui for w in ("change", "edit", "modify", "wrong", "incorrect"))

    # If ambiguous, ask AI
    if not is_yes and not is_no:
        from tools.intent_tools import classify_intent
        intent = classify_intent(ui, allowed=["yes", "no"])
        is_yes = intent == "yes"
        is_no = intent == "no"

    if is_yes:
        if not data.get("_photo_path"):
            state["reply"] = (
                "❌ Photo is mandatory before submitting.\n\n" + _prompt_for_step("person_image", data)
            )
            state["current_step"] = "person_image"
            state["awaiting"] = "photo"
            return state
        return _submit_profile(state)
    if is_no:
        state["reply"] = (
            "✏️ Which field would you like to update?\n\n"
            "Type the field name (e.g. *height*, *nakshatra*, *qualification*)."
        )
        state["current_step"] = "review_field_select"
        state["awaiting"] = "text"
        return state
    state["reply"] = "Please reply *YES* to submit or *NO* to make changes."
    state["awaiting"] = "text"
    return state


def _handle_review_field_select(state: BotState) -> BotState:
    from config.constants import FIELD_KEYWORD_MAP, RESTRICTED_FIELDS
    ui = state.get("user_input", "").strip().lower()
    field_key = None
    for keyword, key in FIELD_KEYWORD_MAP.items():
        if keyword in ui:
            field_key = key
            break
    if not field_key:
        state["reply"] = "❌ I didn't recognize that field. Try: height, nakshatra, qualification, etc."
        state["awaiting"] = "text"
        return state
    if field_key in RESTRICTED_FIELDS:
        state["reply"] = "🚫 That field cannot be updated by users."
        state["awaiting"] = "text"
        return state
    if field_key == "person_image":
        state["in_review_update_mode"] = True
        state["current_step"] = "person_image"
        state["reply"] = _prompt_for_step("person_image", state.get("collected_data", {}))
        state["awaiting"] = "photo"
        return state
    state["in_review_update_mode"] = True
    state["current_step"] = field_key
    state["reply"] = _prompt_for_step(field_key, state.get("collected_data", {}))
    state["awaiting"] = "text"
    return state


# ---------- Submit ----------

def _submit_profile(state: BotState) -> BotState:
    data = state.get("collected_data", {})
    profile_type = state.get("category", "Groom")
    session_id = state.get("session_id", "")
    record_id = state.get("airtable_record_id")

    # Strip internal keys and 'profile_type' (set separately)
    payload = {
        k: v for k, v in data.items()
        if not k.startswith("_") and k != "profile_type"
    }

    try:
        if record_id:
            # Draft row already exists (created at profile_type). Fields were saved
            # live, but write them all once more to guarantee nothing is missing.
            for fkey, fval in payload.items():
                try:
                    update_profile_field(profile_type, record_id, fkey, fval)
                except Exception as e:
                    print(f"[Submit] final sync failed for {fkey}: {e}")
        else:
            # Fallback: no draft (shouldn't happen) — create fresh
            record_id = create_profile(profile_type, session_id, payload)
            state["airtable_record_id"] = record_id

        state["is_registered"] = True
        state["is_approved"] = False
        state["current_flow"] = "main_menu"
        state["current_step"] = ""

        # Attach photo(s) — supports multiple
        photo_status = ""
        photo_paths = data.get("_photo_paths") or ([data["_photo_path"]] if data.get("_photo_path") else [])
        if photo_paths:
            ok_count = 0
            for p in photo_paths:
                if attach_file_from_path(profile_type, record_id, "person_image", p):
                    ok_count += 1
            if ok_count == len(photo_paths):
                photo_status = (f"\n📸 {ok_count} photo(s) uploaded to your profile."
                                if ok_count > 1 else "\n📸 Photo uploaded to your profile.")
            elif ok_count > 0:
                photo_status = f"\n📸 {ok_count} of {len(photo_paths)} photos uploaded."
            else:
                photo_status = "\n⚠️ Photo upload failed — admin will help."

        # Attach biodata if uploaded
        biodata_status = ""
        biodata_path = data.get("_biodata_path")
        if biodata_path:
            ok = attach_file_from_path(profile_type, record_id, "biodata_file", biodata_path)
            biodata_status = "\n📄 Biodata file attached." if ok else ""

        from config.settings import settings
        state["reply"] = (
            "✅ *Thank you! Your profile has been submitted successfully.*\n\n"
            f"📋 Profile Type: {profile_type}\n"
            f"✔️ Your details are saved\n"
            f"⏳ Admin Approval: Pending"
            f"{photo_status}{biodata_status}\n\n"
            "Our admin will review and approve your profile shortly. You'll be "
            "notified here automatically once approved. 🙏\n"
            f"For urgent queries: {settings.ADMIN_PHONE}"
        )
        state["awaiting"] = "text"
    except Exception as e:
        state["reply"] = f"⚠️ Submission failed: {e}\n\nPlease try again or contact admin."
        state["awaiting"] = "text"
    return state
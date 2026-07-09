"""Airtable operations - SINGLE TABLE design.

Everything (Bride + Groom) lives in ONE Airtable table (configured as
AIRTABLE_GROOM_TABLE in settings). The 'Profile Type' column distinguishes
'Bride' vs 'Groom' rows. The 'Bride' table is no longer used.
"""
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path
import base64
import re
from pyairtable import Api
from config.settings import settings
from config.constants import AIRTABLE_FIELDS


# Columns we MUST NOT write to (formulas / auto-managed)
READ_ONLY_AIRTABLE_COLUMNS = {
    "Age",
    "Hight in inch",
    "Created Date",
    "Last Update Date",
    "Profile ID",
}


def _api() -> Api:
    return Api(settings.AIRTABLE_API_KEY)


def _table():
    """Single table - everything lives here."""
    return _api().table(settings.AIRTABLE_BASE_ID, settings.AIRTABLE_GROOM_TABLE)


# ---------------- Value transformers ----------------

def _to_iso_date(dob_str: str) -> Optional[str]:
    if not dob_str:
        return None
    s = str(dob_str).strip().replace("/", "-")
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%m-%y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _calculate_age(dob_iso_or_text: str) -> Optional[int]:
    iso = _to_iso_date(dob_iso_or_text)
    if not iso:
        return None
    dob = datetime.strptime(iso, "%Y-%m-%d")
    today = datetime.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def _height_to_inches(height_str: str) -> Optional[int]:
    if not height_str:
        return None
    s = str(height_str).strip().lower()
    patterns = [
        r"^(\d)\s*['\u2032]\s*(\d{1,2})\s*[\"\u2033]?$",
        r"^(\d)\s+(\d{1,2})$",
        r"^(\d)\s*ft\s*(\d{1,2})\s*(?:in|inch|inches)?$",
        r"^(\d)\s*feet\s*(\d{1,2})\s*(?:in|inch|inches)?$",
        r"^(\d)\s*['\u2032]$",
    ]
    for p in patterns:
        m = re.match(p, s)
        if m:
            feet = int(m.group(1))
            inches = int(m.group(2)) if len(m.groups()) > 1 else 0
            return feet * 12 + inches
    return None


def _height_to_cm(height_str: str) -> Optional[int]:
    inches = _height_to_inches(height_str)
    if inches is None:
        return None
    return round(inches * 2.54)


# ---------------- Build the Airtable payload ----------------

def _build_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    for key, value in data.items():
        if key.startswith("_") or value in (None, "", []):
            continue
        if key not in AIRTABLE_FIELDS:
            continue
        col = AIRTABLE_FIELDS[key]
        if col in READ_ONLY_AIRTABLE_COLUMNS:
            continue

        if key == "phone":
            digits = "".join(ch for ch in str(value) if ch.isdigit())
            if digits:
                payload[col] = int(digits)
        elif key == "dob":
            iso = _to_iso_date(value)
            if iso:
                payload[col] = iso
        elif key == "height":
            cm = _height_to_cm(value)
            if cm:
                payload[col] = cm
            else:
                payload[col] = str(value)
        else:
            payload[col] = value
    return payload


# ---------------- Public API ----------------

def lookup_user_by_session(session_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Look up a user in the SINGLE table by digit-only session_id.
    Returns (record_dict, profile_type) where profile_type comes from the row's
    'Profile Type' column ('Bride' or 'Groom')."""
    phone_field = AIRTABLE_FIELDS["phone"]
    digits = "".join(ch for ch in str(session_id) if ch.isdigit())
    if not digits:
        return None, None
    formula = f"{{{phone_field}}} = {digits}"
    try:
        records = _table().all(formula=formula, max_records=1)
        if records:
            rec = records[0]
            profile_type = rec.get("fields", {}).get(AIRTABLE_FIELDS["profile_type"], "Groom")
            return rec, profile_type
    except Exception as e:
        print(f"[Airtable] lookup error: {e}")
    return None, None


def create_profile(profile_type: str, session_id: str, data: Dict[str, Any]) -> str:
    """Create a new profile row. profile_type is 'Bride' or 'Groom' — written
    to the 'Profile Type' column."""
    enriched = dict(data)
    enriched["phone"] = session_id

    payload = _build_payload(enriched)
    payload[AIRTABLE_FIELDS["profile_type"]] = profile_type
    payload[AIRTABLE_FIELDS["candidate_approval"]] = "Approved"
    payload[AIRTABLE_FIELDS["admin_approval"]] = "Pending"

    record = _table().create(payload)
    return record["id"]


def create_draft_profile(profile_type: str, session_id: str) -> str:
    """Create an empty draft row as soon as the user picks Bride/Groom, so that
    every later answer can be saved to Airtable in real time. Returns record id.
    If a row already exists for this session, returns its id instead of duplicating."""
    # Avoid duplicate rows if the user restarts registration in the same session
    existing, _ = lookup_user_by_session(session_id)
    if existing:
        return existing["id"]

    digits = "".join(ch for ch in str(session_id) if ch.isdigit())
    payload = {
        AIRTABLE_FIELDS["profile_type"]: profile_type,
        AIRTABLE_FIELDS["candidate_approval"]: "Approved",
        AIRTABLE_FIELDS["admin_approval"]: "Pending",
    }
    if digits:
        payload[AIRTABLE_FIELDS["phone"]] = int(digits)
    record = _table().create(payload)
    print(f"[Airtable] Draft row created: {record['id']} ({profile_type})")
    return record["id"]


def update_profile_field(profile_type: str, record_id: str, field_key: str, value: Any) -> bool:
    """Update one field. profile_type is now unused (kept for API compatibility)."""
    if field_key not in AIRTABLE_FIELDS:
        print(f"[Airtable] unknown field key: {field_key}")
        return False
    fields_payload = _build_payload({field_key: value})
    if not fields_payload:
        print(f"[Airtable] nothing to update for {field_key}")
        return False
    try:
        _table().update(record_id, fields_payload)
        return True
    except Exception as e:
        print(f"[Airtable] update error: {e}")
        return False


def attach_file_from_path(profile_type: str, record_id: str, field_key: str, file_path: str) -> bool:
    """Attach a local file to an attachment column. profile_type unused (single table)."""
    if field_key not in ("person_image", "biodata_file"):
        print(f"[Airtable] attach: bad field_key {field_key}")
        return False
    path = Path(file_path)
    if not path.exists():
        print(f"[Airtable] file not found: {file_path}")
        return False

    column_name = AIRTABLE_FIELDS[field_key]
    try:
        with open(path, "rb") as f:
            file_bytes = f.read()

        table = _table()
        try:
            table.upload_attachment(
                record_id=record_id,
                field=column_name,
                filename=path.name,
                content=file_bytes,
            )
            return True
        except AttributeError:
            pass

        import requests
        content_type = _guess_content_type(path.suffix)
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        url = (
            f"https://content.airtable.com/v0/"
            f"{settings.AIRTABLE_BASE_ID}/{record_id}/{column_name}/uploadAttachment"
        )
        headers = {
            "Authorization": f"Bearer {settings.AIRTABLE_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"contentType": content_type, "file": b64, "filename": path.name}
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code in (200, 201):
            return True
        print(f"[Airtable] upload failed {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[Airtable] attach_file error: {e}")
        return False


def _guess_content_type(suffix: str) -> str:
    s = suffix.lower()
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp",
        ".pdf": "application/pdf",
    }.get(s, "application/octet-stream")


def search_matches(
    seeker_profile_type: str,
    age_min: int,
    age_max: int,
    nakshatra: Optional[str] = None,
    rashi: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Search for matches in the SINGLE table.
    seeker is 'Groom' -> we return 'Bride' rows, and vice versa.
    Only returns rows where Admin Approval = 'Approved'."""
    target_profile = "Bride" if seeker_profile_type.lower() == "groom" else "Groom"

    profile_col = AIRTABLE_FIELDS["profile_type"]
    approval_col = AIRTABLE_FIELDS["admin_approval"]

    # Build formula. Use LOWER() to make it case-insensitive and trim spaces.
    formula_parts = [
        f"LOWER(TRIM({{{profile_col}}})) = '{target_profile.lower()}'",
        f"LOWER(TRIM({{{approval_col}}})) = 'approved'",
    ]
    if nakshatra:
        formula_parts.append(f"{{{AIRTABLE_FIELDS['nakshatra']}}} = '{nakshatra}'")
    if rashi:
        formula_parts.append(f"{{{AIRTABLE_FIELDS['rashi']}}} = '{rashi}'")
    formula = "AND(" + ", ".join(formula_parts) + ")"

    print(f"\n[Airtable SEARCH]")
    print(f"  Seeker: {seeker_profile_type} -> looking for: {target_profile}")
    print(f"  Age range: {age_min}-{age_max}")
    print(f"  Nakshatra filter: {nakshatra!r}")
    print(f"  Rashi filter: {rashi!r}")
    print(f"  Formula: {formula}")

    try:
        records = _table().all(formula=formula)
    except Exception as e:
        print(f"  ERROR: {e}")
        return []

    print(f"  Raw matches from Airtable: {len(records)}")

    matches = []
    for r in records:
        f = r.get("fields", {})
        name = f.get("Name", "(no name)")
        dob_str = f.get(AIRTABLE_FIELDS["dob"], "")
        age = _calculate_age(dob_str)
        if age is None:
            age_raw = f.get(AIRTABLE_FIELDS["age"], "")
            age = _parse_age_any(age_raw)
        if age is None:
            print(f"    SKIP {name!r}: no usable DOB ({dob_str!r}) or Age ({f.get(AIRTABLE_FIELDS['age'])!r})")
            continue
        if age_min <= age <= age_max:
            matches.append({"record": r, "age": age})
            print(f"    KEEP {name!r}: age {age}")
        else:
            print(f"    SKIP {name!r}: age {age} not in [{age_min}, {age_max}]")
    print(f"  After age filter: {len(matches)}\n")
    return matches[:limit]


def _parse_age_any(value) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    m = re.search(r"(\d{1,3})\s*Years?", s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    return None


def get_approval_status(profile_type: str, record_id: str) -> str:
    """Re-fetch fresh approval status. profile_type unused (single table)."""
    try:
        record = _table().get(record_id)
        return record.get("fields", {}).get(AIRTABLE_FIELDS["admin_approval"], "Pending")
    except Exception as e:
        print(f"[Airtable] approval check error: {e}")
        return "Pending"
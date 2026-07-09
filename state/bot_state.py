"""BotState: shared state object that flows through every LangGraph node."""
from typing import TypedDict, Optional, List, Dict, Any


class BotState(TypedDict, total=False):
    # --- Identity ---
    session_id: str           # unique per chat session (acts as primary key)
    user_input: str           # latest message from user
    uploaded_file_path: Optional[str]   # path to PDF/image uploaded
    uploaded_file_kind: Optional[str]   # "biodata" | "photo"

    # --- Registration status ---
    is_registered: bool
    is_approved: bool
    is_rejected: bool
    approval_announced: bool  # whether we've shown the "you're approved" message
    rejection_announced: bool  # whether we've shown the rejection message
    category: Optional[str]   # "Bride" | "Groom"
    airtable_record_id: Optional[str]

    # --- Flow control ---
    current_flow: str         # "welcome" | "registration" | "search" | "update" | "support" | "main_menu"
    current_step: str         # which registration step we're on
    resume_step: Optional[str]  # for interruption handling
    registration_method: Optional[str]  # "manual" | "upload"
    in_review_update_mode: bool  # True when user said NO at review and is fixing a field
    resume_step_after_edit: str  # step to return to after an inline 'update my X'
    pending_confirm: dict  # holds a 'Did you mean?' guess awaiting yes/no
    invalid_count: int        # consecutive invalid attempts

    # --- Collected data (registration) ---
    collected_data: Dict[str, Any]
    missing_fields_queue: List[str]  # for upload flow: only ask for these
    update_field_name: Optional[str]  # field being updated in update flow

    # --- Search ---
    search_age_min: Optional[int]
    search_age_max: Optional[int]
    search_nakshatra: Optional[str]
    search_rashi: Optional[str]
    search_step: Optional[str]  # "age" | "nakshatra" | "rashi" | "results"
    shown_record_ids: List[str]  # Airtable record IDs already shown to user

    # --- Output ---
    reply: str
    awaiting: Optional[str]   # "text" | "photo" | "biodata" — hints UI what to expect
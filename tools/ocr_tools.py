"""GPT-4o vision/OCR for biodata PDFs and images.

Supports both:
  - OpenAI API (key: sk-...)
  - OpenRouter API (key: sk-or-...) — uses openrouter.ai/api/v1 base URL

CRITICAL RULE: ALWAYS ignore Nakshatra and Rashi from the document.
Even if visible, treat them as not present. The bot ALWAYS asks these manually.
"""
import base64
import json
from pathlib import Path
from openai import OpenAI
from config.settings import settings


def _get_client() -> OpenAI | None:
    if not settings.OPENAI_API_KEY:
        return None
    base_url = settings.openai_base_url  # None for OpenAI, URL for OpenRouter
    if base_url:
        # OpenRouter recommends sending these headers
        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=base_url,
            default_headers={
                "HTTP-Referer": "https://srivasavi-matrimony.local",
                "X-Title": "Sri Vasavi Matrimony Bot",
            },
        )
    return OpenAI(api_key=settings.OPENAI_API_KEY)


OCR_SYSTEM_PROMPT = """You are extracting fields from a matrimonial biodata document.

EXTRACT ONLY THESE 15 FIELDS (return a JSON object, nothing else):
{
  "full_name": "person's full name",
  "dob": "DD-MM-YYYY format only",
  "time_of_birth": "12-hour format like 08:30 AM",
  "place_of_birth": "city and state",
  "height": "like 5'8\" or 5'10\"",
  "swa_gothram": "gothram name",
  "maternal_gothram": "maternal gothram name",
  "qualification": "highest education",
  "profession": "job title or work",
  "salary_package": "closest to one of: ₹1–3 Lakhs, ₹3–6 Lakhs, ₹6–12 Lakhs, ₹12–25 Lakhs, ₹25–50 Lakhs, ₹50 Lakhs–₹1 Crore, Above ₹1 Crore",
  "father_name": "father's full name",
  "mother_name": "mother's full name",
  "father_occupation": "father's job/occupation",
  "mother_occupation": "mother's job/occupation",
  "property_details": "closest to one of: ₹1 Lakh – ₹10 Lakhs, ₹10 Lakhs – ₹50 Lakhs, ₹50 Lakhs – ₹1 Crore, ₹1 Crore – ₹5 Crores, ₹5 Crores – ₹25 Crores, ₹25 Crores – ₹100 Crores, ₹100 Crores – ₹500 Crores, Above ₹500 Crores"
}

CRITICAL RULES:
1. NEVER include Nakshatra or Rashi — even if present in the document, IGNORE them.
2. For any field you cannot find, set value to null.
3. Return ONLY the JSON object — no markdown, no backticks, no explanation.
4. DOB must be DD-MM-YYYY. If you see MM/DD/YYYY or YYYY-MM-DD, convert it.
5. Height must be in feet'inches\" format (e.g. 5'8\").
"""


def extract_biodata_fields(file_path: str) -> dict:
    """Extract fields from a biodata image or PDF using GPT-4o vision.
    Returns a dict of extracted fields (nulls removed).
    Returns {'_error': '...'} on failure.
    """
    client = _get_client()
    if client is None:
        return {"_error": "OPENAI_API_KEY not configured in .env"}

    path = Path(file_path)
    if not path.exists():
        return {"_error": f"File not found: {file_path}"}

    ext = path.suffix.lower()
    image_data_urls = []

    if ext in (".jpg", ".jpeg", ".png", ".webp"):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext[1:]}"
        image_data_urls.append(f"data:{mime};base64,{b64}")

    elif ext == ".pdf":
        # Try PyMuPDF (best quality) → pypdf text fallback
        try:
            import fitz
            doc = fitz.open(path)
            for page in doc[:3]:
                pix = page.get_pixmap(dpi=150)
                b64 = base64.b64encode(pix.tobytes("png")).decode("utf-8")
                image_data_urls.append(f"data:image/png;base64,{b64}")
            doc.close()
        except ImportError:
            # Fallback: extract text from PDF
            try:
                from pypdf import PdfReader
                text = ""
                reader = PdfReader(str(path))
                for page in reader.pages[:3]:
                    text += (page.extract_text() or "") + "\n"
                if text.strip():
                    return _extract_from_text(client, text)
                return {"_error": "Could not extract text from PDF. Install pymupdf for better results: pip install pymupdf"}
            except Exception as e:
                return {"_error": f"PDF read failed: {e}"}
    else:
        return {"_error": f"Unsupported file type: {ext}. Use JPG, PNG, or PDF."}

    if not image_data_urls:
        return {"_error": "No images extracted from file."}

    # Build multimodal message
    content = [{"type": "text", "text": OCR_SYSTEM_PROMPT}]
    for url in image_data_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})

    try:
        # OpenRouter uses model names like "openai/gpt-4o"
        model = settings.OPENAI_MODEL
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()
        # Strip markdown fences if model wrapped in ```json ... ```
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        # Double-safety: scrub Nakshatra and Rashi
        data.pop("nakshatra", None)
        data.pop("rashi", None)
        # Remove nulls and empty strings
        clean = {k: v for k, v in data.items() if v not in (None, "", "null", "N/A", "n/a")}
        print(f"[OCR] Extracted {len(clean)} fields from {path.name}: {list(clean.keys())}")
        return clean
    except json.JSONDecodeError as e:
        print(f"[OCR] JSON parse failed: {e}. Raw: {raw[:200]}")
        return {"_error": f"OCR returned invalid JSON. Try a clearer image."}
    except Exception as e:
        err = str(e)
        print(f"[OCR] API error: {err}")
        if "401" in err or "authentication" in err.lower():
            return {"_error": "API key rejected. Check your OPENAI_API_KEY in .env"}
        if "404" in err or "model" in err.lower():
            return {"_error": f"Model not found. Try setting OPENAI_MODEL=openai/gpt-4o in .env"}
        return {"_error": f"OCR failed: {err[:200]}"}


def _extract_from_text(client: OpenAI, text: str) -> dict:
    """Fallback for PDFs where we extracted text instead of images."""
    try:
        model = settings.OPENAI_MODEL
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": OCR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract from this biodata text:\n\n{text[:3000]}"},
            ],
            temperature=0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip().strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        data = json.loads(raw)
        data.pop("nakshatra", None)
        data.pop("rashi", None)
        clean = {k: v for k, v in data.items() if v not in (None, "", "null", "N/A", "n/a")}
        print(f"[OCR] Text-extracted {len(clean)} fields: {list(clean.keys())}")
        return clean
    except Exception as e:
        return {"_error": f"Text extraction failed: {e}"}
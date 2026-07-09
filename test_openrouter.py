"""Diagnostic: test the OpenRouter key directly.
Run from project root:  python test_openrouter.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("OPENAI_API_KEY", "")
model = os.getenv("OPENAI_MODEL", "openai/gpt-4o")

print("=" * 50)
print("OPENROUTER DIAGNOSTIC")
print("=" * 50)

if not key:
    print("❌ OPENAI_API_KEY is EMPTY in .env")
    raise SystemExit(1)

print(f"Key prefix      : {key[:12]}...")
print(f"Key length      : {len(key)} chars")
print(f"Is OpenRouter   : {key.startswith('sk-or-')}")
print(f"Model           : {model}")
print("-" * 50)

# Test 1: raw HTTP call to OpenRouter /auth/key (checks key validity + credits)
import requests
print("\n[Test 1] Checking key validity via /api/v1/auth/key ...")
try:
    r = requests.get(
        "https://openrouter.ai/api/v1/auth/key",
        headers={"Authorization": f"Bearer {key}"},
        timeout=15,
    )
    print(f"  Status: {r.status_code}")
    print(f"  Body  : {r.text[:300]}")
    if r.status_code == 200:
        print("  ✅ Key is VALID")
    elif r.status_code == 401:
        print("  ❌ Key is INVALID or REVOKED — generate a new one at openrouter.ai/keys")
except Exception as e:
    print(f"  ERROR: {e}")

# Test 2: actual chat completion (text only)
print("\n[Test 2] Simple chat completion ...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=10,
    )
    print(f"  ✅ Response: {resp.choices[0].message.content!r}")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

print("\n" + "=" * 50)
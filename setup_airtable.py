"""
Airtable Setup Verifier for Sri Vasavi Matrimony Bot.

This script:
  1. Confirms it can connect to your Airtable base
  2. Verifies both Groom and Bride tables exist
  3. Writes a test record using the REAL column names + correct types

Run:  python setup_airtable.py
"""
import sys
import random
from datetime import datetime
from pyairtable import Api
from config.settings import settings
from config.constants import AIRTABLE_FIELDS
from tools.airtable_tools import create_profile, _table


def check_schema_loose():
    if not settings.AIRTABLE_API_KEY or not settings.AIRTABLE_BASE_ID:
        print("❌ Please set AIRTABLE_API_KEY and AIRTABLE_BASE_ID in your .env file.")
        sys.exit(1)

    api = Api(settings.AIRTABLE_API_KEY)
    print(f"\n🔌 Connecting to base: {settings.AIRTABLE_BASE_ID}\n")

    required = list(AIRTABLE_FIELDS.values())
    for table_name in (settings.AIRTABLE_GROOM_TABLE, settings.AIRTABLE_BRIDE_TABLE):
        try:
            table = api.table(settings.AIRTABLE_BASE_ID, table_name)
            records = table.all(max_records=10)
            print(f"✅ Found table: {table_name} ({len(records)} sample records read)")
            seen = set()
            for r in records:
                seen.update(r.get("fields", {}).keys())
            missing = [f for f in required if f not in seen]
            if missing:
                print(f"   ℹ️  Columns not seen in sample (may exist but empty):")
                for m in missing:
                    print(f"      - {m}")
        except Exception as e:
            print(f"❌ Could not access table '{table_name}': {e}")
            return False
    return True


def write_test():
    test_session_id = str(random.randint(9000000000, 9999999999))  # 10-digit fake phone
    test_data = {
        "full_name": "Test User Autodelete",
        "dob": "15-08-1995",
        "time_of_birth": "08:30 AM",
        "place_of_birth": "Test City",
        "height": "5'8\"",
        "nakshatra": "Rohini (రోహిణి)",
        "rashi": "Mesha (మేషం)",
        "swa_gothram": "Kashyap",
        "maternal_gothram": "Bharadwaj",
        "qualification": "B.Tech",
        "profession": "Engineer",
        "salary_package": "₹6–12 Lakhs",
        "father_name": "Test Father",
        "mother_name": "Test Mother",
        "father_occupation": "Retired",
        "mother_occupation": "Housewife",
        "property_details": "₹1 Lakh – ₹10 Lakhs",
        "country_of_person": "Indore, India",
        "country_of_parents": "Indore, India",
    }

    print(f"\n🧪 Writing test record to Groom table...")
    print(f"   Test phone (digit-only): {test_session_id}")
    try:
        record_id = create_profile("Groom", test_session_id, test_data)
        print(f"✅ Test record created: {record_id}")
        # Clean up
        _table("Groom").delete(record_id)
        print(f"✅ Test record deleted (cleanup OK)")
        return True
    except Exception as e:
        err = str(e)
        print(f"❌ Write failed: {err[:400]}")
        if "UNKNOWN_FIELD_NAME" in err:
            import re
            m = re.search(r'Unknown field name: "([^"]+)"', err)
            if m:
                print(f"\n💡 Column '{m.group(1)}' doesn't exist in Airtable.")
        elif "INVALID_VALUE_FOR_COLUMN" in err or "Cannot parse value" in err:
            import re
            m = re.search(r'Field "([^"]+)" cannot accept', err)
            if m:
                print(f"\n💡 Column '{m.group(1)}' has a type that doesn't match what we're writing.")
                print(f"   Check its type in Airtable.")
        elif "INVALID_MULTIPLE_CHOICE_OPTIONS" in err:
            print(f"\n💡 A single-select field is missing an option (e.g. 'Approved' or 'Pending').")
            print(f"   Add the missing option to the column's dropdown in Airtable.")
        return False


if __name__ == "__main__":
    if not check_schema_loose():
        sys.exit(1)
    print("\n" + "=" * 60)
    ok = write_test()
    print("=" * 60)
    if ok:
        print("\n🎉 Airtable is set up correctly! You can now run the bot:")
        print("   Terminal 1:  uvicorn main:app --reload")
        print("   Terminal 2:  streamlit run ui/app.py")
    else:
        print("\n⚠️  Fix the error above and run this script again.")
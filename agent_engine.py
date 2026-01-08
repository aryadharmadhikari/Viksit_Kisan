import os
import json
import time
import re
from google import genai
from google.genai import types
from pymongo import MongoClient
from dotenv import load_dotenv
import uuid
from datetime import datetime

load_dotenv()

# --- 1. SETUP CONNECTIONS ---
try:
    mongo_client = MongoClient(os.getenv("MONGO_URI"), serverSelectionTimeoutMS=3000)
    db = mongo_client["viksit_kisan_db"]
    farmers_col = db["farmers"]
    claims_col = db["claims"]
    DB_CONNECTED = True
except Exception as e:
    print(f"⚠️ MongoDB Connection Failed: {e}")
    DB_CONNECTED = False

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# --- HELPER FUNCTIONS ---
def clean_json_text(text):
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```', '', text)
    return text.strip()

def save_claim_to_db(merged_data, ai_confidence):
    if not DB_CONNECTED:
        return f"OFFLINE-{uuid.uuid4().hex[:6].upper()}"
    
    app_id = f"PMFBY-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
    claim_record = {
        "application_id": app_id,
        "farmer_mobile": merged_data.get("mobile", "Unknown"),
        "timestamp": datetime.now(),
        "status": "Submitted",
        "claim_data": merged_data
    }
    try:
        claims_col.insert_one(claim_record)
        return app_id
    except:
        return app_id

def get_farmer_from_db(mobile_number):
    if not DB_CONNECTED: return None
    return farmers_col.find_one({"mobile_number": mobile_number.replace("+91", "").strip()})

# --- CORE FUNCTION (UPDATED) ---
def process_claim(audio_file, land_file, crop_file, mobile_number="9922001122"):
    """
    Accepts THREE files: Audio, Land Doc (PDF/Img), and Crop Photo.
    Dynamically detects MIME types to prevent '400 INVALID_ARGUMENT'.
    """
    print(f"🔄 Processing Claim for {mobile_number}...")

    # --- 1. GET BYTES & DYNAMIC MIME TYPES ---
    # Streamlit file objects have a .type attribute (e.g., 'application/pdf', 'image/png')
    
    # Audio
    audio_bytes = audio_file.getvalue()
    audio_mime = audio_file.type if hasattr(audio_file, 'type') else "audio/mp3"

    # Land Doc (Could be PDF or Image)
    land_bytes = land_file.getvalue()
    land_mime = land_file.type if hasattr(land_file, 'type') else "application/pdf"

    # Crop Photo (Usually Image)
    crop_bytes = crop_file.getvalue()
    crop_mime = crop_file.type if hasattr(crop_file, 'type') else "image/jpeg"

    print(f"📂 Debug Types -> Land: {land_mime}, Crop: {crop_mime}, Audio: {audio_mime}")

        # --- STEP 2: CONSTRUCT THE PROMPT (The Final Master Version) ---
    prompt = f"""
    You are a Senior Talathi (Revenue Officer) and Insurance Expert.
    
    --- INPUTS ---
    1. **DOCUMENT**: A 7/12 Extract (Satbara). Scan the ENTIRE document.
       - "Village Form 7" (Namuna 7 - Ownership) is usually on Page 1.
       - "Village Form 12" (Namuna 12 - Crop History) is usually at the end (Page 2 or 3).
    2. **EVIDENCE**: Photo of the damaged farm.
    3. **VOICE CLAIM**: Farmer's complaint in **Hindi, Marathi, or English**: "{audio_file}" (Assume current year is 2025).

    --- 1. VISUAL VERIFICATION (CONTEXT AWARE) ---
    **Task**: Verify if the EVIDENCE image is *related* to agriculture or disaster.
    
    **ACCEPT AS VALID IF**:
    - Wide shots of fields (Green, Dry, or Harvested).
    - **Flooded land / Waterlogged soil** (CRITICAL: Accept this for flood claims).
    - **Broken plants / Hailstones on ground**.
    - **Muddy / Barren soil** (Post-disaster).
    - **Close-ups** of leaves, cotton bolls, or roots.
    
    **REJECT ONLY IF**:
    - The image is CLEARLY irrelevant (e.g., Selfie, Car, Dog inside house, Laptop screen, Pitch Black).
    
    **RULE**: If the image is ambiguous (e.g., just dirty water), **GIVE THE BENEFIT OF DOUBT** and proceed.

   --- 2. DOCUMENT & DATA EXTRACTION ---
    - **Step A: Identify Target Farmer (CRITICAL EXCLUSION RULE)**:
        - Listen to the **VOICE CLAIM** for the farmer's name.
        - Search the "Namuna 7" (Occupant/Bhogvatadar) column for this name.
        - **⛔ EXCLUSION RULE**: If a name is enclosed in **Square Brackets `[...]`** (e.g., `[Name]`), **Parentheses `(...)`**, or has a **Strike-through**, it is a CANCELLED/DELETED entry. **IGNORE IT COMPLETELY.**
        - You must find the **Active Entry** (Name without brackets) for this farmer.
        - **EXTRACT**: The "Khate Number" (Account No) usually found in the column next to the name (e.g., '330' or '108').
        
    - **Step B: Extract Location**: Village, Taluka, District, Survey/Gat No.
    
    - **Step C: Extract Exact Area (CRITICAL)**:
        - Look for the area (Kshetra) specifically associated with the **Active Farmer's Entry**.
        - Do NOT simply pick the largest number. Pick the number on the **same row/block** as the un-bracketed Name.

    - **Step D: Locate Crop Info (Namuna 12)**: 
        - Scan the table "गाव नमुना बारा" (Village Form 12).
        - Look for the **LATEST AVAILABLE YEAR** (e.g., 2025-26, 2024-25).
        - Extract the Crop Name & Season.
        **Scan ALL rows**: A farmer may have multiple crops (e.g., Soybean 0.40 Ha AND Potato 0.20 Ha).
        - Identify **ALL crops** grown by this specific Khata Number/Farmer in the current season and year.
        - **Area Check**: Use the area found in Namuna 12 (Pikache Kshetra). If it is blank or 0, fallback to the Area found in Step C.

    --- 3. VERIFICATION & LOGIC CHECKS ---
    - **Step A: Recency Check (The "Outdated" Rule)**: 
       - If the Latest Year in Namuna 12 is **2024 or 2025**: The document is CURRENT.
       - If the Latest Year is **Older than 2024**: The document is OUTDATED.
    
    - **Step B: Crop Verification**:
       - **If CURRENT**: Compare Voice Crop vs. Document Crop.
         - If Match -> Status: "Verified".
         - If Document says "Fallow" or different crop -> Status: "Mismatch".
       - **If OUTDATED**: Ignore Document Crop. Trust the Voice Crop. Status: "Verified (Voice Override)".

    - **Step C: Cause Match**: Extract the disaster (Flood/Hail) from Voice.

    --- 4. FINANCIAL CALCULATIONS (SCALE OF FINANCE 2025) ---
    - **Step A: Determine Rate**:
       - Cotton / Potato / Onion: ₹60,000 per Hectare.
       - Soybean / Rice / Maize: ₹45,000 per Hectare.
       - **Jowar / Bajra / Wheat: ₹35,000 per Hectare**.
       - Others: ₹40,000 per Hectare.
    
    **Step B: Calculate Sum Insured (MULTI-CROP SUMMATION)**:
       - **Rule**: If multiple crops are found in Namuna 12 for the current season:
         1. Calculate (Area * Rate) for **Crop A**.
         2. Calculate (Area * Rate) for **Crop B**.
         3. **SUM THEM UP** for the Total Sum Insured.
       - *Example*: (Soybean 0.4 Ha * 45k) + (Potato 0.2 Ha * 60k) = 18k + 12k = ₹30,000.
        - Else: Area (Ha) * Rate.

    - **Step C: Calculate Premium (For PDF Field 'c')**:
       - **Rule**:
         - Commercial (Cotton/Potato): 5% of Sum Insured.
         - Kharif (Soybean/Rice): 2% of Sum Insured.
         - Rabi (Jowar/Wheat): 1.5% of Sum Insured.
       - **Example**: (Cotton 0.5 Ha * 60,000 Rate = 30,000 Sum Insured) -> 30,000 * 0.05 = ₹1,500 Premium.

    - **Step D: Calculate Estimated Payout**: Sum Insured * 100% (Assuming Full Loss).

    --- JSON OUTPUT FORMAT ---
    Return ONLY valid JSON. 
    For the "form_fields" section, you MUST provide the standard value (in Marathi/Hindi as found in doc) AND an "_english" key with the transliteration.
    {{
        "status": "success",
        "voice_response": "Short empathetic response in the same language as input (Hindi/Marathi/English).",
        "verification": {{
           "status": "Verified / Mismatch",
            "reason": "Full explanation logic.",
            "visual_finding": "Short description of what is seen in photo (e.g. 'Standing water visible', 'Hailstones on ground', 'Wilted leaves')."
        }}
        "claim_estimation": {{
            "estimated_payout": "Calculated in Step D (e.g. ₹30,000)",
            "rate_applied": "e.g. ₹ 60,000 / Ha (Cotton)",  # <--- ADD THIS LINE
            "deductible_rule": "e.g. 2% (Kharif Strategy)", # <--- ADD THIS LINE
            "logic": "Show the math (e.g. 0.5 Ha * ₹60,000)",
            "disclaimer": "This is an estimate based on district averages."
        }},
        "form_fields": {{
            "farmer_full_name": "Extract from Namuna 7",
            "farmer_full_name_english": "Name Transliterated to English",
            "address_village": "Extract Village",
            "address_village_english": "Village in English",
            "address_taluka": "Extract Taluka",
            "address_taluka_english": "Taluka in English",
            "address_district": "Extract District",
            "survey_number": "Extract Survey/Gat No",
            "khate_number": "Extract Khate/Account Number (e.g. 330)",
            "crop_name": "FINAL CROP DECISION (If Verified -> Doc Crop. If Outdated -> Voice Crop)",
            "crop_name_english": "Crop Name in English",
            "sown_area_hectare": "Extract Area from Namuna 12",
            "scheme_name": "प्रधानमंत्री पीक विमा योजना (PMFBY)",
            "premium_amount": "Calculated in Step C (e.g. ₹1,500)",
            "cause_of_loss": "Extract from Voice",
            "date_of_loss": "{datetime.now().strftime('%d/%m/%Y')}",
            "season": "Extract Season (Kharif/Rabi) from Namuna 12",
            "financial_year": "Extract Year (e.g. 2025-26) from Namuna 12"
        }}
    }}
    """

    # --- 3. CALL GEMINI (With Correct MIME Types) ---
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", # Switch to 2.0-flash or 1.5-flash
            contents=[
                prompt,
                types.Part.from_bytes(data=land_bytes, mime_type=land_mime), # 7/12 (PDF/Img)
                types.Part.from_bytes(data=crop_bytes, mime_type=crop_mime), # Evidence (Img)
                types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime) # Voice
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", 
                temperature=0.2
            )
        )
        
        text_response = clean_json_text(response.text)
        ai_data = json.loads(text_response)

    except Exception as e:
        return {"status": "error", "reason": f"AI Error: {str(e)}"}

    # --- 4. MERGE & RETURN (Existing Logic) ---
    final_data = ai_data.get("form_fields", {})
    if "claim_estimation" in ai_data:
        final_data["estimated_payout"] = ai_data["claim_estimation"].get("estimated_payout")

    # DB Fallback logic (Keep your existing logic here)
    final_data["mobile"] = mobile_number
    
    real_app_id = save_claim_to_db(final_data, 0.95)
    final_data["application_id"] = real_app_id

    # ... inside agent_engine.py, at the very bottom ...

    return {
        "status": "success", 
        "data": final_data,            # For App Display & Marathi Form
        "full_report_data": ai_data,   # For English PDF Report
        "voice_response": ai_data.get("voice_response")
    }
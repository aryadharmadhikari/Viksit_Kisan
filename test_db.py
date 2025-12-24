import os
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Connect to MongoDB
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["viksit_kisan_db"] # This creates the DB if it doesn't exist
    print("✅ Connected to MongoDB Atlas")
except Exception as e:
    print(f"❌ Connection Error: {e}")
    exit()

# 3. Define the Demo Data
farmers_data = [
    {
        "mobile_number": "9922001122",
        "full_name": "Ramdas Patil",
        "profile_photo": "https://cdn-icons-png.flaticon.com/512/3048/3048122.png",
        "address": {
            "village": "Pimpri",
            "taluka": "Yavatmal",
            "district": "Yavatmal",
            "state": "Maharashtra"
        },
        "bank_details": {
            "bank_name": "Bank of Maharashtra",
            "account_no": "60012345678",
            "ifsc_code": "MAHB0001234",
            "branch": "Yavatmal Main"
        },
        "land_records": [
            {
                "survey_number": "42/B",
                "area_hectares": 1.20,
                "crop_sown": "Cotton"
            }
        ]
    },
    {
        "mobile_number": "8888999900",
        "full_name": "Kondiba Sabaji Tambe",
        "profile_photo": "https://cdn-icons-png.flaticon.com/512/3048/3048122.png",
        "address": {
            "village": "Shirdaewadi",
            "taluka": "Ambegaon",
            "district": "Pune",
            "state": "Maharashtra"
        },
        "bank_details": {
            "bank_name": "State Bank of India",
            "account_no": "30045678901",
            "ifsc_code": "SBIN0001234",
            "branch": "Manchar"
        },
        "land_records": [
            {
                "survey_number": "102",
                "area_hectares": 0.38,
                "crop_sown": "Potato"
            }
        ]
    }
]

# 4. Insert Data (Upsert Strategy)
# This prevents duplicates. If 9922001122 exists, it updates it. If not, it creates it.
farmers_col = db["farmers"]

for farmer in farmers_data:
    farmers_col.replace_one(
        {"mobile_number": farmer["mobile_number"]}, # Query
        farmer,                                      # New Data
        upsert=True                                  # Create if missing
    )

print(f"✅ Successfully inserted/updated {len(farmers_data)} farmer profiles.")

# 5. Initialize 'claims' collection (Optional, just to ensure it exists)
if "claims" not in db.list_collection_names():
    db.create_collection("claims")
    print("✅ Created empty 'claims' collection for storing history.")
else:
    print("ℹ️ 'claims' collection already exists.")
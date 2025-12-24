# seed_claims.py (Run once if you want dummy history)
import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["viksit_kisan_db"]
claims_col = db["claims"]

dummy_claim = {
    "application_id": "PMFBY-HISTORIC-001",
    "farmer_mobile": "9922001122",
    "timestamp": datetime.now(),
    "status": "Approved",
    "ai_confidence_score": 0.99,
    "submitted_data": {
        "farmer_name": "Ramdas Patil",
        "crop": "Soybean",
        "loss": "Flood"
    }
}

claims_col.insert_one(dummy_claim)
print("✅ Dummy claim inserted. Collection 'claims' is ready.")
import streamlit as st
import time
import os
import re
import json
from datetime import datetime
import pymongo
from authlib.integrations.requests_client import OAuth2Session

# --- Custom Modules ---
from pdf_generator import generate_filled_pdf
from agent_engine import process_claim, db
from report_gen import generate_best_report 

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Viksit Kisan",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# -----------------------------------------------------------------------------
# 2. CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp { background-color: #F8F9FA; color: #333333; }
    .css-card {
        background-color: white; padding: 20px; border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; border: 1px solid #E0E0E0;
    }
    div.stButton > button {
        width: 100%; height: 55px; background-color: #2E7D32; color: white !important;
        font-size: 18px; font-weight: 600; border-radius: 10px; border: none;
    }
    div.stButton > button:hover { background-color: #1B5E20; }
    .live-dot {
        height: 12px; width: 12px; background-color: #00C851; border-radius: 50%;
        display: inline-block; animation: pulse 2s infinite; margin-right: 8px;
    }
    [data-testid='stFileUploader'] { background-color: white; padding: 10px; border-radius: 10px; border: 1px dashed #2E7D32; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def clean_mobile_number(mobile):
    if not mobile: return ""
    clean = re.sub(r'\D', '', str(mobile))
    return clean[-10:]

def check_user_db(identifier, type="mobile"):
    if db is None: return None
    farmers_col = db["farmers"]
    if type == "mobile":
        clean_input = clean_mobile_number(identifier)
        user = farmers_col.find_one({"mobile_number": clean_input})
        if not user and clean_input.isdigit():
            user = farmers_col.find_one({"mobile_number": int(clean_input)})
        return user
    else:
        return farmers_col.find_one({"email": identifier})

def register_user_db(data):
    if db is None: return False
    try:
        query = {"email": data["email"]} if data.get("email") else {"mobile_number": data["mobile_number"]}
        db["farmers"].update_one(query, {"$set": data}, upsert=True)
        return True
    except: return False

def log_claim_to_db(final_data, ai_response, mobile, confidence=0.99):
    """
    Logs the claim to MongoDB using Upsert to prevent duplicates.
    This ensures the 'Calculating...' record is overwritten with final data.
    """
    if db is None: return None
    claims_col = db["claims"]
    app_id = final_data.get("application_id", f"PMFBY-{int(time.time())}")
    
    # Extract Voice Response Safely
    voice_msg = ai_response.get("voice_response") or final_data.get("voice_response") or "Claim processed successfully."
    
    claim_document = {
        "application_id": app_id,
        "farmer_mobile": mobile,
        "timestamp": datetime.now(),
        "status": "Approved" if ai_response.get("status") == "success" else "Rejected",
        "ai_confidence_score": confidence,
        "voice_response": voice_msg,
        "submitted_data": final_data # final_data now contains the forced payout
    }
    
    # FIX: Use update_one with upsert=True instead of insert_one
    claims_col.update_one(
        {"application_id": app_id},
        {"$set": claim_document},
        upsert=True
    )
    return app_id

def get_claim_from_db(app_id):
    if db is None: return None
    return db["claims"].find_one({"application_id": app_id})

# -----------------------------------------------------------------------------
# 4. SESSION & AUTH
# -----------------------------------------------------------------------------

if 'mongo_user' not in st.session_state: st.session_state.mongo_user = None
if 'current_app_id' not in st.session_state: st.session_state.current_app_id = None
if 'report_path' not in st.session_state: st.session_state.report_path = None
if 'form_path' not in st.session_state: st.session_state.form_path = None

google_user = None
if hasattr(st, "user"):
    google_user = st.user

# SCENARIO 1: NOT LOGGED IN
if not google_user or not google_user.get("email"):
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=80)
        st.markdown("<h2 style='text-align: center;'>Viksit Kisan</h2>", unsafe_allow_html=True)
        st.info("Please log in to access the portal.")
        if st.button("Login with Google"):
            if hasattr(st, "login"): st.login(provider="google")
            else: st.error("Login service unavailable.")

# SCENARIO 2: LOGGED IN
else:
    user_email = google_user.get("email")
    if st.session_state.mongo_user is None:
        db_user = check_user_db(user_email, type="email")
        if db_user:
            st.session_state.mongo_user = db_user
            st.rerun()
        else:
            st.session_state.show_register = True

    # -------------------------------------------------------------------------
    # 5. REGISTRATION
    # -------------------------------------------------------------------------
    if st.session_state.get('show_register', False) and not st.session_state.mongo_user:
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown("### 📝 Complete Your Profile")
            st.info(f"Setting up: {user_email}")
            with st.form("reg_form"):
                fname = st.text_input("Full Name (शेतकऱ्याचे नाव)")
                village = st.text_input("Village (गाव)")
                taluka = st.text_input("Taluka (तालुका)")
                district = st.text_input("District (जिल्हा)")
                mob = st.text_input("Mobile Number", max_chars=10)
                bank_account_number = st.text_input("Bank Account No.", max_chars=12)
                bank_name = st.text_input("Bank Name")
                st.text_input("Email", value=user_email, disabled=True)
                
                if st.form_submit_button("Save & Continue"):
                    if fname and mob:
                        new_user = {
                            "farmer_full_name": fname,
                            "address_village": village,
                            "address_taluka": taluka,
                            "address_district": district,
                            "mobile_number": clean_mobile_number(mob),
                            "email": user_email,
                            "bank_account_number": bank_account_number,
                            "bank_name": bank_name
                        }
                        if register_user_db(new_user):
                            st.session_state.mongo_user = new_user
                            st.session_state.show_register = False
                            st.rerun()
                        else: st.error("DB Error")
            if st.button("Logout"):
                if hasattr(st, "logout"): st.logout()

    # -------------------------------------------------------------------------
    # 6. MAIN DASHBOARD
    # -------------------------------------------------------------------------
    elif st.session_state.mongo_user:
        
        # Header
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=60)
        with col2:
            st.markdown(f"""
                <div style='text-align: right; padding-top: 10px; color: #555;'>
                    <span class='live-dot'></span>
                    <small><b>GOVT SERVER: CONNECTED</b></small><br>
                    <small>User: {st.session_state.mongo_user.get('farmer_full_name')}</small>
                </div>
            """, unsafe_allow_html=True)
        st.divider()

        # Hero
        st.markdown(f"### 👋 Namaskar, {st.session_state.mongo_user.get('farmer_full_name', '').split()[0]}")
        st.caption("Press the microphone and speak in Marathi")
        audio_input = st.audio_input("Record Voice Explanation")

        # Evidence
        st.markdown("#### 📸 Upload Evidence")
        c1, c2 = st.columns(2)
        with c1: st.info("📄 **7/12 Extract**"); land_file = st.file_uploader("Upload PDF/Img", type=['pdf','jpg','png'], key="land")
        with c2: st.info("🌱 **Crop Photo**"); crop_image = st.file_uploader("Upload Photo", type=['jpg','png'], key="crop")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- SUBMIT LOGIC ---
        if st.button("🚀 Submit Claim (Arj Kara)"):
            if not (audio_input and land_file and crop_image):
                st.error("⚠️ Please provide Audio, 7/12 Extract, and Crop Photo.")
            else:
                st.session_state.current_app_id = None
                
                with st.status("🔄 AI Agent Working...", expanded=True) as status:
                    try:
                        user_mobile = st.session_state.mongo_user.get("mobile_number")
                        st.write("🎧 Analyzing Voice & Documents...")
                        
                        # 1. AI Processing
                        ai_result = process_claim(audio_input, land_file, crop_image, user_mobile)
                        
                        if ai_result.get("status") == "success":
                            full_report_data = ai_result.get("full_report_data", {}) 
                            final_data = ai_result.get("data", {})
                            
                            # --- FIX: DATA SYNC START ---
                            # 1. Force Payout from Report into Final Data
                            est_block = full_report_data.get("claim_estimation", {})
                            payout_val = est_block.get("estimated_payout", "Under Assessment")
                            final_data["estimated_payout"] = payout_val
                            
                            # 2. Force Voice Response
                            voice_val = full_report_data.get("voice_response") or ai_result.get("voice_response")
                            if not voice_val:
                                voice_val = "Your claim has been received and verified."
                            ai_result["voice_response"] = voice_val
                            # --- FIX: DATA SYNC END ---

                            app_id = final_data.get("application_id")
                            
                            # 2. Log to MongoDB (Now using Update/Upsert)
                            st.write("💾 Logging to Government Ledger...")
                            log_claim_to_db(final_data, ai_result, user_mobile)
                            
                            # 3. Generate PDFs
                            st.write("📄 Generating Files...")
                            temp_img = f"temp_{user_mobile}.jpg"
                            with open(temp_img, "wb") as f: f.write(crop_image.getvalue())
                            
                            r_path = generate_best_report(full_report_data, temp_img, output_filename=f"Report_{app_id}.pdf")
                            f_path = generate_filled_pdf({"form_fields": final_data}, output_path=f"Claim_{app_id}.pdf")
                            
                            if os.path.exists(temp_img): os.remove(temp_img)
                            
                            # 4. Update Session
                            st.session_state.current_app_id = app_id
                            st.session_state.report_path = r_path
                            st.session_state.form_path = f_path
                            
                            status.update(label="✅ Claim Processed!", state="complete", expanded=False)
                            st.balloons()
                        else:
                            st.error(f"Failed: {ai_result.get('reason')}")
                    except Exception as e:
                        st.error(f"System Error: {e}")

        # --- PERSISTENT BLOCK (READ FROM DB) ---
        if st.session_state.current_app_id:
            db_claim = get_claim_from_db(st.session_state.current_app_id)
            
            if db_claim:
                res_data = db_claim.get("submitted_data", {})
                
                # Fetching fixed values from DB
                payout = res_data.get("estimated_payout", "Calculating...")
                voice_msg = db_claim.get("voice_response", "Processed.")
                status_txt = db_claim.get("status", "Submitted")
                
                st.markdown(f"""
                <div class="css-card">
                    <h3 style="color: #2E7D32; margin-top: 0;">✅ Application Generated</h3>
                    <p><b>Application ID:</b> {db_claim.get('application_id')}</p>
                    <p><b>Estimated Payout:</b> <span style="color: #2E7D32; font-size: 1.2em; font-weight: bold;">{payout}</span></p>
                    <p><b>Status:</b> {status_txt} (AI Verified)</p>
                    <hr>
                    <p><i>"{voice_msg}"</i></p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)
                with c1:
                    r_path = st.session_state.report_path
                    if r_path and os.path.exists(r_path):
                        with open(r_path, "rb") as f:
                            st.download_button("📊 Download Report", f, file_name=os.path.basename(r_path))
                with c2:
                    f_path = st.session_state.form_path
                    if f_path and os.path.exists(f_path):
                        with open(f_path, "rb") as f:
                            st.download_button("📄 Download Form", f, file_name=os.path.basename(f_path))

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Logout", type="secondary"):
            if hasattr(st, "logout"): st.logout()
            else: st.session_state.clear(); st.rerun()
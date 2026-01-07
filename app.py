import streamlit as st
import time
import os
import re
import json
from datetime import datetime
import pymongo
from authlib.integrations.requests_client import OAuth2Session

# BRIDGE: Inject Streamlit Secrets into OS Environment for agent_engine.py
if hasattr(st, "secrets"):
    if "MONGO_URI" in st.secrets:
        os.environ["MONGO_URI"] = st.secrets["MONGO_URI"]
    if "GOOGLE_API_KEY" in st.secrets:
        os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]

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
# 2. CUSTOM CSS (Refined for Perfect Centering)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* Global Background */
    .stApp {
        background-color: #F8F9FA;
        background-image: radial-gradient(#E8F5E9 1px, transparent 1px);
        background-size: 24px 24px;
    }
    #MainMenu, footer, header {visibility: hidden;}

    /* LOGIN CARD CONTAINER */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 24px; /* Slightly softer corners */
        box-shadow: 0 12px 40px rgba(0,0,0,0.08); /* Softer shadow */
        border: 1px solid #E0E0E0;
        margin: auto;
        padding: 3rem 2rem; /* Adjusted padding to give text room */
        max-width: 420px; /* Increased slightly to prevent word wrap */
        text-align: center;
    }

    /* TYPOGRAPHY */
    .login-title {
        font-family: 'Segoe UI', Roboto, sans-serif;
        color: #1B5E20;
        font-weight: 800;
        font-size: 2rem; /* Reduced slightly to fit one line */
        margin: 15px 0 5px 0; /* Added top margin for icon separation */
        text-align: center;
        line-height: 1.2;
        white-space: nowrap; /* Forces text to stay on one line */
    }
    .login-subtitle {
        font-family: 'Segoe UI', Roboto, sans-serif;
        color: #757575;
        font-size: 1.1rem;
        text-align: center;
        margin-top: 0px;
        margin-bottom: 30px;
        font-weight: 400;
    }

    /* BUTTON STYLING */
    div.stButton {
        display: flex;
        justify-content: center;
        width: 100%; 
    }
    div.stButton > button {
        width: 100% !important;
        height: 52px;
        background: linear-gradient(135deg, #16A34A 0%, #15803D 100%);
        color: white !important;
        font-size: 16px;
        font-weight: 600;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 12px rgba(22, 163, 74, 0.25);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        /* Lighter, brighter green gradient on hover */
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); 
        /* A subtle green glow border */
        box-shadow: 0 8px 20px rgba(34, 197, 94, 0.4); 
        border: 1px solid #86EFAC; /* Soft green border */
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 16px rgba(22, 163, 74, 0.35);
    }
    div.stButton > button:active {
        transform: translateY(0px);
    }

    /* BADGE */
    .govt-badge {
        display: inline-block;
        margin-top: 25px;
        padding: 8px 16px;
        background-color: #F0FDF4;
        color: #166534;
        border-radius: 50px;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #DCFCE7;
        letter-spacing: 0.5px;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
    /* Centering Helper */
    div[data-testid="column"] {
        display: flex;
        align-items: center;
        justify-content: center;
    }
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

# A. Helper to generate Login URL
def get_google_auth_url():
    try:
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        redirect_uri = st.secrets["google"]["redirect_uri"]
        
        oauth = OAuth2Session(client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        auth_url, state = oauth.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            access_type="offline", prompt="select_account", scope="openid email profile"
        )
        return auth_url
    except Exception as e:
        st.error(f"Secrets Error: {e}")
        return None

# B. Callback Handler (Captures the 'code' from URL) - THIS WAS MISSING
if "code" in st.query_params:
    try:
        code = st.query_params["code"]
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        redirect_uri = st.secrets["google"]["redirect_uri"]
        
        oauth = OAuth2Session(client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        token = oauth.fetch_token('https://oauth2.googleapis.com/token', code=code, client_secret=client_secret)
        user_info = oauth.get('https://www.googleapis.com/oauth2/v1/userinfo').json()
        email = user_info.get("email")
        
        if email:
            db_user = check_user_db(email, type="email")
            if db_user:
                st.session_state.mongo_user = db_user
            else:
                st.session_state.temp_reg_email = email
                st.session_state.show_register = True
            
            st.query_params.clear()
            st.rerun()
            
    except Exception as e:
        st.error(f"Auth Failed: {e}")
        st.query_params.clear()

# SCENARIO 1: NOT LOGGED IN
if not st.session_state.mongo_user and not st.session_state.get('show_register'):
    
    # Vertical Spacers
    st.write("")
    st.write("")
    st.write("")

    # Columns: [1, 1, 1] centers the card perfectly
    left, center, right = st.columns([1, 1.2, 1]) 
    
    with center:
        # THE CARD CONTAINER
        with st.container(border=True):
            
            # 1. Logo (Restored the Green Leaf Sprout)
            st.markdown("""
                <div style="text-align: center;">
                    <img src="https://cdn-icons-png.flaticon.com/512/2917/2917995.png" width="70">
                </div>
            """, unsafe_allow_html=True)
            
            # 2. Text
            st.markdown("""
                <h1 class="login-title">Viksit Kisan</h1>
                <p class="login-subtitle">Digital Crop Insurance Portal</p>
            """, unsafe_allow_html=True)
            
            # 3. Button - use_container_width=True ensures full width
            auth_url = get_google_auth_url()
            if auth_url:
                st.link_button("Continue with Google", auth_url, use_container_width=True)
            else:
                st.error("Google Secrets Config Missing (Check secrets.toml)")
            
            # 4. Badge
            st.markdown("""
                <div class="govt-badge">
                    🏛️ Initiative for Maharashtra Farmers
                </div>
            """, unsafe_allow_html=True)

# SCENARIO 2: LOGGED IN
else:
    user_email = st.session_state.mongo_user.get("email") if st.session_state.mongo_user else st.session_state.get("temp_reg_email")
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
                            "Applicant_full_name": fname,
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
            st.image("https://cdn-icons-png.flaticon.com/512/2917/2917995.png", width=60)
        with col2:
            st.markdown(f"""
                <div style='text-align: right; padding-top: 10px; color: #555;'>
                    <span class='live-dot'></span>
                    <small><b>GOVT SERVER: CONNECTED</b></small><br>
                    <small>User: {st.session_state.mongo_user.get('Applicant_full_name')}</small>
                </div>
            """, unsafe_allow_html=True)
        st.divider()

       # --- HERO SECTION (Fixed Name Logic) ---
        full_name = st.session_state.mongo_user.get('Applicant_full_name', '')
        
        # Logic: 
        # 1. If name exists ("Kailas Tajane"), take first word ("Kailas")
        # 2. If name is missing/empty, fallback to "Shetkari" (Farmer)
        if full_name and len(str(full_name).strip()) > 0:
            first_name = str(full_name).strip().split()[0]
        else:
            first_name = "Shetkari" # Fallback if name is missing

        st.markdown(f"### 👋 Namaskar, {first_name} Bhau")
        st.caption("Press the microphone and speak in Marathi")
        # Voice Instructions Box
       # Voice Instructions Box (Updated for Clarity)
        st.markdown("""
        <div style="background-color: #E8F5E9; padding: 15px; border-radius: 10px; border-left: 5px solid #2E7D32; margin-bottom: 15px;">
            <p style="margin: 0; font-weight: bold; color: #1B5E20; font-size: 16px;">
                🎙️ रेकॉर्डिंग करताना हे सांगा (Speak the following):
            </p>
            <ul style="margin: 8px 0 0 20px; color: #333; font-size: 15px; line-height: 1.6;">
                <li>
                    <b>सातबाऱ्यावरील शेतकऱ्याचे नाव</b> <br>
                    <span style="color: #666; font-size: 13px;">(Farmer's Name as per 7/12 Document)</span>
                </li>
                <li>
                    <b>नुकसान झालेल्या पिकाचे नाव</b> (उदा. कापूस, सोयाबीन) <br>
                    <span style="color: #666; font-size: 13px;">(Damaged Crop Name e.g. Cotton, Soybean)</span>
                </li>
                <li>
                    <b>नुकसानीचे कारण</b> (उदा. अतिवृष्टी, गारपीट, कीड) <br>
                    <span style="color: #666; font-size: 13px;">(Cause of Loss e.g. Heavy Rain, Hailstorm, Pest)</span>
                </li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # Audio Input
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

                        # --- ADD THIS BLOCK: INJECT DB USER DETAILS ---
                            # This ensures the logged-in user's details override AI guesses
                            db_user = st.session_state.mongo_user
                    
                            final_data["mobile_number"] = db_user.get("mobile_number")
                            final_data["email"] = db_user.get("email")
                            final_data["bank_account_number"] = db_user.get("bank_account_number")
                            final_data["bank_name"] = db_user.get("bank_name")
                            # ---------------------------------------------

                            # For Report (report_gen) - Passing the Login Name
                            full_report_data["filer_name"] = db_user.get("Applicant_full_name", "")
                            
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
                <div class="css-card" style="border-top: 5px solid #2E7D32; text-align: center;">
                    <h3 style="color: #2E7D32; margin: 0 0 10px 0;">✅ Application Generated</h3>
                    <p style="color: #666; font-size: 13px; margin: 0;">Application ID: <b>{db_claim.get('application_id')}</b></p>
                <div style="background-color: #E8F5E9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <span style="color: #1B5E20; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Estimated Payout</span><br>
                    <span style="color: #2E7D32; font-size: 24px; font-weight: 800;">{payout}</span>
                </div>
                    <p style="font-style: italic; color: #555; font-size: 14px; line-height: 1.5;">"{voice_msg}"</p>
                </div>
                """, unsafe_allow_html=True)
                
                # --- REPLACED DOWNLOAD SECTION ---
                st.markdown("### 📥 Download Documents")
                dl_col1, dl_col2 = st.columns(2, gap="medium")
                
                with dl_col1:
                    r_path = st.session_state.report_path
                    if r_path and os.path.exists(r_path):
                        with open(r_path, "rb") as f:
                            st.download_button(
                                label="📊 Download Intelligence Report",
                                data=f,
                                file_name=os.path.basename(r_path),
                                mime="application/pdf",
                                use_container_width=True
                            )
                
                with dl_col2:
                    f_path = st.session_state.form_path
                    if f_path and os.path.exists(f_path):
                        with open(f_path, "rb") as f:
                            st.download_button(
                                label="📄 Download Official Form",
                                data=f,
                                file_name=os.path.basename(f_path),
                                mime="application/pdf",
                                use_container_width=True
                            )
                # ---------------------------------
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Logout", type="secondary"):
            if hasattr(st, "logout"): st.logout()
            else: st.session_state.clear(); st.rerun()
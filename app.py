import streamlit as st
import time
import os
import re
import json
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
# 2. CUSTOM CSS (The "Mobile App" Look)
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    /* HIDE STREAMLIT BRANDING */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* APP BACKGROUND */
    .stApp {
        background-color: #F8F9FA;
        color: #333333;
    }

    /* CARD STYLE (Neumorphism) */
    .css-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 15px;
        border: 1px solid #E0E0E0;
    }

    /* BIG GREEN BUTTONS */
    div.stButton > button {
        width: 100%;
        height: 55px;
        background-color: #2E7D32; /* Agri Green */
        color: white !important;
        font-size: 18px;
        font-weight: 600;
        border-radius: 10px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #1B5E20;
        color: white !important;
    }

    /* STATUS DOT ANIMATION */
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
    .live-dot {
        height: 12px;
        width: 12px;
        background-color: #00C851;
        border-radius: 50%;
        display: inline-block;
        animation: pulse 2s infinite;
        margin-right: 8px;
    }
    
    /* UPLOAD BOX STYLING */
    [data-testid='stFileUploader'] {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        border: 1px dashed #2E7D32;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE SETUP ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = {} 
if 'show_register' not in st.session_state:
    st.session_state.show_register = False

# -----------------------------------------------------------------------------
# 3. HELPER FUNCTIONS (DB & Auth)
# -----------------------------------------------------------------------------

def clean_mobile_number(mobile):
    """Removes +91, spaces, hyphens to ensure consistent matching."""
    if not mobile: return ""
    clean = re.sub(r'\D', '', str(mobile))
    return clean[-10:]

def check_user_db(identifier, type="mobile"):
    """Checks MongoDB for existing user using fuzzy matching logic."""
    if db is None: 
        st.error("❌ Database Not Connected!")
        return None

    farmers_col = db["farmers"]
    user = None

    if type == "mobile":
        clean_input = clean_mobile_number(identifier)
        print(f"🔍 DEBUG: Searching DB for Mobile: '{clean_input}'")
        
        # 1. Search Clean String
        user = farmers_col.find_one({"mobile_number": clean_input})
        
        # 2. Search Integer
        if not user and clean_input.isdigit():
            user = farmers_col.find_one({"mobile_number": int(clean_input)})
            
        # 3. Search Raw
        if not user:
             user = farmers_col.find_one({"mobile_number": identifier})

    else:
        # Email search
        print(f"🔍 DEBUG: Searching DB for email: '{identifier}'")
        user = farmers_col.find_one({"email": identifier})
        
    return user

def register_user_db(data):
    """Saves new farmer to MongoDB."""
    if db is None: return False
    farmers_col = db["farmers"]
    try:
        query = {"mobile_number": data["mobile_number"]}
        existing = farmers_col.find_one(query)
        
        if existing:
            farmers_col.update_one(query, {"$set": data})
        else:
            farmers_col.insert_one(data)
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False

# --- GOOGLE AUTH ---
def google_login():
    try:
        client_id = st.secrets["google"]["client_id"]
        client_secret = st.secrets["google"]["client_secret"]
        redirect_uri = st.secrets["google"]["redirect_uri"]
        
        oauth = OAuth2Session(client_id, client_secret=client_secret, redirect_uri=redirect_uri)
        authorization_url, state = oauth.create_authorization_url(
            'https://accounts.google.com/o/oauth2/v2/auth',
            access_type="offline", 
            prompt="select_account",
            scope="openid email profile"
        )
        return authorization_url
    except:
        return None

# -----------------------------------------------------------------------------
# 4. LOGIN & REGISTER SCREEN
# -----------------------------------------------------------------------------
if not st.session_state.logged_in:
    
    # --- A. HANDLE OAUTH CALLBACK ---
    try:
        query_params = st.query_params
        if "code" in query_params:
            st.toast("✅ Verifying Google Account...")
            # Simulate email extraction (In production, swap code for token)
            simulated_email = "farmer.demo@gmail.com"
            
            existing_user = check_user_db(simulated_email, type="email")
            
            if existing_user:
                print(f"✅ DEBUG: Found User: {existing_user.get('farmer_full_name')}")
                st.session_state.user_info = existing_user
                st.session_state.logged_in = True
                st.query_params.clear() # CRITICAL FIX
                st.rerun()
            else:
                st.session_state.user_info = {"email": simulated_email}
                st.session_state.show_register = True
                st.query_params.clear() # CRITICAL FIX
                st.rerun()
    except Exception as e:
        st.error(f"Auth Error: {e}")

    # --- B. UI RENDERING ---
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=80)
        st.markdown("<h2 style='text-align: center;'>Viksit Kisan</h2>", unsafe_allow_html=True)
        
        # --- REGISTER SCREEN ---
        if st.session_state.show_register:
            st.markdown("### 📝 Complete Registration")
            st.info("We couldn't find this number/email in our database. Please register.")
            
            with st.form("reg_form"):
                pre_mob = st.session_state.user_info.get("mobile_number", "")
                pre_email = st.session_state.user_info.get("email", "")
                
                fname = st.text_input("Full Name")
                village = st.text_input("Village")
                taluka = st.text_input("Taluka")
                district = st.text_input("District")
                mob = st.text_input("Mobile Number", value=pre_mob)
                
                if st.form_submit_button("Register & Login"):
                    clean_mob = clean_mobile_number(mob)
                    new_user = {
                        "farmer_full_name": fname,
                        "address_village": village,
                        "address_taluka": taluka,
                        "address_district": district,
                        "mobile_number": clean_mob,
                        "email": pre_email
                    }
                    if register_user_db(new_user):
                        st.session_state.user_info = new_user
                        st.session_state.logged_in = True
                        st.success("Registered!")
                        time.sleep(1)
                        st.rerun()
            
            if st.button("⬅️ Back to Login"):
                st.session_state.show_register = False
                st.session_state.otp_sent = False
                st.rerun()

        # --- LOGIN SCREEN ---
        else:
            tab1, tab2 = st.tabs(["📱 Mobile OTP", "G Google Login"])

            with tab1:
                mobile = st.text_input("Mobile Number (+91)", max_chars=10, key="mob_input")
                
                if st.button("Send OTP"):
                    if len(mobile) >= 10:
                        st.session_state.otp_sent = True
                        st.session_state.temp_mobile = clean_mobile_number(mobile)
                        st.success(f"OTP Sent to {mobile}")
                    else:
                        st.error("Invalid Number")
                
                if st.session_state.get('otp_sent'):
                    otp = st.text_input("Enter OTP", type="password")
                    if st.button("Verify & Login"):
                        if otp == "1234":
                            user = check_user_db(st.session_state.temp_mobile, type="mobile")
                            if user:
                                st.session_state.user_info = user
                                st.session_state.logged_in = True
                                st.rerun()
                            else:
                                st.warning(f"Number {st.session_state.temp_mobile} not found.")
                                st.session_state.user_info = {"mobile_number": st.session_state.temp_mobile}
                                st.session_state.show_register = True
                                st.rerun()
                        else:
                            st.error("Invalid OTP")

            with tab2:
                auth_url = google_login()
                if auth_url:
                    st.link_button("Sign in with Google", auth_url)
                
                st.divider()
                if st.button("Simulation: Google Login"):
                     mock_email = "demo.farmer@gmail.com"
                     user = check_user_db(mock_email, type="email")
                     if user:
                         st.session_state.user_info = user
                         st.session_state.logged_in = True
                         st.rerun()
                     else:
                         st.session_state.user_info = {"email": mock_email}
                         st.session_state.show_register = True
                         st.rerun()

# -----------------------------------------------------------------------------
# 5. MAIN APPLICATION (DASHBOARD)
# -----------------------------------------------------------------------------
else:
    # --- HEADER ("The Badge of Trust") ---
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=60)
    with col2:
        st.markdown("""
            <div style='text-align: right; padding-top: 15px; color: #555;'>
                <span class='live-dot'></span>
                <small><b>GOVT SERVER: CONNECTED</b></small><br>
                <small>User: """ + st.session_state.user_info.get('farmer_full_name', 'Farmer') + """</small>
            </div>
        """, unsafe_allow_html=True)
    st.divider()

    # --- HERO ("The Panic Button") ---
    st.markdown(f"### 👋 {st.session_state.user_info.get('farmer_full_name', 'Ramdas').split()[0]} Bhau, kay jhal?")
    st.caption("Press the microphone and speak in Marathi (e.g., 'Garpit jhala')")
    audio_input = st.audio_input("Record Voice Explanation")

    # --- EVIDENCE SECTION ("The Digital Talathi") ---
    st.markdown("#### 📸 Upload Evidence")
    col_left, col_right = st.columns(2)
    with col_left:
        st.info("📄 **7/12 Extract**")
        land_file = st.file_uploader("Upload 7/12", type=['pdf', 'jpg', 'png', 'jpeg'], key="land")
    with col_right:
        st.info("🌱 **Crop Photo**")
        crop_image = st.file_uploader("Upload Photo", type=['jpg', 'png', 'jpeg'], key="crop")

    # --- INITIALIZE SESSION STATE FOR CLAIM DATA ---
    if "claim_results" not in st.session_state:
        st.session_state.claim_results = None

    # --- ACTION & PROCESSING ---
    st.markdown("<br>", unsafe_allow_html=True)

    # BUTTON: Only triggers the processing
    if st.button("🚀 File Claim (Arj Kara)"):
        # --- RESET STATE (CRITICAL FIX) ---
        # Clear previous results immediately when button is clicked.
        st.session_state.claim_results = None

        # VALIDATION
        if not audio_input:
            st.error("⚠️ Please record your voice first.")
        elif not land_file:
            st.error("⚠️ Please upload the 7/12 Extract.")
        elif not crop_image:
            st.error("⚠️ Please upload a photo of the damaged crop.")
        else:
            with st.status("🔄 AI Agent Working...", expanded=True) as status:
                st.write("🎧 Sending Voice & Data to Gemini...")

                user_mobile = st.session_state.user_info.get("mobile_number", "9922001122")
                
                try:
                    # CALL AI ENGINE
                    ai_result = process_claim(
                        audio_file=audio_input, 
                        land_file=land_file,    
                        crop_file=crop_image,   
                        mobile_number=user_mobile
                    )
                    
                    if ai_result.get("status") == "success":
                        
                        # 1. EXTRACT DATA
                        full_report_data = ai_result.get("full_report_data", {}) 
                        final_data = ai_result.get("data", {})
                        app_id = final_data.get("application_id", "PENDING")
                        voice_response = ai_result.get("voice_response", "Claim Processed.")

                        # 2. SAVE TEMP IMAGE
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_img:
                            tmp_img.write(crop_image.getvalue())
                            temp_img_path = tmp_img.name

                        # 3. GENERATE INTELLIGENCE REPORT
                        report_pdf_path = generate_best_report(
                            json_data=full_report_data, 
                            image_path=temp_img_path, 
                            output_filename=f"Report_{app_id}.pdf"
                        )

                        # Cleanup Temp Image
                        if os.path.exists(temp_img_path):
                            os.remove(temp_img_path)
                        
                        st.write("✍️ Generating Official Application...")

                        # 4. GENERATE APPLICATION FORM PDF
                        pdf_input_data = {"form_fields": final_data}
                        final_pdf_path = generate_filled_pdf(pdf_input_data, output_path=f"Claim_{app_id}.pdf")
                        
                        # --- SAVE NEW RESULTS TO SESSION STATE ---
                        st.session_state.claim_results = {
                            "app_id": app_id,
                            "payout": final_data.get("estimated_payout", "Calculating..."),
                            "voice_response": voice_response,
                            "report_path": report_pdf_path,
                            "form_path": final_pdf_path,
                            "success": True
                        }
                        
                        status.update(label="✅ Claim Processed Successfully!", state="complete", expanded=False)
                        st.balloons()

                    else:
                        status.update(label="❌ Verification Failed", state="error")
                        st.error(f"Claim Rejected: {ai_result.get('reason', 'Unknown Error')}")
                        st.session_state.claim_results = None
                        
                except Exception as e:
                    status.update(label="❌ System Error", state="error")
                    st.error(f"Critical Error: {e}")
                    st.session_state.claim_results = None

    # --- DISPLAY LOGIC (PERSISTENT) ---
    # This block runs on every reload, keeping the data visible
    if st.session_state.claim_results and st.session_state.claim_results["success"]:
        
        res = st.session_state.claim_results # Short variable name
        
        # 1. RESULT CARD
        st.markdown(f"""
        <div class="css-card">
            <h3 style="color: #2E7D32; margin-top: 0;">✅ Application Generated</h3>
            <p><b>Application ID:</b> {res['app_id']}</p>
            <p><b>Estimated Payout:</b> <span style="color: #2E7D32; font-size: 1.2em; font-weight: bold;">{res['payout']}</span></p>
            <p><b>Status:</b> Auto-Verified by AI Talathi</p>
            <hr>
            <p><i>"{res['voice_response']}"</i></p>
        </div>
        """, unsafe_allow_html=True)

        # 2. DOWNLOAD BUTTONS
        col_d1, col_d2 = st.columns(2, gap="medium")
        
        with col_d1:
            if res['report_path'] and os.path.exists(res['report_path']):
                with open(res['report_path'], "rb") as f:
                    st.download_button(
                        label="📊 Download Report",
                        data=f,
                        file_name=f"Report_{res['app_id']}.pdf",
                        mime="application/pdf",
                        key="btn_report_persistent"
                    )

        with col_d2:
            if res['form_path'] and os.path.exists(res['form_path']):
                with open(res['form_path'], "rb") as f:
                    st.download_button(
                        label="📄 Download Application",
                        data=f,
                        file_name=f"Claim_{res['app_id']}.pdf",
                        mime="application/pdf",
                        key="btn_app_persistent"
                    )

    # --- LOGOUT ---
    st.divider()
    if st.button("Logout", type="secondary"):
        # Clear session state on logout
        st.session_state.logged_in = False
        st.session_state.user_info = {}
        st.session_state.claim_results = None 
        st.rerun()
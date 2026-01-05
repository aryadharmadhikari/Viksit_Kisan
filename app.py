import streamlit as st
import time
import os
import re
import json

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
        # 1. Search Clean String
        user = farmers_col.find_one({"mobile_number": clean_input})
        # 2. Search Integer
        if not user and clean_input.isdigit():
            user = farmers_col.find_one({"mobile_number": int(clean_input)})
    else:
        # Email search
        user = farmers_col.find_one({"email": identifier})
        
    return user

def register_user_db(data):
    """Upserts user data into MongoDB."""
    if db is None: return False
    farmers_col = db["farmers"]
    try:
        query = {}
        if data.get("email"):
            query = {"email": data["email"]}
        else:
            query = {"mobile_number": data["mobile_number"]}
            
        farmers_col.update_one(query, {"$set": data}, upsert=True)
        return True
    except Exception as e:
        print(f"DB Error: {e}")
        return False

# -----------------------------------------------------------------------------
# 4. AUTHENTICATION & SESSION SETUP
# -----------------------------------------------------------------------------

# Initialize Session State Variables
if 'mongo_user' not in st.session_state:
    st.session_state.mongo_user = None
if 'processing_complete' not in st.session_state:
    st.session_state.processing_complete = False
if 'claim_data' not in st.session_state:
    st.session_state.claim_data = {}
if 'report_path' not in st.session_state:
    st.session_state.report_path = None
if 'form_path' not in st.session_state:
    st.session_state.form_path = None

# --- AUTH LOGIC (Using st.login / st.user) ---
# Note: st.login is available in newer Streamlit versions or specific environments.
# If running locally without ID provider config, this might default or require secrets.
if hasattr(st, "user"):
    google_user = st.user
else:
    # Fallback for older versions if needed, though prompt implies new version
    google_user = None 

if not google_user or not google_user.get("email"):
    # --- SCENARIO 1: NOT LOGGED IN ---
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=80)
        st.markdown("<h2 style='text-align: center;'>Viksit Kisan</h2>", unsafe_allow_html=True)
        st.write("")
        st.info("Please log in to continue.")
        
        if st.button("Login with Google"):
            if hasattr(st, "login"):
                st.login(provider="google")
            else:
                st.error("Login feature not available in this version.")
            
else:
    # --- SCENARIO 2: GOOGLE AUTH SUCCESS ---
    user_email = google_user.get("email")
    
    # Check if they exist in OUR MongoDB
    if st.session_state.mongo_user is None:
        db_user = check_user_db(user_email, type="email")
        
        if db_user:
            # User exists in DB -> Load into session
            st.session_state.mongo_user = db_user
            st.rerun() 
        else:
            # User NOT in DB -> Trigger Registration
            st.session_state.show_register = True

    # -------------------------------------------------------------------------
    # 5. REGISTRATION SCREEN (If Google Auth passed but DB failed)
    # -------------------------------------------------------------------------
    if st.session_state.get('show_register', False) and not st.session_state.mongo_user:
        
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            st.markdown("### 📝 Complete Your Profile")
            st.info(f"Welcome! Please finish setting up your account for **{user_email}**.")
            
            with st.form("reg_form"):
                fname = st.text_input("Full Name (शेतकऱ्याचे नाव)")
                village = st.text_input("Village (गाव)")
                taluka = st.text_input("Taluka (तालुका)")
                district = st.text_input("District (जिल्हा)")
                mob = st.text_input("Mobile Number", max_chars=10)
                bank_account_number = st.text_input("Bank Account No.", max_chars=12)
                bank_name = st.text_input("Bank Name")
                
                # Display Email (Locked)
                st.text_input("Email", value=user_email, disabled=True)
                
                if st.form_submit_button("Save & Continue"):
                    if fname and mob and village:
                        clean_mob = clean_mobile_number(mob)
                        new_user = {
                            "farmer_full_name": fname,
                            "address_village": village,
                            "address_taluka": taluka,
                            "address_district": district,
                            "mobile_number": clean_mob,
                            "email": user_email,
                            "bank_account_number": bank_account_number,
                            "bank_name": bank_name
                        }
                        
                        if register_user_db(new_user):
                            st.session_state.mongo_user = new_user
                            st.session_state.show_register = False
                            st.success("Profile Saved!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Database Error.")
                    else:
                        st.warning("All fields are mandatory.")
            
            if st.button("Logout"):
                if hasattr(st, "logout"): st.logout()

    # -------------------------------------------------------------------------
    # 6. MAIN DASHBOARD (Only if Mongo User is Loaded)
    # -------------------------------------------------------------------------
    elif st.session_state.mongo_user:
        
        # --- HEADER ---
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

        # --- HERO ---
        st.markdown(f"### 👋 Namaskar, {st.session_state.mongo_user.get('farmer_full_name', '').split()[0]}")
        st.caption("Press the microphone and speak in Marathi (e.g., 'Garpit jhala')")
        audio_input = st.audio_input("Record Voice Explanation")

        # --- EVIDENCE UPLOADS ---
        st.markdown("#### 📸 Upload Evidence")
        col_left, col_right = st.columns(2)
        with col_left:
            st.info("📄 **7/12 Extract**")
            land_file = st.file_uploader("Upload 7/12 (PDF/Img)", type=['pdf', 'jpg', 'png', 'jpeg'], key="land")
        with col_right:
            st.info("🌱 **Crop Photo**")
            crop_image = st.file_uploader("Upload Crop Photo", type=['jpg', 'png', 'jpeg'], key="crop")

        # --- PROCESSING LOGIC ---
        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("🚀 Submit Claim (Arj Kara)"):
            
            # 1. Validation
            if not (audio_input and land_file and crop_image):
                st.error("⚠️ Please provide Audio, 7/12 Extract, and Crop Photo.")
                st.session_state.processing_complete = False
            else:
                # 2. Reset Previous State
                st.session_state.processing_complete = False
                st.session_state.claim_data = {}
                st.session_state.report_path = None
                st.session_state.form_path = None

                with st.status("🔄 AI Agent Working...", expanded=True) as status:
                    try:
                        st.write("🎧 Sending Voice & Data to Gemini...")
                        user_mobile = st.session_state.mongo_user.get("mobile_number", "9922001122")

                        # 3. Call AI Engine
                        ai_result = process_claim(
                            audio_file=audio_input, 
                            land_file=land_file,    
                            crop_file=crop_image,   
                            mobile_number=user_mobile
                        )
                        
                        if ai_result.get("status") == "success":
                            
                            # Extract Data
                            full_report_data = ai_result.get("full_report_data", {}) 
                            final_data = ai_result.get("data", {})
                            app_id = final_data.get("application_id", "PENDING")
                            
                            # 4. Generate Files (The missing piece in your previous code)
                            
                            # A. Save Temp Image for Report
                            temp_img_path = f"temp_crop_{user_mobile}.jpg"
                            with open(temp_img_path, "wb") as f:
                                f.write(crop_image.getvalue())

                            # B. Generate Intelligence Report PDF
                            st.write("📊 Generating Intelligence Report...")
                            report_pdf_path = generate_best_report(
                                json_data=full_report_data, 
                                image_path=temp_img_path, 
                                output_filename=f"Report_{app_id}.pdf"
                            )

                            # C. Generate Application Form PDF
                            st.write("✍️ Generating Official Application...")
                            pdf_input_data = {"form_fields": final_data}
                            final_pdf_path = generate_filled_pdf(
                                pdf_input_data, 
                                output_path=f"Claim_{app_id}.pdf"
                            )

                            # Cleanup Temp Image
                            if os.path.exists(temp_img_path):
                                os.remove(temp_img_path)

                            # 5. Update Session State (Persistence)
                            st.session_state.claim_data = ai_result
                            st.session_state.report_path = report_pdf_path
                            st.session_state.form_path = final_pdf_path
                            st.session_state.processing_complete = True
                            
                            status.update(label="✅ Claim Processed Successfully!", state="complete", expanded=False)
                            st.balloons()

                        else:
                            st.error(f"Claim Rejected: {ai_result.get('reason', 'Unknown Error')}")
                            
                    except Exception as e:
                        st.error(f"Critical System Error: {e}")

        # --- DISPLAY RESULTS (Persistent Block) ---
        # This runs on every re-run if processing_complete is True
        if st.session_state.processing_complete:
            
            res_data = st.session_state.claim_data.get('data', {})
            voice_msg = st.session_state.claim_data.get('voice_response', '')
            app_id = res_data.get("application_id", "NA")
            payout = res_data.get("estimated_payout", "Calculating...")

            # 1. Success Card
            st.markdown(f"""
            <div class="css-card">
                <h3 style="color: #2E7D32; margin-top: 0;">✅ Application Generated</h3>
                <p><b>Application ID:</b> {app_id}</p>
                <p><b>Estimated Payout:</b> <span style="color: #2E7D32; font-size: 1.2em; font-weight: bold;">{payout}</span></p>
                <p><b>Status:</b> Auto-Verified by AI Talathi</p>
                <hr>
                <p><i>"{voice_msg}"</i></p>
            </div>
            """, unsafe_allow_html=True)

            # 2. Download Buttons
            col_d1, col_d2 = st.columns(2)
            
            with col_d1:
                r_path = st.session_state.report_path
                if r_path and os.path.exists(r_path):
                    with open(r_path, "rb") as f:
                        st.download_button(
                            label="📊 Download Intelligence Report",
                            data=f,
                            file_name=os.path.basename(r_path),
                            mime="application/pdf",
                            key="btn_report_dl"
                        )
                else:
                    st.warning("Report PDF not found.")

            with col_d2:
                f_path = st.session_state.form_path
                if f_path and os.path.exists(f_path):
                    with open(f_path, "rb") as f:
                        st.download_button(
                            label="📄 Download Application PDF",
                            data=f,
                            file_name=os.path.basename(f_path),
                            mime="application/pdf",
                            key="btn_app_dl"
                        )
                else:
                    st.warning("Form PDF not found.")

        # --- LOGOUT ---
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Logout", type="secondary"):
            if hasattr(st, "logout"):
                st.logout()
            else:
                # Manual session clear fallback
                st.session_state.mongo_user = None
                st.session_state.processing_complete = False
                st.rerun()
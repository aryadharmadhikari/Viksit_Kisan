import streamlit as st
import time
from pdf_generator import generate_filled_pdf
from agent_engine import process_claim # Import the AI Brain
import os
import json
from report_gen import generate_best_report  # <--- ADD THIS LINE
# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION (Must be the first command)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Viksit Kisan",
    page_icon="🌾",
    layout="centered", # vital for mobile look
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
# 3. HEADER SECTION ("The Badge of Trust")
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/9623/9623631.png", width=60)

with col2:
    st.markdown("""
        <div style='text-align: right; padding-top: 15px; color: #555;'>
            <span class='live-dot'></span>
            <small><b>GOVT SERVER: CONNECTED</b></small>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 4. HERO SECTION ("The Panic Button")
# -----------------------------------------------------------------------------
st.markdown("### 👋 Ramdas Bhau, kay jhal?")
st.caption("Press the microphone and speak in Marathi (e.g., 'Garpit jhala')")

# The Audio Input
audio_input = st.audio_input("Record Voice Explanation")

# -----------------------------------------------------------------------------
# 5. EVIDENCE SECTION ("The Digital Talathi")
# -----------------------------------------------------------------------------
st.markdown("#### 📸 Upload Evidence")

# Two columns for uploads
col_left, col_right = st.columns(2)

with col_left:
    st.info("📄 **7/12 Extract**")
    # CHANGED: Accepts PDF (preferred) or Image
    land_file = st.file_uploader("Upload 7/12", type=['pdf', 'jpg', 'png', 'jpeg'], key="land")

with col_right:
    st.info("🌱 **Crop Photo**")
    crop_image = st.file_uploader("Upload Photo", type=['jpg', 'png', 'jpeg'], key="crop")

# -----------------------------------------------------------------------------
# 6. ACTION & PROCESSING ("The Transparency Window")
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

# The "Trigger"
if st.button("🚀 File Claim (Arj Kara)"):
    
    # 6A. VALIDATION
    if not audio_input:
        st.error("⚠️ Please record your voice first.")
    elif not land_file:
        st.error("⚠️ Please upload the 7/12 Extract.")
    elif not crop_image:
        st.error("⚠️ Please upload a photo of the damaged crop.")
    else:
        # 6B. THE "TRANSPARENCY WINDOW" (Progress Bar)
        with st.status("🔄 AI Agent Working...", expanded=True) as status:
            
            st.write("🎧 Sending Voice & Data to Gemini...")

            final_data = {}
            
            # --- CALL THE AI ENGINE ---
            try:
                # UPDATED CALL: Passing all 3 files
                ai_result = process_claim(
                    audio_file=audio_input, 
                    land_file=land_file,    # The PDF/Image from Column 1
                    crop_file=crop_image,   # The Photo from Column 2
                    mobile_number="9922001122"
                )
                
                if ai_result.get("status") == "success":

                    # 1. EXTRACT DATA FOR REPORT
                    full_report_data = ai_result.get("full_report_data", {}) 
                    app_id = final_data.get("application_id", "PENDING")

                    # 2. SAVE TEMP IMAGE (Required for the Report Generator)
                    temp_img_path = "temp_crop_evidence.jpg"
                    with open(temp_img_path, "wb") as f:
                        f.write(crop_image.getvalue())

                    # 3. GENERATE THE NEW INTELLIGENCE REPORT
                    report_pdf_path = generate_best_report(
                        json_data=full_report_data, 
                        image_path=temp_img_path, 
                        output_filename=f"Report_{app_id}.pdf"
                    )

                    # ... (Your existing code generates the Application Form here) ...
                    
                    # 4. ADD THE DOWNLOAD BUTTON (Place this next to your existing button)
                    if report_pdf_path and os.path.exists(report_pdf_path):
                        with open(report_pdf_path, "rb") as f:
                            st.download_button(
                                label="📊 Download Intelligence Report",
                                data=f,
                                file_name=f"Report_{app_id}.pdf",
                                mime="application/pdf",
                                key="btn_report"
                            )
                    
                    # Cleanup Temp Image
                    if os.path.exists(temp_img_path):
                        os.remove(temp_img_path)
                    
                    st.write("👁️ Analyzing Evidence & Checking 7/12...")
                    final_data = ai_result.get("data", {})
                    voice_response = ai_result.get("voice_response", "Claim Processed.")
                    
                    # Wrap it for the PDF generator
                    pdf_input_data = {"form_fields": final_data}
                    
                    st.write("✍️ Generating Official Application...")
                    
                    # GENERATE PDF
                    final_pdf_path = generate_filled_pdf(pdf_input_data, output_path="Ramdas_Claim_Final.pdf")
                    
                    status.update(label="✅ Claim Processed Successfully!", state="complete", expanded=False)
                    
                    # -----------------------------------------------------------------------------
                    # 7. THE RESULT CARD ("The Winning Moment")
                    # -----------------------------------------------------------------------------
                    st.balloons()
                    
                    # --- DYNAMIC SUCCESS CARD ---
                    payout = final_data.get("estimated_payout", "Calculating...")
                    app_id = final_data.get("application_id", "PENDING")
                    
                    st.markdown(f"""
                    <div class="css-card">
                        <h3 style="color: #2E7D32; margin-top: 0;">✅ Application Generated</h3>
                        <p><b>Application ID:</b> {app_id}</p>
                        <p><b>Estimated Payout:</b> <span style="color: #2E7D32; font-size: 1.2em; font-weight: bold;">{payout}</span></p>
                        <p><b>Status:</b> Auto-Verified by AI Talathi</p>
                        <hr>
                        <p><i>"{voice_response}"</i></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 7B. DOWNLOAD BUTTON
                    if final_pdf_path and os.path.exists(final_pdf_path):
                        with open(final_pdf_path, "rb") as f:
                            st.download_button(
                                label="📄 Download Official Application PDF",
                                data=f,
                                file_name=f"Claim_{app_id}.pdf",
                                mime="application/pdf"
                            )
                    else:
                        st.error("Error: PDF File not generated.")
                        
                else:
                    # AI Returned Error (e.g., Image Rejected)
                    status.update(label="❌ Verification Failed", state="error")
                    st.error(f"Claim Rejected: {ai_result.get('reason', 'Unknown Error')}")
                    
            except Exception as e:
                status.update(label="❌ System Error", state="error")
                st.error(f"Critical Error: {e}")
import streamlit as st
import time

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
        color: white;
        font-size: 18px;
        font-weight: 600;
        border-radius: 10px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #1B5E20;
        color: white;
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
    
    /* HEADERS */
    h1, h2, h3 {
        color: #2E7D32;
        font-family: 'Helvetica', sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. HEADER SECTION ("The Badge of Trust")
# -----------------------------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    # Uses a web icon so it doesn't crash if you don't have logo.png yet
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

# The Audio Input (New in Streamlit 1.40+)
audio_input = st.audio_input("Record Voice Explanation")

# -----------------------------------------------------------------------------
# 5. EVIDENCE SECTION ("The Digital Talathi")
# -----------------------------------------------------------------------------
st.markdown("#### 📸 Upload Evidence")

# Two columns for uploads
col_left, col_right = st.columns(2)

with col_left:
    st.info("📄 **7/12 Extract**")
    land_image = st.file_uploader("Upload 7/12", type=['jpg', 'png', 'jpeg'], key="land")

with col_right:
    st.info("🌱 **Crop Photo**")
    crop_image = st.file_uploader("Upload Crop", type=['jpg', 'png', 'jpeg'], key="crop")

# -----------------------------------------------------------------------------
# 6. ACTION & PROCESSING ("The Transparency Window")
# -----------------------------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)

# The "Trigger"
if st.button("🚀 File Claim (Arj Kara)"):
    
    # 6A. VALIDATION
    if not audio_input:
        st.error("⚠️ Please record your voice first.")
    elif not land_image:
        st.error("⚠️ Please upload the 7/12 Extract.")
    else:
        # 6B. THE "TRANSPARENCY WINDOW" (Progress Bar)
        # This replaces the spinning circle with meaningful steps
        with st.status("🔄 AI Agent Working...", expanded=True) as status:
            
            st.write("🎧 Transcribing Varhadi dialect...")
            time.sleep(1.5) # Mock delay
            
            st.write("👁️ Reading 7/12 Extract (Survey No)...")
            time.sleep(1.5)
            
            st.write("⚖️ Checking PMFBY 72-Hour Rule...")
            time.sleep(1.0)
            
            st.write("✍️ Filling Government PDF Form...")
            time.sleep(1.0)
            
            status.update(label="✅ Claim Processed Successfully!", state="complete", expanded=False)

        # -----------------------------------------------------------------------------
        # 7. THE RESULT CARD ("The Winning Moment")
        # -----------------------------------------------------------------------------
        st.balloons()
        
        # Success Container
        with st.container():
            st.markdown("""
            <style>
            /* 1. HIDE DEFAULT STREAMLIT ELEMENTS */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* 2. FORCE TEXT COLORS (Fixes the invisible text issue) */
            .stApp {
                background-color: #F0F2F5; /* Light Grey Background */
                color: #333333;
            }
            
            p, h1, h2, h3, h4, h5, li, div {
                color: #333333; /* Dark Grey Text */
            }

            /* 3. CARD STYLE (Neumorphism with High Contrast) */
            .css-card {
                background-color: #FFFFFF;
                padding: 25px;
                border-radius: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                margin-bottom: 20px;
                border: 1px solid #E0E0E0;
            }
            
            /* 4. EXPLICIT TEXT COLOR FOR CARDS */
            .css-card h2 { color: #2E7D32 !important; }
            .css-card p { color: #555555 !important; }
            .css-card b { color: #000000 !important; }

            /* 5. BIG GREEN BUTTONS */
            div.stButton > button {
                width: 100%;
                height: 60px;
                background-color: #2E7D32;
                color: white !important; /* Force White Text on Green Button */
                font-size: 18px;
                font-weight: 700;
                border-radius: 12px;
                border: none;
                box-shadow: 0 4px 6px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }
            div.stButton > button:hover {
                background-color: #1B5E20;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0,0,0,0.25);
            }
            div.stButton > button:active {
                transform: translateY(1px);
            }

            /* 6. STATUS DOT ANIMATION */
            @keyframes pulse {
                0% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.6; transform: scale(1.1); }
                100% { opacity: 1; transform: scale(1); }
            }
            .live-dot {
                height: 10px;
                width: 10px;
                background-color: #00C851;
                border-radius: 50%;
                display: inline-block;
                animation: pulse 2s infinite;
                margin-right: 6px;
                vertical-align: middle;
            }
            
            /* 7. UPLOAD BOX STYLING */
            [data-testid='stFileUploader'] {
                background-color: white;
                padding: 15px;
                border-radius: 10px;
                border: 1px dashed #2E7D32;
            }
            </style>
        """, unsafe_allow_html=True)

            # 7A. AUDIO CONFIRMATION (Auto-Play Logic)
            st.markdown("🔊 **Listen to Assistant:**")
            # Note: In real app, load 'response.mp3' here
            # For now, we show a dummy player
            st.audio(audio_input) # Replaying input as a placeholder for output
            
            # 7B. DOWNLOAD BUTTON (The Asset)
            # In real app, use the 'final_pdf_path' variable
            with open("app.py", "rb") as f: # Dummy file for demo
                st.download_button(
                    label="📄 Download Official Application PDF",
                    data=f,
                    file_name="Ramdas_Claim_Form.pdf",
                    mime="application/pdf"
                )
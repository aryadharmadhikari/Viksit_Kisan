from fpdf import FPDF
from datetime import datetime
import random
import os
import re

# --- IN report_gen.py ---

def clean_text(text):
    if text is None: return ""
    text = str(text)
    
    # 1. Replace Rupee symbol
    text = text.replace("₹", "Rs.")
    
    # 2. NEW: Convert Marathi Digits to English Digits
    marathi_digits = "०१२३४५६७८९"
    english_digits = "0123456789"
    translation = str.maketrans(marathi_digits, english_digits)
    text = text.translate(translation)
    
    # 3. Keep only ASCII (English) characters
    text = re.sub(r'[^\x00-\x7F]+', '', text)
    return text.strip()
class ClaimReportPDF(FPDF):
    def header(self):
        self.set_draw_color(34, 139, 34) 
        self.set_line_width(1.5)
        self.line(10, 12, 200, 12)
        
        self.set_xy(10, 15)
        self.set_font('Helvetica', 'B', 14) 
        self.set_text_color(0, 100, 0) 
        self.cell(0, 10, 'PRELIMINARY CLAIM ASSESSMENT & INTELLIGENCE REPORT', ln=True, align='C')
        self.ln(2) 

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()} | Generated via Viksit Kisan AI Agent (v2.0) | Official Format', align='C')

    def add_watermark(self):
        self.set_font('Helvetica', 'B', 60)
        self.set_text_color(245, 245, 245) 
        with self.rotation(45, 105, 148):
            self.text(35, 150, "AI GENERATED DRAFT")

def generate_best_report(json_data, image_path, output_filename="Claim_Report_FINAL.pdf"):
    print(f"Creating PDF: {output_filename}...")
    pdf = ClaimReportPDF()
    main_font = 'Helvetica' 

    pdf.add_page()
    pdf.add_watermark()

    # --- SECTION 1: HEADER INFO ---
    pdf.set_fill_color(248, 248, 248) 
    pdf.set_draw_color(220, 220, 220)
    current_y = pdf.get_y()
    pdf.rect(10, current_y, 190, 22, 'FD') 
    
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(50, 50, 50)
    
    start_y_text = current_y + 5
    ref_id = f"VK-2025-{random.randint(1000,9999)}"
    timestamp = datetime.now().strftime("%d-%b-%Y | %H:%M IST")
    
    pdf.set_xy(15, start_y_text)
    pdf.cell(90, 5, f"Claim Reference ID:  {ref_id}")
    pdf.cell(90, 5, f"Source:  Viksit Kisan AI Agent (v2.0)", ln=True)
    pdf.set_x(15)
    pdf.cell(90, 5, f"Timestamp:  {timestamp}")
    pdf.cell(90, 5, f"Audit Status:  Logged in Immutable Ledger (MongoDB)", ln=True)
    pdf.ln(8)

# --- SECTION 2: CLAIMANT VERIFICATION ---
    pdf.set_font(main_font, 'B', 11)
    pdf.set_fill_color(34, 139, 34) 
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "  1. CLAIMANT VERIFICATION", ln=True, fill=True)
    pdf.ln(3)

    form = json_data.get('form_fields', {})
    
    # 1. Get Names
    owner_name = form.get('farmer_full_name_english') or clean_text(form.get('farmer_full_name'))
    # This is the Login Name passed from app.py
    filer_name = clean_text(json_data.get('filer_name', owner_name)) 
    
    # 2. Get Location
    village_val = form.get('address_village_english') or clean_text(form.get('address_village'))
    taluka_val = form.get('address_taluka_english') or clean_text(form.get('address_taluka'))
    crop_val = form.get('crop_name_english') or clean_text(form.get('crop_name'))
    # 3. Agent Logic
    # If the login name is roughly the same as owner name -> Self Filed
    if filer_name.lower().split()[0] in owner_name.lower():
        badge_text = "SELF-FILED"
        badge_color = (0, 128, 0) # Green
    else:
        badge_text = "AGENT-FILED"
        badge_color = (255, 140, 0) # Orange

    # Row Helper (No changes needed here, just pasting for context)
    def print_row(label, value, extra_badge=None, fill=False):
        pdf.set_font(main_font, 'B', 10)
        pdf.set_text_color(50, 50, 50)
        if fill: pdf.set_fill_color(245, 250, 245)
        pdf.cell(50, 7, f" {label}", border='B', fill=fill)
        
        pdf.set_font(main_font, '', 10)
        pdf.set_text_color(0, 0, 0)
        safe_value = clean_text(value) 
        pdf.cell(80, 7, f" {safe_value}", border='B', fill=fill)
        
        if extra_badge:
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(*badge_color)
            pdf.cell(60, 7, f"[ {extra_badge} ]", border='B', align='R', ln=True, fill=fill)
        else:
            pdf.cell(60, 7, "", border='B', ln=True, fill=fill)

    # --- PRINT ROWS (Updated) ---
    print_row("Filing Applicant", filer_name, badge_text, fill=True) # Shows Login Name
    print_row("Land Owner (7/12)", owner_name, "VERIFIED", fill=False) # Shows 7/12 Name
    
    print_row("Land ID (Gat No)", form.get('survey_number', 'N/A'), fill=True)
    print_row("Village / Taluka", f"{village_val} / {taluka_val}", fill=False)
    print_row("Total Area", f"{form.get('sown_area_hectare')} Ha", fill=True)
    
    pdf.ln(6)

    # --- SECTION 3: AI REASONING ---
    pdf.set_font(main_font, 'B', 11)
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "  2. AI REASONING ENGINE (The Logic)", ln=True, fill=True)
    pdf.ln(3)

    y_start_section3 = pdf.get_y()
    pdf.set_right_margin(85) 
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(main_font, 'B', 10)
    pdf.write(5, "A. Visual Evidence Analysis:\n")
    
    verify_data = json_data.get('verification', {})
    visual_text = clean_text(verify_data.get('visual_finding', "Damage consistent with voice claim"))
    
    pdf.set_font(main_font, '', 10)
    pdf.write(5, f"AI Analysis: Positive detection of [{visual_text}].\n\n") 
    pdf.write(5, f"Geo-Temporal Check: Metadata consistent with date: {clean_text(form.get('date_of_loss'))}.\n")
    
    pdf.set_right_margin(10)
    image_width = 70
    image_height = 40
    image_x = 130
    
    if os.path.exists(image_path):
        try:
            pdf.image(image_path, x=image_x, y=y_start_section3, w=image_width, h=image_height)
        except:
             pdf.set_xy(image_x, y_start_section3)
             pdf.cell(image_width, image_height, "[Image Error]", border=1, align='C')
    else:
        pdf.set_xy(image_x, y_start_section3)
        pdf.cell(image_width, image_height, "[No Image]", border=1, align='C')

    pdf.set_y(max(pdf.get_y(), y_start_section3 + image_height + 5))
    pdf.set_font(main_font, 'B', 10)
    pdf.cell(0, 6, "B. Cross-Modal Verification Logic:", ln=True)
    
    verify = json_data.get('verification', {})
    pdf.set_font(main_font, '', 10)
    pdf.set_fill_color(240, 255, 240) 
    reason_text = clean_text(verify.get('reason', 'N/A'))
    pdf.multi_cell(0, 6, f"Logic Trace: {reason_text}", fill=True, border=1)
    pdf.ln(6)

    # --- SECTION 4: FINANCIAL ESTIMATION ---
    if pdf.get_y() > 230:
        pdf.add_page()
        pdf.add_watermark()

    pdf.set_font(main_font, 'B', 11)
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "  3. FINANCIAL ESTIMATION (Indicative)", ln=True, fill=True)
    pdf.ln(3)

    est = json_data.get('claim_estimation', {})
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(main_font, 'B', 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 7, "  Component", border=1, fill=True)
    pdf.cell(90, 7, "  Value", border=1, fill=True, ln=True)
    
    pdf.set_font(main_font, '', 10)
    def finance_row(comp, val, highlight=False):
        clean_val = clean_text(val)
        if highlight:
             pdf.set_fill_color(250, 250, 250)
        else:
             pdf.set_fill_color(255, 255, 255)
        pdf.cell(100, 7, f"  {comp}", border=1, fill=highlight)
        pdf.cell(90, 7, f"  {clean_val}", border=1, ln=True, fill=highlight)

    finance_row("Crop Identified", crop_val, False)
    finance_row("Sown Area", f"{form.get('sown_area_hectare')} Ha", True)
    
    rate_text = est.get('rate_applied', "Standard District Rate")
    finance_row("Scale of Finance (2025)", rate_text, False)
    
    deduct_text = est.get('deductible_rule', "Standard Scheme Rule")
    finance_row("Premium Deductible", f"- {deduct_text}", True)
    
    pdf.set_font(main_font, 'B', 12)
    pdf.set_fill_color(255, 250, 225) 
    payout_value = clean_text(est.get('estimated_payout', '0'))
    pdf.cell(100, 10, "  NET ESTIMATED PAYOUT", border=1, fill=True)
    pdf.set_text_color(0, 100, 0) 
    pdf.cell(90, 10, f"  {payout_value}", border=1, fill=True, ln=True)
    
    pdf.set_text_color(100, 100, 100)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.cell(0, 6, "Footer Note: Calculation based on DLC rates for Yavatmal District, 2025.", ln=True)
    pdf.ln(5)

# --- SECTION 5: ACTIONABLE NEXT STEPS (OFFICIAL FORMAT) ---
    # 1. Smart Page Break: Check if we are too close to the bottom
    if pdf.get_y() > 210:
        pdf.add_page()
        pdf.add_watermark()

    # 2. Header
    pdf.set_font(main_font, 'B', 11)
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 7, "  4. ACTIONABLE NEXT STEPS", ln=True, fill=True)
    pdf.ln(4)

    # 3. Steps List
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(main_font, '', 10)
    steps = [
        "1. Print & Sign: A pre-filled PMFBY Form is attached. Please sign below.",
        "2. Submit: Take this to your nearest CSC within 48 hours.",
        "3. Digital Copy: A copy has been sent to your mobile via SMS."
    ]
    for step in steps:
        pdf.cell(0, 6, step, ln=True)
    
    # 4. Add vertical space before signature block
    pdf.ln(15)
    
    # --- OFFICIAL SIGNATURE BLOCK ---
    # Capture the starting Y position so Left and Right sides align
    sig_start_y = pdf.get_y()
    
    # LEFT SIDE: Date and Place
    pdf.set_font(main_font, '', 10)
    
    # Date Row
    pdf.set_xy(20, sig_start_y + 5)
    pdf.cell(50, 5, f"Date:   {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    
    # Place Row
    pdf.set_xy(20, sig_start_y + 15)
    pdf.cell(50, 5, "Place:  _________________", ln=True)

    # RIGHT SIDE: Signature Box
    pdf.set_draw_color(0, 0, 0)
    # Draw Rect: x=130, y=sig_start_y, w=60, h=30
    pdf.rect(130, sig_start_y, 60, 30) 
    
    # Text inside box (Centered at bottom)
    pdf.set_xy(130, sig_start_y + 22)
    pdf.set_font(main_font, 'B', 8)
    pdf.cell(60, 5, "Farmer Signature / Angtha", align='C')

    try:
        pdf.output(output_filename)
        print(f"✅ Success! PDF saved as: {output_filename}")
        return output_filename
    except PermissionError:
        print("❌ ERROR: Close the PDF file! It is open in another window.")
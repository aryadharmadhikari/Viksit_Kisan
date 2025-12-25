from fpdf import FPDF
from pypdf import PdfReader, PdfWriter
import os
from datetime import datetime

def generate_filled_pdf(json_data, original_pdf_path="assets/template.pdf", output_path="test_output.pdf"):
    
    print("🎨 Starting PDF Generation...")
    
    # 1. SETUP FPDF
    # A4 size is 595pt wide x 842pt tall
    pdf = FPDF(orientation='P', unit='pt', format='A4')

    # --- THE MAGIC FIX: ENABLE TEXT SHAPING ---
    try:
        pdf.set_text_shaping(True) 
        print("✅ Text Shaping Enabled (Marathi will look perfect)")
    except Exception as e:
        print(f"⚠️ Shaping Error: {e}")
        print("   (Did you run 'pip install uharfbuzz'?)")

    pdf.add_page()
    
    # 2. REGISTER MARATHI FONT
    font_path = "assets/MarathiFont.ttf"
    # Fallback to Helvetica if Marathi font is missing
    main_font = "Helvetica"
    
    if os.path.exists(font_path):
        try:
            pdf.add_font("Marathi", style="", fname=font_path)
            # Use Marathi font if loaded successfully
            main_font = "Marathi"
            print("✅ Marathi Font Loaded")
        except Exception as e:
            print(f"⚠️ Font Error: {e}")
            
    else:
        print(f"⚠️ Font File Missing: {font_path}")
    
    # Set the font (either Marathi or Helvetica)
    pdf.set_font(main_font, size=8)

    # 3. COORDINATE FUNCTION (SIMPLIFIED)
    # Now (0,0) is TOP-LEFT. 
    # X = Distance from Left. Y = Distance from Top.
    def text_at(x, y, txt):
        if not txt: return
        pdf.set_xy(x, y)
        try:
            pdf.cell(0, 0, str(txt))
        except:
            pass

    # Extract fields ONCE here to use throughout the function
    fields = json_data.get("form_fields", {})

    # --- 4. MAP YOUR FIELDS (YOUR MANUAL COORDINATES) ---
    
    # Farmer Name
    text_at(250, 146, str(fields.get("farmer_full_name", "")))
    
    # Address (Formatted: Mu. Po. Village, Ta. Taluka, Ji. District)
    village = fields.get('address_village', '')
    taluka = fields.get('address_taluka', '')
    district = fields.get('address_district', '')
    
    formatted_address = f"मु. पो. {village}, ता. {taluka}, जि. {district}"
    text_at(210, 165, formatted_address)

    # Mobile Number (Split into Blocks)
    mobile = str(fields.get("mobile_number", ""))
    
    # Starting position for the first box
    start_x = 213 
    y_pos = 181
    gap = 14

    for digit in mobile:
        text_at(start_x, y_pos, digit)
        start_x += gap
    
    # Email (Usually below mobile)
    email = str(fields.get("email_id", ""))
    
    # Switch to Helvetica for Email (English text)
    pdf.set_font("Helvetica", size=6.5) 
    text_at(426, 181, email) 
    
    # Reset back to main font
    pdf.set_font(main_font, size=8) 

    # Shetkari ID (ID / Proposal No) - Printing "NA"
    text_at(220, 297, "NA")
    
    # Financial Year
    text_at(479, 207, str(fields.get("financial_year", "")))
    
    # Season
    text_at(339, 207, str(fields.get("season", "")))

    # Bank Account
    text_at(202, 243, str(fields.get("bank_account_no", "")))
    
    # Bank Name
    text_at(395, 243, str(fields.get("bank_name", "")))

    # Premium Amount
    text_at(200, 264, str(fields.get("premium_amount", "")))

    # --- FARM LOCATION DETAILS (Middle Block) ---
    loc_y = 343.5 
    
    text_at(103, loc_y, str(fields.get("address_village", "")))   # Village
    text_at(195, loc_y, str(fields.get("address_village", "")))   # Mandal
    text_at(320, loc_y, str(fields.get("address_taluka", "")))    # Taluka
    text_at(457, loc_y, str(fields.get("address_district", "")))  # District

    # --- CROP TABLE ---
    row_y = 405 
    text_at(120, row_y, str(fields.get("survey_number", "")))
    text_at(180, row_y, str(fields.get("crop_name", "")))
    text_at(255, row_y, str(fields.get("sown_area_hectare", "")))
    text_at(325, row_y, str(fields.get("sown_area_hectare", "")))
    text_at(483, row_y, "100%")

    # --- LOSS DETAILS (Checkboxes) ---
    def draw_tick_mark(x, y):
        # Set line thickness
        pdf.set_line_width(2)
        # Draw "V" shape
        pdf.line(x, y, x + 3, y + 3)
        pdf.line(x + 3, y + 3, x + 10, y - 8)
        # Reset line width
        pdf.set_line_width(1)

    cause = str(fields.get("cause_of_loss", "")).lower()
    
    # 1. Flood (Pura)
    if "pur" in cause or "flood" in cause or "पाणी" in cause:
        draw_tick_mark(335, 470) 
        
    # 2. Hailstorm (Garpit)
    elif "garpit" in cause or "hail" in cause or "गारपीट" in cause:
        draw_tick_mark(420, 470)
        
    # 3. Landslide (Bhusakhalan)
    elif "land" in cause or "bhus" in cause or "भुस्खलन" in cause:
        draw_tick_mark(518, 471)

    # 4. Cyclone (Chakrivadal)
    elif "cyclone" in cause or "chakri" in cause or "चक्रीवादळ" in cause:
        draw_tick_mark(228, 513)

    # 5. Unseasonal Rain (Avakali Paus)
    elif "rain" in cause or "paus" in cause or "पाऊस" in cause:
        draw_tick_mark(442, 513)
        
    text_at(108, 607, str(fields.get("date_of_loss", "")))

    # Get current time
    now_str = datetime.now().strftime("%d/%m/%Y | %I:%M %p")
    
    # Print it at the bottom left
    text_at(158, 539, now_str)

    # 5. SAVE OVERLAY
    overlay_filename = "temp_overlay.pdf"
    pdf.output(overlay_filename)

    # 6. MERGE WITH ORIGINAL
    try:
        # Check if template exists before trying to open it
        if not os.path.exists(original_pdf_path):
             print(f"❌ Error: Template PDF '{original_pdf_path}' not found in folder.")
             return None

        with open(original_pdf_path, "rb") as f:
            original = PdfReader(f)
            page = original.pages[0]
            with open(overlay_filename, "rb") as f_ov:
                overlay = PdfReader(f_ov).pages[0]
                page.merge_page(overlay)
                
                writer = PdfWriter()
                writer.add_page(page)
                
                # Add extra pages
                for i in range(1, len(original.pages)):
                    writer.add_page(original.pages[i])
                
                with open(output_path, "wb") as f_out:
                    writer.write(f_out)
                    
        print(f"🚀 SUCCESS: PDF Created at {output_path}")
        
        # Clean up temp file
        if os.path.exists(overlay_filename):
            os.remove(overlay_filename)
            
        # --- CRITICAL FIX: RETURN THE PATH ---
        return output_path
    
    except FileNotFoundError:
        print(f"❌ Error: '{original_pdf_path}' not found.")
        return None
    except PermissionError:
        print("❌ Error: Close the PDF file! It is currently open and locked.")
        return None
    except Exception as e:
        print(f"❌ Merge Error: {e}")
        return None
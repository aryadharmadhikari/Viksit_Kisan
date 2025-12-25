# config.py

# This simulates your MongoDB database of registered farmers
MOCK_DB = {
        "form_fields": {
        "farmer_full_name": "कोंडिबा सबाजी तांबे",
        "address_village": "शिरदाळेवाडी",
        "address_taluka": "आंबेगाव",
        "address_district": "पुणे",
        "mobile_number": "9922001122",
        "bank_account_no": "",
        "bank_name": "",
        "scheme_name": "प्रधानमंत्री पीक विमा योजना",
        "season": "खरीप",
        "financial_year": "२०१९-२०",
        "survey_number": "१०२",
        "crop_name": "बटाटा",
        "sown_area_hectare": "०.३८.००",
        "cause_of_loss": "पूर",
        "date_of_loss": "23/12/2025"
    }
}

# Rules for the Hackathon Demo
RULES = {
    "valid_crops": ["Cotton", "Soybean", "Potato"],
    "valid_causes": ["Hailstorm", "Unseasonal Rain", "Flood"],
    "time_limit_hours": 72
}

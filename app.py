import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- 2. THE BUTLER'S CONNECTION ENGINE ---
@st.cache_resource
def get_gspread_client():
    """
    Manually connects to Google Sheets by fixing the Secret Key formatting.
    This bypasses the buggy Streamlit GSheets wrapper.
    """
    try:
        # Grab secrets from the [connections.gsheets] section
        info = st.secrets["connections"]["gsheets"].to_dict()
        
        # THE FIX: Replace text "\n" with real newlines so Google can read it
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace("\\n", "\n")
        
        # Define the access levels (scopes)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # Create credentials and authorize gspread
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"⚠️ Butler Connection Error: {e}")
        return None

# --- 3. INITIALIZE ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")
client = get_gspread_client()

# --- 4. UI ---
st.title("🍷 Hedrick Wine Butler")
st.markdown("### *Your cellar assistant is ready.*")

# Image Inputs
cam = st.camera_input("📸 Scan Label")
upload = st.file_uploader("📂 Or Upload", type=['jpg', 'png', 'jpeg'])
img_file = cam if cam else upload

st.write("---")
rating = st.feedback("stars")

if st.button("Consult the Butler", type="primary"):
    if img_file and client:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                # 1. Open the Spreadsheet
                sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
                sheet = client.open_by_url(sheet_url).sheet1
                
                # 2. Process Image with Gemini
                img = Image.open(img_file)
                prompt = """
                Analyze this wine label. Return ONLY a JSON object: 
                {"Winery": str, "Wine_Name": str, "Vintage": str, "Varietal": str, "Region": str, "Butler_Comment": str}
                """
                response = model.generate_content([prompt, img])
                
                # Clean Gemini's JSON response
                res_text = response.text.strip()
                if "```json" in res_text:
                    res_text = res_text.split("```json")[1].split("```")[0]
                elif "```" in res_text:
                    res_text = res_text.split("```")[1].split("```")[0]
                
                data = json.loads(res_text.strip())
                
                # --- 5. DISPLAY RESULTS ---
                st.subheader(f"{data.get('Winery')} - {data.get('Wine_Name')}")
                st.markdown(f"**Vintage:** {data.get('Vintage')} | **Region:** {data.get('Region')}")
                st.info(data.get('Butler_Comment'))
                
                # --- 6. SAVE TO SHEET ---
                # This matches your screenshot headers exactly
                new_row = [
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    data.get("Winery"),
                    data.get("Wine_Name"),
                    data.get("Vintage"),
                    data.get("Varietal"),
                    data.get("Region"),
                    (rating + 1) if rating is not None else 0,
                    data.get("Butler_Comment")
                ]
                
                sheet.append_row(new_row)
                
                st.success("The Butler has recorded this in your Cellar Book!")
                st.toast("Cellar updated.", icon="🍷")
                
            except Exception as e:
                st.error(f"The Butler encountered an issue: {e}")
    elif not client:
        st.error("Butler could not connect. Check your Secrets formatting.")
    else:
        st.warning("Please provide an image.")

st.caption("Hedrick Wine Butler | v1.6 (Stable)")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- 1. THE BUTLER'S REPAIR KIT ---
def get_cleaned_connection():
    """
    Fixes the PEM formatting and passes credentials in the 
    one format the GSheets library actually accepts.
    """
    # Get the secrets
    gs_creds = st.secrets["connections"]["gsheets"].to_dict()
    
    # Fix the PEM formatting (replaces text '\n' with real newlines)
    if "private_key" in gs_creds:
        gs_creds["private_key"] = gs_creds["private_key"].replace("\\n", "\n")
    
    # Create the service_account_info dictionary
    # This is the standard format Google expects
    service_account_info = {
        "type": gs_creds.get("type", "service_account"),
        "project_id": gs_creds.get("project_id"),
        "private_key_id": gs_creds.get("private_key_id"),
        "private_key": gs_creds.get("private_key"),
        "client_email": gs_creds.get("client_email"),
        "client_id": gs_creds.get("client_id"),
        "auth_uri": gs_creds.get("auth_uri"),
        "token_uri": gs_creds.get("token_uri"),
        "auth_provider_x509_cert_url": gs_creds.get("auth_provider_x509_cert_url"),
        "client_x509_cert_url": gs_creds.get("client_x509_cert_url"),
    }
        
    # Pass it as ONE single argument called service_account_info
    return st.connection("gsheets", type=GSheetsConnection, service_account_info=service_account_info)

# --- 2. CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")
SHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]

# --- 3. CONNECTIONS ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

try:
    conn = get_cleaned_connection()
except Exception as e:
    st.error(f"⚠️ Butler Connection Error: {e}")
    st.stop()

# --- 4. UI ---
st.title("🍷 Hedrick Wine Butler")
st.markdown("### *Your cellar assistant is ready.*")

cam = st.camera_input("📸 Scan Label")
upload = st.file_uploader("📂 Or Upload", type=['jpg','png','jpeg'])
img_file = cam if cam else upload

st.write("---")
rating = st.feedback("stars")

if st.button("Consult the Butler", type="primary"):
    if img_file:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                img = Image.open(img_file)
                # We tell Gemini to use the exact names of your Sheet columns
                prompt = """
                Analyze this wine label. Return ONLY a JSON object: 
                {"Winery": str, "Wine_Name": str, "Vintage": str, "Varietal": str, "Region": str, "Butler_Comment": str}
                Be sophisticated and witty in the Butler_Comment.
                """
                
                response = model.generate_content([prompt, img])
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
                
                # --- 5. DISPLAY RESULTS ---
                st.subheader(f"{data.get('Winery')} - {data.get('Wine_Name')}")
                st.info(data.get('Butler_Comment'))
                
                # --- 6. SAVE TO SHEET ---
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get('Winery'),
                    "Wine_Name": data.get('Wine_Name'),
                    "Vintage": data.get('Vintage'),
                    "Varietal": data.get('Varietal'),
                    "Region": data.get('Region'),
                    "User_Rating": rating + 1 if rating is not None else 0,
                    "Butler_Comment": data.get('Butler_Comment')
                }])
                
                # Use the SHEET_URL to read and update
                df = conn.read(spreadsheet=SHEET_URL, ttl=0)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                
                st.success("Entry saved to the Hedrick Cellar Book!")
                st.toast("Cellar updated.", icon="🍷")
                
            except Exception as e:
                st.error(f"The Butler encountered an error: {e}")
    else:
        st.warning("Please provide an image.")

st.caption("Hedrick Wine Butler v1.3")

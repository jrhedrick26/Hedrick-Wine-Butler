import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- 1. THE BUTLER'S REPAIR KIT ---
def get_cleaned_connection():
    # 1. Get the gsheets secrets into a dictionary
    gs_creds = st.secrets["connections"]["gsheets"].to_dict()
    
    # 2. Fix the PEM formatting (\n issues)
    if "private_key" in gs_creds:
        gs_creds["private_key"] = gs_creds["private_key"].replace("\\n", "\n")
    
    # 3. List of keys that Google Service Accounts actually want
    # We remove 'spreadsheet' and 'type' because they aren't part of the 
    # official Google credential format and cause errors in st.connection
    valid_keys = [
        "project_id", "private_key_id", "private_key", 
        "client_email", "client_id", "auth_uri", "token_uri", 
        "auth_provider_x509_cert_url", "client_x509_cert_url"
    ]
    
    # Create a clean dictionary with ONLY the valid keys
    clean_creds = {k: gs_creds[k] for k in valid_keys if k in gs_creds}
        
    # 4. Initialize connection with ONLY the clean service account credentials
    return st.connection("gsheets", type=GSheetsConnection, **clean_creds)

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
                prompt = 'Return ONLY a JSON object: {"winery": str, "wine_name": str, "vintage": str, "varietal": str, "region": str, "butler_comment": str}'
                
                response = model.generate_content([prompt, img])
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
                
                # --- 5. DISPLAY RESULTS ---
                st.subheader(f"{data.get('winery')} - {data.get('wine_name')}")
                st.info(data.get('butler_comment'))
                
                # --- 6. SAVE TO SHEET ---
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get('winery'),
                    "Wine": data.get('wine_name'),
                    "Rating": rating + 1 if rating is not None else 0,
                    "Comment": data.get('butler_comment')
                }])
                
                # We pass the SHEET_URL directly here to avoid the connection error
                df = conn.read(spreadsheet=SHEET_URL, ttl=0)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                
                conn.update(spreadsheet=SHEET_URL, data=updated_df)
                
                st.success("Entry saved to the Hedrick Cellar Book!")
                st.toast("Cellar updated.", icon="🍷")
                
            except Exception as e:
                st.error(f"The Butler encountered an error: {e}")
    else:
        st.warning("Please provide an image.")

st.caption("Hedrick Wine Butler v1.2")

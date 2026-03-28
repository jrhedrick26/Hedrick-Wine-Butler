import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- 1. THE BUTLER'S REPAIR KIT (Fixes the PEM Error) ---
def fix_private_key(key):
    # This converts literal "\n" text into actual line breaks
    return key.replace("\\n", "\n")

# --- 2. CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- 3. CONNECTIONS ---
# Initialize Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize GSheets with Self-Healing Secrets
try:
    # Create a copy of secrets to modify for the connection
    secrets_dict = st.secrets.to_dict()
    # Apply the fix to the private_key
    raw_key = secrets_dict["connections"]["gsheets"]["private_key"]
    secrets_dict["connections"]["gsheets"]["private_key"] = fix_private_key(raw_key)
    
    # Connect using the fixed credentials
    conn = st.connection("gsheets", type=GSheetsConnection, **secrets_dict["connections"]["gsheets"])
except Exception as e:
    st.error(f"⚠️ Butler Connection Error: {e}")

# --- 4. UI ---
st.title("🍷 Hedrick Wine Butler")
st.write("Take a photo of a wine label and I shall record it for you.")

cam = st.camera_input("Scan Label")
upload = st.file_uploader("Or Upload", type=['jpg','png','jpeg'])
img_file = cam if cam else upload

rating = st.feedback("stars")

if st.button("Consult the Butler", type="primary"):
    if img_file:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                img = Image.open(img_file)
                prompt = "Return ONLY a JSON object: winery, wine_name, vintage, varietal, region, butler_comment. Be sophisticated."
                
                response = model.generate_content([prompt, img])
                
                # Clean JSON response
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
                
                # Display Results
                st.subheader(f"{data.get('winery')} - {data.get('wine_name')}")
                st.markdown(data.get('butler_comment'))
                
                # Save to Sheet
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get('winery'),
                    "Wine": data.get('wine_name'),
                    "Rating": rating + 1 if rating is not None else 0,
                    "Comment": data.get('butler_comment')
                }])
                
                # Read, Append, Update
                df = conn.read()
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Entry saved to the Hedrick Cellar Book!")
                
            except Exception as e:
                st.error(f"The Butler encountered an error during analysis: {e}")
    else:
        st.warning("Please provide an image.")

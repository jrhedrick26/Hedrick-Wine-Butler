import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- CONNECTIONS ---
# Initialize Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash") # 1.5-flash is extremely stable

# Initialize GSheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"The Butler is having trouble accessing the cellar book. Check your Secrets formatting. Error: {e}")

# --- UI ---
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
                prompt = "Return JSON: winery, wine_name, vintage, varietal, region, general_profile, suggested_pairing, butler_comment. Be sophisticated."
                
                # Use standard generation
                response = model.generate_content([prompt, img])
                
                # Clean JSON response (sometimes Gemini adds ```json tags)
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(clean_text)
                
                # Display Results
                st.subheader(f"{data.get('winery')} - {data.get('wine_name')}")
                st.info(data.get('butler_comment'))
                
                # Save to Sheet
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get('winery'),
                    "Wine": data.get('wine_name'),
                    "Rating": rating + 1 if rating is not None else 0,
                    "Comment": data.get('butler_comment')
                }])
                
                df = conn.read()
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Entry saved to the Hedrick Cellar Book!")
                
            except Exception as e:
                st.error(f"The Butler encountered an error: {e}")
    else:
        st.warning("Please provide an image.")

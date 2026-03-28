import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- 1. CONFIG ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- 2. CONNECTIONS ---
# Initialize Gemini
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# Initialize GSheets
# We call it simply. The library will look for [connections.gsheets] in secrets.
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"The Butler can't find the cellar book: {e}")

# --- 3. UI ---
st.title("🍷 Hedrick Wine Butler")
st.markdown("### *At your service for the Hedrick Cellar.*")

cam = st.camera_input("📸 Scan Label")
upload = st.file_uploader("📂 Or Upload", type=['jpg', 'png', 'jpeg'])
img_file = cam if cam else upload

st.write("---")
# User feedback returns 0-4 stars, we add 1 to make it 1-5
rating = st.feedback("stars")

if st.button("Consult the Butler", type="primary"):
    if img_file:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                # Process Image
                img = Image.open(img_file)
                
                # Holistic Prompting: Clearer instructions for Gemini
                prompt = """
                Identify this wine. Return ONLY a JSON object with these keys:
                "Winery", "Wine_Name", "Vintage", "Varietal", "Region", "Butler_Comment"
                The Butler_Comment should be sophisticated, witty, and mention a food pairing.
                """
                
                response = model.generate_content([prompt, img])
                
                # Holistic JSON Cleaning: Removes markdown backticks if Gemini adds them
                raw_text = response.text
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                
                data = json.loads(raw_text.strip())
                
                # --- 4. DISPLAY RESULTS ---
                st.subheader(f"{data.get('Winery')} - {data.get('Wine_Name')}")
                st.markdown(f"**Vintage:** {data.get('Vintage')} | **Region:** {data.get('Region')}")
                st.info(data.get('Butler_Comment'))
                
                # --- 5. SAVE TO SHEET ---
                # We create the row using the exact column names from your screenshot
                new_row = pd.DataFrame([{
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Winery": data.get('Winery'),
                    "Wine_Name": data.get('Wine_Name'),
                    "Vintage": data.get('Vintage'),
                    "Varietal": data.get('Varietal'),
                    "Region": data.get('Region'),
                    "User_Rating": (rating + 1) if rating is not None else 0,
                    "Butler_Comment": data.get('Butler_Comment')
                }])
                
                # Read existing data (ttl=0 ensures we don't get a cached version)
                existing_df = conn.read(ttl=0)
                
                # Combine and Update
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success("The Butler has recorded this in your Cellar Book!")
                st.toast("Cellar updated.", icon="🍷")
                
            except Exception as e:
                st.error(f"The Butler encountered an issue: {e}")
    else:
        st.warning("Please provide a label for the Butler to inspect.")

st.caption("Hedrick Wine Butler | v1.4")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image

# --- PAGE SETUP ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷")

# --- STYLE ---
st.markdown("<style>.stApp {background-color: #fcfaf7;}</style>", unsafe_allow_html=True)

# --- CONNECTIONS ---
# These look for secrets in the Streamlit Cloud dashboard automatically
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash") # Use 1.5-flash for reliability
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🍷 Hedrick Wine Butler")

# --- INPUTS ---
col1, col2 = st.columns(2)
with col1:
    img_file = st.camera_input("Take Photo")
with col2:
    img_upload = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

rating = st.feedback("stars")
input_img = img_file if img_file else img_upload

# --- LOGIC ---
if st.button("Consult the Butler", type="primary"):
    if input_img:
        with st.spinner("The Butler is reviewing the label..."):
            try:
                img = Image.open(input_img)
                prompt = """Analyze this wine label. Return ONLY a JSON object:
                {"Error_Flag": bool, "Error_Message": str, "Winery": str, "Wine_Name": str, 
                "Vintage": str, "Varietal": str, "Region": str, "General_Profile": str, 
                "Suggested_Pairing": str, "Butler_Comment": str}"""
                
                response = model.generate_content([prompt, img])
                data = json.loads(response.text)

                if data.get("Error_Flag"):
                    st.error(data["Error_Message"])
                else:
                    st.subheader(f"{data['Winery']} {data['Wine_Name']}")
                    st.write(data['Butler_Comment'])
                    
                    # Save to Google Sheet
                    new_data = pd.DataFrame([{
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Winery": data['Winery'],
                        "Wine": data['Wine_Name'],
                        "Rating": rating + 1 if rating is not None else 0,
                        "Comment": data['Butler_Comment']
                    }])
                    
                    existing_df = conn.read()
                    updated_df = pd.concat([existing_df, new_data], ignore_index=True)
                    conn.update(data=updated_df)
                    st.toast("Saved to the Cellar Book!")
            except Exception as e:
                st.error(f"Butler Error: {e}")
    else:
        st.warning("Please provide an image.")

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import io

# --- APP CONFIGURATION ---
st.set_page_config(page_title="Hedrick Wine Butler", page_icon="🍷", layout="centered")

# --- STYLING ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    .stTitle { color: #4A0E0E; font-family: 'Serif'; border-bottom: 2px solid #4A0E0E; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE CONNECTIONS & MODELS ---
# Securely fetch API Key from secrets.toml
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize Gemini 2.0 Flash
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={
        "response_mime_type": "application/json",
    }
)

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

# --- UI HEADER ---
st.title("🍷 Hedrick Wine Butler")
st.subheader("Your personal sommelier for the Hedrick Cellar")

# --- INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    cam_image = st.camera_input("Take a photo of the label")

with col2:
    file_image = st.file_uploader("Or upload from camera roll", type=['jpg', 'jpeg', 'png'])

# Prioritize camera input over file upload
input_image = cam_image if cam_image else file_image

# --- RATING SECTION ---
user_rating = st.feedback("stars") # Returns 0-4, we'll convert to 1-5
# Fallback slider if you prefer numeric: user_rating = st.slider("Rate this wine", 1, 5, 3)

# --- PROCESSING LOGIC ---
if st.button("Consult the Butler", type="primary", use_container_width=True):
    if input_image is not None:
        with st.spinner("The Butler is examining the vintage..."):
            try:
                # Convert image for Gemini API
                img = Image.open(input_image)
                
                # Prompt Construction
                prompt = """
                Analyze this wine label image. Return a JSON object with the following schema:
                {
                    "Error_Flag": bool,
                    "Error_Message": str,
                    "Winery": str,
                    "Wine_Name": str,
                    "Vintage": str,
                    "Varietal": str,
                    "Region": str,
                    "General_Profile": str,
                    "Suggested_Pairing": str,
                    "Butler_Comment": str
                }
                If the image is not a wine label, set Error_Flag to true and provide an Error_Message.
                The Butler_Comment should be written in a sophisticated, helpful tone, 
                using markdown bullet points for the profile and pairing.
                """

                # Call Gemini API
                response = model.generate_content([prompt, img])
                data = json.loads(response.text)

                if data.get("Error_Flag"):
                    st.error(f"The Butler apologizes: {data['Error_Message']}")
                else:
                    # --- DISPLAY RESULTS ---
                    st.success("Analysis Complete!")
                    
                    st.markdown(f"### {data['Winery']} - {data['Wine_Name']} ({data['Vintage']})")
                    st.markdown(f"**Region:** {data['Region']} | **Varietal:** {data['Varietal']}")
                    
                    st.info(data['Butler_Comment'])
                    
                    # --- DATABASE SAVE ---
                    # Prepare the row for Google Sheets
                    new_row = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Winery": data['Winery'],
                        "Wine_Name": data['Wine_Name'],
                        "Vintage": data['Vintage'],
                        "Varietal": data['Varietal'],
                        "Region": data['Region'],
                        "General_Profile": data['General_Profile'],
                        "Suggested_Pairing": data['Suggested_Pairing'],
                        "User_Rating": (user_rating + 1) if user_rating is not None else "N/A",
                        "Butler_Comment": data['Butler_Comment']
                    }
                    
                    # Read current data to append
                    existing_data = conn.read(ttl=0) # ttl=0 ensures we don't use cached data
                    updated_df = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Update Google Sheet
                    conn.update(data=updated_df)
                    
                    st.toast("Entry logged in the Hedrick Cellar Book!", icon="📖")

            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please provide an image of a wine label first.")

# --- FOOTER ---
st.caption("Powered by Gemini 2.0 Flash • Hedrick Wine Butler v1.0")
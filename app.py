import streamlit as st
from streamlit_gsheets import GSheetsConnection
import google.generativeai as genai
import pandas as pd
import json
from datetime import datetime
from PIL import Image
import io

# --- 1. APP CONFIGURATION ---
st.set_page_config(
    page_title="Hedrick Wine Butler", 
    page_icon="🍷", 
    layout="centered"
)

# Sophisticated styling
st.markdown("""
    <style>
    .main { background-color: #fcfaf7; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #4A0E0E; color: white; }
    .stTitle { color: #4A0E0E; font-family: 'Georgia', serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALIZE CONNECTIONS ---
# Configure Gemini using secrets
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Initialize Gemini 2.0 Flash (Optimized for Speed and Vision)
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"response_mime_type": "application/json"}
)

# Initialize Google Sheets Connection
# Ensure your requirements.txt has 'st-gsheets-connection'
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. UI HEADER ---
st.title("🍷 Hedrick Wine Butler")
st.markdown("### *At your service for the perfect pour.*")
st.divider()

# --- 4. INPUT SECTION ---
col1, col2 = st.columns(2)

with col1:
    cam_image = st.camera_input("📸 Take a photo of the label")

with col2:
    file_image = st.file_uploader("📂 Or upload from your phone", type=['jpg', 'jpeg', 'png'])

# Use camera input if available, otherwise use file upload
input_image = cam_image if cam_image else file_image

st.write("---")
st.write("#### How would you rate this wine?")
user_rating = st.feedback("stars") # Returns 0 to 4. We'll add 1 later for 1-5 scale.

# --- 5. PROCESSING LOGIC ---
if st.button("Consult the Butler"):
    if input_image is not None:
        with st.spinner("The Butler is examining the label..."):
            try:
                # Load the image
                img = Image.open(input_image)
                
                # Construct the sophisticated Butler prompt
                prompt = """
                You are the 'Hedrick Wine Butler', a world-class sommelier. 
                Analyze this wine label and return a JSON object with this EXACT schema:
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
                If the image is not a wine label, set Error_Flag to true. 
                In Butler_Comment, be sophisticated and use markdown bullet points for the profile and pairings.
                """

                # Call Gemini
                response = model.generate_content([prompt, img])
                data = json.loads(response.text)

                if data.get("Error_Flag"):
                    st.error(f"The Butler apologizes: {data['Error_Message']}")
                else:
                    # --- 6. DISPLAY RESULTS ---
                    st.success("The Butler has finished his assessment.")
                    
                    st.markdown(f"## {data['Winery']}")
                    st.markdown(f"### {data['Wine_Name']} ({data['Vintage']})")
                    
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Varietal", data['Varietal'])
                    with col_b:
                        st.metric("Region", data['Region'])
                    
                    st.markdown("---")
                    st.markdown(data['Butler_Comment'])
                    
                    # --- 7. DATABASE SAVE ---
                    # Prepare the data for the Google Sheet
                    # Mapping to the headers you created in Step 1
                    new_entry = {
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
                    
                    # Read current data and append
                    try:
                        existing_df = conn.read(ttl=0) # ttl=0 to avoid old cached data
                        updated_df = pd.concat([existing_df, pd.DataFrame([new_entry])], ignore_index=True)
                        
                        # Write back to Google Sheets
                        conn.update(data=updated_df)
                        st.toast("Entry safely recorded in the Cellar Book!", icon="📖")
                    except Exception as sheet_err:
                        st.error(f"Butler found the cellar book, but couldn't write in it: {sheet_err}")

            except Exception as e:
                st.error(f"A technical error occurred: {e}")
    else:
        st.warning("Please provide a label for the Butler to inspect.")

# Footer
st.caption("Hedrick Wine Butler | Powered by Gemini 2.0 Flash")
